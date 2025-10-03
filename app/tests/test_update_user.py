import pytest
from app.models.schemas import EmailMessage, PersonalizedKeyword
from app.services.normalizer import normalize_thread
from app.services.extractor import extract_tasks
from app.services.prioritizer import calculate_priority
from app.services.user_settings import update_user_settings, get_user_keywords


@pytest.mark.asyncio
async def test_keyword_impact_on_priority():
    messages = [
        EmailMessage(
            id="m1",
            thread_id="t1",
            date="2025-10-05T10:00:00Z",
            **{"from": "alice@company.com"},
            to=["me@us.edu"],
            cc=[],
            subject="Interview preparation",
            body="Please prepare for the interview next week."
        )
    ]
    
    thread = normalize_thread(messages)
    
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
    
    tasks = await extract_tasks(messages_dict)
    
    priority_without = calculate_priority(messages_dict, tasks, [])
    
    keywords = [
        PersonalizedKeyword(term="interview", weight=2.5, scope="subject")
    ]
    
    priority_with = calculate_priority(messages_dict, tasks, keywords)
    
    assert priority_with.score > priority_without.score


def test_user_settings_crud():
    user_id = "test_user_crud_456"
    
    existing_keywords = get_user_keywords(user_id)
    update_user_settings(
        user_id,
        [],
        [kw['term'] for kw in existing_keywords]
    )
    
    update_user_settings(
        user_id,
        [{"term": "urgent", "weight": 2.0, "scope": "subject"}],
        []
    )
    
    keywords = get_user_keywords(user_id)
    assert len(keywords) == 1
    assert keywords[0]['term'] == "urgent"
    assert keywords[0]['weight'] == 2.0
    
    update_user_settings(
        user_id,
        [{"term": "critical", "weight": 3.0, "scope": "body"}],
        ["urgent"]
    )
    
    keywords = get_user_keywords(user_id)
    assert len(keywords) == 1
    assert keywords[0]['term'] == "critical"
