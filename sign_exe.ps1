# MusicTagEditor 自动签名脚本
param(
    [string]$TargetExe = "$PSScriptRoot\dist\MusicTagEditor\MusicTagEditor.exe"
)

Write-Host ">>> 正在检查代码签名证书..." -ForegroundColor Cyan

# 查找已存在的证书
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Where-Object { $_.Subject -like "*MusicTagEditor*" } | Select-Object -First 1

if (-not $cert) {
    Write-Host ">>> 未找到已有证书，正在生成新的自签名代码证书..." -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate -Type CodeSigningCert `
        -Subject "CN=MusicTagEditor" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -FriendlyName "MusicTagEditor Code Signing" `
        -NotAfter (Get-Date).AddYears(5)
    
    # 导出证书
    $cerPath = "$PSScriptRoot\MusicTagEditor.cer"
    [System.IO.File]::WriteAllBytes($cerPath, $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))
    Write-Host ">>> 已导出公钥证书至: $cerPath" -ForegroundColor Green
}

# 确保安装到 TrustedPublisher
$tpStore = New-Object System.Security.Cryptography.X509Certificates.X509Store "TrustedPublisher", "CurrentUser"
$tpStore.Open("ReadWrite")
$tpStore.Add($cert)
$tpStore.Close()

if (Test-Path $TargetExe) {
    Write-Host ">>> 正在对可执行文件执行 Authenticode 签名: $TargetExe" -ForegroundColor Cyan
    $sig = Set-AuthenticodeSignature -FilePath $TargetExe -Certificate $cert
    Write-Host ">>> 签名执行完毕，当前状态: $($sig.Status)" -ForegroundColor Green
    Write-Host ">>> 状态详细信息: $($sig.StatusMessage)" -ForegroundColor Gray
} else {
    Write-Host ">>> 未找到目标文件: $TargetExe" -ForegroundColor Red
}
