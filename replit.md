# AI Email Assistant - Web Application & Gmail Add-on

## Overview

This project is an AI-powered email assistant designed to enhance email management. It features **dual deployment modes**: a current **Web Application** (React + Tailwind with Gmail OAuth) for rapid iteration, and a future **Gmail Add-on** (Google Apps Script) for production. The system leverages **GPT-4o-mini** within a **hybrid rule-based + LLM architecture** to classify email priority (P1/P2/P3), generate one-sentence summaries, and extract structured tasks in `[verb + object + owner + due]` format. The core purpose is to streamline email processing, reduce cognitive load, and provide actionable insights directly from the inbox.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions

The web application features a **three-column UI layout** inspired by Gmail:
- **Left Sidebar**: Navigation with lucide-react icons (Inbox, To-Do, Starred, etc.)
- **Center Panel**: Email list with subject, preview, and time.
- **Right Panel**: **AIMailPilot intelligent assistant** with a **5-layer navigation system**:
    1.  **Inbox Reminder**: Priority cards (Urgent/To-Do/FYI), task timeline.
    2.  **Category Detail**: Filtered email lists with actions.
    3.  **AI Chatbot**: Conversational interface for email queries.
    4.  **Customize Priorities**: Tag management.
    5.  **Flagged Mails**: View for bookmarked emails.
A consistent **purple theme** (`#5B2C6F`) is applied using semantic CSS variables, and all emojis are replaced with professional `lucide-react` icons.

### Technical Implementations

The project uses a **monorepo architecture** with distinct frontend (React/TypeScript) and backend (FastAPI/Python) components.
-   **Frontend (Web App)**: Built with React 18, TypeScript, Vite, TanStack Query for server state, Wouter for routing, and Shadcn UI (Radix primitives) with Tailwind CSS for styling. It implements a custom, secure Google OAuth 2.0 flow with CSRF protection, session fixation mitigation, and secure cookie management.
-   **Backend (FastAPI)**: Implemented in Python 3.11+, following a **Service Layer Pattern** with modules for Normalizer, Summarizer, Extractor, Prioritizer, and QA. It uses **GPT-4o-mini** for AI tasks with intelligent fallback mechanisms (rule-based heuristics) for robustness. The AI models prioritize cost-effectiveness and speed.
-   **Gmail Add-on (Future)**: Will use Google Apps Script with the Cards UI framework, leveraging `PropertiesService` for persistent state and `CacheService` for in-memory caching. A core principle is "Read = Processed," where read emails are hidden unless explicitly saved or flagged.

### Feature Specifications

-   **Priority-based email classification**: P1 (Urgent) ≥ 0.75, P2 (To-do) ≥ 0.45, P3 (FYI) < 0.45.
-   **Structured Task Extraction**: Enforced format `[verb + object + owner + due]`.
-   **Hybrid AI Architecture**: Combines rule-based feature extraction (e.g., deadline proximity, urgent terms) with LLM semantic classification for robust prioritization.
-   **Authentication**: Secure Google OAuth 2.0 with Express session management.
-   **Data Flow**: Integrated Gmail API data fetching -> AI analysis -> UI rendering with real-time updates and error handling.
-   **Conversational AI**: Chatbot for interacting with email content.
-   **Customizable Priorities**: User-defined tags and keyword weighting for personalized prioritization.

### System Design Choices

-   **Stateless Request/Response Model**: No email content is stored persistently; only derived analysis results and user preferences.
-   **Scalability**: Designed for potential migration from SQLite to PostgreSQL using Drizzle ORM and Neon Database for production.
-   **Robustness**: Extensive error handling, retry mechanisms (exponential backoff), and fallback strategies for AI API calls.
-   **Security**: Comprehensive OAuth 2.0 security measures including CSRF, session fixation, and secure cookie practices.

## External Dependencies

### Third-Party Services

-   **OpenAI API**: Provides **GPT-4o-mini** for core AI functionalities (summarization, extraction, prioritization).
-   **Gmail API**: Used for fetching email data. Requires Google Cloud Console credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) and specific scopes (`gmail.readonly`, `userinfo.email`, `userinfo.profile`).

### Key Python Libraries

-   **FastAPI**: Backend web framework.
-   **Pydantic**: Data validation.
-   **python-dateutil**: Date parsing.
-   **numpy**, **scikit-learn**: Feature extraction for prioritization.
-   **httpx**, **tenacity**: HTTP client and retry logic for AI API calls.
-   **rapidfuzz**: Fuzzy text matching.
-   **transformers**, **sentence-transformers**, **torch**, **tokenizers**: For advanced NLP and embeddings (primarily for RAG-powered chatbot in add-on).

### Key JavaScript/TypeScript Libraries (Web App Frontend)

-   **React**, **Vite**: Frontend framework and build tool.
-   **TanStack Query**: Server state management.
-   **Radix UI**, **Tailwind CSS**: UI component primitives and styling.
-   **Wouter**: Client-side routing.

### Database & ORM

-   **SQLite**: Currently used for user settings (e.g., keyword weights).
-   **Drizzle ORM**: Configured for future PostgreSQL integration.
-   **@neondatabase/serverless**: Serverless PostgreSQL driver.

### Development & Deployment

-   **Replit**: Primary hosting and development environment.
-   **Google Apps Script**: Environment for Gmail Add-on development.