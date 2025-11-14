# Force a clean rebuild of the GDExtension
Write-Host "Forcing clean rebuild..." -ForegroundColor Cyan

Set-Location "c:\Projects\Agent Arena\godot\build"

# Rebuild Debug
Write-Host "Building Debug configuration..." -ForegroundColor Yellow
cmake --build . --config Debug --clean-first

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDebug build successful!" -ForegroundColor Green

    $debugDll = "c:\Projects\Agent Arena\bin\windows\libagent_arena.windows.template_debug.x86_64.dll"
    if (Test-Path $debugDll) {
        $fileInfo = Get-Item $debugDll
        Write-Host "Debug DLL timestamp: $($fileInfo.LastWriteTime)" -ForegroundColor Gray
    }
} else {
    Write-Host "`nDebug build failed!" -ForegroundColor Red
    exit 1
}

# Rebuild Release
Write-Host "`nBuilding Release configuration..." -ForegroundColor Yellow
cmake --build . --config Release

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nRelease build successful!" -ForegroundColor Green

    $releaseDll = "c:\Projects\Agent Arena\bin\windows\libagent_arena.windows.template_release.x86_64.dll"
    if (Test-Path $releaseDll) {
        $fileInfo = Get-Item $releaseDll
        Write-Host "Release DLL timestamp: $($fileInfo.LastWriteTime)" -ForegroundColor Gray
    }

    Write-Host "`nAll builds completed successfully!" -ForegroundColor Green
} else {
    Write-Host "`nRelease build failed!" -ForegroundColor Red
    exit 1
}
