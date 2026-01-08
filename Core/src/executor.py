import httpx
import logging
import os
import shutil
from datetime import datetime

logger = logging.getLogger("codeweaver-agent")

async def execute_plan(plan: dict) -> dict:
    """
    Execute the action plan.
    Supports code patching for 'apply_code_patch'.
    """
    action = plan.get('action')
    
    if action == 'apply_code_patch':
        file_path = plan.get('file_path')
        original_code = plan.get('original_code')
        fixed_code = plan.get('fixed_code')
        
        logger.info(f"[EXECUTOR] ⚡ Applying code patch to {file_path}...")
        
        try:
            # Determine the workspace path (inside Docker container)
            workspace = os.getenv("PROJECT_PATH", "/workspace")
            full_path = os.path.join(workspace, file_path)
            
            if not os.path.exists(full_path):
                logger.error(f"[EXECUTOR] File not found: {full_path}")
                return {
                    'status': 'error',
                    'details': f'Target file not found: {file_path}'
                }
            
            # Backup the original file
            backup_path = f"{full_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(full_path, backup_path)
            logger.info(f"[EXECUTOR] Created backup: {backup_path}")
            
            # Read current content
            with open(full_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            # Verify that the original code exists in the file
            if original_code not in current_content:
                logger.error(f"[EXECUTOR] Original code not found in file!")
                logger.error(f"[EXECUTOR] Looking for:\n{original_code[:200]}...")
                return {
                    'status': 'error',
                    'details': 'Original code section not found in file. Patch cannot be applied.'
                }
            
            # Apply the patch (simple string replacement)
            patched_content = current_content.replace(original_code, fixed_code, 1)
            
            # Write the patched content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(patched_content)
            
            logger.info(f"[EXECUTOR] ✅ Patch applied successfully to {file_path}")
            logger.info(f"[EXECUTOR] Backup available at: {backup_path}")
            
            return {
                'status': 'success',
                'details': f'Code patch applied to {file_path}',
                'backup_path': backup_path
            }
            
        except Exception as e:
            logger.error(f"[EXECUTOR] Patch application failed: {e}")
            logger.error(f"[EXECUTOR] Traceback:", exc_info=True)
            return {
                'status': 'error',
                'details': f'Patch failed: {str(e)}'
            }
            
            
    elif action == 'resolve_chaos':
        endpoint = plan.get('endpoint')
        logger.info(f"[EXECUTOR] Calling chaos resolution endpoint: {endpoint}")
        
        try:
            import requests
            response = requests.post(endpoint, timeout=5.0)
            response.raise_for_status()
            
            logger.info(f"[EXECUTOR] ✅ Chaos resolved successfully")
            return {
                'status': 'success',
                'details': f'Chaos scenario resolved via {endpoint}'
            }
        except Exception as e:
            logger.error(f"[EXECUTOR] Failed to resolve chaos: {e}")
            return {
                'status': 'error',
                'details': f'Chaos resolution failed: {str(e)}'
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

