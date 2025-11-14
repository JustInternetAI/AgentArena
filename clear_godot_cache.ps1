# Clear Godot cache to fix class registration issues
Write-Host "Clearing Godot cache..." -ForegroundColor Cyan

$cachePath = "c:\Projects\Agent Arena\.godot"

if (Test-Path $cachePath) {
    Write-Host "Found .godot cache directory" -ForegroundColor Yellow

    # Remove the entire .godot directory
    Remove-Item "$cachePath\*" -Recurse -Force -Exclude ".gdignore"

    Write-Host "Cache cleared!" -ForegroundColor Green
    Write-Host "Restart Godot to regenerate the cache." -ForegroundColor Cyan
} else {
    Write-Host "No cache directory found at $cachePath" -ForegroundColor Yellow
}
