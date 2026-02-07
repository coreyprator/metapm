# 🔴 MetaPM v1.6.0 UAT — UI Improvements

**Test URL**: https://metapm.rentyourcio.com  
**Version**: 1.6.0  
**Remember**: Hard refresh (Ctrl+Shift+R) to clear cached CSS/JS

---

## Pre-Flight

| Step | Action | Expected | Pass/Fail |
|------|--------|----------|-----------|
| 0.1 | Hard refresh (Ctrl+Shift+R) | Page loads fresh | ☐ |
| 0.2 | Check version badge in header | Shows **v1.6.0** with high contrast | ☐ |
| 0.3 | Verify single-line header | All elements on one line | ☐ |

---

## 1. Title Bar (Single Line)

| Step | Action | Expected | Pass/Fail |
|------|--------|----------|-----------|
| 1.1 | Look at header layout | Single horizontal line | ☐ |
| 1.2 | Find "MetaPM" name | Visible on left | ☐ |
| 1.3 | Find version badge | **High contrast** `v1.6.0` visible | ☐ |
| 1.4 | Find sync status | Shows "✓ Synced" or similar | ☐ |
| 1.5 | Find date | Current date visible | ☐ |
| 1.6 | Find theme toggle | Theme buttons visible | ☐ |
| 1.7 | Click theme toggle | Theme changes (light/dark) | ☐ |
| 1.8 | Find view dropdown | Dropdown (not tabs) visible | ☐ |
| 1.9 | Find "+ Add" button | Button visible | ☐ |
| 1.10 | Find refresh button | Refresh icon visible | ☐ |
| 1.11 | Find docs link | Link visible | ☐ |

---

## 2. View Selector Dropdown

| Step | Action | Expected | Pass/Fail |
|------|--------|----------|-----------|
| 2.1 | Click view dropdown | Options appear | ☐ |
| 2.2 | Verify options | Tasks, Projects, AI History, Methodology, Backlog | ☐ |
| 2.3 | Select "Projects" | View changes to Projects | ☐ |
| 2.4 | Select "AI History" | View changes to AI History | ☐ |
| 2.5 | Select "Backlog" | View changes to Backlog | ☐ |
| 2.6 | Select "Tasks" | Returns to Tasks view | ☐ |

---

## 3. Context-Aware Add Button

| Step | Action | Expected | Pass/Fail |
|------|--------|----------|-----------|
| 3.1 | With Tasks view selected | Button shows **"+ Add Task"** | ☐ |
| 3.2 | Select Projects view | Button changes to **"+ Add Project"** | ☐ |
| 3.3 | Select Methodology view | Button changes to **"+ Add Rule"** or similar | ☐ |
| 3.4 | Select Backlog view | Button changes to **"+ Add Backlog Item"** or similar | ☐ |
| 3.5 | Return to Tasks view | Button shows "+ Add Task" | ☐ |

---

## 4. Filter Bar (Horizontal Dropdowns)

| Step | Action | Expected | Pass/Fail |
|------|--------|----------|-----------|
| 4.1 | Find filter bar | Horizontal row below header | ☐ |
| 4.2 | Find Status dropdown | "Status: [All ▼]" visible | ☐ |
| 4.3 | Click Status dropdown | Options: All, New, Active, Blocked, Done | ☐ |
| 4.4 | Select "New" | List filters to only New items | ☐ |
| 4.5 | Select "All" | List shows all items | ☐ |
| 4.6 | Find Priority dropdown | "Priority: [All ▼]" visible | ☐ |
| 4.7 | Select "P1" | List filters to P1 only | ☐ |
| 4.8 | Select "All" | List shows all | ☐ |
| 4.9 | Find Project dropdown | "Project: [All ▼]" visible | ☐ |
| 4.10 | Select a specific project | List filters to that project | ☐ |
| 4.11 | Find **Type dropdown** | "Type: [All ▼]" visible | ☐ |
| 4.12 | Select "Bug" | Shows only BUG-xxx items | ☐ |
| 4.13 | Select "Requirement" | Shows only REQ-xxx items | ☐ |
| 4.14 | Select "All" | Shows all types | ☐ |
| 4.15 | Find Sort dropdown | Sort options visible | ☐ |
| 4.16 | Find sort direction button | ↑ or ↓ visible | ☐ |
| 4.17 | Click sort direction | Toggles between ↑/↓ | ☐ |
| 4.18 | Find Search field | Search input visible | ☐ |
| 4.19 | Type "Stability" in search | Filters to matching items | ☐ |
| 4.20 | Clear search | All items return | ☐ |

---

## 5. Task Rows (Single-Line Grid)

| Step | Action | Expected | Pass/Fail |
|------|--------|----------|-----------|
| 5.1 | Look at task list | Single-line rows (not cards) | ☐ |
| 5.2 | Verify grid columns | Checkbox, Type, Title, Status, Priority, Project, Actions | ☐ |
| 5.3 | Check alternating colors | Odd/even rows have different background | ☐ |
| 5.4 | Find type icons | 🐛 for bugs, 📋 for requirements, ✓ for tasks | ☐ |
| 5.5 | Find status badges | Colored badges (NEW, ACTIVE, etc.) | ☐ |
| 5.6 | Find priority badges | P1, P2, P3 with colors | ☐ |
| 5.7 | Find project badges | Project abbreviations with colors | ☐ |
| 5.8 | Hover over a row | Row highlights, edit button appears | ☐ |
| 5.9 | Find checkbox on left | Selection checkbox visible | ☐ |

