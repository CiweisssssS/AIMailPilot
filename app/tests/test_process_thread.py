import pytest
from app.models.schemas import ProcessThreadRequest, EmailMessage, PersonalizedKeyword
from app.services.normalizer import normalize_thread
from app.services.summarizer import summarize_thread
from app.services.extractor import extract_tasks
from app.services.prioritizer import calculate_priority


@pytest.mark.asyncio
async def test_process_thread_basic():
    messages = [
        EmailMessage(
            id="m1",
            thread_id="t1",
            date="2025-10-01T10:45:00Z",
            **{"from": "alice@company.com"},
            to=["me@us.edu"],
            cc=[],
            subject="Project kickoff this Friday",
            body="Hi team, please finalize slides by Thu EOD. Bob owns agenda."
        ),
        EmailMessage(
            id="m2",
            thread_id="t1",
            date="2025-10-01T18:10:00Z",
            **{"from": "bob@company.com"},
            to=["me@us.edu"],
            cc=[],
            subject="Re: Project kickoff this Friday",
            body="Action items: Alice → timeline, You → metrics. Meeting Fri 2pm."
        )
    ]
    
    thread = normalize_thread(messages)
    
    assert thread.thread_id == "t1"
    assert len(thread.participants) >= 2
    assert len(thread.timeline) == 2
    assert thread.timeline[0].id == "m1"
    assert thread.timeline[1].id == "m2"
    
    messages_dict = [
        {
            'id': msg.id,
            'from_': next((m.from_ for m in messages if m.id == msg.id), 'unknown'),
            'subject': next((m.subject for m in messages if m.id == msg.id), ''),
            'clean_body': msg.clean_body,
            'to': next((m.to for m in messages if m.id == msg.id), []),
            'cc': next((m.cc for m in messages if m.id == msg.id), [])
        }
        for msg in thread.normalized_messages
    ]
    
    summary = await summarize_thread(messages_dict)
    assert len(summary) > 0
    
    tasks = await extract_tasks(messages_dict)
    assert len(tasks) >= 1
    
    priority = calculate_priority(messages_dict, tasks, [])
    assert priority.label in ["P1", "P2", "P3"]
    assert 0 <= priority.score <= 1
