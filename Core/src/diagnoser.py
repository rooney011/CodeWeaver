from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser


class DiagnosisResult(BaseModel):
    """Pydantic model for diagnosis results"""
    root_cause: str = Field(description="The identified root cause of the issue")
    confidence: float = Field(description="Confidence level between 0.0 and 1.0")


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
            "You are an expert SRE. Analyze the following logs specifically looking for "
            "errors, exceptions, or latency warnings. "
            "Output ONLY valid JSON. Do not include any conversational text or markdown formatting like ```json. "
            f"\n\n{format_instructions}\n\n"
            "If no error is found, set confidence to 0.0."
        )
    
    def analyze_logs(self, log_path: str) -> dict:
        """
        Analyze logs from a file and identify potential issues.
        
        Args:
            log_path: Path to the log file to analyze
            
        Returns:
            Dictionary with root_cause and confidence keys
        """
        # Read the last 50 lines from the log file
        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()
                last_50_lines = lines[-50:] if len(lines) > 50 else lines
                log_content = ''.join(last_50_lines)
        except FileNotFoundError:
            return {
                "root_cause": f"Log file not found at {log_path}",
                "confidence": 0.0
            }
        except Exception as e:
            return {
                "root_cause": f"Error reading log file: {str(e)}",
                "confidence": 0.0
            }
        
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
            return result
            
        except Exception as e:
            # If parsing fails, return a fallback response
            return {
                "root_cause": f"LLM analysis failed: {str(e)}",
                "confidence": 0.0
            }
