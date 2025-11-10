# GitHub CLI Guide for Agent Arena

Complete guide to using GitHub CLI (`gh`) for creating issues, managing the project board, and coordinating development.

## Table of Contents

- [Installation & Setup](#installation--setup)
- [Creating Issues](#creating-issues)
- [Managing Project Board](#managing-project-board)
- [Common Workflows](#common-workflows)
- [Batch Operations](#batch-operations)

---

## Installation & Setup

### Install GitHub CLI

**Windows**:
```powershell
# Using winget
winget install --id GitHub.cli

# Or download from: https://cli.github.com/
```

**Mac**:
```bash
brew install gh
```

**Linux**:
```bash
# Debian/Ubuntu
sudo apt install gh

# Or see: https://github.com/cli/cli/blob/trunk/docs/install_linux.md
```

### Authenticate

```bash
# Login to GitHub
gh auth login

# Follow prompts:
# 1. Choose GitHub.com
# 2. Choose HTTPS
# 3. Authenticate via browser
# 4. Choose default git protocol: HTTPS

# Verify authentication
gh auth status
```

### Set Default Repository

```bash
# Navigate to repo directory
cd "c:\Projects\Agent Arena"

# Verify you're in correct repo
gh repo view

# Should show: JustInternetAI/AgentArena
```

---

## Creating Issues

### Basic Issue Creation

```bash
# Simple issue
gh issue create --title "Fix bug in foraging scene" --body "Resource collection not working"

# Issue with labels
gh issue create \
  --title "Add vLLM backend" \
  --label "backend,enhancement,high-priority" \
  --body "Implement vLLM for faster inference"

# Issue with assignee
gh issue create \
  --title "Setup Python environment" \
  --assignee @me \
  --label "python,setup" \
  --body "Create venv and requirements.txt"
```

### Issue from Template File

Create a file with the issue body:

**File**: `issue_templates/vllm_backend.md`
```markdown
## Description
Support vLLM for faster batch inference.

## Tasks
- [ ] Research vLLM API
- [ ] Create backend class
- [ ] Add tests

## Acceptance Criteria
- Works with Llama-2
- Faster than sequential inference
```

Then create the issue:
```bash
gh issue create \
  --title "vLLM Backend Integration" \
  --label "backend,enhancement" \
  --body-file issue_templates/vllm_backend.md
```

### Interactive Issue Creation

```bash
# Opens editor for title and body
gh issue create

# Follow the prompts
```

---

## Managing Project Board

### Create Project (v2)

Projects v2 must be created via web interface currently, but you can link issues to it.

**Via Web**:
1. Go to https://github.com/orgs/JustInternetAI/projects
2. Click **New project**
3. Choose **Board** template
4. Name: "Agent Arena Development"
5. Note the project number (e.g., #1)

### List Projects

```bash
# List organization projects
gh project list --owner JustInternetAI

# Output shows project number and title
```

### Add Issue to Project

```bash
# Get project number (e.g., 1) and issue URL
gh project item-add 1 \
  --owner JustInternetAI \
  --url https://github.com/JustInternetAI/AgentArena/issues/5

# Or use issue number
ISSUE_URL=$(gh issue view 5 --json url -q .url)
gh project item-add 1 --owner JustInternetAI --url $ISSUE_URL
```

**Windows PowerShell**:
```powershell
# Get issue URL
$ISSUE_URL = gh issue view 5 --json url -q .url

# Add to project
gh project item-add 1 --owner JustInternetAI --url $ISSUE_URL
```

### List Project Items

```bash
# View all items in project
gh project item-list 1 --owner JustInternetAI

# With specific fields
gh project item-list 1 --owner JustInternetAI --format json
```

---

## Common Workflows

### Workflow 1: Create Issue and Add to Board

```bash
# 1. Create the issue
gh issue create \
  --title "Implement LlamaCppBackend" \
  --label "python,backend,critical" \
  --assignee @me \
  --body "Create llama.cpp backend for local LLM inference"

# 2. Get the issue number from output (e.g., #7)

# 3. Add to project board
ISSUE_URL=$(gh issue view 7 --json url -q .url)
gh project item-add 1 --owner JustInternetAI --url $ISSUE_URL

# 4. Verify
gh issue view 7
```

**One-liner** (PowerShell):
```powershell
$issue = gh issue create --title "Test Issue" --body "Test" --json number | ConvertFrom-Json
$url = gh issue view $issue.number --json url -q .url
gh project item-add 1 --owner JustInternetAI --url $url
```

### Workflow 2: Bulk Create Issues from List

Create a file with issue data:

**File**: `backlog.csv`
```csv
title,labels,priority,body
vLLM Backend,backend;enhancement,high,Implement vLLM for batch inference
Long-Term Memory,memory;enhancement,high,Add FAISS vector store
Evaluation Harness,evals;critical,high,Automated benchmark running
```

**Script** (`scripts/bulk_create_issues.sh`):
```bash
#!/bin/bash
while IFS=, read -r title labels priority body
do
  gh issue create \
    --title "$title" \
    --label "$labels" \
    --body "$body\n\nPriority: $priority"
done < backlog.csv
```

Run it:
```bash
bash scripts/bulk_create_issues.sh
```

### Workflow 3: Update Issue Labels

```bash
# Add labels
gh issue edit 5 --add-label "good-first-issue"

# Remove labels
gh issue edit 5 --remove-label "wontfix"

# Replace all labels
gh issue edit 5 --label "backend,python,high-priority"
```

### Workflow 4: Assign Issues

```bash
# Assign to yourself
gh issue edit 5 --assignee @me

# Assign to specific user
gh issue edit 5 --assignee colleague-username

# Assign multiple people
gh issue edit 5 --assignee user1,user2
```

### Workflow 5: Close Issue with Comment

```bash
# Close issue
gh issue close 5

# Close with comment
gh issue close 5 --comment "Fixed in PR #12"
```

---

## Batch Operations

### Create All Backlog Issues

Use the provided script:

**Windows**:
```bash
# Run the batch script
scripts\create_github_issues.bat
```

**Linux/Mac**:
```bash
# Make executable
chmod +x scripts/create_github_issues.sh

# Run
bash scripts/create_github_issues.sh
```

### Add All Issues to Project

```bash
# Get all open issues
gh issue list --state open --limit 100 --json number -q '.[].number' > issues.txt

# Add each to project (PowerShell)
Get-Content issues.txt | ForEach-Object {
  $url = gh issue view $_ --json url -q .url
  gh project item-add 1 --owner JustInternetAI --url $url
  Write-Host "Added issue #$_ to project"
}
```

**Bash version**:
```bash
# Get all open issues
gh issue list --state open --limit 100 --json number -q '.[].number' | while read num; do
  url=$(gh issue view $num --json url -q .url)
  gh project item-add 1 --owner JustInternetAI --url $url
  echo "Added issue #$num to project"
done
```

---

## Useful Commands Reference

### Issues

```bash
# List all issues
gh issue list

# List with filters
gh issue list --label "python" --state open
gh issue list --assignee @me
gh issue list --author colleague-username

# View issue details
gh issue view 5
gh issue view 5 --web  # Open in browser

# Comment on issue
gh issue comment 5 --body "Working on this now"

# Search issues
gh issue list --search "backend"
```

### Pull Requests

```bash
# Create PR from current branch
gh pr create --title "Add vLLM backend" --body "Implements vLLM integration"

# Create draft PR
gh pr create --draft --title "WIP: vLLM backend"

# List PRs
gh pr list
gh pr list --author @me

# View PR
gh pr view 10
gh pr view 10 --web

# Check PR status
gh pr status

# Merge PR
gh pr merge 10 --squash

# Close PR
gh pr close 10
```

### Repository

```bash
# View repo info
gh repo view

# Clone repo
gh repo clone JustInternetAI/AgentArena

# Fork repo
gh repo fork

# View in browser
gh repo view --web
```

---

## Project Management Automation

### Script: Add New Issues to Project Automatically

**File**: `.github/workflows/add-to-project.yml`
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

This automatically adds new issues to your project board!

---

## Tips & Tricks

### 1. Create Aliases

Add to `.bashrc` or PowerShell profile:

```bash
# Bash aliases
alias ghic='gh issue create'
alias ghil='gh issue list'
alias ghiv='gh issue view'
alias ghpc='gh pr create'
alias ghpl='gh pr list'
```

**PowerShell**:
```powershell
# Add to $PROFILE
function ghic { gh issue create $args }
function ghil { gh issue list $args }
function ghiv { gh issue view $args }
```

### 2. Use JSON Output for Scripting

```bash
# Get issue data as JSON
gh issue view 5 --json number,title,state,labels

# Parse with jq
gh issue list --json number,title,state | jq '.[] | select(.state == "OPEN")'
```

### 3. Quick Issue Templates

Create template files in `issue_templates/`:

```bash
# Python issue template
cat > issue_templates/python.md << 'EOF'
## Description
[Describe the Python component]

## Tasks
- [ ] Implementation
- [ ] Tests
- [ ] Documentation

## Component
Python
EOF

# Use it
gh issue create --body-file issue_templates/python.md --title "New Python Feature"
```

### 4. Link Issues and PRs

```bash
# Reference issue in PR
gh pr create --title "Fix #5: Add vLLM backend"

# Close issue when PR merges (in PR description)
gh pr create --body "Closes #5\n\nImplements vLLM backend"
```

### 5. Use Issue Numbers in Commits

```bash
git commit -m "feat(backend): add vLLM support (#5)"

# GitHub automatically links the commit to issue #5
```

---

## Complete Example: Week 1 Setup

Here's a complete workflow for Week 1:

```bash
# 1. Authenticate
gh auth login

# 2. Navigate to repo
cd "c:\Projects\Agent Arena"

# 3. Create issues for Week 1
gh issue create \
  --title "Setup Python environment and requirements.txt" \
  --label "python,setup,good-first-issue" \
  --assignee colleague-username \
  --body-file docs/issue_bodies/issue_1.md

gh issue create \
  --title "Implement BaseBackend abstract class" \
  --label "python,backend,architecture" \
  --assignee colleague-username \
  --body-file docs/issue_bodies/issue_2.md

gh issue create \
  --title "Implement FastAPI IPC server" \
  --label "python,ipc,critical" \
  --assignee colleague-username \
  --body-file docs/issue_bodies/issue_3.md

# 4. View created issues
gh issue list --assignee colleague-username

# 5. Add to project board (assuming project #1)
for i in {1..3}; do
  url=$(gh issue view $i --json url -q .url)
  gh project item-add 1 --owner JustInternetAI --url $url
  echo "Added issue #$i to project"
done

# 6. View project
gh project view 1 --owner JustInternetAI --web
```

---

## Troubleshooting

### Error: "Resource not accessible by personal access token"

**Solution**: Create a Personal Access Token with `project` scope:
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Check `project` and `repo` scopes
4. Copy token
5. Use: `gh auth login --with-token < token.txt`

### Error: "Project not found"

**Solution**: Use the correct project number:
```bash
# List all projects
gh project list --owner JustInternetAI

# Note the correct number
```

### Issues Not Showing in Project

**Solution**: Manually add via web or use correct project URL:
```bash
gh project item-add <number> \
  --owner JustInternetAI \
  --url https://github.com/JustInternetAI/AgentArena/issues/<issue-num>
```

---

## Resources

- [GitHub CLI Manual](https://cli.github.com/manual/)
- [GitHub CLI Reference](https://cli.github.com/manual/gh)
- [GitHub Projects Docs](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [GitHub CLI Issues](https://github.com/cli/cli/issues)

---

**Next Steps**:
1. Install and authenticate GitHub CLI
2. Run `scripts/create_github_issues.bat` (Windows) or `.sh` (Linux/Mac)
3. Create project board via web interface
4. Add issues to board using commands above
5. Start developing!
