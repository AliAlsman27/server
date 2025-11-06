# FastAPI Backend for Device Communication

A FastAPI backend server that manages WebSocket connections with Raspberry Pi devices and forwards commands to them.

## Features

- **POST /send** endpoint with API key authentication
- **WebSocket /ws/{device_id}** endpoint for device connections
- Command forwarding from HTTP requests to WebSocket clients
- Response handling from devices

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
# Edit .env with your API key
```

3. Run locally:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Railway Deployment

1. Create a new Railway project
2. Connect your repository
3. Set environment variables in Railway dashboard:
   - `API_KEY`: Your secret API key
   - `PORT`: Railway sets this automatically
4. Railway will detect the `requirements.txt` and run:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

## API Usage

### Send Command to Device

```bash
curl -X POST "https://your-app.railway.app/send" \
  -H "x-api-key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "pi1", "cmd": "OPEN D1"}'
```

### WebSocket Connection

Devices connect to: `wss://your-app.railway.app/ws/{device_id}`

## Endpoints

- `GET /` - Health check with connection status
- `GET /health` - Simple health check
- `POST /send` - Send command to device (requires `x-api-key` header)
- `WS /ws/{device_id}` - WebSocket endpoint for device connections

