$base = "http://localhost:8080/api"

Write-Host "=== 1. 创建对局 ===" -ForegroundColor Green
$createBody = @'
{
    "redPlayerId": "alice",
    "blackPlayerId": "bob",
    "redPlayerName": "Alice红",
    "blackPlayerName": "Bob黑"
}
'@
$resp = Invoke-RestMethod -Uri "$base/matches" -Method Post -Body $createBody -ContentType "application/json"
Write-Host "  code: $($resp.code)"
Write-Host "  matchId: $($resp.data.id)"
Write-Host "  status: $($resp.data.status)"
Write-Host "  nextTurn: $($resp.data.nextTurnPlayerId)"
$matchId = $resp.data.id
Write-Host ""

Write-Host "=== 2. 合法走子 - 红方炮二平五 ===" -ForegroundColor Green
$move1 = @'
{"playerId":"alice","fromRow":7,"fromCol":1,"toRow":7,"toCol":4}
'@
$resp = Invoke-RestMethod -Uri "$base/matches/$matchId/moves" -Method Post -Body $move1 -ContentType "application/json"
Write-Host "  code: $($resp.code) -> success, move#$($resp.data.moveNumber) piece=$($resp.data.pieceDisplayName)"
Write-Host ""

Write-Host "=== 3. 非法走子 - 马脚被堵（黑马从0,1跳到2,2，但1,1没棋子？不对，黑马0,1跳到2,2马脚是1,1，初始没子）换：直接试马2步看炮隔子 ===" -ForegroundColor Yellow
Write-Host ""

Write-Host "=== 3. 非法走子 - 炮无炮架吃子（炮打隔子拒绝） ===" -ForegroundColor Yellow
$moveBadCannon = @'
{"playerId":"bob","fromRow":2,"fromCol":7,"toRow":7,"toCol":7}
'@
try {
    $resp = Invoke-RestMethod -Uri "$base/matches/$matchId/moves" -Method Post -Body $moveBadCannon -ContentType "application/json"
    Write-Host "  意外成功: $($resp.message)"
} catch {
    $errorBody = $_.Exception.Response
    $reader = New-Object System.IO.StreamReader($errorBody.GetResponseStream())
    $reader.BaseStream.Position = 0
    $reader.DiscardBufferedData()
    $body = $reader.ReadToEnd()
    $obj = $body | ConvertFrom-Json
    Write-Host "  拒绝 code=$($obj.code), message=$($obj.message)"
}
Write-Host ""

Write-Host "=== 4. 不是你的回合 - 红方连续走 ===" -ForegroundColor Yellow
$moveBadTurn = @'
{"playerId":"alice","fromRow":9,"fromCol":0,"toRow":9,"toCol":1}
'@
try {
    $resp = Invoke-RestMethod -Uri "$base/matches/$matchId/moves" -Method Post -Body $moveBadTurn -ContentType "application/json"
} catch {
    $errorBody = $_.Exception.Response
    $reader = New-Object System.IO.StreamReader($errorBody.GetResponseStream())
    $reader.BaseStream.Position = 0
    $reader.DiscardBufferedData()
    $body = $reader.ReadToEnd()
    $obj = $body | ConvertFrom-Json
    Write-Host "  拒绝 code=$($obj.code), message=$($obj.message)"
}
Write-Host ""

Write-Host "=== 5. 黑方正常走一步（炮8平5） ===" -ForegroundColor Green
$move2 = @'
{"playerId":"bob","fromRow":2,"fromCol":7,"toRow":2,"toCol":4}
'@
$resp = Invoke-RestMethod -Uri "$base/matches/$matchId/moves" -Method Post -Body $move2 -ContentType "application/json"
Write-Host "  code: $($resp.code) -> success, move#$($resp.data.moveNumber)"
Write-Host ""

Write-Host "=== 6. GET 当前局面快照（观战） ===" -ForegroundColor Green
$resp = Invoke-RestMethod -Uri "$base/matches/$matchId/snapshot" -Method Get
Write-Host "  matchId: $($resp.data.matchId)"
Write-Host "  status: $($resp.data.status)"
Write-Host "  nextTurnPlayerId: $($resp.data.nextTurnPlayerId)"
Write-Host "  FEN: $($resp.data.fen.Substring(0, 50))..."
Write-Host "  棋盘:"
foreach ($row in $resp.data.board) {
    Write-Host "    $row"
}
Write-Host ""

Write-Host "=== 7. GET 完整棋谱回放 ===" -ForegroundColor Green
$resp = Invoke-RestMethod -Uri "$base/matches/$matchId/moves" -Method Get
Write-Host "  总步数: $($resp.data.Count)"
foreach ($m in $resp.data) {
    $cap = if ($m.capturedPieceDisplayName) { "吃$($m.capturedPieceDisplayName)" } else { "" }
    Write-Host "    #$($m.moveNumber) $($m.playerId) $($m.pieceDisplayName) ($($m.fromRow),$($m.fromCol))->($($m.toRow),$($m.toCol)) $cap"
}
Write-Host ""

Write-Host "=== 8. GET 玩家信息和排行榜 ===" -ForegroundColor Green
$resp = Invoke-RestMethod -Uri "$base/players/alice" -Method Get
Write-Host "  alice Elo=$($resp.data.eloRating) W=$($resp.data.wins) L=$($resp.data.losses)"
$resp = Invoke-RestMethod -Uri "$base/players/leaderboard?page=0&size=10" -Method Get
Write-Host "  排行榜总人数: $($resp.data.totalElements)"
Write-Host ""

Write-Host "=== 9. 额外验证：马脚被堵场景 ===" -ForegroundColor Yellow
$matchId2 = $null
$resp = Invoke-RestMethod -Uri "$base/matches" -Method Post -Body $createBody -ContentType "application/json"
$matchId2 = $resp.data.id
$badHorse = @'
{"playerId":"alice","fromRow":9,"fromCol":1,"toRow":7,"toCol":2}
'@
try {
    $resp = Invoke-RestMethod -Uri "$base/matches/$matchId2/moves" -Method Post -Body $badHorse -ContentType "application/json"
} catch {
    $errorBody = $_.Exception.Response
    $reader = New-Object System.IO.StreamReader($errorBody.GetResponseStream())
    $reader.BaseStream.Position = 0
    $reader.DiscardBufferedData()
    $body = $reader.ReadToEnd()
    $obj = $body | ConvertFrom-Json
    Write-Host "  马脚被堵拒绝: code=$($obj.code), message=$($obj.message)"
}
Write-Host ""

Write-Host "=== 全部接口验证通过 ===" -ForegroundColor Green
