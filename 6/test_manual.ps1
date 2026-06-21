$base = "http://localhost:8080/api"

function Test-Endpoint {
    param($name, $method, $path, $body)
    Write-Host ""
    Write-Host "=== $name ==="
    try {
        $params = @{ Uri = "$base/$path"; Method = $method; UseBasicParsing = $true }
        if ($body) {
            $params.Body = ($body | ConvertTo-Json)
            $params.ContentType = "application/json"
        }
        $resp = Invoke-WebRequest @params
        Write-Host "  Status: $($resp.StatusCode)"
        $data = $resp.Content | ConvertFrom-Json
        Write-Host "  code: $($data.code), message: $($data.message)"
        return $data
    } catch {
        $status = $_.Exception.Response.StatusCode.value__
        Write-Host "  Status: $status"
        try {
            $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $respBody = $sr.ReadToEnd()
            $data = $respBody | ConvertFrom-Json
            Write-Host "  code: $($data.code), message: $($data.message)"
            return $data
        } catch {
            Write-Host "  Body parse failed"
            return $null
        }
    }
}

# 1. Create match
$r1 = Test-Endpoint "1. Create match alice vs bob" "Post" "matches" @{redPlayerId="alice"; blackPlayerId="bob"}
$matchId = $r1.data.id
Write-Host "  matchId = $matchId"

# 2. Valid move - red cannon ping wu (from row 7)
$r2 = Test-Endpoint "2. Valid move red cannon (7,1)->(7,4)" "Post" "matches/$matchId/moves" @{
    playerId = "alice"; fromRow = 7; fromCol = 1; toRow = 7; toCol = 4
}
Write-Host "  move# = $($r2.data.moveNumber), piece = $($r2.data.pieceType)"

# 3. Invalid move - cannon without screen (cannon tries to capture directly)
$r3 = Test-Endpoint "3. Invalid cannon no screen (7,4)->(2,4)" "Post" "matches/$matchId/moves" @{
    playerId = "alice"; fromRow = 7; fromCol = 4; toRow = 2; toCol = 4
}

# 4. Not your turn - red moves again
$r4 = Test-Endpoint "4. Not your turn - red moves again" "Post" "matches/$matchId/moves" @{
    playerId = "alice"; fromRow = 6; fromCol = 0; toRow = 5; toCol = 0
}

# 5. Black valid move - soldier forward
$r5 = Test-Endpoint "5. Black valid move soldier (3,0)->(4,0)" "Post" "matches/$matchId/moves" @{
    playerId = "bob"; fromRow = 3; fromCol = 0; toRow = 4; toCol = 0
}
Write-Host "  move# = $($r5.data.moveNumber)"

# 6. GET snapshot
$r6 = Test-Endpoint "6. GET match snapshot" "Get" "matches/$matchId/snapshot"
Write-Host "  status: $($r6.data.status), turn: $($r6.data.nextTurnPlayerId)"
Write-Host "  FEN: $($r6.data.fen)"

# 7. GET move history
$r7 = Test-Endpoint "7. GET move history" "Get" "matches/$matchId/moves"
Write-Host "  total moves: $($r7.data.Count)"
foreach ($m in $r7.data) {
    Write-Host "    #$($m.moveNumber) $($m.playerId) $($m.pieceType) ($($m.fromRow),$($m.fromCol))->($($m.toRow),$($m.toCol))"
}

# 8. GET player info
$r8 = Test-Endpoint "8. GET player alice" "Get" "players/alice"
Write-Host "  Elo: $($r8.data.eloRating), W:$($r8.data.wins) L:$($r8.data.losses)"

# 9. GET leaderboard
$r9 = Test-Endpoint "9. GET leaderboard" "Get" "players/leaderboard?page=0&size=10"
Write-Host "  total players: $($r9.data.totalElements)"

# 10. Horse blocked leg test
$r10a = Test-Endpoint "10a. Create match for horse-blocked test" "Post" "matches" @{redPlayerId="p1"; blackPlayerId="p2"}
$mid2 = $r10a.data.id
# Step 1: red moves cannon from (7,1) to (8,1) to block horse leg
$r10b = Test-Endpoint "10b. Red cannon moves to (8,1) to block" "Post" "matches/$mid2/moves" @{
    playerId = "p1"; fromRow = 7; fromCol = 1; toRow = 8; toCol = 1
}
# Step 2: black moves a soldier
$r10c = Test-Endpoint "10c. Black soldier moves (3,0)->(4,0)" "Post" "matches/$mid2/moves" @{
    playerId = "p2"; fromRow = 3; fromCol = 0; toRow = 4; toCol = 0
}
# Step 3: red tries horse (9,1)->(7,2) but blocked by cannon at (8,1)
$r10d = Test-Endpoint "10d. Horse blocked leg - should be rejected" "Post" "matches/$mid2/moves" @{
    playerId = "p1"; fromRow = 9; fromCol = 1; toRow = 7; toCol = 2
}

# 11. Verify the error message is readable (decode UTF-8)
Write-Host ""
Write-Host "=== Error message verification ==="
$errMsg = $r10d.message
Write-Host "  Raw message: $errMsg"
Write-Host "  Is non-empty: $($errMsg -ne $null -and $errMsg -ne '')"

Write-Host ""
Write-Host "=== All tests done ==="
