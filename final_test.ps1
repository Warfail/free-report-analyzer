Write-Host "🎯 FINAL SYSTEM TEST" -ForegroundColor Cyan
Write-Host "=================================================="

# 1. Test backend
Write-Host "`n1. Testing Backend API..." -ForegroundColor Yellow
try {
    $home = curl.exe -s http://localhost:8000
    $homeJson = $home | ConvertFrom-Json
    Write-Host "   ✅ Backend: $($homeJson.message)" -ForegroundColor Green
    
    $stats = curl.exe -s http://localhost:8000/api/stats
    $statsJson = $stats | ConvertFrom-Json
    Write-Host "   📊 Total Reports: $($statsJson.total_reports)" -ForegroundColor White
    Write-Host "   🏢 Departments: $($statsJson.total_departments)" -ForegroundColor White
    Write-Host "   📅 Today's Reports: $($statsJson.today_reports)" -ForegroundColor White
} catch {
    Write-Host "   ❌ Backend test failed" -ForegroundColor Red
}

# 2. Create test CSV file
Write-Host "`n2. Creating test file..." -ForegroundColor Yellow
$testContent = "Department,Date,Task,Status,Notes`r`n"
$testContent += "IT,2024-01-15,Server maintenance,Completed,All systems up`r`n"
$testContent += "HR,2024-01-15,Employee onboarding,In Progress,3 new hires`r`n"
$testContent += "Finance,2024-01-15,Budget review,Completed,Q1 planning done"

Set-Content -Path "system_test.csv" -Value $testContent -Encoding UTF8
Write-Host "   ✅ Created system_test.csv" -ForegroundColor Green

# 3. Upload test file
Write-Host "`n3. Testing File Upload..." -ForegroundColor Yellow
try {
    $uploadResult = curl.exe -s -X POST -F "department=IT" -F "date=2024-01-15" -F "file=@system_test.csv" http://localhost:8000/api/upload
    $uploadJson = $uploadResult | ConvertFrom-Json
    
    if ($uploadJson.success -eq $true) {
        Write-Host "   ✅ File uploaded successfully!" -ForegroundColor Green
        Write-Host "   📁 File: $($uploadJson.filename)" -ForegroundColor White
        Write-Host "   📝 Type: $($uploadJson.file_type)" -ForegroundColor White
        Write-Host "   🔢 Words: $($uploadJson.word_count)" -ForegroundColor White
    } else {
        Write-Host "   ❌ Upload failed: $($uploadJson.error)" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ Upload test failed: $_" -ForegroundColor Red
}

# Clean up
if (Test-Path "system_test.csv") {
    Remove-Item "system_test.csv"
    Write-Host "`n   🗑️  Cleaned up test file" -ForegroundColor Gray
}

# 4. Verify database
Write-Host "`n4. Verifying Database..." -ForegroundColor Yellow
try {
    $reports = curl.exe -s http://localhost:8000/api/reports
    $reportsJson = $reports | ConvertFrom-Json
    
    if ($reportsJson.count -gt 0) {
        Write-Host "   ✅ Database contains $($reportsJson.count) reports" -ForegroundColor Green
        
        $latest = $reportsJson.reports[0]
        Write-Host "   📋 Latest report:" -ForegroundColor White
        Write-Host "      Department: $($latest.department)" -ForegroundColor Gray
        Write-Host "      Date: $($latest.report_date)" -ForegroundColor Gray
        Write-Host "      File Type: $($latest.file_type)" -ForegroundColor Gray
        Write-Host "      Words: $($latest.word_count)" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠️  Database is empty (upload might have failed)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Database verification failed: $_" -ForegroundColor Red
}

# 5. Instructions
Write-Host "`n5. Frontend Instructions:" -ForegroundColor Yellow
Write-Host "   🌐 Open: frontend/index.html in your browser" -ForegroundColor White
Write-Host "   📤 Try uploading a report" -ForegroundColor White
Write-Host "   🔍 Filter by department" -ForegroundColor White
Write-Host "   📥 Export reports to CSV" -ForegroundColor White

Write-Host "`n=================================================="
Write-Host "🎉 SYSTEM READY FOR USE!" -ForegroundColor Green
Write-Host "=================================================="