import httpx
import logging

logger = logging.getLogger("codeweaver-agent")

async def execute_plan(plan: dict) -> dict:
    """
    Execute the action plan.
    Supports dynamic script execution for 'run_remediation_script'.
    """
    action = plan.get('action')
    
    if action == 'run_remediation_script':
        script = plan.get('python_script')
        logger.info("[EXECUTOR] ⚡ Executing autonomous remediation script...")
        
        try:
            # Import requests to make it available for generated scripts
            import requests
            
            # Create a restricted environment for execution
            import io
            import sys
            
            # Capture stdout/stderr
            capture_io = io.StringIO()
            
            safe_globals = {
                "requests": requests,
                "httpx": httpx,
                "print": lambda *args, **kwargs: print(*args, file=capture_io, **kwargs),
                "logger": logger
            }
            
            logger.info(f"[EXECUTOR] Script to execute:\n{script}")
            
            # Execute
            exec(script, safe_globals)
            
            # Get output
            output = capture_io.getvalue()
            logger.info(f"[EXECUTOR] Script Output:\n{output if output else '(no output)'}")
            
            return {
                'status': 'success',
                'details': 'Autonomous script executed successfully',
                'output': output
            }
            
        except Exception as e:
            logger.error(f"[EXECUTOR] Script Execution Failed: {e}")
            logger.error(f"[EXECUTOR] Traceback:", exc_info=True)
            return {
                'status': 'error',
                'details': f'Script crashed: {str(e)}'
            }
            
    elif action == 'escalate':
        logger.info("[EXECUTOR] Plan escalated to human - no automated fix available")
        return {
            'status': 'escalated',
            'details': plan.get('reason', 'No automated remediation possible')
        }
    
    return {
        'status': 'skipped',
        'details': 'No execution path for this action'
    }
