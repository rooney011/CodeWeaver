# Quick Start Guide 🚀

## Run CodeWeaver with Docker Compose

### 1. Set up your API key

Copy the example env file and add your Groq API key:
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

Also copy to the Core directory:
```bash
cp .env Core/.env
```

### 2. Start the system
```bash
docker-compose up --build
```

### 3. Wait for services to be ready
You should see:
```
chaos-app        | INFO: Application startup complete.
codeweaver-agent | INFO: Application startup complete.
```

### 4. Test the full autonomous recovery flow

**Step 1: Verify services are healthy**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/" -Method Get
Invoke-RestMethod -Uri "http://localhost:8001/" -Method Get
```

**Step 2: Trigger chaos mode**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/chaos/trigger" -Method Post
```

**Step 3: Verify service is broken**
```powershell
# This should fail with 500 error
Invoke-RestMethod -Uri "http://localhost:8000/buy" -Method Get
```

**Step 4: Send alert to CodeWeaver**
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/webhook/alert" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"data": {"message": "Critical failure", "severity": "high"}}'
```

**Step 5: Watch the magic! ✨**

CodeWeaver will:
1. 📖 Read logs from `/logs/chaos-app/service.log`
2. 🔍 Detect the `ConnectionRefusedError`
3. 🎯 Plan a `restart_service` action
4. ⚡ Execute `POST http://chaos-app:8000/chaos/resolve`
5. ✅ Service automatically recovers!

**Step 6: Verify recovery**
```powershell
# This should now succeed
Invoke-RestMethod -Uri "http://localhost:8000/buy" -Method Get
```

## View Logs

```bash
# All logs
docker-compose logs -f

# CodeWeaver agent only
docker-compose logs -f codeweaver-agent

# Chaos app only
docker-compose logs -f chaos-app

# View shared log file
docker exec -it codeweaver-agent cat /logs/chaos-app/service.log
```

## Stop the system

```bash
docker-compose down
```

## Clean up everything (including volumes)

```bash
docker-compose down -v
```

## Troubleshooting

**"GROQ_API_KEY not set" error:**
- Make sure you copied `.env` to the Core directory
- Verify the key is correct in both `.env` files

**Services won't start:**
- Check if ports 8000 and 8001 are available
- Run `docker-compose down -v` to clean up
- Try `docker-compose up --build --force-recreate`

**Can't connect to chaos-app from agent:**
- Services should use network names: `http://chaos-app:8000`
- Not `localhost` when in Docker!
