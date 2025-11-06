# GitHub Repository Setup Guide

This guide explains how to set up the Agent Arena repository on GitHub under the JustInternetAI organization.

## Repository Structure

- **Organization**: JustInternetAI
- **Repository**: AgentArena
- **URL**: https://github.com/JustInternetAI/AgentArena
- **Visibility**: Public (recommended for open source)

## Initial Setup Steps

### 1. Create Repository on GitHub

1. Go to https://github.com/organizations/JustInternetAI/repositories/new
2. Repository name: `AgentArena`
3. Description: `A Godot-native framework for LLM-driven NPCs with tools, memory, and goal-oriented behavior`
4. Visibility: **Public**
5. Do NOT initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

### 2. Initialize Git Locally

```bash
cd "c:/Projects/Agent Arena"

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Agent Arena framework

- Godot C++ GDExtension module
- Python agent runtime with LLM backends
- Tool system and memory infrastructure
- Comprehensive documentation
- Apache 2.0 license

Founded by Andrew Madison and Justin Madison
"

# Add remote
git remote add origin https://github.com/JustInternetAI/AgentArena.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 3. Configure Repository Settings

#### Topics/Tags
Add these topics to help discovery:
- `godot`
- `godot4`
- `llm`
- `agents`
- `ai`
- `machine-learning`
- `game-development`
- `multi-agent`
- `reinforcement-learning`
- `simulation`

#### About Section
```
A Godot-native framework for LLM-driven NPCs with tools, memory, and goal-oriented behavior
```

Website: (Add your website if you have one)

#### Branch Protection (Recommended)

For `main` branch:
- ✓ Require pull request reviews before merging
- ✓ Require status checks to pass (once CI is set up)
- ✓ Require branches to be up to date
- ✓ Include administrators (optional)

### 4. Set Up Teams and Permissions

#### Create Teams:

1. **Core Team**
   - Members: Andrew Madison (@andrewmadison), Justin Madison (@justinmadison)
   - Permission: Admin

2. **Contributors**
   - Members: (Add trusted contributors)
   - Permission: Write

3. **Triage Team**
   - Members: (Community moderators)
   - Permission: Triage

### 5. Configure Issue Templates

GitHub will use the templates in `.github/ISSUE_TEMPLATE/`:

Create `.github/ISSUE_TEMPLATE/bug_report.md`:
```markdown
---
name: Bug Report
about: Report a bug in Agent Arena
title: '[BUG] '
labels: bug
assignees: ''
---

**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior.

**Expected behavior**
What you expected to happen.

**Environment:**
- OS: [e.g., Windows 11]
- Godot Version: [e.g., 4.2]
- Python Version: [e.g., 3.11]
- Agent Arena Version: [e.g., 0.1.0]

**Additional context**
Any other context about the problem.
```

Create `.github/ISSUE_TEMPLATE/feature_request.md`:
```markdown
---
name: Feature Request
about: Suggest a feature for Agent Arena
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives you've considered**
Other approaches you've thought about.

**Additional context**
Any other context or screenshots.
```

### 6. Set Up Pull Request Template

Create `.github/pull_request_template.md`:
```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests (if applicable)
- [ ] Documentation updated

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-reviewed my code
- [ ] Commented complex code
- [ ] Updated documentation
- [ ] No new warnings
```

### 7. Add GitHub Actions (CI/CD)

Create `.github/workflows/tests.yml`:
```yaml
name: Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  python-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        cd python
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        cd tests
        pytest -v --cov=../python

    - name: Upload coverage
      uses: codecov/codecov-action@v3

  cpp-build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3
      with:
        submodules: recursive

    - name: Install dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y cmake build-essential

    - name: Setup godot-cpp
      run: |
        ./scripts/setup_godot_cpp.sh

    - name: Build C++ module
      run: |
        cd godot
        mkdir build
        cd build
        cmake ..
        cmake --build .
