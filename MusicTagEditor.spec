# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('app.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# 关键：过滤掉 Anaconda 误判收集的 Windows 系统/外部冲突库
# 1. icuuc*.dll, icudt*.dll: 杜绝与 PySide6/Qt6 依赖的系统原生 C:\Windows\System32\icuuc.dll 符号冲突 (Win32 Error 127)
# 2. api-ms-win-*.dll, ucrtbase.dll: 杜绝因 Anaconda 旧版 UCRT 导致 Windows 10/11 动态库初始化崩溃 (Win32 Error 0xC0000142)
def should_exclude_binary(name):
    lower = name.lower()
    if lower.startswith(('icuuc', 'icudt', 'icuin')):
        return True
    if lower.startswith(('api-ms-win-', 'ucrtbase')):
        return True
    return False

a.binaries = [x for x in a.binaries if not should_exclude_binary(x[0])]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MusicTagEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MusicTagEditor',
)
