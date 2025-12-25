import logging
import sys
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import requests

# Initialize FastAPI app
app = FastAPI(title="Chaos App", version="1.0.0")

# Enable CORS for Next.js dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Docker networking
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Global state variables
BROKEN_MODE = False
ALERT_SENT = False  # Track if alert was already sent for this incident

# Configure logging to write to both file and stdout
log_dir = Path("/var/log/chaos-app")
log_file = log_dir / "service.log"

# Create log directory if it doesn't exist (for local development)
log_dir.mkdir(parents=True, exist_ok=True)

# Configure logger with immediate flushing
logger = logging.getLogger("chaos-app")
logger.setLevel(logging.INFO)

# File handler with immediate flush (no buffering)
file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                   datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)
# Force immediate flush after every log
file_handler.flush = lambda: file_handler.stream.flush()

# Console handler (stdout) with immediate flush
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                     datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(console_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Ensure Python doesn't buffer stdout
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None


@app.get("/")
async def root():
    """Serve the E-Commerce frontend"""
    return FileResponse(static_dir / "index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "running"}


@app.get("/buy")
async def buy_endpoint():
    """
    Payment endpoint that simulates database connectivity issues when BROKEN_MODE is True
    """
    global BROKEN_MODE, ALERT_SENT
    
    if not BROKEN_MODE:
        logger.info("Payment processed successfully")
        return {"status": "payment_success", "latency": "10ms"}
    else:
        # Log the exact error message and flush immediately
        error_msg = "ConnectionRefusedError: Unable to connect to database at 192.168.1.55"
        logger.error(error_msg)
        # Force immediate flush to file
        for handler in logger.handlers:
            handler.flush()
        
        # Log additional critical error about service failure
        logger.critical("Service creates 500 error on endpoint /buy")
        for handler in logger.handlers:
            handler.flush()
            
        # AUTO-ALERT: Notify the agent immediately (but only once per incident)
        if not ALERT_SENT:
            ALERT_SENT = True  # Mark as sent immediately to prevent retries
            try:
                # URL for agent inside Docker network
                agent_url = "http://codeweaver-agent:8001/webhook/alert"
                payload = {
                    "data": {
                        "source": "chaos-app",
                        "severity": "critical",
                        "message": error_msg,
                        "timestamp": datetime.now().isoformat(),
                        "log_path": "/logs/service.log"
                    }
                }
                # Use short timeout so we don't block the user response too long
                requests.post(agent_url, json=payload, timeout=0.5)
                logger.info("Sent automatic alert to SRE Agent")
            except Exception as e:
                # Don't crash if agent is down, just log it
                logger.error(f"Failed to auto-alert agent: {str(e)}")
        
        # Raise HTTP 500 error
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/chaos/trigger")
async def trigger_chaos():
    """
    Trigger chaos mode - makes the service start failing
    """
    global BROKEN_MODE, ALERT_SENT
    BROKEN_MODE = True
    ALERT_SENT = False  # Reset alert flag for new incident
    logger.warning("CHAOS MODE ACTIVATED - Service will now fail")
    return {"status": "chaos_started"}


@app.post("/chaos/resolve")
async def resolve_chaos():
    """
    Resolve chaos mode - restores service to healthy state
    """
    global BROKEN_MODE, ALERT_SENT
    BROKEN_MODE = False
    ALERT_SENT = False  # Reset alert flag
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
