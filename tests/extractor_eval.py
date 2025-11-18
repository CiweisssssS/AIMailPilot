import argparse
import asyncio
import importlib
import copy
import json
import re
import sys
from datetime import timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from dateutil import parser as date_parser
from difflib import SequenceMatcher

# Import eval script logic for consistency
sys.path.insert(0, str(Path(__file__).parent.parent))
from eval.run_pipeline import prf_tasks, due_date_correctness, _normalize_owner, _normalize_text, _normalize_date, _similarity


@dataclass
class EvalResult:
    strict_tp: int
    partial_tp: int
    fp: int
    fn: int
    owner_correct: int
    owner_total: int
    due_correct: int
    due_total: int

    @property
    def tp(self) -> int:
        return self.strict_tp + self.partial_tp

    @property
    def precision(self) -> float:
        tp = self.tp
        denom = tp + self.fp
        return tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        tp = self.tp
        denom = tp + self.fn
        return tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        prec = self.precision
        rec = self.recall
        denom = prec + rec
        return 2 * prec * rec / denom if denom else 0.0

    @property
    def owner_accuracy(self) -> Optional[float]:
        if not self.owner_total:
            return None
        return self.owner_correct / self.owner_total

    @property
    def due_accuracy(self) -> Optional[float]:
        if not self.due_total:
            return None
        return self.due_correct / self.due_total


def load_agent(path: str) -> Callable[..., Awaitable[Any]]:
    """Load an async extractor function from module:function string."""
    if ":" not in path:
        raise ValueError("--agent must be in 'module:function' format")
    module_path, func_name = path.split(":", 1)
    module = importlib.import_module(module_path)
    func = getattr(module, func_name, None)
    if func is None:
        raise AttributeError(f"Function '{func_name}' not found in module '{module_path}'")
    if not callable(func):
        raise TypeError(f"Loaded object '{func_name}' is not callable")
    return func


