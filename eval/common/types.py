from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EmailSample:
    id: str
    subject: str
    from_addr: str
    to_addrs: List[str]
    cc_addrs: List[str]
    received_at: str  # ISO8601
    body_text: str
    ground_truth: Dict[str, Any]


@dataclass
class SummarySlots:
    actor: Optional[str]
    action: Optional[str]
    object: Optional[str]
    deadline: Optional[str]  # ISO date if resolved
    notes: Optional[str]


@dataclass
class ExtractedTask:
    owner: Optional[str]
    action: Optional[str]
    object: Optional[str]
    deadline: Optional[str]
    priority: Optional[str]


@dataclass
class ModelOutput:
    # structured outputs for downstream evaluators
    summary_json: Dict[str, Any]
    tasks_json: List[Dict[str, Any]]
    # diagnostics
    raw_summary_text: str
    raw_tasks_text: str
    json_compliant: bool
    confidence: Optional[float]  # if model provides


@dataclass
class RunMetrics:
    total_latency_ms: int
    summary_slot_accuracy: Dict[str, float]  # actor/action/object/deadline
    extractor_task_prf: Tuple[float, float, float]
    due_date_correctness: float
    json_compliance_rate: float
    cost_estimate: Optional[float]


