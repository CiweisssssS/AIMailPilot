# AI Email Assistant - Gmail Workspace Add-on

## Overview

An AI-powered email assistant designed as a Gmail Workspace Add-on with a Python FastAPI backend and Google Apps Script frontend. The system provides inbox-level intelligence through a 4-layer sidebar interface that analyzes multiple emails using delta fetch + unresolved pool strategy. All analysis is heuristic-based (no paid LLM APIs required).

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Framework**: Google Apps Script with Gmail Add-on Cards UI framework

**State Management**: PropertiesService for persistent storage (LAST_OPEN_TS, UNRESOLVED_THREAD_IDS, SNOOZED_UNTIL, DISMISSED_SET, USER_KEYWORDS) + CacheService for in-memory caching with 5-minute TTL

**4-Layer Navigation**:
1. **Inbox Reminder** - Category overview (Urgent/To-do/FYI) with display mode toggle (New/Unresolved/All)
2. **Category Expanded** - Filtered email list with actions (Open/Mark as Done/Snooze/Dismiss)
3. **Chatbot Q&A** - Context-aware questions using already-extracted data
4. **Keyword Settings** - Customize priority keywords with High/Medium/Low weights

**Delta Fetch Strategy**: Fetches threads since last sidebar open OR last 7 days (first run), merges with unresolved pool, filters out snoozed/dismissed threads

**Design Philosophy**: Inbox-level intelligence (not single-email), stateful thread tracking, cache-optimized backend calls, persistent user preferences

### Backend Architecture

**Framework**: FastAPI with Uvicorn server (Python 3.11+)

**Service Layer Pattern**: Modular services for distinct responsibilities:
- **Normalizer**: Sorts messages chronologically, deduplicates, strips quoted replies and signatures
- **Summarizer**: Map-reduce summarization with LLM or rule-based fallback
- **Extractor**: Pattern-matching for tasks, owners, dates/deadlines with optional LLM enhancement
- **Prioritizer**: Score-based classification (P1 Urgent / P2 To-do / P3 FYI) using deadline proximity, sender importance, meeting detection, and personalized keyword weights
- **QA Service**: RAG-lite chatbot using fuzzy text matching for retrieval and LLM for answer generation
- **User Settings**: SQLite-based keyword preference storage

**Analysis Mode**: Fully heuristic-based (no LLM APIs) - rule-based summarization, regex task extraction, deadline proximity scoring, keyword matching with enum weights (High=2.0, Medium=1.0, Low=0.5)

**Data Flow**: Stateless request/response model - no email storage, only derived analysis results. User preferences persisted in SQLite.

**CORS Configuration**: Configured for Google Apps Script domains (script.google.com, script.googleusercontent.com, mail.google.com) and Replit deployment URLs

**Priority Thresholds**: P1 (Urgent) ≥ 0.75, P2 (To-do) ≥ 0.45, P3 (FYI) < 0.45

### API Design

**Core Endpoints**:
- `POST /api/process-thread`: Complete thread analysis pipeline (normalize → summarize → extract → prioritize)
- `POST /api/chatbot-qa`: Conversational Q&A grounded in thread context
- `POST /api/update-user-settings`: Manage personalized keyword weights
- `POST /api/batch-analyze`: Batch processing for inbox-level analysis
- `GET /healthz`, `GET /version`: Service health monitoring

**Data Models**: Pydantic schemas with Zod validation on frontend, ensuring type safety across stack

### Database Strategy

**SQLite**: Used exclusively for user settings (keyword weights, not email data)

**Schema**: Simple key-value store with `user_keywords` table (user_id, term, weight, scope)

**Note**: The application is configured for Drizzle ORM with PostgreSQL via `drizzle.config.ts` and uses `@neondatabase/serverless` in dependencies, indicating planned migration from SQLite to Postgres for production deployment.

### Google Apps Script Implementation

**Gmail Add-on Structure**: Cards UI framework with modular components:
- `Code.gs`: Homepage trigger entry point
- `StateManager.gs`: PropertiesService wrapper for persistent state
- `GmailFetcher.gs`: Delta fetch + unresolved pool logic
- `CacheManager.gs`: In-memory caching with TTL
- `BackendClient.gs`: HTTP client for FastAPI backend
- `Config.gs`: Backend URL configuration
- `InboxReminderCard.gs`: Layer 1 - Category overview
- `TaskScheduleCard.gs`: Layer 1 - Timeline view
- `CategoryExpandedCard.gs`: Layer 2 - Email list with actions
- `ChatbotCardNew.gs`: Layer 3 - Q&A interface
- `SettingsCard.gs`: Layer 4 - Keyword customization

**Deployment Model**: Google Workspace Add-on installed per user, communicating with Replit-hosted backend via secure HTTPS

**Data Strategy**: Time-window delta fetching (tracks `LAST_OPEN_TS`) combined with unresolved thread pool to prevent missed emails, LRU capping at 1000 threads, stored in PropertiesService

**Trigger Model**: Homepage trigger (sidebar open) - analyzes inbox immediately, no contextual email trigger

## External Dependencies

### Third-Party Services

**OpenAI API** (not used): System uses fully heuristic analysis - no paid LLM APIs required

**Gmail API**: Advanced service enabled in Apps Script for email thread retrieval and metadata access.

### Key Python Libraries

- **FastAPI + Uvicorn**: Web framework and ASGI server
- **Pydantic**: Data validation and settings management
- **python-dateutil**: Natural language date parsing for deadline extraction
- **numpy + scikit-learn**: Feature extraction for priority scoring
- **httpx**: Async HTTP client for LLM API calls
- **tenacity**: Retry logic with exponential backoff
- **rapidfuzz**: Fuzzy text matching for QA retrieval and keyword matching

### Key JavaScript/TypeScript Libraries (Frontend Dev Environment - Not Used in Gmail Add-on)

Note: The Gmail Add-on uses Google Apps Script (JavaScript ES5/ES6), not the React/TypeScript frontend. These libraries are part of the development environment but not deployed:

- **React + Vite**: Frontend framework and build tooling
- **TanStack Query**: Server state management
- **Radix UI**: Accessible component primitives
- **Tailwind CSS**: Utility-first styling framework

### Database & ORM

- **Drizzle ORM**: TypeScript ORM configured for PostgreSQL
- **@neondatabase/serverless**: Neon Postgres serverless driver
- **sqlite3** (Python stdlib): Current user settings storage (SQLite)

### Development & Deployment

- **Replit**: Primary hosting platform with environment-based deployment
- **esbuild**: Server-side bundling for production
- **pytest**: Python testing framework
- **TypeScript**: Static type checking across frontend and shared schemas