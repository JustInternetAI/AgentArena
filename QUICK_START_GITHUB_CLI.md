# Quick Start: GitHub CLI for Agent Arena

Quick reference for using GitHub CLI to manage Agent Arena development.

## Setup (One Time)

```bash
# 1. Install GitHub CLI
winget install --id GitHub.cli  # Windows

# 2. Authenticate
gh auth login

# 3. Navigate to repo
cd "c:\Projects\Agent Arena"
```

---

## Create Labels & Issues (Automated)

**IMPORTANT: Run these scripts in order!**

### Step 1: Create Labels First

```bash
# Windows
scripts\create_github_labels.bat

# Linux/Mac
bash scripts/create_github_labels.sh
```

This creates all the labels (backend, python, enhancement, etc.) that issues will use.

### Step 2: Create Issues

```bash
# Windows
scripts\create_github_issues.bat

# Linux/Mac
bash scripts/create_github_issues.sh
```

This creates ~10 high-priority issues with the labels you just created.

**Why this order?** Labels must exist before you can assign them to issues!

---

## Manual Issue Creation

### Create Issue

```bash
gh issue create \
  --title "Your issue title" \
  --label "python,enhancement" \
  --assignee @me \
  --body "Issue description"
```

### Create Issue for Colleague

```bash
gh issue create \
  --title "Setup Python environment" \
  --label "python,setup,good-first-issue" \
  --assignee colleague-github-username \
  --body "Create venv and requirements.txt"
```

---

## Project Board Management

### Create Project Board (Web)

1. Go to: https://github.com/JustInternetAI/AgentArena
2. Click **Projects** → **New project**
3. Choose **Board** template
4. Name: "Agent Arena Development"
5. Note the project number (shows as `#1`, `#2`, etc.)

### Add Issue to Project

```bash
# Replace 1 with your project number, 5 with issue number
gh project item-add 1 \
  --owner JustInternetAI \
  --url https://github.com/JustInternetAI/AgentArena/issues/5
```

**PowerShell (easier)**:
```powershell
# Add issue #5 to project #1
$url = gh issue view 5 --json url -q .url
gh project item-add 1 --owner JustInternetAI --url $url
```

### Add All Open Issues to Project

**PowerShell**:
```powershell
# Add all open issues to project #1
gh issue list --state open --json number -q '.[].number' | ForEach-Object {
  $url = gh issue view $_ --json url -q .url
  gh project item-add 1 --owner JustInternetAI --url $url
  Write-Host "Added issue #$_"
}
```

**Bash**:
```bash
gh issue list --state open --json number -q '.[].number' | while read num; do
  url=$(gh issue view $num --json url -q .url)
  gh project item-add 1 --owner JustInternetAI --url $url
  echo "Added issue #$num"
done
```

---

## Daily Workflow

### View Your Issues

```bash
# Issues assigned to you
gh issue list --assignee @me

# All open issues
gh issue list --state open

# Python-related issues
gh issue list --label "python"
```

### Update Issue

```bash
# Add label
gh issue edit 5 --add-label "in-progress"

# Assign yourself
gh issue edit 5 --assignee @me

# Close issue
gh issue close 5 --comment "Completed in PR #10"
```

### Create PR

```bash
# From current branch
gh pr create --title "Add vLLM backend" --body "Implements issue #5"

# Draft PR
gh pr create --draft --title "WIP: vLLM backend"
```

---

## Common Commands

| Action | Command |
|--------|---------|
| List issues | `gh issue list` |
| View issue | `gh issue view 5` |
| Create issue | `gh issue create` |
| Edit issue | `gh issue edit 5` |
| Close issue | `gh issue close 5` |
| List PRs | `gh pr list` |
| Create PR | `gh pr create` |
| View PR | `gh pr view 10` |
| Merge PR | `gh pr merge 10 --squash` |
| Open repo in browser | `gh repo view --web` |
| View project | `gh project list --owner JustInternetAI` |

---

## Week 1 Quick Setup

```bash
# 1. Create issues for colleague (Python work)
gh issue create --title "Setup Python environment" \
  --label "python,setup,good-first-issue" \
  --assignee colleague-username

gh issue create --title "Implement BaseBackend class" \
  --label "python,backend,architecture" \
  --assignee colleague-username

gh issue create --title "Implement FastAPI IPC server" \
  --label "python,ipc,critical" \
  --assignee colleague-username

# 2. View created issues
gh issue list

# 3. Create project board (via web)
# Go to: https://github.com/JustInternetAI/AgentArena/projects

# 4. Add issues to board (PowerShell)
1..3 | ForEach-Object {
  $url = gh issue view $_ --json url -q .url
  gh project item-add 1 --owner JustInternetAI --url $url
}

# 5. Done! View the board
gh project view 1 --owner JustInternetAI --web
```

---

## Tips

1. **Use `--web` flag** to open items in browser:
   ```bash
   gh issue view 5 --web
   gh pr view 10 --web
   gh repo view --web
   ```

2. **Use interactive mode** (prompts for input):
   ```bash
   gh issue create  # No flags = interactive
   gh pr create
   ```

3. **Get JSON output** for scripting:
   ```bash
   gh issue list --json number,title,state
   ```

4. **Reference issues in commits**:
   ```bash
   git commit -m "feat: add vLLM backend (#5)"
   ```

5. **Auto-close issues with PRs**:
   ```bash
   gh pr create --body "Closes #5"
   ```

---

## Next Steps

✅ Install GitHub CLI
✅ Run `scripts\create_github_issues.bat`
✅ Create project board via web
✅ Add issues to board
✅ Start developing!

**Full documentation**: See [docs/github_cli_guide.md](docs/github_cli_guide.md)

**Backlog items**: See [docs/backlog_items.md](docs/backlog_items.md)

**Issue templates**: See [docs/github_issues.md](docs/github_issues.md)
