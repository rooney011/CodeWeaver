import os
import logging
from typing import Optional, List, Dict

logger = logging.getLogger("codeweaver-agent")

class CodeAnalyzer:
    """Analyzes source code from the monitored project"""
    
    def __init__(self, project_path: str = "/workspace"):
        self.project_path = project_path
        logger.info(f"[CODE_ANALYZER] Initialized with project path: {project_path}")
    
    def get_file_content(self, file_path: str, start_line: int = None, end_line: int = None) -> Optional[str]:
        """
        Get content of a source file, optionally with line range.
        
        Args:
            file_path: Relative path to file (e.g., "main.py")
            start_line: Optional starting line (1-indexed)
            end_line: Optional ending line (1-indexed)
            
        Returns:
            File content or None if not found
        """
        try:
            full_path = os.path.join(self.project_path, file_path)
            
            if not os.path.exists(full_path):
                logger.warning(f"[CODE_ANALYZER] File not found: {full_path}")
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # If line range specified, extract that section
            if start_line is not None and end_line is not None:
                # Convert to 0-indexed and extract
                start_idx = max(0, start_line - 1)
                end_idx = min(len(lines), end_line)
                lines = lines[start_idx:end_idx]
            
            content = ''.join(lines)
            logger.info(f"[CODE_ANALYZER] Read {len(lines)} lines from {file_path}")
            return content
            
        except Exception as e:
            logger.error(f"[CODE_ANALYZER] Error reading {file_path}: {e}")
            return None
    
    def get_context_around_line(self, file_path: str, line_number: int, context_lines: int = 10) -> Dict[str, any]:
        """
        Get code context around a specific line number.
        
        Args:
            file_path: Relative path to file
            line_number: Target line number (1-indexed)
            context_lines: Number of lines before and after to include
            
        Returns:
            Dict with 'content', 'start_line', 'end_line', 'target_line'
        """
        try:
            full_path = os.path.join(self.project_path, file_path)
            
            with open(full_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            total_lines = len(all_lines)
            start_line = max(1, line_number - context_lines)
            end_line = min(total_lines, line_number + context_lines)
            
            # Extract the context
            context_content = ''.join(all_lines[start_line-1:end_line])
            
            return {
                'content': context_content,
                'start_line': start_line,
                'end_line': end_line,
                'target_line': line_number,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"[CODE_ANALYZER] Error getting context for {file_path}:{line_number}: {e}")
            return None
    
    def find_files_by_pattern(self, pattern: str = "*.py") -> List[str]:
        """
        Find all files matching a pattern in the project.
        
        Args:
            pattern: Glob pattern (e.g., "*.py", "**/*.js")
            
        Returns:
            List of relative file paths
        """
        import glob
        
        search_path = os.path.join(self.project_path, "**", pattern)
        files = glob.glob(search_path, recursive=True)
        
        # Return relative paths
        relative_files = [os.path.relpath(f, self.project_path) for f in files]
        logger.info(f"[CODE_ANALYZER] Found {len(relative_files)} files matching '{pattern}'")
        
        return relative_files
