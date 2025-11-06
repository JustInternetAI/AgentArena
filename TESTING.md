# Testing the Agent Arena GDExtension

## Status
✅ C++ module built successfully
✅ Godot project configured
✅ Test scene created

## What Was Built

The following C++ classes are now available in Godot:
- **SimulationManager** - Core simulation controller
- **Agent** - Base agent class
- **EventBus** - Event recording system
- **ToolRegistry** - Tool management

## How to Test

### 1. Download Godot 4.2+ (if not installed)
- Download from: https://godotengine.org/download/windows/
- Get **Godot 4.2** or later (Standard version)
- Extract it somewhere convenient

### 2. Open the Project
```bash
# Option 1: Via command line (if godot is in PATH)
godot --path "c:\Projects\Agent Arena"

# Option 2: Via Godot Project Manager
1. Open Godot
2. Click "Import"
3. Browse to: c:\Projects\Agent Arena
4. Select project.godot
5. Click "Import & Edit"
```

### 3. Verify the Extension Loaded
When Godot opens, check the **Output** panel (bottom) for:
```
Registered class: SimulationManager
Registered class: Agent
Registered class: EventBus
Registered class: ToolRegistry
```

If you see errors, the extension failed to load. Common issues:
- Missing DLL dependencies (MSVC runtime)
- Incompatible Godot version
- Build configuration mismatch

### 4. Run the Test Scene
1. The project should auto-open `scenes/test_arena.tscn`
2. Press **F5** or click the **Play** button to run the scene
3. You should see a window with instructions

### 5. Test Controls
- **SPACE** - Start/Stop simulation
- **S** - Step simulation (advance one tick)
- **R** - Reset simulation
- **T** - Test agent functions

### 6. Expected Output

When you press **T** (test agent), you should see in the console:
```
Testing agent functions...
Agent perceived: {position: (10, 0, 5), health: 100, nearby_objects: [tree, rock, water]}
Agent decided action: {type: idle, params: {}}
Retrieved memory: test_value
Agent executing action: idle
Tool result: {success: false, error: Tool not implemented}
```

When you press **SPACE** (start simulation):
```
✓ Simulation started!
Simulation started at tick 0
```

When you press **S** (step):
```
Tick: 1
Tick: 2
...
```

## Troubleshooting

### Extension not loading
**Error: "Can't open dynamic library"**
- Install Visual C++ Redistributable 2022: https://aka.ms/vs/17/release/vc_redist.x64.exe
- Check that the DLL exists at: `bin/windows/libagent_arena.windows.template_release.x86_64.dll`

**Error: "Symbol not found"**
- Rebuild the extension (CMake might have failed silently)
- Check that godot-cpp was cloned correctly

### Scene won't run
**Error: "Invalid type in function 'create'"**
- The extension classes aren't registered properly
- Check the Output panel for registration messages

### No output when testing
- Make sure the Output panel is visible (View → Output)
- Check that signals are connected properly

## Next Steps After Testing

Once the extension works:
1. ✅ Extension loads in Godot
2. ✅ Can create SimulationManager and Agent nodes
3. ✅ Signals work (simulation_started, tick_advanced, etc.)
4. ⏳ Implement Python IPC layer
5. ⏳ Build actual benchmark scenes

## File Structure

```
c:\Projects\Agent Arena\
├── project.godot              # Main Godot project file
├── icon.svg                   # Project icon
├── godot/
│   ├── agent_arena.gdextension  # Extension configuration
│   └── build/                 # CMake build files
├── bin/
│   └── windows/
│       └── libagent_arena.*.dll  # Built extension
└── scenes/
    ├── test_arena.tscn        # Test scene
    └── test_arena.gd          # Test script
```

## Development Workflow

After making changes to C++ code:
```bash
cd godot/build
"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" --build . --config Debug
cp bin/windows/Debug/*.dll ../bin/windows/
```

Then reload the project in Godot (Ctrl+R).
