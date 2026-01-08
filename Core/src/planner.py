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
    action: str = Field(description="Short description of the action (e.g. 'fix_database_connection', 'patch_memory_leak')")
    reason: str = Field(description="Explanation of why this fix was chosen")
    target: str = Field(description="The target file or component to patch")
    file_path: str = Field(description="Relative path to the file that needs to be patched (e.g. 'main.py')")
    original_code: str = Field(description="The exact buggy code section to be replaced. Must match EXACTLY.")
    fixed_code: str = Field(description="The corrected code that will replace the buggy section")

class SafePlanner:
    def __init__(self):
        self.llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0)
        self.parser = JsonOutputParser(pydantic_object=RemediationPlan)
        
        self.system_prompt = (
            "You are an Expert SRE Code Fixing Agent. Your job is to analyze errors and generate SAFE code patches.\n"
            "You will receive:\n"
            "1. Error logs with stack trace\n"
            "2. The FULL source code of the buggy file\n\n"
            "Your task: Generate a JSON patch to fix the bug.\n\n"
            "SAFETY RULES (CRITICAL):\n"
            "- ONLY fix the specific bug causing the error\n"
            "- DO NOT modify database operations, credentials, or authentication logic\n"
            "- DO NOT delete functions or classes\n"
            "- DO NOT change API contracts or function signatures\n"
            "- ONLY fix: connection errors, memory leaks, null checks, exception handling, timeouts\n\n"
            "CODE PATCH FORMAT:\n"
            "- file_path: The file to patch (e.g. 'main.py')\n"
            "- original_code: The EXACT buggy code section (must match character-for-character)\n"
            "- fixed_code: The corrected code that replaces it\n\n"
            "EXAMPLES:\n\n"
            "Example 1 - Database Connection:\n"
            "If you see: 'ConnectionRefusedError: Unable to connect to database'\n"
            "And code shows: db_client = DBClient(host='192.168.1.55')\n"
            "Fix: Add retry logic or connection pooling\n\n"
            "Example 2 - Memory Leak:\n"
            "If you see: 'MemoryError: Out of memory'\n"
            "And code shows: cache = {}  # unbounded\n"
            "Fix: Add size limits or use LRU cache\n\n"
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
        source_context = diagnosis.get('source_code_context', '')
        
        # DETECT CHAOS SCENARIO  
        # If logs mention "CHAOS MODE" or error from chaos-app, resolve it via API
        raw_logs = diagnosis.get('raw_logs', '')
        root_cause_text = root_cause.lower() if root_cause else ''
        
        if 'CHAOS MODE' in raw_logs or 'chaos' in root_cause_text or 'CHAOS' in raw_logs:
            logger.info("[PLANNER] 🎯 Detected chaos scenario - will resolve via API")
            return {
                "action": "resolve_chaos",
                "target": "chaos-app",
                "reason": "Detected simulated chaos test. Calling /chaos/resolve endpoint to restore system.",
                "endpoint": "http://chaos-app:8000/chaos/resolve",
                "safety_warnings": [],
                "status": "waiting_for_approval"
            }
        
        # Build the prompt with source code context
        user_prompt = f"""Diagnosis: {root_cause}
Involved Files: {involved}

{source_context}

Based on the error logs and source code above, generate a code patch to fix the bug.
Remember: Extract the EXACT buggy code section and provide the corrected version."""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt)
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
            
            # Extract JSON from the response
            json_start = content.find('{')
            json_end = content.rfind('}')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                content = content[json_start:json_end + 1]
                logger.info(f"[PLANNER] Extracted JSON: {content[:200]}...")
            
            plan_data = self.parser.parse(content)
            
            # SAFETY ANALYSIS for code patches
            fixed_code = plan_data.get('fixed_code', '')
            is_catastrophic, safety_warnings = self.analyze_safety(fixed_code)
            
            if is_catastrophic:
                logger.error(f"[SAFETY] ⛔ CATASTROPHIC PATCH BLOCKED")
                logger.error(f"[SAFETY] Rejected patch:\n{fixed_code}")
                return {
                    "action": "escalate",
                    "reason": f"Generated patch is unsafe: {safety_warnings}",
                    "status": "waiting_for_approval"
                }
            
            # Allow with warnings
            if safety_warnings:
                logger.warning(f"[SAFETY] ⚠️ Patch has warnings: {safety_warnings}")
            else:
                logger.info(f"[SAFETY] ✅ Patch appears safe")
            
            return {
                "action": "apply_code_patch",
                "target": plan_data.get('file_path', 'unknown'),
                "reason": plan_data.get('reason', 'Automated Code Fix'),
                "file_path": plan_data.get('file_path'),
                "original_code": plan_data.get('original_code'),
                "fixed_code": fixed_code,
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
