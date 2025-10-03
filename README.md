# AI Email Assistant Backend

A FastAPI-based backend service for an AI Email Assistant that powers a Gmail Workspace Add-on sidebar. This MVP processes email threads to provide intelligent summarization, task extraction, priority classification, and chatbot QA capabilities.

## Features

### Core Capabilities
- **Email Thread Normalization**: Sorts messages chronologically, deduplicates, and strips quoted replies/signatures
- **AI-Powered Summarization**: Uses OpenAI GPT-4o-mini with map-reduce approach (with rule-based fallback)
- **Task & Entity Extraction**: Identifies action items, owners, dates/deadlines using pattern matching and optional LLM enhancement
- **Priority Classification**: P1 (Urgent) / P2 (To-do) / P3 (FYI) based on due dates, meeting times, sender importance, and personalized keywords
- **RAG-lite Chatbot QA**: Answers questions grounded in thread context with source citations
- **User Settings Management**: Stores personalized keyword weights in SQLite for customized priority scoring

### Technical Stack
- **Framework**: FastAPI + Uvicorn
- **Python**: 3.11+
- **LLM Provider**: OpenAI (with mock fallback)
- **Database**: SQLite (for user settings only)
- **Dependencies**: pydantic, python-dateutil, numpy, scikit-learn, httpx, tenacity, rapidfuzz, python-dotenv, pytest

## Project Structure

```
/app
  main.py                 # FastAPI application entry point
  api/
    routes.py            # API endpoint definitions
  core/
    config.py            # Configuration and settings
    llm.py               # LLM provider abstraction (OpenAI + mock)
    prompts.py           # LLM prompt templates
  services/
    normalizer.py        # Email thread normalization
    summarizer.py        # Thread summarization logic
    extractor.py         # Task/entity extraction
    prioritizer.py       # Priority scoring algorithm
    qa.py                # Chatbot QA functionality
    user_settings.py     # User preferences management
  models/
    schemas.py           # Pydantic data models
  tests/
    test_process_thread.py
    test_chatbot_qa.py
    test_update_user.py
```

## Setup & Installation

### 1. Install Dependencies
```bash
pip install fastapi uvicorn pydantic python-dateutil numpy scikit-learn httpx tenacity rapidfuzz python-dotenv pytest pytest-asyncio pydantic-settings
```

### 2. Configure Environment
Create a `.env` file (copy from `.env.example`):
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
MAX_INPUT_TOKENS=12000
```

**Note**: The system works without an API key by using rule-based fallbacks.

### 3. Run the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health & Info
- `GET /healthz` - Health check
- `GET /version` - API version

### Core Endpoints

#### 1. Process Email Thread
`POST /api/process-thread`

Processes an email thread to return normalized data, summary, tasks, and priority.

**Request Body**:
```json
{
  "user_id": "u_123",
  "personalized_keywords": [
    {"term": "CPT", "weight": 2.0, "scope": "subject|body|sender"}
  ],
  "messages": [
    {
      "id": "m1",
      "thread_id": "t1",
      "date": "2025-10-01T10:45:00Z",
      "from": "alice@company.com",
      "to": ["me@us.edu"],
      "cc": [],
      "subject": "Project kickoff this Friday",
      "body": "Hi team, please finalize slides by Thu EOD. Bob owns agenda."
    }
  ]
}
```

**Response**:
```json
{
  "thread": {
    "thread_id": "t1",
    "participants": ["alice@company.com", "bob@company.com", "me@us.edu"],
    "timeline": [...],
    "normalized_messages": [...]
  },
  "summary": "Project kickoff on Fri 2pm; finalize slides by Thu EOD...",
  "tasks": [
    {
      "title": "Finalize slides",
      "owner": "team",
      "due": "2025-10-02T23:59:00",
      "source_message_id": "m1",
      "type": "deadline"
    }
  ],
  "priority": {
    "label": "P1",
    "score": 0.82,
    "reasons": ["due date within 24h", "personalized keyword hit: metrics"]
  }
}
```

#### 2. Chatbot QA
`POST /api/chatbot-qa`

Answers questions about the email thread using RAG-lite approach.

**Request Body**:
```json
{
  "question": "What do I need to deliver before the meeting?",
  "thread": {
    "thread_id": "t1",
    "participants": [...],
    "timeline": [...],
    "normalized_messages": [...]
  }
}
```

**Response**:
```json
{
  "answer": "You need to finalize the slides by Thu EOD and prepare metrics.",
  "sources": ["m1", "m2"]
}
```

#### 3. Update User Settings
`POST /api/update-user-settings`

Manages personalized keyword weights for priority scoring.

**Request Body**:
```json
{
  "user_id": "u_123",
  "add_keywords": [{"term": "interview", "weight": 2.5, "scope": "subject"}],
  "remove_keywords": ["newsletter"]
}
```

**Response**:
```json
{
  "ok": true
}
```

## Testing

### Run Unit Tests
```bash
pytest app/tests/ -v
```

### Test with Sample Data
```bash
# Process thread
curl -X POST http://localhost:8000/api/process-thread \
  -H "Content-Type: application/json" -d @sample_request.json

# Chatbot QA
curl -X POST http://localhost:8000/api/chatbot-qa \
  -H "Content-Type: application/json" -d @sample_qa.json

# Update settings
curl -X POST http://localhost:8000/api/update-user-settings \
  -H "Content-Type: application/json" -d @sample_user.json
```

## Implementation Details

### Normalization
- Sorts messages by date, deduplicates by ID
- Strips quoted replies (lines starting with `>`)
- Removes common signatures and reply headers
- Returns participants, timeline, and cleaned messages

### Summarization
- **With LLM**: Map-reduce approach for long threads (batches of 2 messages)
- **Without LLM**: Rule-based extraction of imperative sentences from first/last emails
- Output limited to 1-3 sentences

### Task Extraction
- **Pattern matching**: Detects action verbs, dates (EOD, Fri 2pm), owners (names/emails)
- **Date parsing**: Handles natural language dates like "Thu EOD", "Fri 2pm"
- **Owner detection**: Maps "you" to recipient, extracts explicit names/emails
- **LLM enhancement**: Optional JSON-based task extraction for improved precision

### Priority Scoring
- **Due date proximity**: ≤24h (strong boost), ≤72h (medium)
- **Meeting detection**: Concrete times within 48h
- **Sender importance**: Configurable boss/client domain list
- **Keyword matching**: Uses rapidfuzz for fuzzy matching with user weights
- **Score → Label**: ≥0.75 → P1, ≥0.4 → P2, else P3

### QA System
- Builds in-memory index from normalized messages
- Retrieves top-k snippets via keyword/fuzzy matching
- **With LLM**: Generates grounded answer with source citations
- **Without LLM**: Returns concatenated snippet text

### Security & Privacy
- No raw email storage - only derived results in memory
- SQLite stores only keyword preferences
- Rate limiting ready (placeholder in routes)
- Request size validation

## Acceptance Criteria ✓

- [x] Processes 10-30 message threads with sorted timeline
- [x] Returns ≤3 sentence summary with dates, owners, deliverables
- [x] Extracts ≥1 task with parsed due/meeting time
- [x] Assigns priority label (P1/P2/P3) with reasons
- [x] Answers "What do I need to deliver before the meeting?"
- [x] Answers "When is the meeting and who owns the agenda?"
- [x] Source citations point to message IDs
- [x] Updating keywords flips borderline P2→P1

## API Documentation

Interactive Swagger documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

MIT
