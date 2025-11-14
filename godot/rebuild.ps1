# Quick rebuild script for Agent Arena GDExtension
Set-Location -Path "c:\Projects\Agent Arena\godot\build"

Write-Host "Building Agent Arena GDExtension..." -ForegroundColor Cyan

# Try using cmake
cmake --build . --config Debug

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful!" -ForegroundColor Green
    Write-Host "DLL location: c:\Projects\Agent Arena\bin\windows\" -ForegroundColor Yellow
} else {
    Write-Host "Build failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