---

## 6. Fixed Status Bar (Bottom)

| Step | Action | Expected | Pass/Fail |
|------|--------|----------|-----------|
| 6.1 | Look at bottom of screen | Fixed status bar visible | ☐ |
| 6.2 | Find selection count | "0 selected" visible on left | ☐ |
| 6.3 | Find Delete button | "🗑️ Delete" button (disabled) | ☐ |
| 6.4 | Find Clear button | "✕ Clear" button (disabled) | ☐ |
| 6.5 | Find stats on right | "X New, Y Active, Z Blocked, W Done" | ☐ |
| 6.6 | Scroll the task list | **Status bar stays fixed** at bottom | ☐ |
| 6.7 | Stats still visible after scroll | Yes | ☐ |

---

## 7. Multi-Select Functionality

| Step | Action | Expected | Pass/Fail |
|------|--------|----------|-----------|
| 7.1 | Click checkbox on first task | Checkbox selected | ☐ |
| 7.2 | Check selection count | Shows **"1 selected"** | ☐ |
| 7.3 | Check Delete/Clear buttons | **Now enabled** | ☐ |
| 7.4 | Select 2 more tasks | 3 checkboxes selected | ☐ |
| 7.5 | Check selection count | Shows **"3 selected"** | ☐ |
| 7.6 | Scroll down | Status bar stays visible with count | ☐ |
| 7.7 | Click "✕ Clear" | All selections cleared | ☐ |
| 7.8 | Check selection count | Shows "0 selected" | ☐ |
| 7.9 | Check buttons | Delete/Clear disabled again | ☐ |

---

## 8. TaskType Field & Auto-Prefix

| Step | Action | Expected | Pass/Fail |
|------|--------|----------|-----------|
| 8.1 | Click "+ Add Task" | Add modal opens | ☐ |
| 8.2 | Find Type dropdown in modal | Dropdown with Task/Bug/Requirement | ☐ |
| 8.3 | Select "Bug" | Type set to Bug | ☐ |
| 8.4 | Enter title: "Test bug auto prefix" | Title entered | ☐ |
| 8.5 | Fill required fields | Complete the form | ☐ |
| 8.6 | Save the task | Task created | ☐ |
| 8.7 | Find new task in list | Task appears | ☐ |
| 8.8 | Check title | **"BUG-XXX: Test bug auto prefix"** | ☐ |
| 8.9 | Check type icon | Shows 🐛 | ☐ |
| 8.10 | Create a Requirement | Same process | ☐ |
| 8.11 | Check requirement title | **"REQ-XXX: ..."** with auto-prefix | ☐ |
| 8.12 | Check type icon | Shows 📋 | ☐ |

---

## 9. Edit Task

| Step | Action | Expected | Pass/Fail |
|------|--------|----------|-----------|
| 9.1 | Hover over a task row | Edit button appears | ☐ |
| 9.2 | Click edit button (or row) | Edit modal opens | ☐ |
| 9.3 | Verify Type field shown | Type dropdown visible | ☐ |
| 9.4 | Change a field | Make an edit | ☐ |
| 9.5 | Save | Changes saved | ☐ |
| 9.6 | Verify changes in list | Updated values shown | ☐ |

---

## 10. Delete Task (Bulk)

| Step | Action | Expected | Pass/Fail |
|------|--------|----------|-----------|
| 10.1 | Create a test task | Task for deletion | ☐ |
| 10.2 | Select the test task | Checkbox checked | ☐ |
| 10.3 | Click "🗑️ Delete" | Confirmation dialog | ☐ |
| 10.4 | Confirm deletion | Task deleted | ☐ |
| 10.5 | Verify task gone | Not in list | ☐ |

---

## UAT Summary Checklist

```
MetaPM v1.6.0 UI Improvements UAT
Date: ___________
Tester: Corey

Pre-Flight              [ ] Pass  [ ] Fail
1. Title Bar            [ ] Pass  [ ] Fail
2. View Dropdown        [ ] Pass  [ ] Fail
3. Context-Aware Add    [ ] Pass  [ ] Fail
4. Filter Bar           [ ] Pass  [ ] Fail
5. Task Rows            [ ] Pass  [ ] Fail
6. Fixed Status Bar     [ ] Pass  [ ] Fail
7. Multi-Select         [ ] Pass  [ ] Fail
8. TaskType & Prefix    [ ] Pass  [ ] Fail
9. Edit Task            [ ] Pass  [ ] Fail
10. Delete Task         [ ] Pass  [ ] Fail

Notes:
_________________________________
_________________________________

Issues Found:
_________________________________
_________________________________
```

---

## Key Things to Verify

| Feature | What to Check |
|---------|---------------|
| Version visibility | Can you easily see v1.6.0? |
| Single-line header | No wrapping to second line? |
| Filter dropdowns | All 5 filters working? |
| Type filter | Can filter bugs vs requirements? |
| Row layout | Single line, not cards? |
| Alternating colors | Can distinguish rows? |
| Type icons | 🐛 📋 ✓ showing correctly? |
| Status bar fixed | Stays at bottom when scrolling? |
| Selection count | Updates live? |
| Auto-prefix | BUG-XXX and REQ-XXX generated? |

---

Good luck with testing! 🔴
