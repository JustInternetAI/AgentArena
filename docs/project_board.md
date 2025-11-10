# Agent Arena Project Board Structure

This document describes the recommended GitHub Project Board setup for managing Agent Arena development.

## Overview

We use a **Kanban-style project board** to track issues, pull requests, and overall project progress. This provides visibility into what's being worked on and helps coordinate between team members.

## Creating the Project Board

### Via GitHub CLI

```bash
cd "c:\Projects\Agent Arena"

# Create project (v2)
gh project create --title "Agent Arena Development" --owner JustInternetAI

# Note: GitHub Projects v2 uses a different CLI - use web interface for full setup
```

### Via GitHub Web Interface

1. Go to https://github.com/JustInternetAI/AgentArena
2. Click **Projects** tab
3. Click **New project**
4. Choose **Board** template
5. Name: "Agent Arena Development"
6. Click **Create**

## Board Columns

### 1. Backlog
**Purpose**: Unprioritized ideas and future work

**Contains**:
- Feature ideas not yet planned
- Low-priority bug fixes
- Future enhancements
- "Nice to have" items

**Move to "Todo" when**: Item is prioritized for current sprint/milestone

---

### 2. Todo
**Purpose**: Prioritized work ready to be started

**Contains**:
- Issues assigned to upcoming work
- Prioritized bug fixes
- Planned features for current milestone
- Dependencies resolved

**Move to "In Progress" when**: Someone starts working on it

---

### 3. In Progress
**Purpose**: Work currently being done

**Contains**:
- Issues actively being worked on
- PRs in draft or development
- Items with assignee actively coding

**Move to "Review" when**: PR is created and ready for review

**Limit**: Each person should have max 2-3 items here (avoid context switching)

---

### 4. Review
**Purpose**: Code review and testing

**Contains**:
- PRs awaiting code review
- Items needing testing
- Documentation needing review

**Move to "Done" when**: PR is approved and merged

**Move back to "In Progress" if**: Changes requested

---

### 5. Done
**Purpose**: Completed work in current sprint

**Contains**:
- Merged PRs
- Closed issues
- Completed milestones

**Archive**: Clear monthly or per release

---

## Custom Fields

Add these custom fields to track additional metadata:

### Priority
- **Type**: Single select
- **Options**:
  - 🔴 Critical
  - 🟠 High
  - 🟡 Medium
  - 🟢 Low

### Component
- **Type**: Single select
- **Options**:
  - Godot/C++
  - Python/Runtime
  - Backends
  - Memory
  - Tools
  - Scenes
  - Documentation
  - Testing
  - IPC

### Size
- **Type**: Single select
- **Options**:
  - XS (< 2 hours)
  - S (< 1 day)
  - M (1-3 days)
  - L (3-5 days)
  - XL (> 1 week)

### Sprint
- **Type**: Iteration
- **Duration**: 1 week
- **Use**: Track weekly work cycles

## Automation Rules

Set up GitHub Actions workflows to automate board movement:

### Auto-move to "In Progress"
**Trigger**: Issue assigned or PR opened in draft
**Action**: Move to "In Progress" column

### Auto-move to "Review"
**Trigger**: PR marked ready for review
**Action**: Move to "Review" column

### Auto-move to "Done"
**Trigger**: PR merged or issue closed
**Action**: Move to "Done" column

### Example Workflow

Create `.github/workflows/project-automation.yml`:

```yaml
name: Project Board Automation

on:
  issues:
    types: [assigned, closed]
  pull_request:
    types: [opened, ready_for_review, closed]

jobs:
  update_board:
    runs-on: ubuntu-latest
    steps:
      - name: Move assigned issues to In Progress
        if: github.event.action == 'assigned'
        uses: alex-page/github-project-automation-plus@v0.9.0
        with:
          project: Agent Arena Development
          column: In Progress
          repo-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Move PRs to Review
        if: github.event.action == 'ready_for_review'
        uses: alex-page/github-project-automation-plus@v0.9.0
        with:
          project: Agent Arena Development
          column: Review
          repo-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Move merged PRs to Done
        if: github.event.pull_request.merged == true
        uses: alex-page/github-project-automation-plus@v0.9.0
        with:
          project: Agent Arena Development
          column: Done
          repo-token: ${{ secrets.GITHUB_TOKEN }}
```

## Initial Board Population

### Week 1 Issues (Your Colleague - Python)

