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
            # In a real SRE context, this might run in a sandbox container
            safe_globals = {
                "requests": requests,  # LLM uses requests.post()
                "httpx": httpx,
                "print": print,
                "logger": logger
            }
            
            logger.info(f"[EXECUTOR] Script to execute:\n{script}")
            exec(script, safe_globals)
            
            return {
                'status': 'success',
                'details': 'Autonomous script executed successfully'
            }
            
        except Exception as e:
            logger.error(f"[EXECUTOR] Script Execution Failed: {e}")
            logger.error(f"[EXECUTOR] Traceback:", exc_info=True)
            return {
                'status': 'error',
                'details': f'Script crashed: {str(e)}'
            }
            
            
    elif action == 'restart_service':
        # Legacy fallback support
        target = plan.get('target', 'unknown')
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post("http://chaos-app:8000/chaos/resolve")
                if response.status_code == 200:
                    return {'status': 'success', 'details': 'Service restarted successfully'}
                return {'status': 'error', 'details': f'Restart failed with status {response.status_code}'}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    return {
        'status': 'skipped',
        'details': 'No execution path for this action'
    }
