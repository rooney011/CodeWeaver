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
            # Track HTTP calls made by the script
            http_calls_made = []
            
            def tracked_requests_post(*args, **kwargs):
                """Wrapper around requests.post to track calls"""
                logger.info(f"[EXECUTOR] Making POST request to: {args[0] if args else kwargs.get('url', 'unknown')}")
                response = requests.post(*args, **kwargs)
                http_calls_made.append({
                    'url': args[0] if args else kwargs.get('url'),
                    'status': response.status_code,
                    'response': response.text[:200]  # First 200 chars
                })
                logger.info(f"[EXECUTOR] Response: {response.status_code} - {response.text[:100]}")
                return response
            
            # Monkey-patch requests module for tracking
            mock_requests = type('requests', (), {
                'post': tracked_requests_post,
                'get': requests.get,
                'RequestException': requests.RequestException
            })()
            
            safe_globals = {
                "requests": mock_requests,
                "httpx": httpx,
                "logger": logger
            }
            
            logger.info(f"[EXECUTOR] Script to execute:\n{script}")
            
            # Execute
            exec(script, safe_globals)
            
            # Log results
            if http_calls_made:
                logger.info(f"[EXECUTOR] HTTP calls made: {len(http_calls_made)}")
                for call in http_calls_made:
                    logger.info(f"  - {call['url']}: {call['status']}")
            else:
                logger.warning("[EXECUTOR] Script completed but made no HTTP calls!")
            
            return {
                'status': 'success',
                'details': 'Autonomous script executed successfully',
                'http_calls': http_calls_made
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
