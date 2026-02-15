# Scripts Directory

This directory contains GDScript files and GitHub automation scripts for the Agent Arena project.

## GitHub Setup Scripts (*.bat / *.sh)

Scripts for creating GitHub labels and issues.

### Quick Start

Run these scripts **in order**:

#### Step 1: Create Labels First

```bash
scripts\create_github_labels.bat
```

This creates all necessary labels (backend, python, enhancement, high-priority, etc.).

**Note**: Labels must exist before you can assign them to issues!

#### Step 2: Create Issues

```bash
scripts\create_github_issues.bat
```

This creates the initial backlog issues with proper labels.

See [GitHub Guide](../docs/github_guide.md) for more details.

---

## GDScript Files

All GDScript files for the Godot simulation.

## Organization

```
scripts/
├── tests/              # Test and diagnostic scripts
│   ├── test_extension.gd    # Tests that all GDExtension classes load correctly
│   └── ipc_test.gd          # Tests IPC communication between Godot and Python
└── test_arena.gd       # Main test arena scene script
```

## Running Scripts

### Test Scripts

**Test Extension Loading:**
```
1. Open scripts/tests/test_extension.gd in Godot
2. Press F6 (Run Current Scene)
3. Check console for results
```

**Test IPC Communication:**
```
1. Start Python IPC server:
   cd python
   python run_ipc_server.py

2. Open scripts/tests/ipc_test.gd in Godot
3. Press F6 (Run Current Scene)
4. Watch both consoles for communication
```

## Best Practices

### File Naming
- Use `snake_case` for script filenames
- Test scripts should start with `test_`
- Keep scripts focused on single responsibilities

### Directory Structure
- **Root scripts**: Main game/simulation scripts
- **tests/**: Diagnostic and test scripts
- **ui/**: UI-related scripts (to be added)
- **gameplay/**: Gameplay mechanics (to be added)

### Script Organization
- Scene-specific scripts go in `scripts/` and reference `.tscn` files in `scenes/`
- Keep `.gd` scripts separate from `.tscn` scene files for better version control
- Reusable components should be in their own files

## Creating New Scripts

When creating a new script:
1. Decide if it's a test, UI, or gameplay script
2. Create it in the appropriate subdirectory
3. Use clear, descriptive names
4. Add documentation comments at the top

Example:
```gdscript
# scripts/ui/main_menu.gd
# Main menu UI controller
# Handles menu navigation and settings

extends Control

# ... implementation
```
