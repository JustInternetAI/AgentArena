# Troubleshooting: IPCClient Not Found

## Error
```
ERROR: Could not find type "IPCClient" in the current scope.
```

## Cause
Godot cached the old GDExtension DLL before IPCClient was added. It needs to reload the new version.

## Solution

### Method 1: Clear Cache and Restart (Most Reliable)

1. **Close Godot completely** (make sure it's not running in background)

2. **Delete the `.godot` cache folder**:
   ```bash
   # Windows PowerShell
   Remove-Item -Recurse -Force ".godot"

   # Or Windows Command Prompt
   rmdir /s /q ".godot"

   # Or manually delete the .godot folder in Windows Explorer
   ```

3. **Restart Godot**:
   - It will recreate the `.godot` folder
   - It will reimport all assets and reload the extension

4. **Verify the classes are loaded**:
   - Open and run `scripts/tests/test_extension.gd`
   - You should see all 5 classes (including IPCClient) pass

### Method 2: Just Restart Godot

Sometimes simply closing and reopening Godot is enough:
1. Close Godot completely
2. Reopen the project
3. Try running `scripts/tests/test_extension.gd`

### Method 3: Rebuild the Extension

If the above doesn't work, the DLL might not have been built correctly:

```bash
cd "c:\Projects\Agent Arena\godot\build"

# Clean build
"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" --build . --config Debug --clean-first

# Restart Godot after build completes
```

## Verification Steps

### 1. Check DLL Exists
```bash
dir "c:\Projects\Agent Arena\bin\windows\libagent_arena.windows.template_debug.x86_64.dll"
```
Should show a file ~3.5 MB in size with recent timestamp.

### 2. Check Extension Configuration
File `agent_arena.gdextension` should contain:
```ini
[configuration]
entry_symbol = "agent_arena_library_init"
compatibility_minimum = "4.5"

[libraries]
windows.debug.x86_64 = "res://bin/windows/libagent_arena.windows.template_debug.x86_64.dll"
```

### 3. Run Test Script
Open `scenes/test_extension.gd` and run it (F6). You should see:
```
=== Testing GDExtension Classes ===
  ✓ SimulationManager - OK
  ✓ EventBus - OK
  ✓ Agent - OK
  ✓ ToolRegistry - OK
  ✓ IPCClient - OK
=== Test Complete ===
All classes loaded successfully!
```

### 4. Check Godot Console on Startup
When Godot starts, it should print:
```
IPCClient initialized with server URL: http://127.0.0.1:5000
```
(This appears when you create an IPCClient node)

## Common Issues

### "Still getting IPCClient not found after restart"
- Make sure you deleted the entire `.godot` folder
- Make sure Godot was completely closed (check Task Manager)
- Try rebuilding the extension with `--clean-first`

### "Other classes work but IPCClient doesn't"
- Check that `godot/src/register_types.cpp` includes:
  ```cpp
  ClassDB::register_class<IPCClient>();
  ```
- Rebuild the extension

### "DLL file is locked / can't delete"
- Close Godot first
- If still locked, restart Windows (Godot may have crashed)

### "Extension loads but crashes"
- Check Windows Event Viewer for C++ errors
- Try Debug build instead of Release build
- Check that all includes are correct in `agent_arena.h`

## Still Not Working?

1. Check the build output for any errors (warnings are OK)
2. Verify the file `godot/src/agent_arena.cpp` contains the IPCClient implementation
3. Verify `godot/include/agent_arena.h` contains the IPCClient class definition
4. Try creating a minimal test:
   ```gdscript
   extends Node
   func _ready():
       var client = IPCClient.new()
       print("IPCClient created: ", client)
       client.free()
   ```

## Quick Checklist

- [ ] Godot is completely closed
- [ ] `.godot` folder deleted
- [ ] DLL exists and is recent (check timestamp)
- [ ] Extension built successfully (no errors)
- [ ] `IPCClient` registered in `register_types.cpp`
- [ ] Godot restarted
- [ ] Test script runs successfully
