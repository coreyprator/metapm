# UI_DESIGN.md Template

**Project**: {{PROJECT_NAME}}  
**Version**: 1.0  
**Last Updated**: {{DATE}}

---

## Design Overview

### Purpose
[Brief description of what the UI enables users to do]

### Target Users
[Who will use this application]

### Design Principles
- Clean and intuitive interface
- Mobile-responsive (if applicable)
- Accessible (WCAG 2.1 AA minimum)
- Consistent visual language

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Framework | [React / Vue / Vanilla JS / etc.] |
| Styling | [Tailwind / CSS Modules / etc.] |
| Icons | [Lucide / Heroicons / etc.] |
| State Management | [React hooks / Zustand / etc.] |

---

## Color Palette

| Purpose | Color | Hex |
|---------|-------|-----|
| Primary | [Color name] | `#XXXXXX` |
| Secondary | [Color name] | `#XXXXXX` |
| Background | [Color name] | `#XXXXXX` |
| Text | [Color name] | `#XXXXXX` |
| Success | Green | `#10B981` |
| Warning | Yellow | `#F59E0B` |
| Error | Red | `#EF4444` |

---

## Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| H1 | [Font] | 2rem | Bold |
| H2 | [Font] | 1.5rem | Semibold |
| Body | [Font] | 1rem | Normal |
| Small | [Font] | 0.875rem | Normal |

---

## Layout Structure

### Overall Layout
```
┌─────────────────────────────────────────────┐
│                   Header                     │
├─────────────────────────────────────────────┤
│                                             │
│                Main Content                  │
│                                             │
├─────────────────────────────────────────────┤
│                   Footer                     │
└─────────────────────────────────────────────┘
```

### Responsive Breakpoints
| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Mobile | < 640px | Single column, hamburger menu |
| Tablet | 640-1024px | Adjusted spacing |
| Desktop | > 1024px | Full layout |

---

## Page Designs

### Page 1: [Page Name]

**Purpose**: [What this page does]

**URL**: `/[path]`

**Wireframe**:
```
┌─────────────────────────────────────────────┐
│  Logo              [Navigation]    [User]   │
├─────────────────────────────────────────────┤
│                                             │
│  [Page Title]                               │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │                                     │   │
│  │         [Main Component]            │   │
│  │                                     │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [Action Buttons]                           │
│                                             │
└─────────────────────────────────────────────┘
```

**Components**:
- [ ] Header with navigation
- [ ] [Component 1]
- [ ] [Component 2]
- [ ] Action buttons

**States**:
- Loading: [Description]
- Empty: [Description]
- Error: [Description]
- Success: [Description]

---

### Page 2: [Page Name]

**Purpose**: [What this page does]

**URL**: `/[path]`

**Wireframe**:
```
[ASCII wireframe]
```

**Components**:
- [ ] [List components]

**States**:
- Loading: [Description]
- Empty: [Description]
- Error: [Description]

---

## Component Library

### Buttons

| Type | Use Case | Style |
|------|----------|-------|
| Primary | Main actions | Solid background, primary color |
| Secondary | Secondary actions | Outlined, primary color |
| Danger | Destructive actions | Solid background, red |
| Ghost | Tertiary actions | No background, text only |

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Primary    │  │  Secondary   │  │    Danger    │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Form Elements

| Element | Description |
|---------|-------------|
| Text Input | Single line, with label and optional helper text |
| Textarea | Multi-line, with character count if limited |
| Select | Dropdown with searchable option if many items |
| Checkbox | For multiple selections |
| Radio | For single selection from options |
| Toggle | For on/off states |

### Cards

```
┌─────────────────────────────────┐
│  [Image/Icon]                   │
│                                 │
│  Title                          │
│  Description text goes here     │
│                                 │
│  [Action]           [Action]    │
└─────────────────────────────────┘
```

### Modals

```
┌─────────────────────────────────────┐
│  Modal Title                    ✕   │
├─────────────────────────────────────┤
│                                     │
│  Modal content goes here            │
│                                     │
├─────────────────────────────────────┤
│              [Cancel]  [Confirm]    │
└─────────────────────────────────────┘
```

### Toast Notifications

| Type | Icon | Background |
|------|------|------------|
| Success | ✓ | Green |
| Error | ✕ | Red |
| Warning | ⚠ | Yellow |
| Info | ℹ | Blue |

---

## User Flows

### Flow 1: [Primary User Flow]

```
[Start] → [Step 1] → [Step 2] → [Step 3] → [Complete]
                ↓
           [Error] → [Recovery]
```

**Steps**:
1. User does [action]
2. System responds with [response]
3. User sees [result]

### Flow 2: [Secondary User Flow]

[Describe flow]

---

## Loading & Empty States

### Loading States

| Component | Loading UI |
|-----------|------------|
| Page load | Skeleton screen |
| Button action | Spinner inside button, disabled |
| List refresh | Spinner above list |

### Empty States

| Component | Empty UI |
|-----------|----------|
| List with no items | Illustration + "No items yet" + CTA |
| Search with no results | "No results for [query]" + suggestions |

---

## Error Handling

### Error Display

| Error Type | Display Method |
|------------|----------------|
| Form validation | Inline below field, red text |
| API error | Toast notification |
| Page error | Full page error with retry |
| Network error | Banner at top with retry |

### Error Messages

User-friendly, actionable messages:
- ❌ "Error 500: Internal Server Error"
- ✅ "Something went wrong. Please try again."

---

## Accessibility

### Requirements
- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Color contrast ratio ≥ 4.5:1
- [ ] Keyboard navigation works
- [ ] Focus states visible
- [ ] Screen reader compatible

### ARIA Labels
- Buttons with icons need `aria-label`
- Dynamic content uses `aria-live`
- Modals trap focus appropriately

---

## Help & Onboarding

### First-Time User Experience
- [ ] Welcome message explaining core workflow
- [ ] Tooltips on key features (optional)
- [ ] Link to help documentation

### Help Integration
- Help link in header/footer
- Points to: `https://github.com/{{GITHUB_REPO}}/blob/main/docs/USER_GUIDE.md`

---

## Implementation Notes

### Component Priority
1. [Highest priority components]
2. [Second priority]
3. [Polish items]

### Known Constraints
- [Any technical limitations]
- [Browser support requirements]
- [Performance considerations]

---

## Appendix: Asset List

### Icons Needed
- [ ] [Icon 1] - [Purpose]
- [ ] [Icon 2] - [Purpose]

### Images Needed
- [ ] [Image 1] - [Purpose]
- [ ] [Image 2] - [Purpose]

### External Resources
- Font: [URL]
- Icons: [URL]
