# Python Environment Setup

## Python Version Requirement

**Agent Arena requires Python 3.11** (specifically tested with 3.11.9)

Many ML/AI packages (llama-cpp-python, torch, faiss, etc.) don't yet have pre-built wheels for Python 3.14. Using Python 3.11 ensures all dependencies install smoothly.

## Installation Steps

### 1. Install Python 3.11

**Download**: [Python 3.11.9 (64-bit)](https://www.python.org/downloads/release/python-3119/)

**During installation**:
- ✅ Check "Add Python 3.11 to PATH"
- ✅ Check "Install for all users" (optional)

**Verify installation**:
```bash
py -3.11 --version
# Should output: Python 3.11.9
```

### 2. Create Virtual Environment

```bash
cd "c:\Projects\Agent Arena\python"

# Create venv with Python 3.11
py -3.11 -m venv venv

# Activate venv
venv\Scripts\activate

# Verify Python version in venv
python --version
# Should output: Python 3.11.9
```

### 3. Install Dependencies

#### Option A: Full Installation (Recommended)
Installs all dependencies including LLM backends, vector stores, etc.

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note**: This may take 5-10 minutes as some packages (torch, transformers) are large.

#### Option B: Minimal Installation (For IPC Testing Only)
If you just want to test the IPC system quickly:

```bash
pip install --upgrade pip
pip install -r requirements-minimal.txt
```

This installs only FastAPI, uvicorn, and essential packages. You'll need the full installation later for LLM functionality.

### 4. Verify Installation

```bash
# Test imports
python -c "import fastapi; import uvicorn; print('IPC dependencies OK')"

# Full test (only if you did full installation)
python -c "import torch; import transformers; import faiss; print('All dependencies OK')"
```

## Running the IPC Server

```bash
cd "c:\Projects\Agent Arena\python"
venv\Scripts\activate
python run_ipc_server.py
```

You should see:
```
============================================================
Agent Arena IPC Server
============================================================
Host: 127.0.0.1
Port: 5000
Max Workers: 4
============================================================
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:5000
```

## Troubleshooting

### "Python 3.11 not found"
- Make sure you installed Python 3.11 from python.org
- Try `py --list` to see available Python versions
- If 3.11 doesn't appear, reinstall and check "Add to PATH"

### "No module named 'fastapi'"
- Make sure venv is activated: `venv\Scripts\activate`
- Reinstall: `pip install -r requirements.txt`

### "ERROR: Could not build wheels for llama-cpp-python"
- Requires Visual Studio C++ Build Tools
- On Windows, install: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- Select "Desktop development with C++" workload

### "torch" installation is very slow
- torch is ~2GB, be patient
- Alternative: Use CPU-only version: `pip install torch --index-url https://download.pytorch.org/whl/cpu`

### Port 5000 already in use
- Change port: `python run_ipc_server.py --port 5001`
- Update Godot IPCClient.server_url to match

## Using Different Python Versions

If you need to keep Python 3.14 as default but use 3.11 for this project:

```bash
# Always use py -3.11 to create the venv
py -3.11 -m venv venv

# Once activated, the venv uses 3.11 automatically
venv\Scripts\activate
python --version  # Shows 3.11.9
```

## Next Steps

After setup:
1. Start IPC server: `python run_ipc_server.py`
2. Open Godot and run [scenes/ipc_test.gd](scenes/ipc_test.gd)
3. Verify communication in console logs

See [docs/ipc.md](docs/ipc.md) for detailed IPC documentation.
