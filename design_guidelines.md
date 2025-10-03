# AI Email Assistant - Gmail Sidebar Add-on Design Guidelines

## Design Approach
**Selected Approach:** Utility-Focused Design System (Google Workspace Integration)

**Justification:** As a Gmail Workspace Add-on, this interface must:
- Integrate seamlessly with Google Workspace visual language (Material Design 3)
- Maximize information density in a constrained sidebar width (360px max)
- Prioritize scanning efficiency and quick decision-making
- Maintain consistency with Gmail's existing UI patterns

**Primary Reference:** Google Workspace Add-ons (Calendar, Keep, Tasks) + Linear's information hierarchy

---

## Core Design Elements

### A. Color Palette

**Light Mode:**
- Primary: 220 95% 50% (Google Blue - for priority P1, CTAs)
- Surface: 0 0% 100% (White backgrounds)
- Surface Variant: 220 20% 97% (Card backgrounds)
- Border: 220 15% 88% (Dividers, card outlines)
- Text Primary: 220 20% 15%
- Text Secondary: 220 15% 45%
- Success: 140 65% 42% (Task completion, P3 labels)
- Warning: 35 90% 55% (P2 labels)
- Error: 0 85% 58% (P1 urgent labels)

**Dark Mode:**
- Primary: 220 95% 65%
- Surface: 220 15% 12%
- Surface Variant: 220 15% 16%
- Border: 220 10% 25%
- Text Primary: 220 10% 95%
- Text Secondary: 220 8% 70%
- Success: 140 55% 52%
- Warning: 35 80% 65%
- Error: 0 75% 68%

### B. Typography
**Font Stack:** 'Google Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui

**Hierarchy:**
- Heading (Section titles): 14px/600 (font-semibold text-sm)
- Body (Content): 13px/400 (font-normal text-[13px])
- Caption (Metadata): 12px/400 (font-normal text-xs)
- Label (Tags, badges): 11px/500 (font-medium text-[11px])

### C. Layout System
**Spacing Primitives:** Tailwind units of 1, 2, 3, 4, 6, 8 (tight spacing for sidebar density)

**Container:**
- Width: w-[360px] fixed (Gmail sidebar standard)
- Padding: px-4 (16px horizontal)
- Section spacing: space-y-4 between major sections
- Card internal padding: p-3 or p-4

**Vertical Rhythm:**
- Header: h-14 sticky top
- Content sections: py-3 consistent padding
- List items: py-2.5 for comfortable tap targets

---

## Component Library

### 1. Header Section
**Layout:** Sticky top bar with context awareness
- Thread subject (truncated, tooltip on hover): text-sm font-semibold
- Participant count badge: text-xs bg-surface-variant rounded-full px-2 py-0.5
- Refresh/settings icon buttons: w-8 h-8 hover:bg-surface-variant rounded

### 2. Priority Indicator Card
**Visual Treatment:** Bold, top-positioned card with icon + label
- P1 Urgent: Red left border (border-l-4), red badge with flame icon
- P2 To-do: Amber left border, yellow badge with clock icon  
- P3 FYI: Green left border, green badge with info icon
- Score display: Circular progress indicator (0-100%) with percentage text
- Reasons list: text-xs text-secondary with bullet points

**Layout:** bg-surface-variant rounded-lg p-3 mb-4

### 3. Summary Card
**Component:** Expandable card with gradient fade
- Title: "Thread Summary" text-sm font-semibold text-secondary mb-2
- Content: text-[13px] leading-relaxed, max 3 lines initially
- Expand button: "Read more" text-xs text-primary if truncated
- Timeline indicator: Dot + line visual showing message flow (vertical timeline with 2px connecting lines)

### 4. Tasks List
**Visual Hierarchy:** Grouped by type (Deadline > Meeting > Action)

**Task Card:**
- Checkbox: w-5 h-5 rounded border-2, checked state with primary fill
- Title: text-[13px] font-medium, strikethrough when complete
- Owner chip: bg-primary/10 text-primary rounded-full px-2 py-0.5 text-[11px]
- Due date: 
  - Overdue: text-error with alert icon
  - Today: text-warning with clock icon
  - Future: text-secondary
- Type badge: Meeting (calendar icon), Deadline (flag icon), Action (check icon)
- Source link: text-xs text-primary "→ View in m2" (message ID)

**Layout:** Compact cards with hover elevation, space-y-2

### 5. Chatbot QA Interface
**Design Pattern:** Minimalist chat embedded at bottom

**Input Area:**
- Sticky bottom position with backdrop blur (backdrop-blur-sm bg-surface/95)
- Textarea: min-h-10 max-h-24 auto-resize, border-2 focus:border-primary rounded-lg px-3 py-2
- Submit button: Icon only (paper plane), primary color, w-8 h-8 rounded-full
- Quick prompts: Chip buttons above input ("What do I need to do?", "When's the meeting?")

**Message Bubbles:**
- User: bg-primary text-white rounded-2xl rounded-br-sm px-3 py-2 ml-auto max-w-[85%]
- Assistant: bg-surface-variant rounded-2xl rounded-bl-sm px-3 py-2 mr-auto max-w-[85%]
- Source citations: text-xs text-primary underline decoration-dotted "Sources: m1, m2"
- Timestamp: text-[11px] text-secondary mt-1

### 6. User Settings Panel
**Access:** Slide-out panel from right, triggered by gear icon

**Keyword Management:**
- Add keyword form: Inline with term input + weight slider (1.0-3.0) + scope dropdown
- Keyword chips: Removable badges showing term (weight) with X button
- Scope indicators: Small colored dots (Subject=blue, Body=gray, Sender=purple)

**Layout:** Full-height overlay with bg-surface shadow-2xl p-4

---

## Interaction Patterns

### Micro-interactions:
- Card hover: subtle shadow elevation (shadow-sm → shadow-md)
- Button press: scale-95 transform
- Task completion: slide-out + fade animation (300ms ease-out)
- Priority badge pulse: Subtle pulse animation for P1 only (animate-pulse with low opacity)

### Loading States:
- Skeleton screens: animated gradient shimmer for cards during API calls
- Inline spinners: 16px spinner with primary color for actions

### Empty States:
- No tasks: Illustration (simple line icon) + "All clear! No tasks found." text-secondary
- Chat initial: "Ask me anything about this thread" with example questions

---

## Special Considerations

### Accessibility:
- All interactive elements ≥44px touch target (via padding)
- Focus indicators: 2px primary ring on keyboard navigation
- ARIA labels for icon-only buttons
- Color contrast ≥4.5:1 for all text

### Responsive Adaptation:
- Fixed 360px width (Gmail constraint)
- Vertical scroll for content overflow
- Sticky header and chat input

### Performance:
- Virtual scrolling for threads with 30+ messages
- Debounced chatbot input (500ms)
- Optimistic UI updates for task completion

---

## Images
**No hero images** - This is a compact sidebar utility interface where every pixel is functional. All icons use Heroicons (outline style for non-primary actions, solid for primary).