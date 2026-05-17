# Chay 1 lan neu .bat bi loi 'cho', '║' is not recognized (file LF thay vi CRLF):
#   powershell -ExecutionPolicy Bypass -File fix_bat_crlf.ps1
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
Get-ChildItem -Path $dir -Filter '*.bat' | ForEach-Object {
    $raw = [System.IO.File]::ReadAllText($_.FullName)
    $raw = $raw -replace "`r`n", "`n" -replace "`r", "`n"
    $raw = $raw -replace "`n", "`r`n"
    [System.IO.File]::WriteAllText($_.FullName, $raw, [System.Text.UTF8Encoding]::new($false))
    Write-Host "OK: $($_.Name)"
}
Write-Host "Done. Chay lai 1_setup_install.bat"
