$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'token-pet-v2.lnk'
if (Test-Path $lnk) {
    Remove-Item $lnk -Force
    Write-Host ''
    Write-Host '[완료] 자동 시작을 해제했습니다.' -ForegroundColor Green
} else {
    Write-Host ''
    Write-Host '자동 시작이 등록되어 있지 않습니다.' -ForegroundColor Yellow
}
$p = Get-Process -Name 'token-pet-v2' -ErrorAction SilentlyContinue
if ($p) {
    $p | Stop-Process -Force
    Write-Host '실행 중이던 토큰 팻을 종료했습니다.'
}
