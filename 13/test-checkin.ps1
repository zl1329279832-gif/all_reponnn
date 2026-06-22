$ErrorActionPreference = "Stop"
$base = "http://localhost:8080/api"

function Write-Color($msg, $color) { Write-Host $msg -ForegroundColor $color }
function Test-Rest($method, $url, $body) {
    try {
        $headers = @{"Content-Type" = "application/json"}
        if ($body) {
            $resp = Invoke-RestMethod -Method $method -Uri $url -Headers $headers -Body ($body | ConvertTo-Json -Depth 10)
            return @{ ok=$true; code=200; data=$resp }
        } else {
            $resp = Invoke-RestMethod -Method $method -Uri $url
            return @{ ok=$true; code=200; data=$resp }
        }
    } catch {
        $code = 500
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode.value__ }
        $msg = ""
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $msg = $reader.ReadToEnd()
        } catch {}
        return @{ ok=$false; code=$code; message=$msg }
    }
}

Write-Color "===== CHECKIN / RELEASE TEST =====" Cyan

Write-Color "1. Meeting room list" Yellow
$r = Test-Rest GET "$base/meeting-rooms"
if ($r.ok -and $r.code -eq 200) {
    $rooms = $r.data.data
    Write-Color "[PASS] Got $($rooms.Count) rooms, pick id=$($rooms[0].id) name=$($rooms[0].name)" Green
    $roomId = $rooms[0].id
} else {
    Write-Color "[FAIL] HTTP $($r.code): $($r.message)" Red; exit 1
}

Write-Color "2. Compute start time (now + 2 minutes, small window for quick observation)" Yellow
$start = (Get-Date).AddMinutes(2).ToString("yyyy-MM-dd HH:mm:00")
$end   = (Get-Date).AddMinutes(62).ToString("yyyy-MM-dd HH:mm:00")
Write-Color "   start=$start, end=$end" Gray

Write-Color "3. Create single reservation" Yellow
$body = @{
    roomId=$roomId
    employeeId="EMP001"
    employeeName="Zhang San"
    title="Checkin and release test"
    startTime=$start
    endTime=$end
}
$r = Test-Rest POST "$base/reservations" $body
if ($r.ok) {
    $res = $r.data.data[0]
    Write-Color "[PASS] Reservation id=$($res.id) status=$($res.status) checkedIn=$($res.checkedIn) released=$($res.released)" Green
    $resId = $res.id
} else {
    Write-Color "[FAIL] HTTP $($r.code): $($r.message)" Red; exit 1
}

Write-Color "4. Reservation detail has status/checkedIn/released fields" Yellow
$r = Test-Rest GET "$base/reservations/$resId"
if ($r.ok) {
    $d = $r.data.data
    if ($null -ne $d.status -and $null -ne $d.checkedIn -and $null -ne $d.released) {
        Write-Color "[PASS] status=$($d.status) checkedIn=$($d.checkedIn) released=$($d.released) checkInTime=$($d.checkInTime)" Green
    } else {
        Write-Color "[FAIL] Missing fields: $($r.data.data | ConvertTo-Json)" Red; exit 1
    }
} else {
    Write-Color "[FAIL] HTTP $($r.code): $($r.message)" Red; exit 1
}

Write-Color "5. Check in too early - should fail (window not open)" Yellow
$r = Test-Rest POST "$base/reservations/$resId/check-in" @{operator="Li Si"}
if (-not $r.ok -and ($r.code -eq 400 -or $r.code -eq 409)) {
    $trunc = if ($r.message.Length -gt 250) { $r.message.Substring(0,250) } else { $r.message }
    Write-Color "[PASS] Early check-in rejected HTTP $($r.code): $trunc" Green
} else {
    Write-Color "[FAIL] Expected 400/409, got HTTP $($r.code): $($r.message)" Red
}

Write-Color "6. Audit list (empty so far, no check-in or cancel happened)" Yellow
$r = Test-Rest GET "$base/reservations/$resId/audits"
if ($r.ok) {
    Write-Color "[PASS] Audit record count=$($r.data.data.Count)" Green
} else {
    Write-Color "[FAIL] HTTP $($r.code): $($r.message)" Red
}

Write-Host ""
Write-Color "===== BASIC FUNCTIONALITY VERIFIED =====" Cyan
Write-Color "Next: scheduler runs every 60s. Wait ~17 minutes from now and GET $base/reservations/$resId" Cyan
Write-Color "Expected: status becomes RELEASED, released=true, and there is a RELEASE_TIMEOUT audit" Cyan
Write-Color "After released: POST the same slot should succeed (conflict detection excludes RELEASED)" Cyan
Write-Host "Reservation ID for follow-up: $resId"
Write-Host "Start time: $start"