```

### 8. Repository Badges

Add to top of README.md:

```markdown
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/JustInternetAI/AgentArena.svg)](https://github.com/JustInternetAI/AgentArena/stargazers)
[![GitHub Issues](https://img.shields.io/github/issues/JustInternetAI/AgentArena.svg)](https://github.com/JustInternetAI/AgentArena/issues)
[![Tests](https://github.com/JustInternetAI/AgentArena/workflows/Tests/badge.svg)](https://github.com/JustInternetAI/AgentArena/actions)
```

## Organization Profile Setup

### Create JustInternetAI Profile README

In the organization, create a special repository called `.github` with a `profile/README.md`:

```markdown
# JustInternetAI

Building intelligent systems for interactive experiences.

## Projects

### 🎮 Agent Arena
A Godot-native framework for LLM-driven NPCs
→ [JustInternetAI/AgentArena](https://github.com/JustInternetAI/AgentArena)

## About

Founded by Andrew Madison and Justin Madison.

We focus on:
- AI-driven game development tools
- Multi-agent systems
- Local LLM integration
- Open source frameworks

## Get Involved

- Star our projects
- Open issues and discussions
- Submit pull requests
- Join our community
```

## Personal vs Organization Accounts

### Contribution Attribution

When committing code:

```bash
# Configure git for proper attribution
git config user.name "Justin Madison"
git config user.email "justin@justinternetai.com"  # Use org email if available

# Commits will show:
# - Author: Justin Madison (your personal account)
# - Repository: JustInternetAI/AgentArena (organization)
```

### GitHub Contributions Graph

- Commits to `JustInternetAI/AgentArena` will appear on your personal profile (@justinmadison)
- They'll show as contributions to the organization's repository
- Your personal contribution graph will include these commits

### Best Practices

1. **Use Personal Account for Commits**
   - Commit and push using your @justinmadison account
   - This ensures proper attribution

2. **Organization Owns Repository**
   - Repository lives under JustInternetAI
   - Organization provides the "home" and brand

3. **Admin Access**
   - Add both personal accounts as admins
   - Gives you full control

4. **Email Configuration**
   ```bash
   # Option 1: Use personal email
   git config user.email "your@personal.email"

   # Option 2: Use GitHub noreply email
   git config user.email "justinmadison@users.noreply.github.com"

   # Option 3: Use organization email (if you have one)
   git config user.email "justin@justinternetai.com"
   ```

## Releases and Tags

### Creating Releases

1. Tag a version:
   ```bash
   git tag -a v0.1.0 -m "Initial release"
   git push origin v0.1.0
   ```

2. Create release on GitHub:
   - Go to Releases → Draft a new release
   - Choose the tag (v0.1.0)
   - Write release notes
   - Attach compiled binaries if available

### Semantic Versioning

Follow semantic versioning (semver):
- MAJOR version: Breaking changes
- MINOR version: New features (backward compatible)
- PATCH version: Bug fixes

Example:
- v0.1.0 - Initial alpha release
- v0.2.0 - Add new backend support
- v0.2.1 - Fix memory leak

## Community Management

### Discussions

Enable GitHub Discussions for:
- Q&A
- Feature ideas
- Show and tell
- General chat

### Wiki

Consider enabling the Wiki for:
- Detailed tutorials
- Architecture deep-dives
- FAQ
- Community guides

### Sponsorship

Consider setting up GitHub Sponsors:
- Add `.github/FUNDING.yml`
- Link to sponsorship platforms
- Transparent about use of funds

## Security

### Security Policy

Create `SECURITY.md`:
```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public issues.**

Email: security@justinternetai.com

We'll respond within 48 hours.
```

### Dependabot

Enable Dependabot for automatic dependency updates.

## Next Steps

After initial setup:

1. ✓ Push code to GitHub
2. ✓ Configure repository settings
3. ✓ Add issue templates
4. ✓ Set up CI/CD
5. ✓ Create first release (v0.1.0)
6. ✓ Announce project
7. ✓ Enable discussions
8. ✓ Add contributing guidelines

## Questions?

If you need help with any of these steps, GitHub documentation is excellent:
- [Organizations](https://docs.github.com/en/organizations)
- [Repository settings](https://docs.github.com/en/repositories)
- [GitHub Actions](https://docs.github.com/en/actions)
