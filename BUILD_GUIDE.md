# Build Guide for Agent Arena GDExtension

## Quick Start

### Rebuild Everything (Recommended)
```powershell
.\rebuild_clean.ps1
```
This script will:
1. Clean the build
2. Build Debug configuration
3. Build Release configuration
4. Output DLLs to `bin/windows/` with correct names

### Build Debug Only
```powershell
cmake --build godot/build --config Debug
```

### Build Release Only
```powershell
cmake --build godot/build --config Release
```

### Force Clean Rebuild
```powershell
cmake --build godot/build --config Debug --clean-first
```

## After Building

### Clear Godot Cache
If Godot doesn't pick up changes, clear the cache:
```powershell
Remove-Item .godot -Recurse -Force
```
Then restart Godot editor.

### Verify Build
Check DLL timestamps:
```powershell
Get-Item bin/windows/*.dll | Select-Object Name, LastWriteTime
```

## Build Output Locations

- **Debug DLL**: `bin/windows/libagent_arena.windows.template_debug.x86_64.dll`
- **Release DLL**: `bin/windows/libagent_arena.windows.template_release.x86_64.dll`

## CMake Configuration

The project uses CMake with Visual Studio generator (multi-config).

### Reconfigure CMake (if CMakeLists.txt changes)
```powershell
cmake -S godot -B godot/build -G "Visual Studio 17 2022" -A x64
```

## Troubleshooting

### "cmake: command not found"
CMake needs to be in your PATH. Either:
1. Restart your terminal/VS Code after installing CMake
2. Use full path: `& "C:\Program Files\CMake\bin\cmake.exe"`

### "EventBus node not found in scene"
1. Make sure DLL was rebuilt: `Get-Item bin/windows/*.dll | Select-Object LastWriteTime`
2. Clear Godot cache: `Remove-Item .godot -Recurse -Force`
3. Restart Godot editor

### Wrong DLL location
If DLL goes to `bin/windows/Debug/`, the CMakeLists.txt wasn't updated correctly.
Make sure lines 96-105 in `godot/CMakeLists.txt` have the `RUNTIME_OUTPUT_DIRECTORY_*` properties.

## Architecture Notes

The GDExtension includes these C++ classes:
- `SimulationManager` - Manages simulation tick loop
- `EventBus` - Handles event recording/replay (critical for deterministic simulation)
- `Agent` - Agent representation with perception/action
- `ToolRegistry` - Manages available agent tools
- `IPCClient` - Communication with Python runtime

All classes are registered in `godot/src/register_types.cpp`.
