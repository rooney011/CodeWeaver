import logging
import sys
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pathlib import Path

# Initialize FastAPI app
app = FastAPI(title="Chaos App", version="1.0.0")

# Global state variable
BROKEN_MODE = False

# Configure logging to write to both file and stdout
log_dir = Path("/var/log/chaos-app")
log_file = log_dir / "service.log"

# Create log directory if it doesn't exist (for local development)
log_dir.mkdir(parents=True, exist_ok=True)

# Configure logger
logger = logging.getLogger("chaos-app")
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('[%(levelname)s] %(asctime)s %(message)s', 
                                   datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)

# Console handler (stdout)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('[%(levelname)s] %(asctime)s %(message)s',
                                     datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(console_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)


@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "running"}


@app.get("/buy")
async def buy_endpoint():
    """
    Payment endpoint that simulates database connectivity issues when BROKEN_MODE is True
    """
    global BROKEN_MODE
    
    if not BROKEN_MODE:
        logger.info("Payment processed successfully")
        return {"status": "payment_success", "latency": "10ms"}
    else:
        # Log the exact error message
        error_msg = "ConnectionRefusedError: Unable to connect to database at 192.168.1.55"
        logger.error(error_msg)
        
        # Log additional critical error about service failure
        logger.critical("Service creates 500 error on endpoint /buy")
        
        # Raise HTTP 500 error
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/chaos/trigger")
async def trigger_chaos():
    """
    Trigger chaos mode - makes the service start failing
    """
    global BROKEN_MODE
    BROKEN_MODE = True
    logger.warning("CHAOS MODE ACTIVATED - Service will now fail")
    return {"status": "chaos_started"}


@app.post("/chaos/resolve")
async def resolve_chaos():
    """
    Resolve chaos mode - restores service to healthy state
    """
    global BROKEN_MODE
    BROKEN_MODE = False
    logger.info("CHAOS MODE RESOLVED - Service restored to healthy state")
    return {"status": "recovered"}


@app.get("/status")
async def get_status():
    """
    Get current service status
    """
    return {
        "broken_mode": BROKEN_MODE,
        "status": "degraded" if BROKEN_MODE else "healthy"
    }
