from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
from dotenv import load_dotenv
from src.diagnoser import Diagnoser
from src.planner import generate_plan
from src.executor import execute_plan
import logging
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Configure logging to write to shared log file
log_file = Path("/logs/service.log")  # Shared volume with chaos-app
logger = logging.getLogger("codeweaver-agent")
logger.setLevel(logging.INFO)

# File handler for shared logs (so dashboard can see agent activity)
try:
    # Create directory if it doesn't exist
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - [AGENT] %(levelname)s - %(message)s',
                                       datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
except Exception as e:
    print(f"Warning: Could not create shared log file handler: {e}")

# Console handler (for docker logs)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - [AGENT] %(levelname)s - %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

app = FastAPI(title="CodeWeaver SRE Agent", version="1.0.0")

# Enable CORS for Next.js dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Docker networking
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Global variable to store the current plan waiting for approval
CURRENT_PLAN = {}


class AlertPayload(BaseModel):
    """Generic alert payload model"""
    data: Dict[str, Any]


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "CodeWeaver SRE Agent"}


@app.get("/health")
async def health_check():
    """Explicit health check endpoint for dashboard connectivity"""
    return {"status": "ok", "service": "CodeWeaver SRE Agent"}


@app.post("/webhook/alert")
async def receive_alert(payload: AlertPayload):
    """
    Webhook endpoint to receive alerts from monitoring systems.
    
    Args:
        payload: Generic JSON payload containing alert data
        
    Returns:
        Acknowledgment of received alert with diagnosis and action plan (awaiting approval)
    """
    global CURRENT_PLAN
    
    try:
        # 1. Start the Story - AGENT
        logger.info(f"[AGENT] 🚨 Alert Received: {payload.data.get('message', 'Unknown Alert')}")
        
        # Get log path from payload or use default
        # In Docker, logs are shared via volume at /logs/chaos-app/service.log
        # For local development, use test_logs.txt
        log_path = payload.data.get('log_path', '/logs/service.log')
        
        # 2. Continue Story - DIAGNOSER
        logger.info(f"[DIAGNOSER] 🔍 Reading logs from {log_path}...")
        
        # Initialize diagnoser and analyze logs
        diagnoser = Diagnoser()
        diagnosis = diagnoser.analyze_logs(log_path)
        # Detailed diagnosis log moved to diagnoser.py
        
        # Generate action plan based on diagnosis
        # Plan generation log moved to planner.py
        plan = generate_plan(diagnosis)
        
        # 3. Save Plan and Status
        CURRENT_PLAN = plan
        CURRENT_PLAN['status'] = 'pending'
        
        logger.info("[AGENT] ⚠️ Plan waiting for approval...")
        
        # Flush immediately to shared log
        for handler in logger.handlers:
            handler.flush()
        
        return {
            "status": "waiting_for_approval",
            "message": "Alert received and plan generated. Awaiting human approval.",
            "diagnosis": diagnosis,
            "plan": CURRENT_PLAN
        }
    except Exception as e:
        logger.error(f"Error processing alert: {str(e)}")
        # Flush immediately
        for handler in logger.handlers:
            handler.flush()
        
        return {
            "status": "error",
            "message": f"Internal error processing alert: {str(e)}"
        }


@app.get("/plan/pending")
async def get_pending_plan():
    """
    Get the current plan that is waiting for approval.
    Returns status 'empty' if no plan, 'pending' if plan exists.
    """
    if not CURRENT_PLAN:
        return {
            "status": "empty",
            "plan": None
        }
    
    return {
        "status": "pending",
        "plan": CURRENT_PLAN
    }


@app.post("/plan/approve")
async def approve_plan():
    """
    Approve and execute the pending plan.
    
    Returns:
        Execution result or error if no plan is pending
    """
    global CURRENT_PLAN
    
    if not CURRENT_PLAN:
        return {
            "status": "error",
            "message": "No plan is currently waiting for approval"
        }
    
    # Executing the approved plan - STORY: EXECUTOR
    logger.info("[EXECUTOR] 🛠️ User Approved. Executing remediation plan...")
    execution_result = await execute_plan(CURRENT_PLAN)
    logger.info("[EXECUTOR] ✅ Execution Successful. Service Restored.")
    logger.info(f"[EXECUTOR] Detailed Result: {execution_result.get('status', 'unknown')}")
    
    # Flush immediately
    for handler in logger.handlers:
        handler.flush()
    
    # Clear the current plan after execution
    executed_plan = CURRENT_PLAN
    CURRENT_PLAN = {}
    
    return {
        "status": "approved",
        "message": "Plan approved and executed",
        "plan": executed_plan,
        "execution": execution_result
    }


@app.post("/plan/reject")
async def reject_plan():
    """
    Reject the pending plan.
    
    Returns:
        Confirmation of rejection
    """
    global CURRENT_PLAN
    
    if not CURRENT_PLAN:
        return {
            "status": "no_pending_plan",
            "message": "No plan is currently waiting for approval"
        }
    
    # Clear the current plan
    rejected_plan = CURRENT_PLAN
    CURRENT_PLAN = {}
    
    return {
        "status": "rejected",
        "message": "Plan has been rejected",
        "plan": rejected_plan
    }
