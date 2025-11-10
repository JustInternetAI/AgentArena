#!/bin/bash
# Initialize Git repository and push to GitHub

set -e

echo "=========================================="
echo "  Agent Arena - GitHub Initialization"
echo "=========================================="
echo ""

REPO_URL="https://github.com/JustInternetAI/AgentArena.git"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed"
    exit 1
fi

# Initialize repository if not already done
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
    echo "✓ Git repository initialized"
else
    echo "✓ Git repository already initialized"
fi

# Configure git user (update with your details)
echo ""
echo "Configuring git user..."
read -p "Enter your name (e.g., Justin Madison): " GIT_NAME
read -p "Enter your email: " GIT_EMAIL

git config user.name "$GIT_NAME"
git config user.email "$GIT_EMAIL"
echo "✓ Git user configured"

# Add remote if not exists
if ! git remote | grep -q origin; then
    echo ""
    echo "Adding remote origin..."
    git remote add origin "$REPO_URL"
    echo "✓ Remote added: $REPO_URL"
else
    echo "✓ Remote 'origin' already exists"
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo ""
    echo "Warning: .gitignore not found"
fi

# Show status
echo ""
echo "=========================================="
echo "Repository Status:"
echo "=========================================="
git status

# Ask to commit and push
echo ""
read -p "Ready to commit and push? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Adding files..."
    git add .

    echo "Creating commit..."
    git commit -m "Initial commit: Agent Arena framework

- Godot C++ GDExtension module with core simulation classes
- Python agent runtime with LLM backend support
- Tool system (world query, movement, inventory)
- Memory infrastructure (short-term and RAG)
- Comprehensive documentation and setup guides
- Apache 2.0 license with founder attribution
- GitHub workflows and issue templates

Founded by Andrew Madison and Justin Madison
Maintained by JustInternetAI
" || echo "Note: Commit may have failed if no changes"

    echo ""
    echo "Pushing to GitHub..."
    git branch -M main
    git push -u origin main

    echo ""
    echo "=========================================="
    echo "✓ Repository pushed to GitHub!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Visit: https://github.com/JustInternetAI/AgentArena"
    echo "2. Configure repository settings (topics, about, etc.)"
    echo "3. Review and merge any dependabot PRs"
    echo "4. Create your first release (v0.1.0)"
    echo ""
    echo "See GITHUB_SETUP.md for detailed configuration instructions"
else
    echo ""
    echo "Skipped. When ready, run:"
    echo "  git add ."
    echo "  git commit -m 'Initial commit'"
    echo "  git push -u origin main"
fi
