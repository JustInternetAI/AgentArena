# Testing the Prompt Inspector

## Quick Test with Godot

Use the interactive testing script to monitor and analyze prompt captures:

```bash
# Start in interactive menu mode
python test_inspector_with_godot.py

# Or start in monitor mode (watch real-time)
python test_inspector_with_godot.py --monitor
```

**Features:**
- View latest captures
- View specific ticks
- Performance analysis
- Real-time monitoring
- Export to JSON
- Change agent IDs on the fly

## Prerequisites

1. Start your IPC server with LocalLLMBehavior:
   ```bash
   python run_local_llm_forager.py --model ../models/your_model.gguf
   ```

2. Run Godot foraging scene:
   - Open Godot → Load `scenes/foraging.tscn` → Press F5 → Press SPACE

3. Run the inspector test script

## Full Documentation

For complete testing instructions, see:
- **[docs/testing_prompt_inspector.md](../docs/testing_prompt_inspector.md)** - Complete testing guide
- **[docs/prompt_inspector.md](../docs/prompt_inspector.md)** - API reference and usage

## Available Test Scripts

- `test_inspector_with_godot.py` - Interactive tool for testing with Godot
- `test_prompt_inspector_demo.py` - Standalone demo (no dependencies)
- `test_prompt_inspector_advanced.py` - Comprehensive test suite (10 tests)
