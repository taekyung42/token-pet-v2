$dir = $PSScriptRoot
$exe = Join-Path $dir 'token-pet-v2.exe'
if (-not (Test-Path $exe)) {
    Write-Host ''
    Write-Host '[오류] token-pet-v2.exe 를 찾을 수 없습니다.' -ForegroundColor Red
    Write-Host '이 파일들을 token-pet-v2.exe 와 같은 폴더에 두고 실행하세요.'
    return
}
$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'token-pet-v2.lnk'
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath = $exe
$s.WorkingDirectory = $dir
$s.Save()
Write-Host ''
Write-Host '[완료] 자동 시작 등록 성공!' -ForegroundColor Green
Write-Host '이제 컴퓨터를 켤 때마다 토큰 팻이 자동으로 실행됩니다.'
if (-not (Get-Process -Name 'token-pet-v2' -ErrorAction SilentlyContinue)) {
    Start-Process $exe -WorkingDirectory $dir
    Write-Host '토큰 팻을 지금 실행했습니다.'
} else {
    Write-Host '토큰 팻이 이미 실행 중입니다.'
}
