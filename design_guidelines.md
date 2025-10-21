# AI Email Intelligence Web App - Design Guidelines

## Design Approach
**Selected Approach:** Design System - Material Design 3 with Linear-inspired Information Hierarchy

**Justification:** As a productivity analysis tool, the interface prioritizes:
- Rapid information scanning and decision-making
- Clear visual hierarchy for priority-based content
- Efficient two-step workflow (input → results)
- Professional aesthetic that builds trust in AI capabilities

**Primary References:** Linear's data density + Material Design's elevation system + Notion's clean typography

---

## Core Design Elements

### A. Color Palette

**Light Mode:**
- Primary: 220 95% 50% (Analyze CTA, interactive elements)
- Surface: 0 0% 100% (Main background)
- Surface Elevated: 0 0% 98% (Cards, elevated panels)
- Border: 220 15% 88% (Dividers, inputs)
- Text Primary: 220 20% 15%
- Text Secondary: 220 15% 45%
- P1 Urgent: 0 85% 58% (Red badge, urgent tasks)
- P2 Todo: 35 90% 55% (Yellow/amber badge)
- P3 FYI: 220 10% 50% (Gray badge)
- Success Accent: 140 65% 42% (Completion states)

**Dark Mode:**
- Primary: 220 95% 65%
- Surface: 220 15% 10%
- Surface Elevated: 220 15% 14%
- Border: 220 10% 25%
- Text Primary: 220 10% 95%
- Text Secondary: 220 8% 70%
- P1 Urgent: 0 75% 68%
- P2 Todo: 35 80% 65%
- P3 FYI: 220 8% 60%
- Success Accent: 140 55% 52%

### B. Typography
**Font Stack:** 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui

**Hierarchy:**
- Page Title: 32px/700 (font-bold text-[32px])
- Section Heading: 20px/600 (font-semibold text-xl)
- Card Title: 16px/600 (font-semibold text-base)
- Body Text: 15px/400 (font-normal text-[15px])
- Task Item: 14px/500 (font-medium text-sm)
- Metadata/Labels: 13px/500 (font-medium text-[13px])
- Caption: 12px/400 (font-normal text-xs)

### C. Layout System
**Spacing Primitives:** Tailwind units of 2, 4, 6, 8, 12, 16 (balanced spacing for readability)

**Container Strategy:**
- Input Screen: max-w-3xl centered (optimal for text input)
- Results Screen: max-w-5xl centered (accommodates summary + tasks side-by-side on desktop)
- Section Padding: py-12 desktop, py-8 mobile
- Card Internal: p-6 desktop, p-4 mobile
- Card Gaps: gap-6 between major sections

**Responsive Grid:**
- Desktop (lg:): Two-column layout for summary + tasks
- Tablet/Mobile: Single column stack

---

## Component Library

### 1. Input Screen (Pre-Analysis)

**Hero Section:**
- Centered layout with max-w-2xl
- Page title with gradient text effect: "Analyze Your Emails"
- Subtitle: text-secondary explaining the workflow
- No large hero image - simple gradient background (220 95% 50% to 260 90% 55%)

**Email Input Card:**
- Large elevated card: bg-surface-elevated shadow-lg rounded-2xl p-8
- Textarea: min-h-[320px] w-full rounded-xl border-2 focus:border-primary transition
- Placeholder text: "Paste your email content here..."
- Character counter: bottom-right corner, text-xs text-secondary "0 / 50,000 characters"

**Primary CTA:**
- "Analyze Email" button: Large, full-width or centered
- bg-primary text-white rounded-xl px-8 py-4 text-base font-semibold
- Hover state: brightness increase + subtle scale (scale-[1.02])
- Loading state: Spinner with "Analyzing..." text

**Supporting Elements:**
- Feature icons below input: 3-column grid showing "Smart Summaries", "Priority Detection", "Task Extraction" with Heroicons
- Each feature: Icon (w-10 h-10) + label (text-sm font-medium) + description (text-xs text-secondary)

### 2. Results Screen

