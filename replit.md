# AI Email Assistant - Gmail Workspace Add-on

## Overview

An AI-powered email assistant designed as a Gmail Workspace Add-on with a Python FastAPI backend and Google Apps Script frontend. The system provides inbox-level intelligence through a **5-layer sidebar interface** that analyzes multiple emails using **delta fetch + "Read = Processed" strategy**. Analysis uses **GPT-4o-mini** with a **hybrid rule-based + LLM architecture** for intelligent email prioritization, summarization, and task extraction.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Framework**: Google Apps Script with Gmail Add-on Cards UI framework

**State Management**: PropertiesService for persistent storage (LAST_OPEN_TS, SAVED_THREAD_IDS, FLAGGED_THREAD_IDS, CUSTOM_TAGS) + CacheService for in-memory caching with 5-minute TTL

**5-Layer Navigation**:
1. **Inbox Overview** - Category breakdown (Urgent/To-do/FYI) + Saved for Later section
2. **Category Details** - Filtered email list with actions (Save for Later/Flag/Mark as Done)
3. **Chatbot Q&A** - RAG-powered chatbot using backend embedding/retrieval pipeline
4. **Settings** - Customize tags and keywords for personalized prioritization
5. **Flagged Mails** - Dedicated view for all flagged emails across categories

**"Read = Processed" Strategy**: Core principle - read emails are automatically hidden UNLESS explicitly saved or flagged. Filters show only: unread emails OR saved emails OR flagged emails. Eliminates need for snooze/dismiss actions.

**Delta Fetch Strategy**: Fetches threads since last sidebar open OR last 7 days (first run), filters based on read status + saved/flagged state

**Design Philosophy**: Inbox-level intelligence (not single-email), "Read = Processed" core logic, stateful thread tracking, cache-optimized backend calls, persistent user preferences

### Backend Architecture

**Framework**: FastAPI with Uvicorn server (Python 3.11+)

**Service Layer Pattern**: Modular services for distinct responsibilities:
- **Normalizer**: Sorts messages chronologically, deduplicates, strips quoted replies and signatures
- **Summarizer**: GPT-4o-mini for intelligent summarization with subject-based fallback
- **Extractor**: GPT-4o-mini for task/owner/deadline extraction with validation and fallback handling
- **Prioritizer**: **Hybrid architecture** - Rule-based feature extraction (deadline_proximity, urgent_terms, request_terms, deescalators, noise_signals, sender_weight, direct_recipient) → GPT-4o-mini semantic classification → Fallback to weighted scoring on API errors
- **QA Service**: Prompt-based RAG using GPT-4o-mini with recent message snippets for context
- **User Settings**: SQLite-based custom tag storage

**Analysis Mode**: GPT-4o-mini (OpenAI API) with intelligent fallback mechanisms. When API calls fail, services gracefully degrade to rule-based heuristics ensuring continuous operation.

**AI Model**: **GPT-4o-mini** - OpenAI's lightweight model optimized for speed and cost
- Cost: $0.15/M input tokens, $0.60/M output tokens
- Temperature: 0.3-0.7 depending on task (lower for extraction, higher for summarization)
- Max tokens: 500 per request
- Retry strategy: Exponential backoff (3 attempts) via tenacity

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
- `StateManager.gs`: PropertiesService wrapper for persistent state (saved/flagged threads)
- `GmailFetcher.gs`: Delta fetch + "Read = Processed" filter logic
- `CacheManager.gs`: In-memory caching with TTL
- `BackendClient.gs`: HTTP client for FastAPI backend
- `Config.gs`: Backend URL configuration
- `InboxReminderCard.gs`: Layer 1 - Inbox overview with Saved for Later section
- `CategoryExpandedCard.gs`: Layer 2 - Email list with Save/Flag/Done actions
- `ChatbotCardNew.gs`: Layer 3 - RAG-powered Q&A interface
- `SettingsCard.gs`: Layer 4 - Custom tags and keyword management
- `FlaggedMailCard.gs`: Layer 5 - Dedicated flagged emails view

**Deployment Model**: Google Workspace Add-on installed per user, communicating with Replit-hosted backend via secure HTTPS

**Data Strategy**: Time-window delta fetching (tracks `LAST_OPEN_TS`) combined with unresolved thread pool to prevent missed emails, LRU capping at 1000 threads, stored in PropertiesService

**Note**: Apps Script field names used in backend payloads: `from`, `to`, `subject`, `snippet`, `last_message` (not `from_` or `body`)

**Trigger Model**: Homepage trigger (sidebar open) - analyzes inbox immediately, no contextual email trigger

## External Dependencies

### Third-Party Services

**OpenAI API** (GPT-4o-mini): Primary AI engine for summarization, task extraction, and hybrid prioritization. API key stored in environment variables (OPENAI_API_KEY). Fallback mechanisms ensure system continues operating if API quota is exceeded or service is unavailable.

**Gmail API**: Advanced service enabled in Apps Script for email thread retrieval and metadata access.

### Key Python Libraries

- **FastAPI + Uvicorn**: Web framework and ASGI server
- **Pydantic**: Data validation and settings management
- **python-dateutil**: Natural language date parsing for deadline extraction
- **numpy + scikit-learn**: Feature extraction for priority scoring
- **httpx**: Async HTTP client for LLM API calls
- **tenacity**: Retry logic with exponential backoff
- **rapidfuzz**: Fuzzy text matching for QA retrieval and keyword matching
- **transformers**: Hugging Face transformers for NLP models
- **sentence-transformers**: Sentence embeddings for semantic search
- **torch**: PyTorch backend for model inference (CPU-only)
- **tokenizers**: Fast tokenization for transformer models

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