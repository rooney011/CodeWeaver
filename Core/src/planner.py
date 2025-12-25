import uuid

import logging

# Configure logger
logger = logging.getLogger("codeweaver-agent")

def generate_plan(diagnosis: dict) -> dict:
    """
    Generate an action plan based on the diagnosis results.
    
    Args:
        diagnosis: Dictionary containing root_cause and confidence from the diagnoser
        
    Returns:
        Dictionary with action plan details including status and unique ID
    """
    root_cause = diagnosis.get('root_cause', '').lower()
    confidence = diagnosis.get('confidence', 0.0)
    
    # Patterns that indicate service restart is needed
    restart_patterns = [
        'connectionrefused',
        '500 error',
        'chaos',
        'error',
        'critical',
        'failed',
        'exception',
        'timeout',
        'unavailable',
        'refused'
    ]
    
    plan = None
    
    # Check for known patterns that can be auto-remediated
    # Only restart if confidence is high (>= 0.8)
    if confidence >= 0.8:
        for pattern in restart_patterns:
            if pattern in root_cause:
                plan = {
                    "action": "restart_service",
                    "target": "chaos-app",
                    "reason": f"Detected critical failure: {root_cause}",
                    "root_cause": diagnosis.get("root_cause", "Unknown Issue"),
                    "file_name": diagnosis.get("file_name", "Unknown"),
                    "line_number": diagnosis.get("line_number", "Unknown"),
                    "code_snippet": diagnosis.get("code_snippet", "No stack trace available"),
                    "status": "waiting_for_approval",
                    "id": f"plan_{uuid.uuid4().hex[:8]}"
                }
                break
    
    # Default to escalation if no specific plan matched
    if not plan:
        plan = {
            "action": "escalate",
            "reason": "Root cause unclear or requires human intervention.",
            "root_cause": diagnosis.get("root_cause", "Unknown Issue"),
            "file_name": diagnosis.get("file_name", "Unknown"),
            "line_number": diagnosis.get("line_number", "Unknown"),
            "code_snippet": diagnosis.get("code_snippet", "No stack trace available"),
            "status": "waiting_for_approval",
            "id": f"plan_{uuid.uuid4().hex[:8]}"
        }
        
    # STORY LOGGING: Plan generated
    logger.info(f"[PLANNER] 📝 Generated Plan: {plan['action']} (Reason: {plan['reason']})")
    logger.info("[PLANNER] ⚠️ Plan Status: WAITING FOR APPROVAL")
    
    return plan
