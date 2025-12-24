def generate_plan(diagnosis: dict) -> dict:
    """
    Generate an action plan based on the diagnosis results.
    
    Args:
        diagnosis: Dictionary containing root_cause and confidence from the diagnoser
        
    Returns:
        Dictionary with action plan details
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
    
    # Check for known patterns that can be auto-remediated
    # Only restart if confidence is high (>= 0.8)
    if confidence >= 0.8:
        for pattern in restart_patterns:
            if pattern in root_cause:
                return {
                    "action": "restart_service",
                    "target": "chaos-app",
                    "reason": f"High confidence ({confidence}) failure detected: {pattern}"
                }
    
    # Default to escalation for unclear or complex issues
    return {
        "action": "escalate",
        "reason": "Root cause unclear or requires human intervention."
    }
