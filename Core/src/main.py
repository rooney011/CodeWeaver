import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from src.diagnoser import Diagnoser
from src.planner import generate_plan
from src.executor import execute_plan

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("codeweaver-agent")

# Initialize FastAPI app
app = FastAPI(title="CodeWeaver SRE Agent", version="2.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for current plan
CURRENT_PLAN: Optional[Dict[str, Any]] = None

# Initialize components
diagnoser = Diagnoser()

# Pydantic models
class AlertData(BaseModel):
    source: str
    severity: str
    message: str
    timestamp: str
    log_path: str

class AlertPayload(BaseModel):
    data: AlertData

class PlanResponse(BaseModel):
    status: str
    plan: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "operational", "service": "codeweaver-agent"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "components": {
            "diagnoser": "ready",
            "planner": "ready",
            "executor": "ready"
        }
    }

@app.post("/webhook/alert")
async def receive_alert(payload: AlertPayload):
    """
    Receive alert from chaos-app and trigger diagnosis + planning
    """
    global CURRENT_PLAN
    
    try:
        logger.info(f"[AGENT] 🚨 Alert received from {payload.data.source}")
        logger.info(f"[AGENT] Severity: {payload.data.severity}")
        logger.info(f"[AGENT] Message: {payload.data.message}")
        
        # Step 1: Diagnose the issue
        logger.info("[AGENT] 🔍 Analyzing logs...")
        log_path = payload.data.log_path
        
        # Read logs from the shared volume
        try:
            with open(log_path, 'r') as f:
                # Read last 100 lines
                lines = f.readlines()
                log_content = ''.join(lines[-100:])
        except FileNotFoundError:
            logger.error(f"[AGENT] Log file not found: {log_path}")
            log_content = f"Alert Message: {payload.data.message}"
        
        diagnosis = diagnoser.analyze_logs(log_content)
        
        logger.info(f"[AGENT] 📊 Diagnosis Complete:")
        logger.info(f"  - Root Cause: {diagnosis.get('root_cause')}")
        logger.info(f"  - Confidence: {diagnosis.get('confidence')}")
        logger.info(f"  - File: {diagnosis.get('file_name')}:{diagnosis.get('line_number')}")
        logger.info(f"  - Involved Files: {diagnosis.get('involved_files', [])}")
        
        # Step 2: Generate remediation plan
        logger.info("[AGENT] 📝 Generating remediation plan...")
        plan = generate_plan(diagnosis)
        
        logger.info(f"[AGENT] Plan Generated: {plan.get('action')}")
        logger.info(f"[AGENT] Reason: {plan.get('reason')}")
        
        # Store plan globally
        CURRENT_PLAN = {
            **plan,
            "status": "pending"
        }
        
        logger.info("[AGENT] ⚠️  Plan awaiting human approval")
        
        return {
            "status": "plan_generated",
            "plan_id": plan.get("id"),
            "action": plan.get("action")
        }
        
    except Exception as e:
        logger.error(f"[AGENT] Error processing alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/plan/pending")
async def get_pending_plan() -> PlanResponse:
    """
    Get the current pending plan (if any)
    """
    global CURRENT_PLAN
    
    if CURRENT_PLAN and CURRENT_PLAN.get("status") == "pending":
        return PlanResponse(status="pending", plan=CURRENT_PLAN)
    
    return PlanResponse(status="empty", plan=None)

@app.post("/plan/approve")
async def approve_plan():
    """
    Approve and execute the current plan
    """
    global CURRENT_PLAN
    
    if not CURRENT_PLAN or CURRENT_PLAN.get("status") != "pending":
        raise HTTPException(status_code=400, detail="No pending plan to approve")
    
    try:
        logger.info(f"[AGENT] ✅ Plan approved by human operator")
        logger.info(f"[AGENT] Executing: {CURRENT_PLAN.get('action')}")
        
        # Execute the plan
        result = await execute_plan(CURRENT_PLAN)
        
        logger.info(f"[AGENT] Execution result: {result.get('status')}")
        
        # Clear the plan
        CURRENT_PLAN = None
        
        return {
            "status": "executed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"[AGENT] Execution failed: {str(e)}")
        CURRENT_PLAN = None
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plan/reject")
async def reject_plan():
    """
    Reject the current plan
    """
    global CURRENT_PLAN
    
    if not CURRENT_PLAN or CURRENT_PLAN.get("status") != "pending":
        raise HTTPException(status_code=400, detail="No pending plan to reject")
    
    logger.info(f"[AGENT] ❌ Plan rejected by human operator")
    CURRENT_PLAN = None
    
    return {"status": "rejected"}

@app.get("/status")
async def get_status():
    """
    Get agent status and current activity
    """
    return {
        "agent_status": "active",
        "current_plan": "pending" if CURRENT_PLAN else "none",
        "components": {
            "diagnoser": "operational",
            "planner": "operational",
            "executor": "operational"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
