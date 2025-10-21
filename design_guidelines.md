# AIMailPilot - Gmail Smart Email Assistant - Design Guidelines

## Design Approach
**Selected Approach:** Material Design 3 with Gmail-inspired Information Architecture

**Justification:** As a Gmail-integrated productivity tool, the interface requires:
- Familiar Gmail-like navigation patterns for instant user recognition
- Dense information display across three panels
- Seamless AI insights integration without disrupting email workflow
- Professional elegance through sophisticated purple theming

**Primary References:** Gmail's three-pane layout + Linear's typography hierarchy + Notion's card aesthetics

---

## Core Design Elements

### A. Color Palette

**Light Mode:**
- Primary Purple: 285 47% 30% (Deep purple #5B2C6F - headers, CTAs, active states)
- Purple Accent: 285 40% 65% (Interactive elements, links)
- Card Background Lavender: 285 45% 94% (#E8D9F0 - elevated cards)
- Card Background Lilac: 285 35% 88% (#D4BAE0 - secondary cards)
- Surface White: 0 0% 100% (Main background)
- Border Subtle: 285 15% 85% (Dividers, panel separators)
- Text Primary: 285 25% 20% (Deep charcoal-purple)
- Text Secondary: 285 12% 50% (Muted purple-gray)
- AI Insight Badge: 160 60% 45% (Teal accent for AI features)
- Priority Urgent: 0 80% 58%
- Priority Important: 35 85% 55%
- Priority Normal: 285 12% 60%

**Dark Mode:**
- Primary Purple: 285 50% 70%
- Purple Accent: 285 45% 75%
- Card Background: 285 25% 18%
- Card Background Secondary: 285 20% 22%
- Surface: 285 18% 12%
- Border: 285 12% 30%
- Text Primary: 285 8% 95%
- Text Secondary: 285 10% 70%
- AI Insight Badge: 160 50% 55%

### B. Typography
**Font Stack:** 'Inter', 'Roboto', -apple-system, system-ui

**Hierarchy:**
- App Title: 24px/700 (Panel headers)
- Email Subject: 18px/600 (Email list items)
- Section Heading: 16px/600 (AI panel sections)
- Body Text: 15px/400 (Email content, summaries)
- List Item: 14px/500 (Sender names, metadata)
- Label/Badge: 13px/600 (Tags, categories)
- Caption: 12px/400 (Timestamps, counts)

### C. Layout System
**Spacing Primitives:** Tailwind units of 2, 4, 6, 8, 12

**Three-Column Desktop Layout:**
- Left Panel (Navigation): 240px fixed width, collapsible to 64px (icon-only)
- Middle Panel (Email List): 380px fixed width, scrollable
- Right Panel (AI Analysis): Flexible remaining space (min 480px)
- Panel separators: 1px border-r with subtle shadow

**Mobile Strategy:**
- Tab navigation switching between Inbox/Email/AI panels
- Floating action button for quick AI analysis
- Bottom navigation bar with 3 tabs

**Container Padding:**
- Panel internal: p-4
- Card internal: p-6
- List items: px-4 py-3

---

## Component Library

### 1. Left Navigation Panel

**Header Section:**
- App logo + "AIMailPilot" title in Primary Purple
- Gradient background: subtle vertical gradient (285 50% 98% to white)
- "Compose" button: Full-width, bg-primary-purple text-white, rounded-xl, font-semibold with plus icon

**Navigation Menu:**
- Icon + Label list items (Inbox, Starred, Sent, Drafts, etc.)
- Active state: bg-card-lavender with left border-l-4 border-primary-purple
- Hover state: bg-card-lavender/50
- Icon color: Primary purple for active, text-secondary for inactive
- Unread count badges: Small circular badges in AI teal color

**Labels Section:**
- Collapsible "Labels" header with chevron
- Color-coded label dots (8px circles) + label names
- Add label button at bottom

**AI Features Section:**
- "Smart Summaries" with sparkle icon
- "Task Extraction" with checklist icon
- "Priority Scoring" with gauge icon
- Divider line above this section

### 2. Middle Panel - Email List

**Search & Filter Bar:**
- Search input: rounded-full with search icon, bg-card-lavender
- Filter chips row: "All", "Unread", "Important" with active state in primary purple
- Sort dropdown: "Newest first" with chevron

**Email List Items:**
- Card-style items: rounded-lg mb-2 p-4 bg-white hover:bg-card-lavender/30
- Left section: Checkbox + Star icon + Sender avatar (32px circular)
- Middle section: 
  - Sender name (font-semibold) + timestamp (text-xs text-secondary) in flex row
  - Subject line (font-medium, max 1 line truncate)
  - Preview snippet (text-sm text-secondary, max 2 lines)
  - AI insight badge: Small pill "3 tasks • P1" in teal with shimmer effect
- Right section: Priority indicator dot + Attachment icon if present
- Active/Selected state: bg-card-lilac border-l-4 border-primary-purple

**Unread Styling:**
- Bold sender name and subject
- Purple dot indicator (6px) before sender avatar

**Loading State:**
- Skeleton cards with shimmer animation in card-lavender

### 3. Right Panel - AI Analysis

**Email Display Section:**
- Email header card: bg-white rounded-xl p-6 mb-4 shadow-sm
  - Large sender avatar (48px) + name (text-xl font-semibold)
  - Subject line (text-2xl font-bold text-primary-purple)
  - Metadata row: timestamp, recipient count, reply chain indicator
  - Action buttons row: Reply, Forward, Archive (outline style)
- Email body: Rich text with proper spacing, quoted text indented with border-l-2

**AI Insights Panel (Sticky Below Header):**
- Gradient card: bg-gradient-to-br from-card-lavender to-card-lilac rounded-2xl p-6 shadow-lg
- "AI Analysis" header with sparkle icon
- Priority badge hero: Large pill with icon + confidence score (circular progress, 64px)
  - P1: "🔥 Urgent" with red gradient
  - P2: "⚠️ Important" with amber gradient
  - P3: "📋 Normal" with gray gradient
- Key insights: 3-4 bullet points with checkmark icons, text-sm

**Smart Summary Card:**
- bg-white rounded-xl p-6 mb-4
- "Thread Summary" header with document icon
- Expandable/collapsible content
- Summary text: leading-relaxed, structured paragraphs
- "Show more" link in primary-purple

**Extracted Tasks Card:**
- bg-white rounded-xl p-6 mb-4
- "Action Items" header with checkbox-list icon + count badge
- Task items grouped by deadline:
  - Today section (bg-red/5)
  - This Week section (bg-amber/5)
  - Later section
- Each task:
  - Interactive checkbox (20px, rounded, border-2 hover:border-primary)
  - Task title (font-medium, max 2 lines)
  - Due date chip: inline, rounded-full, small
  - Assignee avatar stack if detected
  - Source context: "From email line 15" in caption text
- "Add to Calendar" button per task (text-sm, text-primary-purple)

**Key Entities Card:**
- bg-white rounded-xl p-6
- "Detected Information" header
- Pills grid for: People mentioned, Dates, Locations, Links
- Each pill: bg-card-lavender rounded-full px-3 py-1.5 with icon

**Suggested Replies Card:**
- bg-gradient-to-r from-purple/5 to-teal/5 rounded-xl p-6
- "AI Suggested Replies" header with magic-wand icon
- 3 response options as cards:
  - Tone badge: "Professional", "Friendly", "Brief"
  - Preview text (2 lines)
  - "Use This Reply" button (outline, primary-purple)

### 4. Mobile Layout

**Bottom Tab Navigation:**
- 3 tabs: Inbox icon, Email icon, AI Analysis icon
- Active tab: Primary purple with label, inactive: gray icon only
- Tab indicator line at top

**Floating Action Button:**
- Fixed bottom-right, circular 56px
- bg-primary-purple with white icon
- "Analyze with AI" tooltip on hover
- Shadow-lg with purple tint

**Mobile Email View:**
- Full-screen email with sticky header
- AI insights as collapsible accordion at top
- Tasks as bottom sheet modal
- Swipe gestures for archive/delete

---

## Interaction Patterns

**Micro-interactions:**
- Email item hover: Slide-in action buttons (reply, archive) from right
- Checkbox check: Scale bounce + purple fill animation
- Task completion: Confetti burst + strikethrough with 300ms delay
- AI badge: Subtle pulse animation on new insights
- Panel resize: Smooth width transition with drag handle

**Loading States:**
- Email list: Wave shimmer animation in card-lavender
- AI analysis: Typing indicator dots for real-time generation
- Progress bar at top of AI panel during processing

**Transitions:**
- Panel switching (mobile): Horizontal slide 300ms ease-out
- Card expansion: Height animation with ease-in-out
- Email selection: Fade + scale-up 200ms

---

## Images

**No Hero Image** - This is a utility application focused on email workflow. Visual elements limited to:
- User avatars: Circular, 32px (list) or 48px (detail)
- Sender/contact avatars with fallback initials on colored backgrounds
- App logo: Purple gradient icon (48px) with geometric mail envelope design
- Empty state illustrations: Simple line-art style in purple tones (max 200px) for "No emails selected", "Inbox zero"
- All icons via Heroicons (solid for active states, outline for inactive)

---

## Accessibility & Polish

- Focus indicators: 3px ring-primary-purple ring-offset-2
- Touch targets: Minimum 44px height for all interactive elements
- Keyboard shortcuts: "/" for search, "c" for compose, arrow navigation in list
- Screen reader: ARIA labels for all icon buttons, live regions for AI updates
- Color contrast: All text meets WCAG AAA (7:1) against backgrounds
- Dark mode toggle: Top-right corner with moon/sun icon, persistent preference
- Reduced motion: Disable animations, keep functional transitions only
- Panel resize persistence: Save column widths in localStorage