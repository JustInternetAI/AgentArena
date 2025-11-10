# Linting Guide for Agent Arena

## Overview
This project uses automated linting tools to maintain code quality and consistency. All Python code must pass linting checks before being merged.

## Tools Used

### 1. **Black** - Code Formatter
- Automatically formats Python code to maintain consistent style
- Configuration: `pyproject.toml` ([tool.black])
- Line length: 100 characters

### 2. **Ruff** - Fast Python Linter
- Catches common errors and enforces code quality rules
- Configuration: `pyproject.toml` ([tool.ruff.lint])
- Checks for: unused imports, import sorting, naming conventions, and more

### 3. **MyPy** - Static Type Checker
- Verifies type hints and catches type-related bugs
- Configuration: `pyproject.toml` ([tool.mypy])
- Currently set to not fail builds (continue-on-error: true)

## Running Linters Locally

### Check for issues:
```bash
# Check formatting
python -m black --check python

# Check linting
python -m ruff check python

# Check types
mypy --ignore-missing-imports python/agent_runtime python/backends python/tools
```

### Auto-fix issues:
```bash
# Auto-format code
python -m black python

# Auto-fix linting issues
python -m ruff check python --fix
```

## Pre-commit Hooks (Automatic Prevention)

Pre-commit hooks automatically run linters before each commit, catching issues before they reach CI/CD.

### Installation:
```bash
pip install pre-commit
pre-commit install
```

### Manual run on all files:
```bash
pre-commit run --all-files
```

### What happens on commit:
1. **Black** formats your Python files
2. **Ruff** checks and auto-fixes linting issues
3. **MyPy** checks types (optional)
4. If any issues can't be auto-fixed, the commit is blocked

## Common Issues and Fixes

### 1. Unused Imports
**Error:** `F401: 'module.Class' imported but unused`

**Fix:** Remove the unused import
```python
# Before
from fastapi.responses import JSONResponse  # Unused!
from fastapi import FastAPI

# After
from fastapi import FastAPI
```

### 2. Import Sorting
**Error:** `I001: Import block is un-sorted or un-formatted`

**Fix:** Run `python -m ruff check python --fix` to auto-sort imports

Ruff follows this order:
1. Standard library imports
2. Third-party imports
3. Local imports (separated by blank lines)

### 3. Line Too Long
**Error:** Lines longer than 100 characters

**Fix:** Run `python -m black python` to auto-format

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/python-tests.yml`) runs:
1. **Black** check (fails if code isn't formatted)
2. **Ruff** check (fails on linting errors)
3. **MyPy** check (warnings only, doesn't fail build)

### Viewing CI Results:
```bash
# List recent workflow runs
gh run list --workflow="Python Tests"

# View specific run details
gh run view <run-id>
```

## Best Practices

1. **Run linters before committing:**
   ```bash
   python -m black python && python -m ruff check python --fix
   ```

2. **Use pre-commit hooks** - They catch issues automatically

3. **Don't disable linting rules** without team discussion

4. **Keep imports clean** - Remove unused imports immediately

5. **Format on save** - Configure your IDE to run Black on save:
   - VSCode: Install "Black Formatter" extension
   - PyCharm: Enable Black under Tools → Black

## IDE Integration

### VSCode Settings
Add to `.vscode/settings.json`:
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true
}
```

### PyCharm
1. Go to Preferences → Tools → Black
2. Enable "On code reformat"
3. Install Ruff plugin from marketplace

## Troubleshooting

### Pre-commit hooks not running?
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install
```

### Linter version conflicts?
```bash
# Update all linters
pip install --upgrade black ruff mypy pre-commit
```

### Can't fix an issue?
- Check the specific error code in [Ruff documentation](https://docs.astral.sh/ruff/rules/)
- Ask the team for help
- Comment the line with `# noqa: <error-code>` only as last resort

## Summary

✅ All Python code must pass Black, Ruff, and MyPy checks
✅ Pre-commit hooks prevent issues before they reach CI/CD
✅ Use `--fix` flags to auto-resolve most issues
✅ Configure your IDE for automatic formatting
