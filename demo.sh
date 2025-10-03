#!/bin/bash

echo "=========================================="
echo "AI Email Assistant - FastAPI Backend Demo"
echo "=========================================="
echo ""

# Start server
echo "Starting FastAPI server on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/fastapi_demo.log 2>&1 &
SERVER_PID=$!
sleep 3

echo -e "\n✅ Server started (PID: $SERVER_PID)"
echo ""
echo "📚 API Documentation available at:"
echo "   - Swagger UI: http://localhost:8000/docs"
echo "   - ReDoc:      http://localhost:8000/redoc"
echo ""

# Health check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s http://localhost:8000/healthz | python -m json.tool
echo ""

# Process thread - demonstrate all features
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Process Email Thread"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Input: 2-message thread about project kickoff"
echo "Features tested: normalization, summarization, task extraction, priority scoring"
echo ""
PROCESS_RESPONSE=$(curl -s -X POST http://localhost:8000/api/process-thread \
  -H "Content-Type: application/json" \
  -d '{
  "user_id": "demo_user",
  "personalized_keywords": [
    {"term": "metrics", "weight": 1.5, "scope": "subject|body"}
  ],
  "messages": [
    {
      "id": "msg_001",
      "thread_id": "thread_demo",
      "date": "2025-10-01T10:45:00Z",
      "from": "alice@company.com",
      "to": ["you@company.com"],
      "cc": ["team@company.com"],
      "subject": "Project Kickoff - Action Required",
      "body": "Hi team,\n\nPlease finalize the presentation slides by Thursday EOD. Bob will own the meeting agenda.\n\nBest regards,\nAlice"
    },
    {
      "id": "msg_002",
      "thread_id": "thread_demo",
      "date": "2025-10-01T15:30:00Z",
      "from": "bob@company.com",
      "to": ["you@company.com"],
      "cc": [],
      "subject": "Re: Project Kickoff - Action Required",
      "body": "Action items assigned:\n- Alice: Create timeline\n- You: Prepare metrics dashboard\n\nMeeting scheduled for Friday at 2pm in Conference Room A."
    }
  ]
}')

echo "$PROCESS_RESPONSE" | python -m json.tool

# Extract thread for QA
THREAD=$(echo "$PROCESS_RESPONSE" | python -c "import sys, json; data = json.load(sys.stdin); print(json.dumps(data['thread']))")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  Chatbot QA - Question 1"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Q: What do I need to deliver before the meeting?"
echo ""
curl -s -X POST http://localhost:8000/api/chatbot-qa \
  -H "Content-Type: application/json" \
  -d "{
  \"question\": \"What do I need to deliver before the meeting?\",
  \"thread\": $THREAD
}" | python -m json.tool

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  Chatbot QA - Question 2"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Q: When is the meeting and who owns the agenda?"
echo ""
curl -s -X POST http://localhost:8000/api/chatbot-qa \
  -H "Content-Type: application/json" \
  -d "{
  \"question\": \"When is the meeting and who owns the agenda?\",
  \"thread\": $THREAD
}" | python -m json.tool

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  Update User Settings"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Adding keyword: 'urgent' with weight 2.5"
echo ""
curl -s -X POST http://localhost:8000/api/update-user-settings \
  -H "Content-Type: application/json" \
  -d '{
  "user_id": "demo_user",
  "add_keywords": [
    {"term": "urgent", "weight": 2.5, "scope": "subject"},
    {"term": "deadline", "weight": 2.0, "scope": "body"}
  ],
  "remove_keywords": []
}' | python -m json.tool

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Demo Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🧪 To run tests: pytest app/tests/ -v"
echo "📖 See README.md for full documentation"
echo ""

# Cleanup
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null
echo "Done!"