def parse_action_object_from_title(title: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse action and object from title field.
    Title format is typically "[VERB OBJECT OWNER]" or natural language.
    
    Returns: (action, object)
    """
    if not title:
        return None, None
    
    # Try to parse [VERB OBJECT OWNER] format
    bracket_match = re.match(r'\[([^\]]+)\]', title)
    if bracket_match:
        content = bracket_match.group(1).strip()
        # Split by spaces and try to identify verb, object, owner
        parts = content.split()
        if len(parts) >= 2:
            # First part is usually the verb (action)
            action = parts[0].lower()
            # Last part might be owner, rest is object
            # Heuristic: if last part is capitalized and short, it's likely owner
            if len(parts) >= 3 and parts[-1][0].isupper() and len(parts[-1]) <= 15:
                object_parts = parts[1:-1]
            else:
                object_parts = parts[1:]
            obj = " ".join(object_parts).lower() if object_parts else None
            return action, obj
    
    # Try to parse natural language format
    # Look for verb at the beginning (including compound verbs like "review and send")
    verb_pattern = r'^(review|submit|send|schedule|prepare|update|complete|approve|finalize|upload|export|remove|attach|check|verify|revise|refresh|resend|align|sync|meet|discuss|decide|agree|propose|edit|look|take|make|ensure|remember|double-check|fix|attend|finalize|upload|provide|return|circulate|distribute|transmit|draft|create|write|compile|develop|generate|modify|amend|correct|confirm|acknowledge|validate|affirm|synchronize|reconcile|request|ask|need|require|solicit|petition|remind|notify|alert|inform|announce|report|troubleshoot|resolve|debug|investigate|escalate|process|handle|manage|deal with|address)'
    verb_match = re.match(verb_pattern, title.lower())
    if verb_match:
        action = verb_match.group(1)
        # Rest is object - handle compound actions like "review and send"
        remaining = title[verb_match.end():].strip()
        # Check for "and [verb]" pattern (e.g., "review and send feedback")
        and_verb_match = re.match(r'^\s+and\s+(send|submit|upload|provide|return)', remaining.lower())
        if and_verb_match:
            # For compound actions, use the first verb as action
            # Object includes everything after "and [verb]"
            obj = remaining[and_verb_match.end():].strip()
        else:
            obj = remaining
        # Remove common prefixes
        obj = re.sub(r'^(the|a|an|your|our|updated|new|latest)\s+', '', obj, flags=re.IGNORECASE)
        obj = obj.strip()
        # Remove trailing phrases like "and send feedback", "by Friday", etc.
        obj = re.sub(r'\s+(and|by|before|on|at|from|to|for|with).*$', '', obj, flags=re.IGNORECASE)
        obj = obj.strip()
        return action, obj if obj else None
    
    # Fallback: first word as action, rest as object
    parts = title.split()
    if len(parts) >= 2:
        return parts[0].lower(), " ".join(parts[1:]).lower()
    elif len(parts) == 1:
        return parts[0].lower(), None
    
    return None, None


def convert_task_to_eval_format(task: Dict[str, Any], raw_due: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert task from {title, owner, due_iso} format to {owner, action, object, deadline} format
    expected by eval script.
    
    Args:
        task: Task dict with title, owner, due_iso (or due)
        raw_due: Raw due text from LLM (if available)
    
    Returns:
        Task dict in eval format: {owner, action, object, deadline}
    """
    title = task.get("title", "")
    owner = task.get("owner")
    due_iso = task.get("due_iso")
    due = task.get("due") or raw_due
    
    # Parse action and object from title
    action, obj = parse_action_object_from_title(title)
    
    # Use raw due text if available, otherwise try to extract from due_iso
    deadline = due
    if not deadline and due_iso:
        # If due_iso is in ISO format, keep it as-is (eval script normalizes dates)
        deadline = due_iso
    
    return {
        "owner": owner,
        "action": action,
        "object": obj,
        "deadline": deadline,
    }


STOPWORDS = {
    "the",
    "a",
    "an",
    "please",
    "pls",
    "kindly",
    "team",
    "thanks",
    "update",
    "task",
    "action",
}

REFERENCE_DATE = "2025-11-14"

TEST_EMAIL_CASES_LONG: List[Dict[str, Any]] = [
    {
        "id": "msg_01_long",
        "subject": "Q4 Project Review and Next Steps",
        "clean_body": (
            "Hi team,\n\n"
            "Thanks for the successful Q4 planning meeting yesterday. We covered a lot of ground, "
            "but I want to ensure we don't lose sight of the action items and deadlines we agreed upon.\n\n"
            "First, regarding the budget. Sarah, we need you to review the final budget proposal "
            "for completeness and ensure it aligns with the updated forecast. **Please finalize this review by 2025-12-01** "
            "and share the greenlight with finance. This is a hard deadline.\n\n"
            "Second, the client pitch deck is crucial. John, can you take point on preparing the initial draft? "
            "I'd like to see a robust outline by the end of next week. Remember to incorporate the new marketing slides we reviewed. "
            "Also, we need a final list of all required assets from the creative team.\n\n"
            "Finally, Mark needs to book the conference room for the client presentation. "
            "Please confirm the booking with me once it's done. Let's aim to have all logistics sorted out soon."
        ),
        "sent_date": "2025-11-14T10:00:00Z",
        "expected_tasks": [
            {
                "title": "Finalize the final budget review and share with finance",
                "owner": "Sarah",
                "due_phrase": "2025-12-01",
            },
            {
                "title": "Prepare the initial draft of the client pitch deck",
                "owner": "John",
                "due_phrase": "by the end of next week",
            },
            {
                "title": "Book the conference room for the client presentation",
                "owner": "Mark",
                "due_phrase": None,
            },
        ],
    },
    {
        "id": "msg_02_long",
        "subject": "Requirement Document Review Process",
        "clean_body": (
            "Team,\n\n"
            "The requirements document has been uploaded to SharePoint. It's a large file, "
            "and we must ensure all stakeholders have signed off on it before the kick-off meeting.\n\n"
            "Could you please dedicate some time to thoroughly review the technical specifications? "
            "**I need your feedback compiled and sent to me by next Monday morning.** I will be out of the office on Tuesday, "
            "so submitting it early is essential for me to aggregate the comments.\n\n"
            "Separately, James needs to confirm the license count with the vendor. James, can you get that confirmation to me before the end of the day today? "
            "This has been pending for a while."
        ),
        "sent_date": "2025-11-14T10:00:00Z",
        "expected_tasks": [
            {
                "title": "Review the technical specifications and compile feedback",
                "owner": "You (implicit)",
                "due_phrase": "by next Monday morning",
            },
            {
                "title": "Confirm the license count with the vendor",
                "owner": "James",
                "due_phrase": "before the end of the day today",
            },
        ],
    },
    {
        "id": "msg_03_long",
        "subject": "Project Proposal Draft v1.1 and Event Notice",
        "clean_body": (
            "Good morning,\n\n"
            "Attached is the latest version (1.1) of the Project Alpha proposal. "
            "Please read pages 5 through 12 carefully, as these sections contain the revised scope and deliverables. "
            "We received feedback from management that we need to slightly adjust our projected timeline.\n\n"
            "**Action Item: I need the final sign-off from the legal department on the risk assessment section by Wednesday.** "
            "Please follow up with David from Legal if you encounter any delays. He said he would prioritize it.\n\n"
            "Also, a quick note: the company is hosting a holiday luncheon on 2025-12-19. "
            "Please RSVP using the separate link in the calendar invite. "
            "It's a mandatory event, so please plan accordingly. This is just an FYI.\n\n"
            "Finally, Tom needs to update the project repository with the new code base. Tom, please push your changes by 5 PM today."
        ),
        "sent_date": "2025-11-14T10:00:00Z",
        "expected_tasks": [
            {
                "title": "Get the final sign-off from the legal department on the risk assessment section",
                "owner": "You (implicit)",
                "due_phrase": "by Wednesday",
            },
            {
                "title": "Update the project repository with the new code base",
                "owner": "Tom",
                "due_phrase": "by 5 PM today",
            },
        ],
    },
    {
        "id": "msg_04_long",
        "subject": "Weekly Check-in: Status and Blockers",
        "clean_body": (
            "Team,\n\n"
            "Here is the summary of our key focus areas this week:\n"
            "1. Development: The API integration is 80% complete. We hit a blocker with the authentication module (Server Error 503).\n"
            "2. Marketing: The ad campaign copy draft is ready for review. Sarah has uploaded it.\n"
            "3. Sales: Q3 numbers are looking good. We need to formalize the Q4 projections.\n\n"
            "Based on this, here are the required actions:\n"
            "A. **Mary, resolve the Server Error 503 issue ASAP.** This is our highest priority and must be fixed today.\n"
            "B. **Everyone, review the ad campaign copy draft and send feedback to Sarah before next Tuesday.** "
            "C. John needs to prepare the formal Q4 sales projections. The executive review is scheduled for the 28th, so **John, please submit the projections by the 26th.**\n\n"
            "Let me know if you have any questions. Thanks."
        ),
        "sent_date": "2025-11-14T10:00:00Z",
        "expected_tasks": [
            {
                "title": "Resolve the Server Error 503 issue",
                "owner": "Mary",
                "due_phrase": "ASAP / today",
            },
            {
                "title": "Review the ad campaign copy draft and send feedback to Sarah",
                "owner": "Everyone",
                "due_phrase": "before next Tuesday",
            },
            {
                "title": "Prepare and submit the formal Q4 sales projections",
                "owner": "John",
                "due_phrase": "by the 26th",
            },
        ],
    },
    {
        "id": "msg_05_long_truncated",
        "subject": "Extremely Long Internal Discussion",
        "clean_body": (
            "Dear all,\n\n"
            "We have had extensive internal discussions regarding the new HR policy rollout. The key points are:\n"
            "1. Compliance training is mandatory for all employees.\n"
            "2. The new sick leave policy takes effect on 2026-01-01.\n\n"
            "Please ensure you read the attached document (pages 1-5). It is crucial that the implementation proceeds smoothly. "
            "**Action:** Mary, you must update the internal wiki with the new policy links by December 5th. This needs to be checked by the audit team.\n\n"
            "Furthermore, John needs to draft the communication email to the entire company. "
            "He should complete the draft by the 20th of this month. We will review it together on the 21st. "
            "Also, we need to schedule the mandatory Q&A sessions for all departments. Please organize this with the department leads. "
            "Remember, this is a very sensitive topic, and we must proceed with caution and clarity. The full details of the rollout plan are..."
            "... [truncated]"
        ),
        "sent_date": "2025-11-14T10:00:00Z",
        "expected_tasks": [
            {
                "title": "Update the internal wiki with the new policy links",
                "owner": "Mary",
                "due_phrase": "by December 5th",
            },
            {
                "title": "Draft the communication email to the entire company",
                "owner": "John",
                "due_phrase": "by the 20th of this month",
            },
            {
                "title": "Schedule the mandatory Q&A sessions for all departments",
                "owner": "You (implicit)",
                "due_phrase": None,
            },
        ],
    },
]

TEST_EMAIL_CASES_MEDIUM: List[Dict[str, Any]] = [
    {
        "id": "msg_06_medium",
        "subject": "Website Redesign - Review and next actions",
        "clean_body": (
            "Hi team,\n\n"
            "The designer has sent over the wireframes for the new website homepage. Attached is the PDF. "
            "I know we have a lot on our plate, but this is a priority. I need rapid feedback.\n\n"
            "**Action Point:** Everyone should review the wireframes and send a list of UI/UX comments directly to me by the end of the day next Thursday. "
            "I'll consolidate them before sending them back to the agency.\n\n"
            "Also, please remind me to follow up with the hosting provider about the server migration next week. Thanks!"
        ),
        "sent_date": "2025-11-14T10:00:00Z",
        "expected_tasks": [
            {
                "title": "Review the wireframes and send a list of UI/UX comments to me",
                "owner": "Everyone",
                "due_phrase": "by the end of the day next Thursday",
            },
            {
                "title": "Follow up with the hosting provider about the server migration",
                "owner": "Sender (Self-task)",
                "due_phrase": "next week",
            },
        ],
    },
    {
        "id": "msg_07_medium",
        "subject": "Security Audit Planning",
        "clean_body": (
            "Heads up, we are starting the annual security audit. This will require coordination across teams.\n\n"
            "The **IT Department must finalize the access control list audit by 2025-12-15.** This is a critical compliance item.\n\n"
            "The HR team needs to schedule the mandatory security training for all new hires. Please ensure it is completed before the end of the year."
        ),
        "sent_date": "2025-11-14T10:00:00Z",
        "expected_tasks": [
            {
                "title": "Finalize the access control list audit",
                "owner": "IT Department",
                "due_phrase": "by 2025-12-15",
            },
            {
                "title": "Schedule the mandatory security training for all new hires",
                "owner": "HR team",
                "due_phrase": "before the end of the year",
            },
        ],
    },
    {
        "id": "msg_08_medium",
        "subject": "Urgent Client Issue",
        "clean_body": (
            "A major client (Alpha Corp) is experiencing a service outage. This is a P1 issue.\n\n"
            "**Action:** Susan, jump on a call with the support team immediately to troubleshoot. "
            "I need a full incident report submitted as soon as the service is restored, but no later than tomorrow morning."
        ),
        "sent_date": "2025-11-14T10:00:00Z",
        "expected_tasks": [
            {
                "title": "Jump on a call with the support team to troubleshoot",
                "owner": "Susan",
                "due_phrase": "immediately",
            },
            {
                "title": "Submit a full incident report",
                "owner": "Susan",
                "due_phrase": "no later than tomorrow morning",
            },
        ],
    },
    {
        "id": "msg_09_medium",
        "subject": "Travel Confirmation and Self Task",
        "clean_body": (
            "My flight to London is confirmed for 2025-11-25. I will be out of the office until 2025-11-30. "
            "Please hold all non-urgent items until my return.\n\n"
            "**Self-Task (for the sender):** I need to remember to send my itinerary to Jane for expense tracking purposes before I leave."
        ),
        "sent_date": "2025-11-14T10:00:00Z",
        "expected_tasks": [
            {
                "title": "Send my itinerary to Jane for expense tracking purposes",
                "owner": "Sender (Self-task)",
                "due_phrase": "before I leave",
            }
        ],
    },
    {
        "id": "msg_10_medium",
        "subject": "New Marketing Asset Review",
        "clean_body": (
            "We finalized the new product brochure. Here is the link for review: [Link to Document].\n\n"
            "Please check the product features listed on page 3. **We must send this to the printers by 18:00 on Monday.** "
            "John, verify the compliance statements are correct. Sarah, check the imagery and branding standards."
        ),
        "sent_date": "2025-11-14T10:00:00Z",
        "expected_tasks": [
            {
                "title": "Send this to the printers",
                "owner": "team",
                "due_phrase": "by 18:00 on Monday",
            },
            {
                "title": "Verify the compliance statements are correct",
                "owner": "John",
                "due_phrase": None,
            },
            {
                "title": "Check the imagery and branding standards",
                "owner": "Sarah",
                "due_phrase": None,
            },
        ],
    },
]

TEST_EMAIL_CASES = TEST_EMAIL_CASES_LONG + TEST_EMAIL_CASES_MEDIUM

ADDITIONAL_TEST_EMAILS: List[Dict[str, Any]] = [
    {
        "id": "e001",
        "subject": "Brand Guidelines Review",
        "from_": "Rebecca Lee <rebecca@designhub.com>",
        "sent_date": "2025-11-10T09:00:00Z",
        "body": (
            "Hi Mark,\n\n"
            "We've completed the first draft of the updated brand guidelines. "
            "Please review the new color palette and logo usage and send your feedback by Friday at 6 PM.\n\n"
            "Best,\nRebecca"
        ),
        "tasks": [
            {
                "title": "Review updated brand guidelines and send feedback",
                "owner": "Mark",
                "due_raw": "Friday at 6 PM",
            }
        ],
    },
    {
        "id": "e002",
        "subject": "Invoice Submission Reminder",
        "from_": "David Chen <david@financepro.io>",
        "sent_date": "2025-11-15T12:00:00Z",
        "body": (
            "Hi team,\n\n"
            "Please finalize your September invoice and upload it to the finance portal "
            "by November 20 at 5:00 PM UTC.\n\n"
            "Thanks,\nDavid"
        ),
        "tasks": [
            {
                "title": "Finalize September invoice and upload to the finance portal",
                "owner": "team",
                "due_raw": "November 20 at 5:00 PM UTC",
            }
        ],
    },
    {
        "id": "e003",
        "subject": "API Issue Sync",
        "from_": "Alex Wu <alexwu@devteam.com>",
        "sent_date": "2025-11-13T18:00:00Z",
        "body": (
            "Hi all,\n\n"
            "Let's meet tomorrow at 10:00 AM PT to discuss the API rate limit issue and agree on next steps.\n\n"
            "Alex"
        ),
        "tasks": [
            {
                "title": "Attend meeting to discuss API rate limit issue",
                "owner": "team",
                "due_raw": "tomorrow at 10:00 AM PT",
            }
        ],
    },
    {
        "id": "e004",
        "subject": "Document Feedback Request",
        "from_": "Nina Patel <nina@marketinglab.org>",
        "sent_date": "2025-11-12T09:30:00Z",
        "body": (
            "Hi,\n\n"
            "Could you please review the attached campaign document and send me your comments "
            "by end of day Wednesday?\n\n"
            "Best,\nNina"
        ),
        "tasks": [
            {
                "title": "Review campaign document and send comments",
                "owner": "team",
                "due_raw": "end of day Wednesday",
            }
        ],
    },
    {
        "id": "e005",
        "subject": "Team Offsite Venue",
        "from_": "Marcus Hall <marcus@opscenter.co>",
        "sent_date": "2025-11-09T16:00:00Z",
        "body": (
            "Hi team,\n\n"
            "We need to finalize the offsite venue. Please send your preferred options by Monday morning.\n\n"
            "Regards,\nMarcus"
        ),
        "tasks": [
            {
                "title": "Send preferred options for offsite venue",
                "owner": "team",
                "due_raw": "Monday morning",
            }
        ],
    },
    {
        "id": "e006",
        "subject": "Client Demo Preparation",
        "from_": "Ivy Thompson <ivy@productexperts.ai>",
        "sent_date": "2025-11-14T08:00:00Z",
        "body": (
            "Hi,\n\n"
            "Please prepare the client demo slides and upload them to the shared drive before noon tomorrow.\n\n"
            "Thanks,\nIvy"
        ),
        "tasks": [
            {
                "title": "Prepare client demo slides and upload to shared drive",
                "owner": "team",
                "due_raw": "before noon tomorrow",
            }
        ],
    },
    {
        "id": "e007",
        "subject": "Weekly Report",
        "from_": "Liam Zhang <liam@analyticsnow.io>",
        "sent_date": "2025-11-14T09:00:00Z",
        "body": (
            "Hi,\n\n"
            "Just a reminder to submit your weekly report by 4:00 PM today so I can consolidate the numbers.\n\n"
            "Liam"
        ),
        "tasks": [
            {
                "title": "Submit weekly report",
                "owner": "team",
                "due_raw": "4:00 PM today",
            }
        ],
    },
    {
        "id": "e008",
        "subject": "Budget Approval Needed",
        "from_": "Grace Kim <grace@financehub.net>",
        "sent_date": "2025-11-11T14:00:00Z",
        "body": (
            "Hi,\n\n"
            "The Q4 marketing budget draft is ready. Please review and approve it by Thursday afternoon.\n\n"
            "Best,\nGrace"
        ),
        "tasks": [
            {
                "title": "Review and approve Q4 marketing budget draft",
                "owner": "team",
                "due_raw": "Thursday afternoon",
            }
        ],
    },
    {
        "id": "e009",
        "subject": "Design Sprint Brief",
        "from_": "Hannah Lee <hlee@uxcreators.com>",
        "sent_date": "2025-11-08T10:00:00Z",
        "body": (
            "Hi all,\n\n"
            "Our next design sprint starts on Monday. Please read the attached brief before Monday so we can jump straight into work.\n\n"
            "Hannah"
        ),
        "tasks": [
            {
                "title": "Read design sprint brief",
                "owner": "team",
                "due_raw": "before Monday",
            }
        ],
    },
    {
        "id": "e010",
        "subject": "Internship Proposal Feedback",
        "from_": "Olivia Park <olivia@hrpartners.org>",
        "sent_date": "2025-11-07T13:00:00Z",
        "body": (
            "Hi,\n\n"
            "Please review the internship program proposal and share your recommendations by next Tuesday.\n\n"
            "Best,\nOlivia"
        ),
        "tasks": [
            {
                "title": "Review internship program proposal and share recommendations",
                "owner": "team",
                "due_raw": "next Tuesday",
            }
        ],
    },
    {
        "id": "e011",
        "subject": "Contract Renewal Confirmation",
        "from_": "Vendor Support <support@vendorsuite.com>",
        "sent_date": "2025-11-01T09:00:00Z",
        "body": (
            "Dear customer,\n\n"
            "Your service contract will expire on December 1. "
            "Please confirm your renewal decision by November 25.\n\n"
            "Best regards,\nVendor Support"
        ),
        "tasks": [
            {
                "title": "Confirm contract renewal decision",
                "owner": "team",
                "due_raw": "November 25",
            }
        ],
    },
    {
        "id": "e012",
        "subject": "Strategy Deck Update",
        "from_": "Tom Rivera <trivera@strategyteam.io>",
        "sent_date": "2025-11-10T15:00:00Z",
        "body": (
            "Hi,\n\n"
            "Could you send me the latest version of the strategy deck before our meeting on Thursday morning?\n\n"
            "Thanks,\nTom"
        ),
        "tasks": [
            {
                "title": "Send latest version of strategy deck",
                "owner": "team",
                "due_raw": "before our meeting on Thursday morning",
            }
        ],
    },
    {
        "id": "e013",
        "subject": "Q2 Hiring Plan Review",
        "from_": "Ella Morgan <ella@hrteam.co>",
        "sent_date": "2025-11-05T11:00:00Z",
        "body": (
            "Hi team,\n\n"
            "Please take a look at the Q2 hiring plan draft and provide your suggestions by the end of this week.\n\n"
            "Ella"
        ),
        "tasks": [
            {
                "title": "Review Q2 hiring plan draft and provide suggestions",
                "owner": "team",
                "due_raw": "the end of this week",
            }
        ],
    },
    {
        "id": "e014",
        "subject": "Data Migration Notice",
        "from_": "Infra Team <infra@company.com>",
        "sent_date": "2025-11-03T20:00:00Z",
        "body": (
            "Hi all,\n\n"
            "We will perform a database migration on November 18 from 1:00 AM to 3:00 AM UTC. "
            "Please plan around this maintenance window.\n\n"
            "Infra Team"
        ),
        "tasks": [
            {
                "title": "Plan around database migration window",
                "owner": "team",
                "due_raw": "November 18 from 1:00 AM to 3:00 AM UTC",
            }
        ],
    },
    {
        "id": "e015",
        "subject": "User Research Session Signup",
        "from_": "UX Research <research@uxlab.com>",
        "sent_date": "2025-11-06T09:30:00Z",
        "body": (
            "Hi,\n\n"
            "Please sign up for one of the user research sessions taking place next Wednesday afternoon.\n\n"
            "Thanks,\nUX Research Team"
        ),
        "tasks": [
            {
                "title": "Sign up for a user research session",
                "owner": "team",
                "due_raw": "next Wednesday afternoon",
            }
        ],
    },
    {
        "id": "e016",
        "subject": "September Invoice Tasks",
        "from_": "David Chen <dchen@financepro.io>",
        "sent_date": "2025-11-15T12:00:00Z",
        "body": (
            "Hi Alice and Bob,\n\n"
            "We need to close out September billing. Alice, please finalize the September invoice and upload it "
            "to the finance portal by November 20 at 5:00 PM UTC. Bob, once the invoice is uploaded, please send "
            "the finalized invoice to the client by the end of that day.\n\n"
            "Thanks,\nDavid"
        ),
        "tasks": [
            {
                "title": "Finalize September invoice and upload to the finance portal",
                "owner": "Alice",
                "due_raw": "November 20 at 5:00 PM UTC",
            },
            {
                "title": "Send the finalized invoice to the client",
                "owner": "Bob",
                "due_raw": "the end of that day",
            },
        ],
    },
    {
        "id": "e017",
        "subject": "API Incident Follow-up",
        "from_": "Alex Wu <alexwu@devteam.com>",
        "sent_date": "2025-11-13T18:00:00Z",
        "body": (
            "Hi team,\n\n"
            "Tomorrow at 10:00 AM PT we will have a sync to discuss the API rate limit incident. "
            "Before the meeting, please review the incident report and add your questions or comments by tonight.\n\n"
            "Alex"
        ),
        "tasks": [
            {
                "title": "Review the API incident report and add questions or comments",
                "owner": "team",
                "due_raw": "by tonight",
            },
            {
                "title": "Attend sync to discuss the API rate limit incident",
                "owner": "team",
                "due_raw": "Tomorrow at 10:00 AM PT",
            },
        ],
    },
    {
        "id": "e018",
        "subject": "Client Demo Checklist",
        "from_": "Ivy Thompson <ivy@productexperts.ai>",
        "sent_date": "2025-11-14T08:00:00Z",
        "body": (
            "Hi team,\n\n"
            "For tomorrow's client demo, please finish updating the demo slides by 10:00 AM, "
            "and make sure the demo environment is fully ready by 11:30 AM.\n\n"
            "Thanks,\nIvy"
        ),
        "tasks": [
            {
                "title": "Finish updating demo slides",
                "owner": "team",
                "due_raw": "by 10:00 AM",
            },
            {
                "title": "Make sure the demo environment is fully ready",
                "owner": "team",
                "due_raw": "by 11:30 AM",
            },
        ],
    },
    {
        "id": "e019",
        "subject": "Launch Assets Preparation",
        "from_": "Tara Singh <tara@productlaunch.io>",
        "sent_date": "2025-11-09T10:00:00Z",
        "body": (
            "Hi all,\n\n"
            "To prepare for the product launch, please upload the final social media copy to the shared folder "
            "by Monday at 3:00 PM, and send me your confirmation email once you have uploaded it.\n\n"
            "Best,\nTara"
        ),
        "tasks": [
            {
                "title": "Upload the final social media copy to the shared folder",
                "owner": "team",
                "due_raw": "Monday at 3:00 PM",
            },
            {
                "title": "Send confirmation email after upload",
                "owner": "team",
                "due_raw": "once you have uploaded it",
            },
        ],
    },
    {
        "id": "e020",
        "subject": "Weekly Status Follow-ups",
        "from_": "Project Manager <pm@projects.com>",
        "sent_date": "2025-11-11T09:00:00Z",
        "body": (
            "Hi team,\n\n"
            "For this week's status: please update your task statuses in Jira by Friday noon, "
            "and share any blockers in the Slack channel by Friday at 2:00 PM.\n\n"
            "Thanks,\nPM"
        ),
        "tasks": [
            {
                "title": "Update task statuses in Jira",
                "owner": "team",
                "due_raw": "Friday noon",
            },
            {
                "title": "Share blockers in the Slack channel",
                "owner": "team",
                "due_raw": "Friday at 2:00 PM",
            },
        ],
    },
]

ALL_TEST_EMAIL_CASES = TEST_EMAIL_CASES + ADDITIONAL_TEST_EMAILS


def _build_builtin_cases(selection: str) -> List[Dict[str, Any]]:
    if selection == "long":
        source = TEST_EMAIL_CASES_LONG
    elif selection == "medium":
        source = TEST_EMAIL_CASES_MEDIUM
    elif selection == "extra":
        source = ADDITIONAL_TEST_EMAILS
    else:
        source = ALL_TEST_EMAIL_CASES

    cases: List[Dict[str, Any]] = []
    for case in source:
        case_copy = copy.deepcopy(case)
        if "expected_tasks" in case_copy:
            tasks_source = case_copy.pop("expected_tasks", [])
        else:
            tasks_source = case_copy.get("tasks", [])
        case_copy["tasks"] = [
            {
                "title": task.get("title"),
                "owner": task.get("owner"),
                "due_raw": task.get("due_phrase") or task.get("due_raw"),
            }
            for task in tasks_source
        ]
        case_copy["text"] = case_copy.get("clean_body") or case_copy.get("body", "")
        cases.append(case_copy)
    return cases


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[\w']+", text.lower())
    return [tok for tok in tokens if tok not in STOPWORDS]


def jaccard_similarity(a_tokens: List[str], b_tokens: List[str]) -> float:
    set_a = set(a_tokens)
    set_b = set(b_tokens)
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 0.0
    intersection = set_a & set_b
    return len(intersection) / len(union)


def seq_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def title_similarity(a: str, b: str) -> float:
    """Blend Jaccard token overlap with SequenceMatcher ratio for robustness."""
    tokens_a = tokenize(a)
    tokens_b = tokenize(b)
    jaccard = jaccard_similarity(tokens_a, tokens_b)
    seq_ratio = seq_similarity(a, b)
    # Give slightly higher weight to token overlap to avoid false positives
    return 0.6 * jaccard + 0.4 * seq_ratio


def adjusted_threshold(base_thresh: float, reference_title: str) -> float:
    """
    Dynamically relax threshold for short or low-content titles to better match human judgment.
    """
    tokens = tokenize(reference_title)
    num_tokens = len(tokens)
    char_len = len(reference_title.strip())
    thresh = base_thresh
    if num_tokens <= 3:
        thresh -= 0.15
    elif num_tokens <= 5:
        thresh -= 0.1
    if char_len <= 20:
        thresh -= 0.05
    return max(0.3, thresh)


NULL_MARKERS = {"", "tbd", "none", "null"}


def normalize_due_string(value: Optional[str]) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def due_match(gold_due: Optional[str], pred_due: Optional[str], tolerance_minutes: int = 60) -> bool:
    gold_norm = normalize_due_string(gold_due)
    pred_norm = normalize_due_string(pred_due)

    gold_is_null = gold_norm in NULL_MARKERS
    pred_is_null = pred_norm in NULL_MARKERS

    if gold_is_null or pred_is_null:
        return gold_is_null and pred_is_null

    if not gold_norm:
        return not pred_norm

    if not pred_norm:
        return False

    if gold_norm in pred_norm or pred_norm in gold_norm:
        return True

    gold_dt = _normalize_datetime(_safe_parse_datetime(gold_due))
    pred_dt = _normalize_datetime(_safe_parse_datetime(pred_due))

    if gold_dt and pred_dt:
        delta = abs((gold_dt - pred_dt).total_seconds())
        if delta <= tolerance_minutes * 60:
            return True
        if gold_dt.date() == pred_dt.date():
            return True

    return False


def _safe_parse_datetime(value: Optional[str]) -> Optional[Any]:
    if not value:
        return None
    try:
        return date_parser.parse(value, fuzzy=True)
    except (ValueError, OverflowError, TypeError):
        return None


def _normalize_datetime(dt: Optional[Any]) -> Optional[Any]:
    if dt is None:
        return None
    tzinfo = getattr(dt, "tzinfo", None)
    if tzinfo is None or tzinfo.utcoffset(dt) is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def compute_metrics(
    email_id: str,
    subject: str,
    gold_tasks: List[Dict[str, Any]],
    pred_tasks: List[Dict[str, Any]],
    title_thresh: float,
    tolerance_minutes: int,
    fn_examples: List[Dict[str, Any]],
    fp_examples: List[Dict[str, Any]],
) -> Tuple[int, int, int, int, int, int, int, int]:
    strict_tp = 0
    partial_tp = 0
    owner_correct = 0
    owner_total = 0
    due_correct = 0
    due_total = 0
    used_pred = [False] * len(pred_tasks)
    gold_status = [0] * len(gold_tasks)  # 0=unmatched, 1=strict, 2=partial
    unmatched_gold: List[Tuple[int, Dict[str, Any]]] = []

    for idx_gold, gold in enumerate(gold_tasks):
        gold_title = gold.get("title", "")
        gold_due_raw = gold.get("due_raw")
        effective_thresh = adjusted_threshold(title_thresh, gold_title)
        best_index: Optional[int] = None
        best_sim = 0.0
        best_due_match = False

        for idx, pred in enumerate(pred_tasks):
            if used_pred[idx]:
                continue
            pred_title = pred.get("title", "")
            title_sim = title_similarity(gold_title, pred_title)
            if title_sim < effective_thresh:
                continue
            pred_due_iso = pred.get("due_iso")
            due_is_match = due_match(gold_due_raw, pred_due_iso, tolerance_minutes)
            if title_sim > best_sim:
                best_sim = title_sim
                best_index = idx
                best_due_match = due_is_match
            elif title_sim == best_sim and due_is_match and not best_due_match:
                best_index = idx
                best_due_match = True

        if best_index is not None:
            strict_tp += 1
            used_pred[best_index] = True
            gold_status[idx_gold] = 1
            pred = pred_tasks[best_index]
            owner_total += 1
            if _owners_match(gold.get("owner"), pred.get("owner")):
                owner_correct += 1
            due_total += 1
            if best_due_match:
                due_correct += 1
        else:
            unmatched_gold.append(
                (
                    idx_gold,
                    {
                        "email_id": email_id,
                        "subject": subject,
                        "title": gold_title,
                        "due_raw": gold_due_raw,
                        "owner": gold.get("owner"),
                    },
                )
            )

    # Partial matching with relaxed threshold
    for entry in unmatched_gold:
        gold_idx, example = entry
        gold = gold_tasks[gold_idx]
        gold_title = gold.get("title", "")
        gold_due_raw = gold.get("due_raw")
        fallback_thresh = max(0.3, adjusted_threshold(title_thresh, gold_title) - 0.15)
        best_index: Optional[int] = None
        best_sim = 0.0
        best_due_match = False

        for idx, pred in enumerate(pred_tasks):
            if used_pred[idx]:
                continue
            pred_title = pred.get("title", "")
            title_sim = title_similarity(gold_title, pred_title)
            if title_sim < fallback_thresh:
                continue
            pred_due_iso = pred.get("due_iso")
            due_is_match = due_match(gold_due_raw, pred_due_iso, tolerance_minutes * 2)
            if title_sim > best_sim:
                best_sim = title_sim
                best_index = idx
                best_due_match = due_is_match

        if best_index is not None:
            partial_tp += 1
            used_pred[best_index] = True
            gold_status[gold_idx] = 2
            pred = pred_tasks[best_index]
            owner_total += 1
            if _owners_match(gold.get("owner"), pred.get("owner")):
                owner_correct += 1
            due_total += 1
            if best_due_match:
                due_correct += 1
        else:
            fn_examples.append(example)

    fp = 0
    for idx, pred in enumerate(pred_tasks):
        if not used_pred[idx]:
            fp += 1
            fp_examples.append(
                {
                    "email_id": email_id,
                    "subject": subject,
                    "title": pred.get("title", ""),
                    "due_iso": pred.get("due_iso"),
                    "owner": pred.get("owner"),
                }
            )

    total_matches = strict_tp + partial_tp
    fn = len(gold_tasks) - total_matches
    return (
        strict_tp,
        partial_tp,
        fp,
        fn,
        owner_correct,
        owner_total,
        due_correct,
        due_total,
    )


def _owners_match(gold_owner: Optional[str], pred_owner: Optional[str]) -> bool:
    if gold_owner is None or pred_owner is None:
        return False
    return gold_owner.strip().lower() == pred_owner.strip().lower()


async def evaluate_dataset(
    data_path: Path,
    agent: Callable[..., Awaitable[Any]],
    title_thresh: float,
    tolerance_minutes: int,
    max_examples: int = 5,
    dataset: Optional[List[Dict[str, Any]]] = None,
    lenient: bool = True,
    very_lenient: bool = True,  # Default to very_lenient for better semantic matching
    sim_threshold: float = 0.75,  # Stricter: raised from 0.6 to 0.75
    task_match_k: int = 3,  # Stricter: raised from 2 to 3
) -> EvalResult:
    """
    Evaluate dataset using eval script logic (prf_tasks).
    This matches the evaluation approach in eval/run_pipeline.py.
    """
    strict_tp_total = partial_tp_total = 0
    fp_total = fn_total = 0
    owner_correct_total = owner_total_total = 0
    due_correct_total = due_total_total = 0
    fn_examples: List[Dict[str, Any]] = []
    fp_examples: List[Dict[str, Any]] = []
    due_match_list: List[float] = []

    if dataset is not None:
        row_source = _iterate_cases(dataset)
    else:
        row_source = _load_jsonl_async(data_path)

    async for row in row_source:
        gold_tasks = row.get("tasks")
        if gold_tasks is None:
            gold_tasks = row.get("expected", {}).get("tasks", [])
        text = row.get("text")
        if not text:
            text = row.get("body", "")
        subject = row.get("subject", "")
        email_id = row.get("id", "")

        # Try to get raw LLM response if agent is extract_tasks_from_text
        # Otherwise use the agent's result
        pred_result = await agent(text=text, subject=subject)
        pred_tasks_raw = pred_result.get("tasks", []) if isinstance(pred_result, dict) else []
        
        # If agent is extract_tasks_from_text, try to get raw LLM response
        # to preserve original due text
        agent_name = getattr(agent, '__name__', '')
        if agent_name == 'extract_tasks_from_text':
            try:
                from app.core.llm import LLMProvider
                from app.core.prompts import EXTRACTION_PROMPT
                
                llm_provider = LLMProvider()
                combined_text = f"Subject: {subject}\n\n{text}" if subject else text
                
                llm_messages = [
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": combined_text}
                ]
                
                # Get raw response from LLM
                model_id = llm_provider.default_extractor_model
                response = await llm_provider._call_model(llm_messages, model_id=model_id, temperature=0.3)
                
                # Parse response to get raw tasks with original due
                try:
                    if response.strip().startswith('['):
                        raw_tasks = json.loads(response)
                    elif response.strip().startswith('{'):
                        raw_tasks = [json.loads(response)]
                    else:
                        response_clean = response.strip()
                        if '```json' in response_clean:
                            response_clean = response_clean.split('```json')[1].split('```')[0].strip()
                        elif '```' in response_clean:
                            response_clean = response_clean.split('```')[1].split('```')[0].strip()
                        raw_tasks = json.loads(response_clean)
                    
                    # Merge raw due from LLM response with formatted tasks
                    for i, raw_task in enumerate(raw_tasks):
                        if i < len(pred_tasks_raw):
                            # Add raw due to formatted task
                            pred_tasks_raw[i]["due"] = raw_task.get("due")
                except json.JSONDecodeError:
                    pass  # Fall back to using formatted tasks
            except Exception:
                pass  # Fall back to using formatted tasks

        # Convert tasks to eval format: {owner, action, object, deadline}
        # For predicted tasks: parse from title and use raw due if available
        pred_tasks_eval = []
        for task in pred_tasks_raw:
            # Try to get raw due from task (if LLM returned it)
            raw_due = task.get("due")  # Original due text from LLM
            eval_task = convert_task_to_eval_format(task, raw_due=raw_due)
            pred_tasks_eval.append(eval_task)
            
            # Convert gold tasks to eval format
        gold_tasks_eval = []
        for task in gold_tasks:
            # Gold tasks might already be in eval format or have title format
            if "action" in task and "object" in task:
                # Already in eval format
                gold_tasks_eval.append({
                    "owner": task.get("owner"),
                    "action": task.get("action"),
                    "object": task.get("object"),
                    "deadline": task.get("deadline") or task.get("due_raw"),
                })
            else:
                # Convert from title format
                eval_task = convert_task_to_eval_format({
                    "title": task.get("title", ""),
                    "owner": task.get("owner"),
                    "due": task.get("due_raw"),
                })
                gold_tasks_eval.append(eval_task)

        # Get received_at from row for date normalization
        received_at = row.get("sent_date") or row.get("date") or row.get("received_at")
        
        # Use eval script's prf_tasks function for main metrics
        precision, recall, f1 = prf_tasks(
            pred_tasks_eval,
            gold_tasks_eval,
            lenient=lenient,
            very_lenient=very_lenient,
            sim_threshold=sim_threshold,
            task_match_k=task_match_k,
            received_at=received_at,
        )
        
        # Calculate strict matches (exact JSON match after normalization)
        # This is used for strict_tp vs partial_tp distinction
        pred_set = set(json.dumps({
            "owner": _normalize_owner(t.get("owner")),
            "action": _normalize_text(t.get("action") or ""),
            "object": _normalize_text(t.get("object") or ""),
            "deadline": _normalize_date(t.get("deadline"), received_at=received_at),
        }, sort_keys=True) for t in pred_tasks_eval)
        
        gt_set = set(json.dumps({
            "owner": _normalize_owner(t.get("owner")),
            "action": _normalize_text(t.get("action") or ""),
            "object": _normalize_text(t.get("object") or ""),
            "deadline": _normalize_date(t.get("deadline"), received_at=received_at),
        }, sort_keys=True) for t in gold_tasks_eval)
        
        strict_tp = len(pred_set & gt_set)
        
        # Calculate total TP/FP/FN using the same logic as prf_tasks
        # This ensures consistency with the precision/recall values
        total_pred = len(pred_tasks_eval)
        total_gt = len(gold_tasks_eval)
        
        if not very_lenient:
            # For strict/lenient mode, use set-based matching
            total_tp = len(pred_set & gt_set)
            total_fp = len(pred_set - gt_set)
            total_fn = len(gt_set - pred_set)
        else:
            # For very_lenient mode, use greedy matching (same as prf_tasks)
            used_gt = set()
            total_tp = 0
            for p in pred_tasks_eval:
                best_j = None
                best_score = -1
                for j, g in enumerate(gold_tasks_eval):
                    if j in used_gt:
                        continue
                    match_count = 0
                    # owner
                    if _normalize_owner(p.get("owner")) == _normalize_owner(g.get("owner")) or (
                        _normalize_owner(p.get("owner")) in {"me", ""} and _normalize_owner(g.get("owner")) in {"me", ""}
                    ):
                        match_count += 1
                    # action
                    if _similarity(p.get("action") or "", g.get("action") or "") >= sim_threshold:
                        match_count += 1
                    # object
                    if _similarity(p.get("object") or "", g.get("object") or "") >= sim_threshold:
                        match_count += 1
                    # deadline
                    if _normalize_date(p.get("deadline"), received_at=received_at) == _normalize_date(g.get("deadline"), received_at=received_at):
                        match_count += 1
                    if match_count > best_score:
                        best_score = match_count
                        best_j = j
                if best_j is not None and best_score >= task_match_k:
                    total_tp += 1
                    used_gt.add(best_j)
            total_fp = max(0, total_pred - total_tp)
            total_fn = max(0, total_gt - total_tp)
        
        # Partial TP is total TP minus strict TP
        partial_tp = max(0, total_tp - strict_tp)
        
        strict_tp_total += strict_tp
        partial_tp_total += partial_tp
        fp_total += total_fp
        fn_total += total_fn
        
        # Owner and due accuracy (informational) - use greedy matching from prf_tasks logic
        # Match tasks using the same logic as prf_tasks
        used_gt = set()
        for p in pred_tasks_eval:
            best_j = None
            best_score = -1
            for j, g in enumerate(gold_tasks_eval):
                if j in used_gt:
                    continue
                match_count = 0
                # owner
                if _normalize_owner(p.get("owner")) == _normalize_owner(g.get("owner")) or (
                    _normalize_owner(p.get("owner")) in {"me", ""} and _normalize_owner(g.get("owner")) in {"me", ""}
                ):
                    match_count += 1
                # action
                if very_lenient:
                    if _similarity(p.get("action") or "", g.get("action") or "") >= sim_threshold:
                        match_count += 1
                else:
                    if _normalize_text(p.get("action") or "") == _normalize_text(g.get("action") or ""):
                        match_count += 1
                # object
                if very_lenient:
                    if _similarity(p.get("object") or "", g.get("object") or "") >= sim_threshold:
                        match_count += 1
                else:
                    if _normalize_text(p.get("object") or "") == _normalize_text(g.get("object") or ""):
                        match_count += 1
                # deadline
                if _normalize_date(p.get("deadline"), received_at=received_at) == _normalize_date(g.get("deadline"), received_at=received_at):
                    match_count += 1
                if match_count > best_score:
                    best_score = match_count
                    best_j = j
            if best_j is not None and best_score >= task_match_k:
                # This is a matched task
                owner_total_total += 1
                g = gold_tasks_eval[best_j]
                if _normalize_owner(p.get("owner")) == _normalize_owner(g.get("owner")) or (
                    _normalize_owner(p.get("owner")) in {"me", ""} and _normalize_owner(g.get("owner")) in {"me", ""}
                ):
                    owner_correct_total += 1
                used_gt.add(best_j)
        
        # Due date correctness (using eval script's function)
        due_score = due_date_correctness(pred_tasks_eval, gold_tasks_eval)
        due_match_list.append(due_score)
        if due_score > 0:
            due_correct_total += 1
        due_total_total += 1

    _report_examples(fn_examples[:max_examples], fp_examples[:max_examples])

    return EvalResult(
        strict_tp_total,
        partial_tp_total,
        fp_total,
        fn_total,
        owner_correct_total,
        owner_total_total,
        due_correct_total,
        due_total_total,
    )


async def _load_jsonl_async(path: Path):
    loop = asyncio.get_running_loop()

    def read_lines() -> List[str]:
        with path.open("r", encoding="utf-8") as file:
            return file.readlines()

    lines = await loop.run_in_executor(None, read_lines)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


async def _iterate_cases(cases: List[Dict[str, Any]]):
    for case in cases:
        yield case


def _report_examples(fn_examples: List[Dict[str, Any]], fp_examples: List[Dict[str, Any]]) -> None:
    if fn_examples:
        print("\nSample FN cases:")
        for example in fn_examples:
            print(
                "  - "
                f"id={example.get('email_id')} | subject={example.get('subject')!r} | "
                f"title={example.get('title')!r} | due_raw={example.get('due_raw')!r} | "
                f"owner={example.get('owner')!r}"
            )
    if fp_examples:
        print("\nSample FP cases:")
        for example in fp_examples:
            print(
                "  - "
                f"id={example.get('email_id')} | subject={example.get('subject')!r} | "
                f"title={example.get('title')!r} | due_iso={example.get('due_iso')!r} | "
                f"owner={example.get('owner')!r}"
            )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate extractor tasks against gold data.")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("tests/data/extractor_gold.jsonl"),
        help="Path to JSONL file with gold annotations.",
    )
    parser.add_argument(
        "--agent",
        required=True,
        help="Extractor function in 'module:function' format.",
    )
    parser.add_argument(
        "--lenient",
        action="store_true",
        help="Use lenient matching (normalized text/date) for metrics",
    )
    parser.add_argument(
        "--very_lenient",
        action="store_true",
        help="Use similarity-based matching for tasks (k-of-4 fields matching)",
    )
    parser.add_argument(
        "--sim_threshold",
        type=float,
        default=0.75,
        help="Similarity threshold for very-lenient mode (stricter: 0.75).",
    )
    parser.add_argument(
        "--task_match_k",
        type=int,
        default=3,
        help="Fields (of 4) required to match a task in very-lenient mode (stricter: 3).",
    )
    parser.add_argument(
        "--max_examples",
        type=int,
        default=5,
        help="Maximum number of FP/FN examples to print.",
    )
    parser.add_argument(
        "--builtin_cases",
        choices=["long", "medium", "extra", "all"],
        help="Use built-in synthetic cases (long, medium, extra, or all) instead of loading JSONL data.",
    )

    args = parser.parse_args()

    agent = load_agent(args.agent)

    dataset = _build_builtin_cases(args.builtin_cases) if args.builtin_cases else None

    if dataset is None and not args.data.exists():
        raise FileNotFoundError(f"Data file not found: {args.data}")

    result = await evaluate_dataset(
        data_path=args.data,
        agent=agent,
        title_thresh=0.5,  # Not used anymore, kept for compatibility
        tolerance_minutes=60,  # Not used anymore, kept for compatibility
        max_examples=args.max_examples,
        dataset=dataset,
        lenient=args.lenient,
        very_lenient=args.very_lenient,
        sim_threshold=args.sim_threshold,
        task_match_k=args.task_match_k,
    )

    print("\nEvaluation Summary")
    print("------------------")
    print(f"TP (strict matches): {result.strict_tp}")
    print(f"TP (partial matches): {result.partial_tp}")
    print(f"TP (total): {result.tp}")
    print(f"FP: {result.fp}")
    print(f"FN: {result.fn}")
    print(f"Task Precision: {result.precision:.4f}")
    print(f"Task Recall: {result.recall:.4f}")
    print(f"Task F1: {result.f1:.4f}")
    owner_acc = result.owner_accuracy
    due_acc = result.due_accuracy
    if owner_acc is not None:
        print(f"Owner match rate (informational): {owner_acc:.4f}")
    else:
        print("Owner match rate (informational): N/A")
    if due_acc is not None:
        print(f"Due match rate (informational): {due_acc:.4f}")
    else:
        print("Due match rate (informational): N/A")


if __name__ == "__main__":
    asyncio.run(main())