**Header Bar:**
- Sticky top navigation: h-16 bg-surface border-b flex items-center px-6
- "New Analysis" button: outline variant, rounded-lg
- Email preview snippet: truncated subject/sender in text-sm text-secondary

**Priority Indicator - Hero Component:**
- Full-width attention card at top: bg-gradient-to-r based on priority
  - P1: from-error/10 to-error/5, left border-l-4 border-error
  - P2: from-warning/10 to-warning/5, left border-l-4 border-warning
  - P3: from-gray/10 to-gray/5, left border-l-4 border-gray
- Large priority badge: Pill shape with icon + label
  - P1: "🔥 Urgent - Action Required" 
  - P2: "⏰ To-Do - Needs Attention"
  - P3: "ℹ️ FYI - For Information"
- Confidence score: Circular progress indicator (72px diameter) showing 0-100%
- Key reasoning bullets: 2-3 concise points in text-sm

**Layout:** p-6 rounded-2xl mb-8

### 3. Content Grid (Desktop: 2-column, Mobile: Stack)

**Left Column - Summary Card:**
- bg-surface-elevated rounded-xl p-6 shadow-sm
- Section title: "Thread Summary" with document icon
- Summary text: text-[15px] leading-relaxed, structured paragraphs
- Timeline visualization: Vertical timeline showing message flow (optional for multi-message threads)
  - Dots + connecting lines (border-l-2) 
  - Message sender + timestamp per node
- "View Full Analysis" expandable section if truncated

**Right Column - Task List:**
- bg-surface-elevated rounded-xl p-6 shadow-sm
- Section title: "Extracted Tasks" with checkbox list icon
- Task counter badge: "3 tasks found"

**Task Card Components:**
- Grouped by type with dividers: Deadlines > Meetings > Actions
- Each task item:
  - Checkbox: w-5 h-5 rounded border-2 hover:border-primary
  - Task title: text-sm font-medium, max 2 lines
  - Due date chip: Inline badge with calendar icon
    - Overdue: bg-error/10 text-error
    - Today: bg-warning/10 text-warning  
    - Future: bg-surface text-secondary
  - Owner badge (if extracted): Small avatar circle + name, text-xs
  - Source reference: "From: [Sender]" text-xs text-secondary
- Hover state: bg-surface-elevated brightness-[0.98]
- Completed state: Strikethrough + opacity-50

**Empty State:** 
- Icon (checklist with sparkles) + "No tasks detected in this email"
- Suggestion text: "This appears to be informational only"

### 4. Action Footer
- Sticky bottom bar (mobile) or inline (desktop)
- Secondary actions: "Export Tasks", "Save Analysis", "Share"
- Button group: gap-2, outline variants with icons

---

## Interaction Patterns

**Micro-interactions:**
- Card hover: shadow-sm → shadow-md transition (200ms)
- Task checkbox: Scale bounce on check (scale-110 → scale-100)
- Priority badge: Subtle pulse for P1 only
- Input focus: Border color transition + ring-2 ring-primary/20

**Loading States:**
- Analysis in progress: Progress bar at top + shimmer cards
- Skeleton loaders: Animated gradient for summary and task cards
- Optimistic completion: Task strikethrough immediate, sync in background

**Transitions:**
- Screen change (input → results): Fade + slide-up (400ms ease-out)
- Card expansion: Height animation (300ms)

---

## Images

**Input Screen:**
- Background: Subtle gradient mesh (abstract geometric pattern, very low opacity)
- No hero image - focus on the input interface

**Results Screen:**
- No decorative images - prioritize information density
- All icons via Heroicons (outline for secondary, solid for primary actions)
- Optional: Small brand mark or logo in top-left corner (max 120px width)

---

## Accessibility & Polish

- Focus indicators: 2px ring-primary ring-offset-2 on keyboard navigation
- All touch targets: minimum 44x44px via padding
- Color contrast: ≥4.5:1 for all text
- Reduced motion: respect prefers-reduced-motion for animations
- ARIA labels: All icon-only buttons labeled
- Dark mode toggle: Persistent user preference in top-right corner