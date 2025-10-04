from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class PersonalizedKeyword(BaseModel):
    term: str
    weight: Literal["High", "Medium", "Low"] = "Medium"
    scope: str = "subject|body|sender"


class EmailMessage(BaseModel):
    id: str
    thread_id: str
    date: str
    from_: str = Field(alias="from")
    to: List[str]
    cc: List[str] = []
    subject: str
    body: str

    class Config:
        populate_by_name = True


class ProcessThreadRequest(BaseModel):
    user_id: str
    personalized_keywords: List[PersonalizedKeyword] = []
    messages: List[EmailMessage]


class TimelineItem(BaseModel):
    id: str
    date: str
    subject: str


class NormalizedMessage(BaseModel):
    id: str
    clean_body: str


class ThreadData(BaseModel):
    thread_id: str
    participants: List[str]
    timeline: List[TimelineItem]
    normalized_messages: List[NormalizedMessage]


class Task(BaseModel):
    title: str
    owner: str
    due: Optional[str] = None
    source_message_id: str
    type: Literal["deadline", "meeting", "action"]


class Priority(BaseModel):
    label: Literal["P1", "P2", "P3"]
    score: float
    reasons: List[str]


class ProcessThreadResponse(BaseModel):
    thread: ThreadData
    summary: str
    tasks: List[Task]
    priority: Priority


class ChatbotQARequest(BaseModel):
    question: str
    thread: ThreadData


class ChatbotQAResponse(BaseModel):
    answer: str
    sources: List[str]


class KeywordUpdate(BaseModel):
    term: str
    weight: Literal["High", "Medium", "Low"]
    scope: str


class UpdateUserSettingsRequest(BaseModel):
    user_id: str
    add_keywords: List[KeywordUpdate] = []
    remove_keywords: List[str] = []


class UpdateUserSettingsResponse(BaseModel):
    ok: bool


class ThreadInput(BaseModel):
    id: str
    subject: str
    snippet: str
    last_message: Optional[str] = None
    from_: Optional[str] = Field(None, alias="from")
    to: Optional[List[str]] = []
    date: Optional[str] = None
    
    class Config:
        populate_by_name = True


class ThreadAnalysisResult(BaseModel):
    id: str
    summary: str
    priority: Priority
    tasks: List[Task]


class BatchAnalyzeRequest(BaseModel):
    threads: List[ThreadInput]
    keywords: List[PersonalizedKeyword] = []


class BatchAnalyzeResponse(BaseModel):
    results: List[ThreadAnalysisResult]


class SummarizeRequest(BaseModel):
    subject: str
    text: str


class SummarizeResponse(BaseModel):
    summary: str


class ExtractTasksRequest(BaseModel):
    text: str


class ExtractTasksResponse(BaseModel):
    tasks: List[Task]


class PrioritizeRequest(BaseModel):
    subject: str
    body: str
    from_: str = Field(alias="from")
    to: List[str] = []
    has_deadline: bool = False
    deadline_hours: Optional[float] = None
    has_meeting: bool = False
    meeting_hours: Optional[float] = None
    keywords: List[PersonalizedKeyword] = []
    
    class Config:
        populate_by_name = True


class PrioritizeResponse(BaseModel):
    priority: Priority
