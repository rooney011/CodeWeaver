# Chaos App 💥

A deliberately unstable service for testing the CodeWeaver SRE agent. This app can simulate failures on demand to test autonomous incident response.

## 🚀 Quick Start

### Local Development
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker
```bash
docker build -t chaos-app .
docker run -p 8000:8000 chaos-app
```

## 📡 API Endpoints

### GET `/`
Health check endpoint
```json
{"status": "running"}
```

### GET `/buy`
Payment endpoint - simulates database connectivity
- **Normal mode**: Returns success
- **Broken mode**: Logs error and returns 500

### GET `/status`
Check current service status
```json
{
  "broken_mode": false,
  "status": "healthy"
}
```

### POST `/chaos/trigger`
Activate chaos mode - service starts failing
```json
{"status": "chaos_started"}
```

### POST `/chaos/resolve`
Deactivate chaos mode - service recovers
```json
{"status": "recovered"}
```

## 🧪 Testing the Chaos

1. **Trigger chaos**: `POST /chaos/trigger`
2. **Try payment**: `GET /buy` → Should fail with 500
3. **Check logs**: `/var/log/chaos-app/service.log`
4. **Resolve chaos**: `POST /chaos/resolve`
5. **Verify recovery**: `GET /buy` → Should succeed

## 📝 Logs

Logs are written to:
- **File**: `/var/log/chaos-app/service.log`
- **Console**: stdout

When in broken mode, logs will show:
```
[ERROR] 2024-05-20 10:05:00 ConnectionRefusedError: Unable to connect to database at 192.168.1.55
[CRITICAL] 2024-05-20 10:05:00 Service creates 500 error on endpoint /buy
```

## 🔗 Integration with CodeWeaver

CodeWeaver monitors this service and:
1. Detects failures via log analysis
2. Diagnoses the root cause (ConnectionRefused)
3. Automatically calls `POST /chaos/resolve` to fix the issue
