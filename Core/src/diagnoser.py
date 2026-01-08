from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from typing import List
import logging
import os

# Configure logger
logger = logging.getLogger("codeweaver-agent")

class DiagnosisResult(BaseModel):
    """Pydantic model for diagnosis results with detailed crash information"""
    root_cause: str = Field(description="Short summary of the root cause (e.g., Database Connection Failed, Memory Exhaustion, Timeout)")
    confidence: float = Field(description="Confidence level between 0.0 and 1.0")
    file_name: str = Field(description="The primary file causing the error (e.g., main.py or payment_service.py)", default="Unknown")
    involved_files: List[str] = Field(description="List of ALL file names found in the stack trace (e.g., ['main.py', 'service.py', 'db.py'])", default_factory=list)
    line_number: str = Field(description="The line number where the error occurred (e.g., 42)", default="Unknown")
    code_snippet: str = Field(description="The specific line of code or stack trace snippet if visible", default="No stack trace available")


class Diagnoser:
    """SRE Log Analyzer using Groq LLM for fast inference"""
    
    def __init__(self, project_path: str = None):
        """Initialize the Groq model and output parser"""
        self.llm = ChatGroq(
            model_name="llama-3.1-8b-instant",
            temperature=0
        )
        
        # Set up the JSON output parser with our schema
        self.parser = JsonOutputParser(pydantic_object=DiagnosisResult)
        
        # Initialize code analyzer
        self.project_path = project_path or os.getenv("PROJECT_PATH", "/workspace")
        
        # Build system prompt with format instructions
        format_instructions = self.parser.get_format_instructions()
        self.system_prompt = (
            "You are an expert SRE. Extract specific crash details from the logs. "
            "Look for errors, exceptions, stack traces, or latency warnings. "
            "Output ONLY valid JSON. Do not include any conversational text or markdown formatting like ```json. "
            f"\n\n{format_instructions}\n\n"
            "Extract these details:\n"
            "- root_cause: Short summary (e.g., 'Database Connection Failed', 'Memory Leak Detected', 'Latency Spike')\n"
            "- file_name: The PRIMARY file where the error originated.\n"
            "- involved_files: A list of ALL unique file names mentioned in the stack trace (e.g. ['main.py', 'utils.py']).\n"
            "- line_number: The line number (e.g., '42')\n"
            "- code_snippet: The specific line of code or stack trace snippet if visible\n"
            "If no error is found, set confidence to 0.0 and use 'Unknown' for missing fields."
        )
    
    def get_source_code_context(self, file_name: str, line_number: str) -> str:
        """
        Attempt to fetch source code context for better analysis.
        For small files (<500 lines), returns the ENTIRE file for accurate patching.
        For large files, returns ±20 lines around the error.
        
        Args:
            file_name: Name of the file (e.g., "main.py")
            line_number: Line number as string (e.g., "127")
            
        Returns:
            Source code context or empty string if unavailable
        """
        try:
            if file_name == "Unknown" or line_number == "Unknown":
                return ""
            
            # Try to convert line number to int
            try:
                line_num = int(line_number)
            except ValueError:
                return ""
            
            # Read file from workspace
            file_path = os.path.join(self.project_path, file_name)
            if not os.path.exists(file_path):
                logger.warning(f"[DIAGNOSER] Source file not found: {file_path}")
                return ""
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            # If file is small, return the ENTIRE file for accurate patching
            if total_lines <= 500:
                context = ''.join(lines)
                logger.info(f"[DIAGNOSER] Fetched FULL file: {file_name} ({total_lines} lines)")
                return f"\n\n--- FULL SOURCE CODE: {file_name} ---\n{context}\n--- END OF FILE ---\n"
            
            # For large files, get ±20 lines around the error
            start_line = max(0, line_num - 21)
            end_line = min(total_lines, line_num + 20)
            context = ''.join(lines[start_line:end_line])
            
            logger.info(f"[DIAGNOSER] Fetched source context from {file_name}:{line_number} (lines {start_line+1}-{end_line})")
            return f"\n\n--- Source Code Context ({file_name} lines {start_line+1}-{end_line}) ---\n{context}\n--- END OF SNIPPET ---\n"
            
        except Exception as e:
            logger.error(f"[DIAGNOSER] Error fetching source context: {e}")
            return ""
    
    def analyze_logs(self, log_content: str) -> dict:
        """
        Analyze log content and identify potential issues.
        
        Args:
            log_content: The actual log content as a string (not a file path)
            
        Returns:
            Dictionary with diagnosis results
        """
        # Validate log content
        if not log_content or not log_content.strip():
            logger.warning("[DIAGNOSER] No log content provided")
            return {
                "root_cause": "No log content provided",
                "confidence": 0.0
            }
        
        logger.info(f"[DIAGNOSER] Analyzing {len(log_content)} characters of log data...")
        
        # Create messages for the LLM
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Logs:\n{log_content}")
        ]
        
        # Get analysis from the LLM
        try:
            response = self.llm.invoke(messages)
            
            # Parse the JSON response using the output parser
            result = self.parser.parse(response.content)
            
            # Try to enhance with source code context
            file_name = result.get('file_name', 'Unknown')
            line_number = result.get('line_number', 'Unknown')
            
            if file_name != 'Unknown' and line_number != 'Unknown':
                source_context = self.get_source_code_context(file_name, line_number)
                if source_context:
                    result['source_code_context'] = source_context
            
            # STORY LOGGING: Diagnoser result
            root_cause = result.get('root_cause', 'unknown')
            confidence = result.get('confidence', 0.0)
            involved = result.get('involved_files', [])
            logger.info(f"[DIAGNOSER] ❌ Root Cause Found: {root_cause} (Confidence: {confidence:.2f}, Files: {involved})")
            
            return result
            
        except Exception as e:
            # If parsing fails, return a fallback response
            logger.error(f"[DIAGNOSER] Analysis failed: {str(e)}")
            return {
                "root_cause": f"LLM analysis failed: {str(e)}",
                "confidence": 0.0
            }
