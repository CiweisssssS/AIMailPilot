# Gmail Add-on Deployment Guide

## Overview

Your AI Email Assistant Gmail Add-on is now complete! This guide will walk you through deploying and testing the 4-layer sidebar interface.

## Architecture Summary

### Backend (FastAPI on Port 8000)
- **Heuristic-based analysis** (no paid LLM APIs required)
- Endpoints:
  - `POST /api/batch-analyze` - Processes multiple threads in chunks of 5
  - `POST /api/prioritize` - Calculates P1/P2/P3 priority using deadline proximity, sender importance, and keyword matching
  - `POST /api/summarize` - Generates quick summaries from subject + last sentence
  - `POST /api/extract-tasks` - Extracts tasks with regex + natural language date parsing
  - `POST /api/update-user-settings` - Syncs keyword preferences

### Frontend (Google Apps Script)
- **4-Layer Sidebar Interface**:
  1. **Inbox Reminder** - Category overview (Urgent/To-do/FYI) with display mode toggle
  2. **Category Expanded** - Filtered email list with actions (Open/Done/Snooze/Dismiss)
  3. **Chatbot Q&A** - Context-aware questions using already-extracted data
  4. **Keyword Settings** - Customize priority keywords with High/Medium/Low weights

- **State Management**:
  - Delta fetch (only new emails since last open)
  - Unresolved pool (tracks in-progress threads)
  - Persistent storage via PropertiesService
  - In-memory cache with 5-minute TTL

## Deployment Steps

### 1. Deploy Replit Backend

Your Replit app is already running! To get the public URL:

1. Click the **Publish** button in the top-right corner
2. Choose "Reserved VM" deployment (required for multi-process Node.js + Python)
3. Wait for deployment to complete
4. Copy your deployment URL (e.g., `https://your-app.replit.app`)

### 2. Configure Apps Script Backend URL

Update the backend URL in `apps-script/Config.gs`:

```javascript
const BACKEND_BASE_URL = 'https://your-app.replit.app';
```

Replace `your-app.replit.app` with your actual Replit deployment URL.

### 3. Deploy Google Apps Script

1. Open [Google Apps Script](https://script.google.com/)
2. Create a new project called "AI Email Assistant"
3. Copy all files from `apps-script/` folder to the project:
   - Code.gs
   - StateManager.gs
   - GmailFetcher.gs
   - CacheManager.gs
   - BackendClient.gs
   - Config.gs
   - InboxReminderCard.gs
   - TaskScheduleCard.gs
   - CategoryExpandedCard.gs
   - ChatbotCardNew.gs
   - SettingsCard.gs
   - appsscript.json

4. Enable Advanced Services:
   - Click on the "+" next to Services
   - Add "Gmail API"

5. Deploy as Gmail Add-on:
   - Click **Deploy** > **Test Deployments**
   - Select "Gmail Add-on"
   - Click **Install**

### 4. Test in Gmail

1. Open Gmail in your browser
2. Look for the add-on icon in the right sidebar
3. Click to open the AI Email Assistant

**Expected Flow:**

1. **Sidebar Opens** → Shows Inbox Reminder with category breakdown
   - Toggle between "New since last open" / "Unresolved only" / "All"
   - See counts for Urgent (P1), To-do (P2), FYI (P3)

2. **Click a Category** → Opens expanded view with email list
   - Each email shows: Subject, Summary, Priority, Timestamp
   - Actions: Open, Mark as Done, Snooze, Dismiss

3. **Click "Ask Assistant"** → Opens chatbot interface
   - Quick questions: "What are my top 3 urgent tasks?"
   - Custom questions: "Any deadlines this week?"

4. **Click "Settings"** → Opens keyword customization
   - Add keywords with High/Medium/Low weights
   - Choose scope: Subject / Body / Everywhere
   - Delete individual keywords or clear all

## Key Features

### Delta Fetch Strategy
- First run: Fetches last 7 days of threads
- Subsequent runs: Only fetches threads since last sidebar open
- Merges with unresolved pool to ensure nothing is missed
- Updates `LAST_OPEN_TS` timestamp after each fetch

### Priority Scoring
- **P1 (Urgent)**: Score ≥ 0.75
  - Deadlines within 48 hours
  - High-priority keywords in subject/body
  - Important senders (boss, executives)

- **P2 (To-do)**: Score ≥ 0.45
  - Deadlines this week
  - Meeting invitations
  - Medium-priority keywords

- **P3 (FYI)**: Score < 0.45
  - No urgent keywords or deadlines
  - Informational emails

### Thread Actions
- **Mark as Done**: Removes from unresolved pool, clears cache
- **Snooze**: Hides until selected time (1h/3h/Tomorrow/Next week)
- **Dismiss**: Removes from view permanently

### Caching
- In-memory cache with 5-minute TTL
- Reduces redundant backend calls
- Cleared on thread actions (Done/Snooze/Dismiss)

## Troubleshooting

### Backend Not Responding
1. Check Replit deployment status
2. Verify URL in `Config.gs` matches deployment URL
3. Check CORS configuration in `app/main.py`

### No Emails Showing
1. Check Gmail API permissions are granted
2. Verify you have unread emails in your inbox
3. Try clicking "Refresh" button in the sidebar

### Priority Scoring Seems Off
1. Check keyword settings - add relevant terms
2. Use High/Medium/Low weights to adjust importance
3. Backend uses heuristics, not LLMs - results are deterministic

### Navigation Issues
1. Use back button provided by Gmail Add-on host
2. If stuck, close and reopen sidebar
3. Check browser console for JavaScript errors

## Next Steps

1. **Test thoroughly** - Open sidebar, navigate all 4 layers, test actions
2. **Customize keywords** - Add your specific urgent/important terms
3. **Monitor performance** - Check backend logs for errors
4. **Iterate** - Adjust priority thresholds if needed

## Architecture Notes

- **Stateless backend** - No email storage, only analysis results
- **Persistent frontend state** - PropertiesService stores timestamps, thread IDs, keywords
- **No LLM costs** - Fully heuristic-based analysis
- **Gmail Add-on limits** - Maximum 30-second execution time per function

Enjoy your AI Email Assistant! 🎉
