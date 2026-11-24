# ============================================================
# MusicTagEditor 自动化构建、打包与自签名流水线脚本
# ============================================================
Set-Location -LiteralPath $PSScriptRoot

try {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   MusicTagEditor 自动化构建打包流水线" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    # 1. 检测 PyInstaller 执行路径
    $PyInstallerPath = "pyinstaller"
    $CondaRoot = "C:\Tools\Anaconda3\envs\TTS"
    $CondaLibBin = "$CondaRoot\Library\bin"
    $CondaPyInstaller = "$CondaRoot\Scripts\pyinstaller.exe"

    if (-not (Get-Command "pyinstaller" -ErrorAction SilentlyContinue)) {
        if (Test-Path $CondaPyInstaller) {
            $PyInstallerPath = $CondaPyInstaller
            Write-Host ">>> 使用 Conda(TTS) 环境打包工具: $PyInstallerPath" -ForegroundColor DarkGray
        } else {
            throw "未找到 pyinstaller 工具，请确认 Conda TTS 环境已安装 pyinstaller！"
        }
    }

    Write-Host ">>> [1/5] 清理旧编译产物与缓存..." -ForegroundColor Cyan
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

    Write-Host ">>> [2/5] 检查多分辨率图标与打包规范..." -ForegroundColor Cyan
    if (-not (Test-Path "app.ico")) {
        throw "缺少 app.ico 图标文件！"
    }
    if (-not (Test-Path "MusicTagEditor.spec")) {
        throw "缺少 MusicTagEditor.spec 规范文件！"
    }

    Write-Host ">>> [3/5] 执行 PyInstaller 工业级单目录打包..." -ForegroundColor Cyan
    & $PyInstallerPath MusicTagEditor.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller 打包失败，退出代码: $LASTEXITCODE"
    }

    Write-Host ">>> [4/5] 补齐 Conda 核心运行时库与便携资源..." -ForegroundColor Cyan
    Copy-Item "app.ico" "dist\MusicTagEditor\app.ico" -Force
    if (Test-Path "MusicTagEditor.cer") {
        Copy-Item "MusicTagEditor.cer" "dist\MusicTagEditor\MusicTagEditor.cer" -Force
    }
    if (Test-Path "install_cert.bat") {
        Copy-Item "install_cert.bat" "dist\MusicTagEditor\install_cert.bat" -Force
    }

    # 1. 补齐 _ctypes 所需的 ffi.dll 及基础压缩模块所需 C-DLL
    $CondaLibDlls = @("ffi.dll", "libexpat.dll", "liblzma.dll", "libbz2.dll")
    foreach ($dll in $CondaLibDlls) {
        $dllPath = Join-Path $CondaLibBin $dll
        if (Test-Path $dllPath) {
            Copy-Item $dllPath "dist\MusicTagEditor\_internal\" -Force
        }
    }

    # 2. 补齐与 PySide6 严格同源的完整 Visual C++ 运行时套件到 _internal 根目录（杜绝 Error 127 导出符号不匹配）
    $PySide6Dir = "$CondaRoot\Lib\site-packages\PySide6"
    $PySide6VCDlls = @(
        "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll",
        "msvcp140_codecvt_ids.dll", "vcruntime140.dll", "vcruntime140_1.dll"
    )
    foreach ($dll in $PySide6VCDlls) {
        $srcPath = Join-Path $PySide6Dir $dll
        if (Test-Path $srcPath) {
            Copy-Item $srcPath "dist\MusicTagEditor\_internal\$dll" -Force
        }
    }

    # 3. 将 shiboken6.abi3.dll 提取到 _internal 及 PySide6 目录，保证动态链接直接可达
    $ShibokenDll = "$CondaRoot\Lib\site-packages\shiboken6\shiboken6.abi3.dll"
    if (Test-Path $ShibokenDll) {
        Copy-Item $ShibokenDll "dist\MusicTagEditor\_internal\shiboken6.abi3.dll" -Force
        Copy-Item $ShibokenDll "dist\MusicTagEditor\_internal\PySide6\shiboken6.abi3.dll" -Force
    }

    # 4. 二次兜底清理：移除任何误打包的冲突 DLL (icu*.dll, ucrtbase.dll, api-ms-win*.dll)
    Remove-Item "dist\MusicTagEditor\_internal\icu*.dll" -Force -ErrorAction SilentlyContinue
    Remove-Item "dist\MusicTagEditor\_internal\ucrtbase.dll" -Force -ErrorAction SilentlyContinue
    Remove-Item "dist\MusicTagEditor\_internal\api-ms-win*.dll" -Force -ErrorAction SilentlyContinue

    # 5. 解除 Windows 对构建产物可能附加的 Zone.Identifier 锁定
    Get-ChildItem "dist\MusicTagEditor" -Recurse | Unblock-File -ErrorAction SilentlyContinue
    Unblock-File "dist\MusicTagEditor\MusicTagEditor.exe" -ErrorAction SilentlyContinue

    Write-Host ">>> [5/5] 执行 Authenticode 自签名..." -ForegroundColor Cyan
    $cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Where-Object { $_.Subject -like "*MusicTagEditor*" } | Select-Object -First 1
    if ($cert) {
        $sig = Set-AuthenticodeSignature -FilePath "dist\MusicTagEditor\MusicTagEditor.exe" -Certificate $cert
        Write-Host ">>> 签名执行成功！状态: $($sig.Status)" -ForegroundColor Green
    } else {
        Write-Warning "未找到代码签名证书，可先运行 install_cert.bat 生成证书。"
    }

    # 签名完成后二次确保所有文件解除安全锁定
    Get-ChildItem "dist\MusicTagEditor" -Recurse | Unblock-File -ErrorAction SilentlyContinue

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host " [成功] 打包构建顺利完成！" -ForegroundColor Green
    Write-Host " 软件输出目录: dist\MusicTagEditor\" -ForegroundColor Green
    Write-Host " 主程序路径:   dist\MusicTagEditor\MusicTagEditor.exe" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host " [失败] 构建过程发生异常: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""
    exit 1
}
