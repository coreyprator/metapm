# [MetaPM] 🔴 Mobile Task List Layout Fix

**Date**: 2026-02-05  
**Version**: 1.6.2  
**Priority**: P2 (UX — affects all mobile users)  
**Reported By**: Corey (iPhone, iOS Safari)

---

## Problem

On mobile (iPhone / narrow viewport), the task list rows show badges and status indicators consuming ~70% of row width, leaving only ~8 characters visible for the task description. The most important information — what the task actually IS — is truncated to near-uselessness.

**Current layout (single-line, all widths)**:
```
☐ 🐛 [WIP] [P1]      BUG-011...
☐ 🐛 [NEW] [P1]      BUG-010...
☐ 📋 [WIP] [P1] [AF] REQ-007...
```

**Problem**: User cannot read task descriptions on mobile. Must tap into every item to see what it is.

---

## Solution: Responsive Two-Line Row

On viewports ≤ 768px, switch from single-line to two-line layout:

**Line 1**: Full-width task ID + description (the important part)  
**Line 2**: Compact badges — type icon, status, priority, project tag

### Visual Spec

**Mobile (≤ 768px)**:
```
┌──────────────────────────────────────────────┐
│ ☐ BUG-011: Stability AI 400 error on        │
│   strength < 30%                             │
│   🐛 WIP   P1                               │
├──────────────────────────────────────────────┤
│ ☐ BUG-010: Image resize still failing       │
│   after fix attempt                          │
│   🐛 NEW   P1                               │
├──────────────────────────────────────────────┤
│ ☐ REQ-007: Premiere XML export endpoint      │
│   📋 WIP   P1   ArtForge                    │
├──────────────────────────────────────────────┤
│ ☐ BUG-016: Export dropdown not closing       │
│   🐛 NEW   P2   ArtForge                    │
└──────────────────────────────────────────────┘
```

**Desktop (> 768px)**: No change. Keep current single-line layout.

---

## Implementation

### CSS Changes

Add a media query to the task list styles. The key change is switching from `flex-direction: row` (horizontal) to a two-line stacked layout on mobile.

```css
/* === MOBILE TASK LIST LAYOUT === */
@media (max-width: 768px) {
    
    /* Task row becomes a flex column wrapper */
    .task-row,
    .task-list-item,
    [class*="task-item"] {  /* adjust selector to match actual class */
        display: flex;
        flex-direction: column;
        padding: 10px 12px;
        gap: 4px;
        border-bottom: 1px solid var(--border-color, #2a2a3e);
    }
    
    /* Line 1: Checkbox + full task title */
    .task-row-line1,
    .task-title-area {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        width: 100%;
        order: 1;
    }
    
    /* Task title gets full width, wraps to 2 lines max */
    .task-title,
    .task-description,
    [class*="task-name"] {
        flex: 1;
        white-space: normal;        /* Allow wrapping */
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;      /* Max 2 lines */
        -webkit-box-orient: vertical;
        font-size: 14px;
        line-height: 1.4;
    }
    
    /* Line 2: Badges row — compact, muted */
    .task-row-line2,
    .task-badges-area {
        display: flex;
        align-items: center;
        gap: 6px;
        padding-left: 32px;  /* Indent to align under title (past checkbox) */
        order: 2;
    }
    
    /* Smaller badges on mobile */
    .status-badge,
    .priority-badge,
    .project-tag,
    [class*="badge"] {
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 3px;
    }
    
    /* Type icon (bug/req) — smaller on mobile */
    .type-icon,
    [class*="type-indicator"] {
        width: 16px;
        height: 16px;
        font-size: 12px;
    }
    
    /* Priority text — compact */
    .priority-badge {
        font-weight: 700;
        min-width: unset;
    }
    
    /* Project tag — only show if cross-project view */
    .project-tag {
        margin-left: auto;  /* Push to right */
        font-size: 10px;
        opacity: 0.7;
    }
    
    /* Checkbox stays same size for touch target */
    .task-checkbox,
    input[type="checkbox"] {
        min-width: 22px;
        min-height: 22px;
        margin-top: 2px;
    }
}
```

### HTML Structure

If the current HTML is a flat row of elements, you may need to wrap them into two groups. The cleanest approach:

**Current (assumed)**:
```html
<div class="task-row">
    <input type="checkbox">
    <span class="type-icon">🐛</span>
    <span class="status-badge">WIP</span>
    <span class="priority-badge">P1</span>
    <span class="project-tag">AF</span>
    <span class="task-title">BUG-011: Stability AI 400 error...</span>
</div>
```

**Updated**:
```html
<div class="task-row">
    <!-- Line 1: Checkbox + Title -->
    <div class="task-row-line1">
        <input type="checkbox" class="task-checkbox">
        <span class="task-title">BUG-011: Stability AI 400 error on strength < 30%</span>
    </div>
    <!-- Line 2: Badges -->
    <div class="task-row-line2">
        <span class="type-icon">🐛</span>
        <span class="status-badge wip">WIP</span>
        <span class="priority-badge p1">P1</span>
        <span class="project-tag">ArtForge</span>
    </div>
</div>
```

