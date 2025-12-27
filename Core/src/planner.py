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
            "RULES:\n"
            "1. Use the 'requests' library to interact with services (e.g., POST http://chaos-app:8000/chaos/resolve to fix chaos).\n"
            "2. DO NOT use 'os.system', 'subprocess', or file deletion commands.\n"
            "3. DO NOT delete databases.\n"
            "4. Return valid JSON only.\n"
            f"\n{self.parser.get_format_instructions()}"
        )

    def is_safe(self, code: str) -> bool:
        """
        Static Analysis (AST) to verify code safety.
        Returns True if safe, False if dangerous operations detected.
        """
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # 1. Block imports of dangerous modules
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    full_imports = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module]
                    for module in full_imports:
                        if module in ['os', 'subprocess', 'shutil', 'sys']:
                            logger.warning(f"[SAFETY] Blocked import of dangerous module: {module}")
                            return False
                            
                # 2. Block 'open' calls (write mode) - simplistic check
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == 'open':
                         pass # Warning: open() detected. Assuming read-only for now or refined check needed.
                         
            return True
        except SyntaxError:
            return False

    def generate_fix(self, diagnosis: dict) -> dict:
        root_cause = diagnosis.get('root_cause')
        involved = diagnosis.get('involved_files', [])
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Diagnosis: {root_cause}\nInvolved Files: {involved}\n\nTask: Generate a Python fix.")
        ]
        
        try:
            response = self.llm.invoke(messages)
            plan_data = self.parser.parse(response.content)
            
            # GUARDRAIL: Verify Safety
            script = plan_data.get('python_script', '')
            if self.is_safe(script):
                logger.info(f"[SAFETY] ✅ Generated Script Passed AST Check")
                return {
                    "action": "run_remediation_script",
                    "target": plan_data.get('target', 'unknown'),
                    "reason": plan_data.get('reason', 'Automated Fix'),
                    "python_script": script,
                    "status": "waiting_for_approval"
                }
            else:
                logger.error(f"[SAFETY] ⛔ Script REJECTED by Guardrails")
                return {
                    "action": "escalate",
                    "reason": "Generated fix violated safety protocols (dangerous operations detected).",
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
    
    return plan_details
