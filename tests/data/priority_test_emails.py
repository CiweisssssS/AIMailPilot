from typing import List, Dict, Any


PRIORITY_TEST_EMAILS: List[Dict[str, Any]] = [
    # ---------- P1：强紧急、强 deadline ----------
    {
        "id": "p1_001",
        "subject": "P1 – Production outage on checkout service",
        "clean_body": (
            "Team,\n\n"
            "Checkout is DOWN for all EU customers. This is a P1 production outage.\n"
            "Please investigate immediately and restore service as fast as possible.\n"
            "I need an initial incident report within the next 30 minutes and a full report by EOD today.\n\n"
            "Do NOT wait for the next standup. Page SRE on-call and keep me posted every 15 minutes.\n"
        ),
        "from_": "cto@example.com",
        "to": ["you@example.com"],
        "cc": ["sre-oncall@example.com"],
        "sent_date": "2025-11-14T09:10:00Z",
        "gold_priority": "P1",
        "gold_reason": "Production outage, hard time pressure, P1 wording.",
    },
    {
        "id": "p1_002",
        "subject": "URGENT: Legal response needed before 5 PM",
        "clean_body": (
            "Hi,\n\n"
            "We received a notice from the regulator and must submit our response today.\n"
            "Please review the attached draft and send me your approved version no later than 5 PM today.\n"
            "If we miss this deadline, there may be financial penalties.\n\n"
            "Marked as URGENT – this cannot slip.\n"
        ),
        "from_": "legal@example.com",
        "to": ["you@example.com"],
        "cc": ["cfo@example.com"],
        "sent_date": "2025-11-14T11:20:00Z",
        "gold_priority": "P1",
        "gold_reason": "External legal deadline today, explicit urgent, high risk.",
    },
    {
        "id": "p1_003",
        "subject": "Client escalation – call in 1 hour",
        "clean_body": (
            "Hello,\n\n"
            "Our top-tier client, Alpha Corp, has escalated a critical issue.\n"
            "They scheduled a call with us in 1 hour to review impact and mitigation.\n"
            "Please join the bridge, prepare a short status summary, and have a proposal ready before the call.\n\n"
            "This is time-sensitive and directly affects renewal.\n"
        ),
        "from_": "account.manager@example.com",
        "to": ["you@example.com"],
        "cc": ["sales-director@example.com"],
        "sent_date": "2025-11-14T12:00:00Z",
        "gold_priority": "P1",
        "gold_reason": "Top client escalation, call within 1 hour.",
    },
    {
        "id": "p1_004",
        "subject": "[Action Required] Security incident triage",
        "clean_body": (
            "Security team,\n\n"
            "We detected suspicious login activity on several admin accounts.\n"
            "Please start incident triage immediately: freeze affected accounts, pull logs for the last 24 hours, "
            "and share a preliminary impact assessment within 2 hours.\n\n"
            "Treat this as high severity until proven otherwise.\n"
        ),
        "from_": "security@example.com",
        "to": ["you@example.com"],
        "cc": ["soc-oncall@example.com"],
        "sent_date": "2025-11-14T08:45:00Z",
        "gold_priority": "P1",
        "gold_reason": "Security incident with 2h SLA.",
    },
    {
        "id": "p1_005",
        "subject": "Last call: payroll corrections for this month",
        "clean_body": (
            "Hi,\n\n"
            "Today is the final cut-off for payroll corrections.\n"
            "If you have any adjustments, please submit them to HR by 3 PM local time.\n"
            "After that, the payroll run will be locked for this month.\n\n"
            "This is your last chance to fix salary or overtime records.\n"
        ),
        "from_": "hr-payroll@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-14T07:00:00Z",
        "gold_priority": "P1",
        "gold_reason": "Hard cut-off today affecting payroll.",
    },
    {
        "id": "p1_006",
        "subject": "Action needed: submit slides before tomorrow’s board meeting",
        "clean_body": (
            "Hi,\n\n"
            "The board meeting is tomorrow morning.\n"
            "Please finalize your slides and upload them to the shared deck by 8 PM tonight.\n"
            "We will not accept last-minute changes during the meeting.\n\n"
            "This is critical for the board review.\n"
        ),
        "from_": "ceo-office@example.com",
        "to": ["you@example.com"],
        "cc": ["strategy@example.com"],
        "sent_date": "2025-11-13T18:30:00Z",
        "gold_priority": "P1",
        "gold_reason": "Board meeting deadline within 24h.",
    },
    {
        "id": "p1_007",
        "subject": "P1 ticket: login API 500s spiking",
        "clean_body": (
            "On-call,\n\n"
            "Monitoring shows a spike in 500 errors on the login API for >30% of traffic.\n"
            "Please investigate logs, roll back the last deployment if necessary, "
            "and post updates in the incident channel every 10 minutes.\n\n"
            "This is a P1 ticket in the incident system.\n"
        ),
        "from_": "alerts@example.com",
        "to": ["you@example.com"],
        "cc": ["eng-manager@example.com"],
        "sent_date": "2025-11-14T09:40:00Z",
        "gold_priority": "P1",
        "gold_reason": "Critical service degradation (P1 alerts).",
    },
    {
        "id": "p1_008",
        "subject": "Visa document submission – today only",
        "clean_body": (
            "Dear employee,\n\n"
            "This is a reminder that today is the LAST DAY to submit your visa renewal documents.\n"
            "Please upload all required files to the HR portal before 6 PM.\n\n"
            "Missing this deadline may affect your legal working status.\n"
        ),
        "from_": "global-mobility@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-14T06:10:00Z",
        "gold_priority": "P1",
        "gold_reason": "Hard legal/immigration deadline today.",
    },
    {
        "id": "p1_009",
        "subject": "Customer refund deadline – resolve open cases",
        "clean_body": (
            "Hi support,\n\n"
            "Regulation requires that all pending refund tickets older than 7 days be resolved by midnight tonight.\n"
            "Please prioritize cases older than 5 days now and clear the backlog.\n\n"
            "Send me a summary once everything is completed.\n"
        ),
        "from_": "compliance@example.com",
        "to": ["you@example.com"],
        "cc": ["support-lead@example.com"],
        "sent_date": "2025-11-14T09:00:00Z",
        "gold_priority": "P1",
        "gold_reason": "Compliance deadline with strong time pressure.",
    },
    {
        "id": "p1_010",
        "subject": "Hotfix must be deployed before tomorrow’s launch",
        "clean_body": (
            "Team,\n\n"
            "We identified a blocker bug in the onboarding flow for tomorrow’s public launch.\n"
            "Engineering must ship a hotfix to production tonight, and QA needs to verify it in staging beforehand.\n\n"
            "If this is not fixed before launch, we should postpone.\n"
        ),
        "from_": "product@example.com",
        "to": ["you@example.com"],
        "cc": ["eng-lead@example.com", "qa-lead@example.com"],
        "sent_date": "2025-11-14T15:00:00Z",
        "gold_priority": "P1",
        "gold_reason": "Launch-blocker bug with explicit tonight deadline.",
    },
    # ---------- P2：重要但不是立刻爆炸 ----------
    {
        "id": "p2_001",
        "subject": "Please review Q4 OKR draft by next Wednesday",
        "clean_body": (
            "Hi team,\n\n"
            "I've attached the first draft of our Q4 OKRs.\n"
            "Please review the document and add your comments by next Wednesday.\n"
            "We will finalize the goals in our planning meeting next Thursday.\n"
        ),
        "from_": "manager@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-14T10:00:00Z",
        "gold_priority": "P2",
        "gold_reason": "Clear action and deadline, but not immediate.",
    },
    {
        "id": "p2_002",
        "subject": "Action: update your training progress",
        "clean_body": (
            "Hello,\n\n"
            "Please log into the LMS and mark your progress on the new data protection training.\n"
            "We'd like everyone to complete it within the next two weeks.\n\n"
            "This is required for annual compliance, but there is still time.\n"
        ),
        "from_": "learning@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-10T08:00:00Z",
        "gold_priority": "P2",
        "gold_reason": "Required task with medium-term deadline.",
    },
    {
        "id": "p2_003",
        "subject": "Product feedback needed for roadmap planning",
        "clean_body": (
            "Hi,\n\n"
            "We are preparing the H1 roadmap and need input from each team.\n"
            "Please summarize the top 3 customer requests from your area and send them to me by the end of next week.\n"
            "We will use this to prioritize roadmap themes.\n"
        ),
        "from_": "head-of-product@example.com",
        "to": ["you@example.com"],
        "cc": ["pm-team@example.com"],
        "sent_date": "2025-11-14T09:30:00Z",
        "gold_priority": "P2",
        "gold_reason": "Planning-related, important but not urgent.",
    },
    {
        "id": "p2_004",
        "subject": "Reminder: complete performance self-review",
        "clean_body": (
            "Hi,\n\n"
            "This is a reminder to complete your performance self-review in the HR system.\n"
            "Please submit it by the end of this month so your manager has time to review before the calibration meeting.\n"
        ),
        "from_": "hr@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-05T12:00:00Z",
        "gold_priority": "P2",
        "gold_reason": "Required HR task within a couple of weeks.",
    },
    {
        "id": "p2_005",
        "subject": "Please clean up stale Jira tickets",
        "clean_body": (
            "Team,\n\n"
            "Our Jira board has many stale tickets.\n"
            "Over the next week, please review your open items, close anything that's no longer relevant, "
            "and add comments to clarify status where needed.\n\n"
            "We'll look at the cleaned-up board in next Friday's standup.\n"
        ),
        "from_": "eng-manager@example.com",
        "to": ["you@example.com"],
        "cc": ["team@example.com"],
        "sent_date": "2025-11-14T10:15:00Z",
        "gold_priority": "P2",
        "gold_reason": "Action required, moderate time window.",
    },
    {
        "id": "p2_006",
        "subject": "Schedule 1:1 to discuss growth plan",
        "clean_body": (
            "Hi,\n\n"
            "I'd like to schedule a 1:1 with you in the next week or two to talk about your growth plan and goals for next year.\n"
            "Please propose a few slots on my calendar.\n"
        ),
        "from_": "manager@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-14T13:00:00Z",
        "gold_priority": "P2",
        "gold_reason": "Important career conversation, flexible timing.",
    },
    {
        "id": "p2_007",
        "subject": "Prepare materials for internal demo day",
        "clean_body": (
            "Hello,\n\n"
            "We are hosting an internal demo day in three weeks.\n"
            "Please prepare a short demo of your recent work (5–7 minutes) and upload your slides to the shared folder at least three days before the event.\n"
        ),
        "from_": "innovation@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-01T09:00:00Z",
        "gold_priority": "P2",
        "gold_reason": "Time-bound but not urgent, clear action.",
    },
    {
        "id": "p2_008",
        "subject": "Follow-up: vendor evaluation survey",
        "clean_body": (
            "Hi,\n\n"
            "We're collecting feedback on our current analytics vendor.\n"
            "Please fill out the short survey and share any blockers you've experienced.\n"
            "We plan to close the survey by next Friday.\n"
        ),
        "from_": "procurement@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-11T10:30:00Z",
        "gold_priority": "P2",
        "gold_reason": "Decision-related task with a clear but non-urgent deadline.",
    },
    {
        "id": "p2_009",
        "subject": "Action: update documentation after release",
        "clean_body": (
            "Team,\n\n"
            "Now that v2.3 has shipped, we need to update the public documentation.\n"
            "Please review your feature areas and update examples, screenshots, and FAQs over the next 10 days.\n"
        ),
        "from_": "docs-lead@example.com",
        "to": ["you@example.com"],
        "cc": ["devrel@example.com"],
        "sent_date": "2025-11-14T16:00:00Z",
        "gold_priority": "P2",
        "gold_reason": "Post-release work, important but with buffer.",
    },
    {
        "id": "p2_010",
        "subject": "Prepare quarterly budget forecast",
        "clean_body": (
            "Hi,\n\n"
            "Finance is requesting updated forecasts for next quarter.\n"
            "Please send me your team’s projected spend and major cost items within the next 10 days.\n"
            "We’ll consolidate and share with the CFO afterwards.\n"
        ),
        "from_": "finance-bp@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-14T11:45:00Z",
        "gold_priority": "P2",
        "gold_reason": "Forecasting task with medium-term deadline.",
    },
    # ---------- P3：低优先级 / 纯信息 / 社交 ----------
    {
        "id": "p3_001",
        "subject": "Team lunch photos from yesterday",
        "clean_body": (
            "Hi team,\n\n"
            "Here are the photos from our team lunch yesterday.\n"
            "No action needed — just sharing for fun.\n"
        ),
        "from_": "teammate@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-13T14:00:00Z",
        "gold_priority": "P3",
        "gold_reason": "Purely informational / social.",
    },
    {
        "id": "p3_002",
        "subject": "Newsletter: Product updates – November",
        "clean_body": (
            "Hello,\n\n"
            "This is our monthly product newsletter.\n"
            "In this issue, we highlight several new features, customer stories, and upcoming events.\n"
            "You don't need to reply, but feel free to reach out if you have questions.\n"
        ),
        "from_": "newsletter@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-01T09:00:00Z",
        "gold_priority": "P3",
        "gold_reason": "Generic newsletter, no required action.",
    },
    {
        "id": "p3_003",
        "subject": "Office coffee machine maintenance complete",
        "clean_body": (
            "Hi all,\n\n"
            "Facilities here. The coffee machines on floors 3–5 have been serviced and are back online.\n"
            "No action required on your side.\n"
        ),
        "from_": "facilities@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-12T07:30:00Z",
        "gold_priority": "P3",
        "gold_reason": "FYI facility update.",
    },
    {
        "id": "p3_004",
        "subject": "Social event: game night next month",
        "clean_body": (
            "Hi team,\n\n"
            "We’re planning an informal game night at the office next month.\n"
            "If you’re interested, you can RSVP via the optional calendar invite.\n"
            "Attendance is completely optional.\n"
        ),
        "from_": "office-admin@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-03T15:00:00Z",
        "gold_priority": "P3",
        "gold_reason": "Optional social event, no real urgency.",
    },
    {
        "id": "p3_005",
        "subject": "FYI: blog post about our design system",
        "clean_body": (
            "Hi,\n\n"
            "We just published a new blog post about our design system.\n"
            "If you're curious, you can read it here.\n"
            "No need to take any action.\n"
        ),
        "from_": "design@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-07T10:10:00Z",
        "gold_priority": "P3",
        "gold_reason": "Content sharing, non-actionable.",
    },
    {
        "id": "p3_006",
        "subject": "Auto notification: ticket assigned",
        "clean_body": (
            "This is an automatic notification from the ticketing system.\n"
            "A low-priority documentation ticket has been assigned to your queue.\n"
            "There is no strict due date; please address it when you have time.\n"
        ),
        "from_": "no-reply@tickets.example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-09T12:00:00Z",
        "gold_priority": "P3",
        "gold_reason": "Explicitly low priority, no due date.",
    },
    {
        "id": "p3_007",
        "subject": "Recording: last week’s all-hands",
        "clean_body": (
            "Hi all,\n\n"
            "The recording of last week’s all-hands meeting is now available.\n"
            "If you couldn’t attend live, you can watch it at your convenience.\n"
            "No follow-up actions are required.\n"
        ),
        "from_": "internal-comms@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-10T09:00:00Z",
        "gold_priority": "P3",
        "gold_reason": "Recording link, optional viewing.",
    },
    {
        "id": "p3_008",
        "subject": "Parking lot resurfacing this weekend",
        "clean_body": (
            "Dear colleagues,\n\n"
            "The main parking lot will be resurfaced this weekend.\n"
            "Please expect some noise on Saturday, but no action is needed from you.\n"
        ),
        "from_": "facilities@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-13T08:30:00Z",
        "gold_priority": "P3",
        "gold_reason": "Information-only notice.",
    },
    {
        "id": "p3_009",
        "subject": "Survey results: team satisfaction Q3",
        "clean_body": (
            "Hi team,\n\n"
            "Thank you for participating in the Q3 satisfaction survey.\n"
            "The aggregated results are attached for your reference.\n"
            "There is nothing you need to do right now.\n"
        ),
        "from_": "people-ops@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-02T11:00:00Z",
        "gold_priority": "P3",
        "gold_reason": "Sharing results, no explicit task.",
    },
    {
        "id": "p3_010",
        "subject": "Just a thank-you note",
        "clean_body": (
            "Hi,\n\n"
            "I just wanted to say thank you for your help on the project last week.\n"
            "No action needed, just appreciation.\n"
        ),
        "from_": "colleague@example.com",
        "to": ["you@example.com"],
        "cc": [],
        "sent_date": "2025-11-14T17:30:00Z",
        "gold_priority": "P3",
        "gold_reason": "Pure gratitude email, no task.",
    },
]

