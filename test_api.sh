#!/bin/bash

echo "Starting FastAPI server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/fastapi.log 2>&1 &
SERVER_PID=$!
sleep 3

echo -e "\n=== Testing /healthz ==="
curl -s http://localhost:8000/healthz | python -m json.tool

echo -e "\n\n=== Testing /version ==="
curl -s http://localhost:8000/version | python -m json.tool

echo -e "\n\n=== Testing /api/process-thread ==="
curl -s -X POST http://localhost:8000/api/process-thread \
  -H "Content-Type: application/json" \
  -d '{
  "user_id": "u_123",
  "personalized_keywords": [
    {"term": "metrics", "weight": 1.2, "scope": "subject|body|sender"}
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
    },
    {
      "id": "m2",
      "thread_id": "t1",
      "date": "2025-10-01T18:10:00Z",
      "from": "bob@company.com",
      "to": ["me@us.edu"],
      "cc": [],
      "subject": "Re: Project kickoff this Friday",
      "body": "Action items: Alice → timeline, You → metrics. Meeting Fri 2pm."
    }
  ]
}' | python -m json.tool

echo -e "\n\n=== Testing /api/chatbot-qa ==="
curl -s -X POST http://localhost:8000/api/chatbot-qa \
  -H "Content-Type: application/json" \
  -d '{
  "question": "What do I need to deliver before the meeting?",
  "thread": {
    "thread_id": "t1",
    "participants": ["alice@company.com", "bob@company.com", "me@us.edu"],
    "timeline": [
      {"id": "m1", "date": "2025-10-01T10:45:00Z", "subject": "Project kickoff"},
      {"id": "m2", "date": "2025-10-01T18:10:00Z", "subject": "Re: Project kickoff"}
    ],
    "normalized_messages": [
      {"id": "m1", "clean_body": "Please finalize slides by Thu EOD. Bob owns agenda."},
      {"id": "m2", "clean_body": "Action items: Alice → timeline, You → metrics. Meeting Fri 2pm."}
    ]
  }
}' | python -m json.tool

echo -e "\n\n=== Testing /api/update-user-settings ==="
curl -s -X POST http://localhost:8000/api/update-user-settings \
  -H "Content-Type: application/json" \
  -d '{
  "user_id": "u_123",
  "add_keywords": [{"term": "interview", "weight": 2.5, "scope": "subject"}],
  "remove_keywords": ["newsletter"]
}' | python -m json.tool

echo -e "\n\n=== Stopping server ==="
kill $SERVER_PID 2>/dev/null
echo "Done!"
