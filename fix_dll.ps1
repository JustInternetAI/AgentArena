# Script to replace the old DLL with the newly built one
Write-Host "Fixing DLL issue..." -ForegroundColor Cyan

$binPath = "c:\Projects\Agent Arena\bin\windows"
$oldDll = "$binPath\libagent_arena.windows.template_debug.x86_64.dll"
$newDll = "$binPath\~libagent_arena.windows.template_debug.x86_64.dll"

# Check if new DLL exists
if (Test-Path $newDll) {
    Write-Host "Found newly built DLL (with ~ prefix)" -ForegroundColor Green

    # Remove old DLL if it exists
    if (Test-Path $oldDll) {
        Write-Host "Removing old DLL..." -ForegroundColor Yellow
        Remove-Item $oldDll -Force
    }

    # Rename new DLL to correct name
    Write-Host "Renaming new DLL to correct name..." -ForegroundColor Yellow
    Move-Item $newDll $oldDll -Force

    Write-Host "Done! DLL has been updated." -ForegroundColor Green
    Write-Host "You can now restart Godot and test." -ForegroundColor Cyan
} else {
    Write-Host "Error: New DLL not found at $newDll" -ForegroundColor Red
}
