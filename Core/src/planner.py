import uuid
import logging
import ast
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# Configure logger
logger = logging.getLogger("codeweaver-agent")

class RemediationPlan(BaseModel):
    """Model for the LLM generated remediation plan"""
    action: str = Field(description="Short description of the action (e.g. 'restart_service', 'clear_cache')")
    reason: str = Field(description="Explanation of why this fix was chosen")
    target: str = Field(description="The target service or component")
    python_script: str = Field(description="A valid, self-contained Python script to execute the fix. Must include imports.")

class SafePlanner:
    def __init__(self):
        self.llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0)
        self.parser = JsonOutputParser(pydantic_object=RemediationPlan)
        
        self.system_prompt = (
            "You are an Expert SRE Agent. Your job is to generate safe Python code to fix system incidents.\n"
            "You will be given a diagnosis of an error.\n"
            "Generate a Python script that remediates the issue.\n\n"
            "GUIDELINES:\n"
            "1. ONLY use the 'requests' library - it's pre-imported and ready to use.\n"
            "2. The target service is 'http://chaos-app:8000' (internal Docker DNS).\n"
            "3. To fix chaos/failures, POST to 'http://chaos-app:8000/chaos/resolve'.\n"
            "4. Do NOT import os, subprocess, or shutil.\n"
            "5. Return valid JSON only. Key 'python_script' must be a single string with \\n for newlines.\n"
            f"\n{self.parser.get_format_instructions()}"
        )

    def analyze_safety(self, code: str) -> tuple[bool, list[str]]:
        """
        Analyze code for safety issues.
        Returns (is_catastrophic, warnings_list)
        """
        warnings = []
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # Check imports
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    full_imports = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module]
                    for module in full_imports:
                        if module in ['subprocess', 'os']:
                            warnings.append(f"Uses {module} module (process execution)")
                        elif module in ['shutil']:
                            warnings.append(f"Uses {module} module (file operations)")
                                    
        except SyntaxError:
            return True, ["CATASTROPHIC: Invalid Python syntax"]
        
        return False, warnings

    def generate_fix(self, diagnosis: dict) -> dict:
        root_cause = diagnosis.get('root_cause')
        involved = diagnosis.get('involved_files', [])
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Diagnosis: {root_cause}\nInvolved Files: {involved}\n\nTask: Generate a Python fix using only the 'requests' library.")
        ]
        
        try:
            response = self.llm.invoke(messages)
            content = response.content
            logger.info(f"[PLANNER] Raw LLM Response:\n{content[:500]}...")
            
            # Clean markdown fences
            if "```json" in content:
                content = content.replace("```json", "").replace("```", "")
            elif "```" in content:
                content = content.replace("```", "")
            
            content = content.strip()
            plan_data = self.parser.parse(content)
            
            # SAFETY ANALYSIS (Warning system, not blocker)
            script = plan_data.get('python_script', '')
            is_catastrophic, safety_warnings = self.analyze_safety(script)
            
            if is_catastrophic:
                logger.error(f"[SAFETY] ⛔ CATASTROPHIC SCRIPT BLOCKED")
                logger.error(f"[SAFETY] Rejected script:\n{script}")
                return {
                    "action": "escalate",
                    "reason": f"Generated fix is catastrophically unsafe: {safety_warnings}",
                    "status": "waiting_for_approval"
                }
            
            # Allow with warnings
            if safety_warnings:
                logger.warning(f"[SAFETY] ⚠️ Script has warnings: {safety_warnings}")
            else:
                logger.info(f"[SAFETY] ✅ Script appears safe")
            
            return {
                "action": "run_remediation_script",
                "target": plan_data.get('target', 'unknown'),
                "reason": plan_data.get('reason', 'Automated Fix'),
                "python_script": script,
                "safety_warnings": safety_warnings,
                "status": "waiting_for_approval"
            }
                
        except Exception as e:
            logger.error(f"[PLANNER] Generation failed: {e}")
            return None


def generate_plan(diagnosis: dict) -> dict:
    """Entry point for the agent"""
    planner = SafePlanner()
    
    # Generate the autonomous plan
    plan_details = planner.generate_fix(diagnosis)
    
    if not plan_details:
        # Fallback
        return {
            "action": "escalate",
            "reason": "Failed to generate plan",
            "status": "waiting_for_approval",
            "id": f"plan_{uuid.uuid4().hex[:8]}"
        }
        
    # Enrich with diagnosis context
    plan_details.update({
        "root_cause": diagnosis.get("root_cause", "Unknown Issue"),
        "file_name": diagnosis.get("file_name", "Unknown"),
        "involved_files": diagnosis.get("involved_files", []),
        "line_number": diagnosis.get("line_number", "Unknown"),
        "code_snippet": diagnosis.get("code_snippet", "No stack trace available"),
        "id": f"plan_{uuid.uuid4().hex[:8]}"
    })
    
    logger.info(f"[PLANNER] 📝 Generated Plan: {plan_details['action']}")
    if plan_details.get('safety_warnings'):
        logger.warning(f"[PLANNER] ⚠️ Safety Warnings: {plan_details['safety_warnings']}")
    
    return plan_details
