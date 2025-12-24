from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict
from dotenv import load_dotenv
from src.diagnoser import Diagnoser
from src.planner import generate_plan
from src.executor import execute_plan

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="CodeWeaver SRE Agent", version="1.0.0")


class AlertPayload(BaseModel):
    """Generic alert payload model"""
    data: Dict[str, Any]


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "CodeWeaver SRE Agent"}


@app.post("/webhook/alert")
async def receive_alert(payload: AlertPayload):
    """
    Webhook endpoint to receive alerts from monitoring systems.
    
    Args:
        payload: Generic JSON payload containing alert data
        
    Returns:
        Acknowledgment of received alert with diagnosis, action plan, and execution result
    """
    print(f"[ALERT RECEIVED] {payload.data}")
    
    # Get log path from payload or use default
    # In Docker, logs are shared via volume at /logs/chaos-app/service.log
    # For local development, use test_logs.txt
    log_path = payload.data.get('log_path', '/logs/service.log')
    
    # Initialize diagnoser and analyze logs
    diagnoser = Diagnoser()
    diagnosis = diagnoser.analyze_logs(log_path)
    print(f"[DIAGNOSIS] {diagnosis}")
    
    # Generate action plan based on diagnosis
    plan = generate_plan(diagnosis)
    print(f"[PLAN] {plan}")
    
    # Execute the plan
    execution_result = await execute_plan(plan)
    print(f"[EXECUTION] {execution_result}")
    
    return {
        "status": "received",
        "message": "Alert has been logged and will be processed",
        "diagnosis": diagnosis,
        "plan": plan,
        "execution": execution_result
    }
