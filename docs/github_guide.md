# GitHub Workflow Guide

Complete guide to using GitHub CLI (`gh`) for managing issues, pull requests, and the project board for Agent Arena.

## Table of Contents

- [Installation & Setup](#installation--setup)
- [Creating Issues](#creating-issues)
- [Managing the Project Board](#managing-the-project-board)
- [Pull Requests](#pull-requests)
- [Common Workflows](#common-workflows)
- [Batch Operations](#batch-operations)
- [Automation](#automation)
- [Tips & Tricks](#tips--tricks)

---

## Installation & Setup

### Install GitHub CLI

**Windows:**
```powershell
winget install --id GitHub.cli
```

**Mac:**
```bash
brew install gh
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install gh
```

### Authenticate

```bash
gh auth login
# Choose GitHub.com > HTTPS > Authenticate via browser

gh auth status  # Verify
```

### Verify Repository

```bash
cd "c:\Projects\Agent Arena"
gh repo view  # Should show: JustInternetAI/AgentArena
```

---

## Creating Issues

### Basic

```bash
gh issue create --title "Fix bug in foraging scene" --body "Resource collection not working"
```

### With Labels and Assignee

```bash
gh issue create \
  --title "Add vLLM backend" \
  --label "backend,enhancement,high-priority" \
  --assignee @me \
  --body "Implement vLLM for faster inference"
```

### From a Template File

```bash
gh issue create \
  --title "vLLM Backend Integration" \
  --label "backend,enhancement" \
  --body-file issue_templates/vllm_backend.md
```

### Interactive

```bash
gh issue create  # Opens editor for title and body
```

### Viewing and Managing Issues

```bash
gh issue list                              # List all
gh issue list --label "python" --state open  # Filter
gh issue list --assignee @me                # Your issues
gh issue view 5                             # View details
gh issue view 5 --web                       # Open in browser
gh issue comment 5 --body "Working on it"   # Add comment
gh issue close 5 --comment "Fixed in PR #12" # Close
gh issue edit 5 --add-label "good-first-issue"
gh issue edit 5 --assignee colleague-username
```

---

## Managing the Project Board

### Board Structure

We use a Kanban-style board with these columns:

| Column | Purpose | Move to next when... |
|--------|---------|---------------------|
| **Backlog** | Unprioritized ideas | Item is prioritized |
| **Todo** | Ready to be started | Someone starts working |
| **In Progress** | Actively being worked on | PR created for review |
| **Review** | Code review and testing | PR approved and merged |
| **Done** | Completed work | Archive monthly |

**Limit In Progress to 2-3 items per person** to avoid context switching.

### Custom Fields

- **Priority**: Critical / High / Medium / Low
- **Component**: Godot/C++, Python/Runtime, Backends, Memory, Tools, Scenes, Documentation, Testing, IPC
- **Size**: XS (<2h), S (<1d), M (1-3d), L (3-5d), XL (>1w)

### CLI Commands

```bash
# List projects
gh project list --owner JustInternetAI

# Add issue to project
ISSUE_URL=$(gh issue view 5 --json url -q .url)
gh project item-add 1 --owner JustInternetAI --url $ISSUE_URL

# List project items
gh project item-list 1 --owner JustInternetAI
```

**PowerShell:**
```powershell
$ISSUE_URL = gh issue view 5 --json url -q .url
gh project item-add 1 --owner JustInternetAI --url $ISSUE_URL
```

---

## Pull Requests

```bash
# Create PR
gh pr create --title "Add vLLM backend" --body "Implements vLLM integration"

# Create draft PR
gh pr create --draft --title "WIP: vLLM backend"

# List PRs
gh pr list
gh pr list --author @me

# View PR
gh pr view 10
gh pr view 10 --web

# Check status
gh pr status

# Merge
gh pr merge 10 --squash

# Close
gh pr close 10
```

---

## Common Workflows

### Create Issue and Add to Board

```bash
# Create the issue
gh issue create \
  --title "Implement LlamaCppBackend" \
  --label "python,backend,critical" \
  --assignee @me \
  --body "Create llama.cpp backend for local LLM inference"

# Add to project board (replace 7 with actual issue number)
ISSUE_URL=$(gh issue view 7 --json url -q .url)
gh project item-add 1 --owner JustInternetAI --url $ISSUE_URL
```

### Link Issues and PRs

```bash
# Reference issue in PR (auto-closes on merge)
gh pr create --title "Fix #5: Add vLLM backend" --body "Closes #5"

# Reference in commits
git commit -m "feat(backend): add vLLM support (#5)"
```

---

## Batch Operations

### Add All Open Issues to Project

**Bash:**
```bash
gh issue list --state open --limit 100 --json number -q '.[].number' | while read num; do
  url=$(gh issue view $num --json url -q .url)
  gh project item-add 1 --owner JustInternetAI --url $url
  echo "Added issue #$num to project"
done
```

**PowerShell:**
```powershell
gh issue list --state open --limit 100 --json number -q '.[].number' | ForEach-Object {
  $url = gh issue view $_ --json url -q .url
  gh project item-add 1 --owner JustInternetAI --url $url
  Write-Host "Added issue #$_ to project"
}
```

---

## Automation

### Auto-add New Issues to Project Board

Create `.github/workflows/add-to-project.yml`:

```yaml
name: Add to Project Board

on:
  issues:
    types: [opened]

jobs:
  add-to-project:
    runs-on: ubuntu-latest
    steps:
      - name: Add issue to project
        uses: actions/add-to-project@v0.5.0
        with:
          project-url: https://github.com/orgs/JustInternetAI/projects/1
          github-token: ${{ secrets.ADD_TO_PROJECT_TOKEN }}
```

---

## Tips & Tricks

### Shell Aliases

**Bash** (add to `.bashrc`):
```bash
alias ghic='gh issue create'
alias ghil='gh issue list'
alias ghiv='gh issue view'
alias ghpc='gh pr create'
alias ghpl='gh pr list'
```

**PowerShell** (add to `$PROFILE`):
```powershell
function ghic { gh issue create $args }
function ghil { gh issue list $args }
function ghiv { gh issue view $args }
```

### JSON Output for Scripting

```bash
gh issue view 5 --json number,title,state,labels
gh issue list --json number,title,state | jq '.[] | select(.state == "OPEN")'
```

---

## Troubleshooting

### "Resource not accessible by personal access token"

Create a Personal Access Token with `project` and `repo` scopes at https://github.com/settings/tokens.

### "Project not found"

```bash
gh project list --owner JustInternetAI  # Find correct project number
```

---

## Resources

- [GitHub CLI Manual](https://cli.github.com/manual/)
- [GitHub Projects Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
