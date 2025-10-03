import pytest
from app.models.schemas import ThreadData, TimelineItem, NormalizedMessage
from app.services.qa import answer_question


@pytest.mark.asyncio
async def test_chatbot_qa_basic():
    thread = ThreadData(
        thread_id="t1",
        participants=["alice@company.com", "bob@company.com", "me@us.edu"],
        timeline=[
            TimelineItem(id="m1", date="2025-10-01T10:45:00Z", subject="Project kickoff"),
            TimelineItem(id="m2", date="2025-10-01T18:10:00Z", subject="Re: Project kickoff")
        ],
        normalized_messages=[
            NormalizedMessage(id="m1", clean_body="Please finalize slides by Thu EOD. Bob owns agenda."),
            NormalizedMessage(id="m2", clean_body="Action items: Alice → timeline, You → metrics. Meeting Fri 2pm.")
        ]
    )
    
    response = await answer_question("What do I need to deliver before the meeting?", thread)
    
    assert len(response.answer) > 0
    assert len(response.sources) > 0
    assert all(source in ["m1", "m2"] for source in response.sources)


@pytest.mark.asyncio
async def test_chatbot_qa_meeting_time():
    thread = ThreadData(
        thread_id="t1",
        participants=["alice@company.com"],
        timeline=[
            TimelineItem(id="m1", date="2025-10-01T10:45:00Z", subject="Meeting details")
        ],
        normalized_messages=[
            NormalizedMessage(id="m1", clean_body="Bob owns the agenda for the Friday 2pm meeting.")
        ]
    )
    
    response = await answer_question("When is the meeting and who owns the agenda?", thread)
    
    assert len(response.answer) > 0
    assert "m1" in response.sources
