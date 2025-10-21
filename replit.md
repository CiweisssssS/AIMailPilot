# AI Email Assistant - Web Application & Gmail Add-on

## Overview

An AI-powered email assistant with **dual deployment modes**:
1. **Web Application** (Current): React + Tailwind frontend with Gmail OAuth integration for rapid testing and iteration
2. **Gmail Add-on** (Future): Google Apps Script sidebar interface for production deployment

The system analyzes Gmail emails using **GPT-4o-mini** with a **hybrid rule-based + LLM architecture** for intelligent priority classification (P1/P2/P3), one-sentence summaries, and structured task extraction in `[verb + object + owner + due]` format.

**Recent Changes (Oct 21, 2025)**:
- Pivoted to Web Application for faster testing workflow vs. Apps Script deployment
- **Implemented custom Google OAuth 2.0 flow** with comprehensive security improvements:
  - Dynamic redirect URI construction from HTTP request headers (protocol + host)
  - Express trust proxy configuration for correct HTTPS detection behind proxies
  - **State parameter CSRF protection**: Cryptographically secure random state (32-byte hex) generation, session storage, and verification
  - **Session fixation mitigation**: Session ID regeneration upon successful authentication
  - Secure cookie configuration (httpOnly, sameSite=lax, secure in production)
- Added Express session management with secure token storage and automatic refresh
- Created authentication routes: `/auth/google`, `/auth/google/callback`, `/api/auth/status`, `/api/auth/logout`
- **Implemented complete three-column UI layout**:
  - Left sidebar: Gmail-style navigation with lucide-react icons (Inbox/To-Do/Starred/Draft/Sent/Archive/Trash)
  - Center panel: Gmail-style email list with avatar, subject, preview, and time
  - Right panel: AIMailPilot intelligent assistant with 5-layer navigation system
- **Built all 5 AIMailPilot layers** matching Figma design specifications:
  - Layer 1a: Inbox Reminder with Urgent/To-Do/FYI priority cards
  - Layer 1b: Task & Schedule timeline view (Today/This Week/In one month)
  - Layer 2: Category Detail view with email list and action buttons
  - Layer 3: AI Chatbot with message input and send functionality
  - Layer 4: Customize Priorities for tag management
  - Layer 5: Flagged Mails view with category labels and timestamps
- Applied consistent **purple theme** (主紫色 #5B2C6F) using semantic CSS variables
- Replaced all emoji with lucide-react icons for professional UI consistency
- Enhanced GPT-4o-mini prompts with clear P1/P2/P3 classification criteria
- Enforced task extraction format `[verb + object + owner + due]` with examples
- Created `/triage` endpoint for batch email analysis

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture (Web App)

**Framework**: React 18 + TypeScript with Vite build system

**State Management**: 
- TanStack Query v5 for server state and cache management
- React hooks (useState) for local UI state
- Authentication state managed via `/api/auth/status` endpoint

**Routing**: Wouter for client-side routing (currently single-page app)

**Authentication Flow**:
1. Check authentication status on mount via `/api/auth/status`
2. Show login screen with "Sign in with Google" button if unauthenticated
3. Redirect to `/auth/google` → Google OAuth consent → callback to `/auth/google/callback`
4. Store tokens in Express session, redirect to home page
5. Display user email in header with logout button when authenticated

**UI Components**: Shadcn UI (Radix primitives) + Tailwind CSS + Lucide React icons

**Three-Column Layout**:
- **Left Sidebar** (240px): Gmail navigation with folder icons, unread counts, Settings button
- **Middle Panel** (384px): Email list with search, category filters (Important/Updates/Promotions), and scrollable email items
- **Right Panel** (flexible): AIMailPilot assistant with layer-based navigation

**5-Layer Navigation System**:
1. **Inbox Reminder (Layer 1a)**: Default view with greeting, unread count, tab switcher, Urgent/To-Do/FYI cards showing latest email previews, "add more tags" button, floating bookmark/refresh buttons
2. **Task & Schedule (Layer 1b)**: Timeline view grouped by Today/This Week/In one month, with calendar icon for adding events
3. **Category Detail (Layer 2)**: Displays filtered email list for selected category (Urgent/To-Do/FYI), back button, checkbox for completion, flag button, "Add to Calendar" action, chatbot entry button
4. **AI Chatbot (Layer 3)**: Conversational interface with welcome message, example prompts, message input with Enter key support, send button with validation
5. **Customize Priorities (Layer 4)**: Tag list editor with sort button, edit icons, "add more tags" button, Finish button
6. **Flagged Mails (Layer 5)**: Dedicated view for bookmarked emails with category labels, flagged timestamps, chatbot entry button

**Key Features**:
- Real-time authentication state checking via session cookies
- Layer-based navigation with state management (back button, tab switching)
- Priority-based email categorization (P1 Urgent/P2 To-Do/P3 FYI)
- Floating action buttons for quick access (bookmark, refresh)
- Responsive design with purple theme (#5B2C6F primary color)
- Professional lucide-react icons throughout (no emoji)

### Frontend Architecture (Gmail Add-on - Future)

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

**Authentication Endpoints** (Express.js):
- `GET /auth/google`: Initiates OAuth flow, redirects to Google consent screen
- `GET /auth/google/callback`: Handles OAuth callback, exchanges code for tokens, stores in session
- `GET /api/auth/status`: Returns authentication status and user info from session
- `POST /api/auth/logout`: Destroys session and clears cookies

**Email Processing Endpoints** (Express.js):
- `GET /api/fetch-gmail-emails`: Fetches emails from Gmail API using session tokens (returns 401 if not authenticated)
- `POST /api/analyze-emails`: Proxies to Python backend `/triage` endpoint for AI analysis

**Analysis Endpoints** (FastAPI/Python):
- `POST /triage`: Complete batch email analysis pipeline (normalize → summarize → extract → prioritize)
- `POST /api/process-thread`: Single thread analysis (legacy, for Gmail Add-on)
- `POST /api/chatbot-qa`: Conversational Q&A grounded in thread context
- `POST /api/update-user-settings`: Manage personalized keyword weights
- `GET /healthz`, `GET /version`: Service health monitoring

**Data Models**: Pydantic schemas with Zod validation on frontend, ensuring type safety across stack

**Session Management**: 
- Express-session with in-memory store (development only - **production requires Redis/persistent store**)
- Secure HTTP-only cookies with 7-day expiration
- Automatic token refresh via Google OAuth2 client event handlers

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

**Gmail API**: 
- Web App: Custom OAuth 2.0 flow with `gmail.readonly`, `userinfo.email`, `userinfo.profile` scopes
- Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET from Google Cloud Console
- Add-on (future): Advanced service enabled in Apps Script for email thread retrieval and metadata access

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