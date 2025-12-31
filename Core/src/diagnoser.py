from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from typing import List


import logging

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
    
    def __init__(self):
        """Initialize the Groq model and output parser"""
        self.llm = ChatGroq(
            model_name="llama-3.1-8b-instant",
            temperature=0
        )
        
        # Set up the JSON output parser with our schema
        self.parser = JsonOutputParser(pydantic_object=DiagnosisResult)
        
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
