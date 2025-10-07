# Reset Audit Trail Script
# This script cleanly resets the audit trail for fresh testing

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "RegDelta Audit Trail Reset" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Stop any running Streamlit processes
Write-Host "`nStopping Streamlit processes..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.ProcessName -eq "streamlit"} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Delete old audit file
Write-Host "Deleting old audit trail..." -ForegroundColor Yellow
$auditFile = "audit\audit.jsonl"
if (Test-Path $auditFile) {
    Remove-Item $auditFile -Force
    Write-Host "  ✓ Deleted old audit file" -ForegroundColor Green
} else {
    Write-Host "  ℹ No audit file found" -ForegroundColor Gray
}

# Delete cached data
Write-Host "Clearing cached data..." -ForegroundColor Yellow
$dataFiles = Get-ChildItem "data\*.json" -ErrorAction SilentlyContinue
foreach ($file in $dataFiles) {
    Remove-Item $file.FullName -Force
    Write-Host "  ✓ Deleted $($file.Name)" -ForegroundColor Green
}

# Create fresh empty audit file
Write-Host "Creating fresh audit file..." -ForegroundColor Yellow
New-Item -ItemType File -Path $auditFile -Force | Out-Null
Write-Host "  ✓ Created new audit file" -ForegroundColor Green

Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
Write-Host "Reset Complete!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "1. Run: streamlit run ui/app.py" -ForegroundColor White
Write-Host "2. In the app, click 'Run Diff • Extract • Map'" -ForegroundColor White
Write-Host "3. Go to Exports tab and click 'Verify Audit Chain'" -ForegroundColor White
Write-Host "4. Should show: ✓ Audit chain verified" -ForegroundColor White

Write-Host "`nPress any key to start Streamlit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Start Streamlit
Write-Host "`nStarting Streamlit..." -ForegroundColor Yellow
streamlit run ui/app.py