**Important**: On desktop (> 768px), use CSS to flatten both lines back into a single row:

```css
/* Desktop: keep current single-line layout */
@media (min-width: 769px) {
    .task-row {
        flex-direction: row;
        align-items: center;
    }
    .task-row-line1,
    .task-row-line2 {
        display: contents;  /* Flatten wrapper, children join parent flex */
    }
}
```

### Alternative: CSS-Only (No HTML Changes)

If restructuring HTML is too invasive, use CSS Grid to reflow:

```css
@media (max-width: 768px) {
    .task-row {
        display: grid;
        grid-template-columns: 28px 1fr;
        grid-template-rows: auto auto;
        gap: 2px 8px;
        padding: 10px 12px;
    }
    
    /* Checkbox: spans both rows, column 1 */
    .task-checkbox {
        grid-row: 1 / 3;
        grid-column: 1;
        align-self: start;
        margin-top: 2px;
    }
    
    /* Title: row 1, column 2 — FULL WIDTH */
    .task-title {
        grid-row: 1;
        grid-column: 2;
        white-space: normal;
        -webkit-line-clamp: 2;
        display: -webkit-box;
        -webkit-box-orient: vertical;
        overflow: hidden;
        order: -1;  /* Force to top if DOM order differs */
    }
    
    /* All badges: row 2, column 2 */
    .type-icon,
    .status-badge,
    .priority-badge,
    .project-tag {
        grid-row: 2;
        grid-column: 2;
    }
    
    /* Badge container for row 2 */
    .task-badges {
        grid-row: 2;
        grid-column: 2;
        display: flex;
        gap: 6px;
        align-items: center;
    }
}
```

---

## Badge Sizing Reference

| Badge | Desktop | Mobile |
|-------|---------|--------|
| Status (WIP/NEW/DONE) | 12px, 4px 10px padding | 11px, 2px 6px padding |
| Priority (P1/P2/P3) | 12px, bold | 11px, bold |
| Project tag (AF/SF/etc.) | 11px, pill | 10px, pill, right-aligned |
| Type icon (🐛/📋) | 20×20px | 16×16px |
| Checkbox | 20×20px | 22×22px (bigger touch target) |

---

## Touch Target Requirements (iOS)

Per Apple HIG, minimum touch target is 44×44 points. Ensure:
- Checkbox tap area: 44×44pt minimum (even if visual is 22px, add padding)
- Row tap area: full width, minimum 44pt height
- Badge taps (if interactive): 44×44pt minimum

---

## Breakpoint

| Width | Layout |
|-------|--------|
| ≤ 768px | Two-line (mobile) |
| > 768px | Single-line (desktop, current) |

768px covers all phones and most small tablets in portrait.

---

## Edge Cases

| Case | Handling |
|------|----------|
| Very long title | Clamp to 2 lines with ellipsis on mobile |
| No project tag | Badge row is shorter, no issue |
| Task in filtered single-project view | Hide project tag entirely (redundant) |
| Very short title (e.g., "Fix CSS") | Single line, badge row still on line 2 |
| Selected state (bulk actions) | Highlight should cover both lines |

---

## Testing

| Test | Expected |
|------|----------|
| Open MetaPM on iPhone Safari | Two-line rows, full titles visible |
| Open MetaPM on desktop Chrome | Single-line rows, current layout unchanged |
| Resize browser 800px → 700px | Layout switches at 768px breakpoint |
| Task with very long title | Wraps to 2 lines, then ellipsis |
| Tap checkbox on mobile | Works (44pt touch target) |
| Tap row to open task | Works, opens detail |
| Bulk select mode | Selection highlight covers full row |
| Dark mode | Badges readable against dark background |
| Scroll performance | No jank from layout changes |

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/tasks.html` or equivalent | Add line1/line2 wrapper divs (if needed) |
| `frontend/css/tasks.css` or `styles.css` | Add mobile media query |
| `frontend/js/tasks.js` | If rows are dynamically rendered, update template |

---

## Acceptance Criteria

- [ ] On iPhone (≤ 768px), task titles are fully readable (2 lines max)
- [ ] Badges display on a compact second line below the title
- [ ] Desktop layout is unchanged
- [ ] Touch targets meet 44pt minimum
- [ ] No horizontal scrolling on mobile
- [ ] Sorted/filtered views still work correctly
- [ ] Bulk select mode still works

---

## Version

After fix: **v1.6.2**

---

## Screenshots

**Before** (current — broken on mobile):
```
☐ 🐛 [WIP] [P1]      BUG-011...
☐ 🐛 [NEW] [P1]      BUG-010...
```

**After** (two-line — mobile only):
```
☐ BUG-011: Stability AI 400 error on
  strength < 30%
  🐛 WIP  P1

☐ BUG-010: Image resize still failing
  after fix attempt
  🐛 NEW  P1
```

---

*This is a mobile-only responsive change. Desktop is unaffected.*
