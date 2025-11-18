# Copy the newly built DLL to the correct location for Godot
Write-Host "Copying newly built DLL to correct location..." -ForegroundColor Cyan

$sourceDll = "c:\Projects\Agent Arena\bin\windows\Debug\libagent_arena.windows.template_release.x86_64.dll"
$targetDll = "c:\Projects\Agent Arena\bin\windows\libagent_arena.windows.template_debug.x86_64.dll"

# Check if source exists
if (Test-Path $sourceDll) {
    Write-Host "Found newly built DLL in Debug folder" -ForegroundColor Green
    Write-Host "Source: $sourceDll" -ForegroundColor Gray

    # Show file info
    $fileInfo = Get-Item $sourceDll
    Write-Host "Build time: $($fileInfo.LastWriteTime)" -ForegroundColor Gray
    Write-Host "Size: $([math]::Round($fileInfo.Length / 1MB, 2)) MB" -ForegroundColor Gray

    # Copy to target location
    Write-Host "`nCopying to: $targetDll" -ForegroundColor Yellow
    Copy-Item $sourceDll $targetDll -Force

    Write-Host "`nDone! DLL has been copied." -ForegroundColor Green
    Write-Host "You can now restart Godot and test the scene." -ForegroundColor Cyan
} else {
    Write-Host "Error: Source DLL not found at $sourceDll" -ForegroundColor Red
}
