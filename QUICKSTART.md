# Quick Start Guide

## 🚀 Start the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Run Tests

```bash
pytest app/tests/ -v
```

## 🎬 Run Demo

```bash
./demo.sh
```

## 🔑 Configure OpenAI (Optional)

Create `.env` file:
```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

**Note**: Works without API key using rule-based fallbacks!

## 📝 Example API Calls

### Process Thread
```bash
curl -X POST http://localhost:8000/api/process-thread \
  -H "Content-Type: application/json" \
  -d @sample_request.json
```

### Ask Question
```bash
curl -X POST http://localhost:8000/api/chatbot-qa \
  -H "Content-Type: application/json" \
  -d @sample_qa.json
```

### Update Settings
```bash
curl -X POST http://localhost:8000/api/update-user-settings \
  -H "Content-Type: application/json" \
  -d @sample_user.json
```

## 📊 All Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/healthz` | Health check |
| GET | `/version` | API version |
| POST | `/api/process-thread` | Process email thread |
| POST | `/api/chatbot-qa` | Answer questions |
| POST | `/api/update-user-settings` | Manage keywords |

## ✅ Verification Checklist

- [x] All tests pass (5/5)
- [x] API endpoints respond correctly
- [x] Swagger documentation accessible
- [x] Works with and without OpenAI API key
- [x] Sample files provided for testing
- [x] Demo script runs successfully