**Backlog → Todo**:
1. Setup Python environment and requirements.txt (#1)
2. Implement BaseBackend abstract class (#2)
3. Implement FastAPI IPC server (#3)

**Priority**: 🔴 Critical
**Component**: Python/Runtime
**Size**: S-M

### Week 2 Issues (Your Colleague - Python)

**Todo**:
4. Implement AgentRuntime class (#4)
5. Implement short-term memory system (#5)
6. Implement ToolDispatcher (#6)

**Priority**: 🟠 High
**Component**: Python/Runtime, Memory, Tools
**Size**: M

### Week 1-2 Issues (You - Godot/C++)

**Todo**:
- Debug foraging scene collision detection
- Implement move_to tool execution in C++
- Add visual improvements to benchmark scenes
- Fix resource collection radius detection

**Priority**: 🟠 High
**Component**: Godot/C++, Scenes
**Size**: S-M

### Week 3 Issues (Your Colleague - Python)

**Todo**:
7. Implement LlamaCppBackend (#7)
8. Create Python unit test suite (#8)

**Priority**: 🟡 Medium
**Component**: Backends, Testing
**Size**: M-L

### Week 4 Issues (Both - Integration)

**Todo**:
9. Create end-to-end integration test (#9)
10. Create Python development documentation (#10)

**Priority**: 🟠 High
**Component**: Testing, Documentation
**Size**: M

## Board Views

Create multiple views for different perspectives:

### 1. Default Board View (Kanban)
Shows all columns with cards

### 2. Python Work View
**Filter**: `Component:Python/Runtime OR Component:Backends OR Component:Memory OR Component:Tools`
**Group by**: Status

### 3. Godot Work View
**Filter**: `Component:Godot/C++ OR Component:Scenes`
**Group by**: Status

### 4. Sprint View
**Filter**: `Sprint:Current`
**Group by**: Assignee
**Sort by**: Priority

### 5. Priority View
**Group by**: Priority
**Sort by**: Size

## Milestones

Create milestones to track larger goals:

### Milestone 1: Basic IPC Working
**Due**: Week 2
**Issues**:
- #1 Python environment
- #2 BaseBackend
- #3 FastAPI IPC server
- Godot IPC client testing

**Success criteria**:
- Godot can send perception data
- Python receives and returns action
- Integration test passes

---

### Milestone 2: Agent Runtime Complete
**Due**: Week 3
**Issues**:
- #4 AgentRuntime
- #5 Short-term memory
- #6 ToolDispatcher
- #8 Unit tests

**Success criteria**:
- Agent can process observations
- Memory system working
- Tools can be called
- >80% test coverage

---

### Milestone 3: LLM Integration
**Due**: Week 4
**Issues**:
- #7 LlamaCppBackend
- Integration testing
- Documentation

**Success criteria**:
- Real LLM can control agent
- Foraging scene works end-to-end
- Performance acceptable (< 1s per action)

---

### Milestone 4: All Scenes Working
**Due**: Week 5-6
**Issues**:
- Crafting chain scene complete
- Team capture scene complete
- Evaluation harness
- Metrics collection

**Success criteria**:
- All 3 scenes functional
- Metrics tracked correctly
- Ready for benchmarking

---

## Daily/Weekly Practices

### Daily (Async)

Each team member posts in GitHub Discussions or comments:

```
Status Update - 2025-11-11

Yesterday: Implemented LlamaCppBackend model loading
Today: Working on function calling integration
Blockers: Need clarification on tool schema format

Board: Moved #7 to In Progress
```

### Weekly Sync

**Monday**:
- Review board
- Prioritize Todo column
- Assign issues for the week
- Update milestone progress

**Friday**:
- Demo completed work
- Move Done items to archive
- Retrospective: What went well? What to improve?
- Plan next week

## Board Maintenance

### Weekly
- Archive "Done" items older than 1 week
- Update issue priorities
- Reassign stale issues
- Close duplicate issues

### Monthly
- Review backlog and close outdated items
- Update custom fields if needed
- Check milestone progress
- Adjust sprint duration if needed

## Example Board State

Here's what the board might look like in Week 2:

```
┌─────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│   Backlog   │     Todo     │ In Progress  │    Review    │     Done     │
├─────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ #11 vLLM    │ #4 Runtime   │ #2 Backend   │ #3 IPC PR    │ #1 Python    │
│   backend   │   (High,M)   │   (Critical) │   (Review)   │   env ✓      │
│             │              │   @colleague │              │              │
│ #12 Vision  │ #5 Memory    │ Scene debug  │              │              │
│   encoder   │   (High,M)   │   (High,S)   │              │              │
│             │   @colleague │   @you       │              │              │
│ #13 RL      │              │              │              │              │
│   training  │ #6 Tools     │              │              │              │
│             │   (High,M)   │              │              │              │
│             │              │              │              │              │
└─────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

## Tips for Effective Board Use

1. **Keep it updated**: Move cards as work progresses
2. **Limit WIP**: Don't have too many items in "In Progress"
3. **Add details**: Comment on cards with progress updates
4. **Link PRs**: Link PRs to issues for automatic tracking
5. **Use labels**: Tag issues with component/priority
6. **Regular grooming**: Review and update board weekly
7. **Celebrate done**: Acknowledge completed work!

## Integration with Issues

When creating issues (see [github_issues.md](github_issues.md)), add them directly to the project:

```bash
# Create issue and add to project
gh issue create \
  --title "Setup Python environment" \
  --label "python,setup,good-first-issue" \
  --project "Agent Arena Development" \
  --body "..."
```

Or use the web interface and select the project when creating the issue.

## Resources

- [GitHub Projects Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [GitHub Projects Best Practices](https://github.com/features/issues)
- [Project Automation](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project)

## Questions?

Open a discussion on GitHub or ask in your team's communication channel.

---

**Next Steps**:
1. Create the project board via GitHub web interface
2. Add the 5 columns (Backlog, Todo, In Progress, Review, Done)
3. Add custom fields (Priority, Component, Size, Sprint)
4. Populate with issues from [github_issues.md](github_issues.md)
5. Set up automation rules
6. Start using it!
