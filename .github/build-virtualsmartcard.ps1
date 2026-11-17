$PSNativeCommandUseErrorActionPreference = $true
$ErrorActionPreference = "Stop"
Set-PSDebug -Trace 1

$TestCertFile = Join-Path (Get-Location) "BixVReader.cer"
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN=UMDF Test Certificate' -KeyExportPolicy Exportable -CertStoreLocation Cert:\CurrentUser\My
Export-Certificate -Cert $cert -FilePath "$TestCertFile"

$VS_PATH = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -property installationPath
& "$VS_PATH\Common7\Tools\Launch-VsDevShell.ps1"
Enter-VsDevShell -VsInstallPath "$VS_PATH" -Arch $env:VCVARS_PLATFORM -HostArch $env:PROCESSOR_ARCHITECTURE -SkipAutomaticLocation

& cl.exe /MT /Ivirtualsmartcard\src\vpcd virtualsmartcard\src\vpcd-config\vpcd-config.c virtualsmartcard\src\vpcd-config\local-ip.c ws2_32.lib

& msbuild "virtualsmartcard\win32\BixVReader.sln" "/p:Configuration=Release;Platform=$env:MSBUILD_PLATFORM;TestCertFile=$TestCertFile"

# BixVReaderInstaller.sln (包含 MSI + 驱动 INF 打包) — 原 CI 漏了这步
& msbuild "virtualsmartcard\win32\BixVReaderInstaller\BixVReaderInstaller.sln" "/p:Configuration=Release;Platform=$env:MSBUILD_PLATFORM;TestCertFile=$TestCertFile"

# 把原始驱动文件（dll/inf/cat/cms）显式 move 到工作目录
# 它们在 BixVReader 工程的 bin/<Config>/<Platform>/ 下
$BixBinDir = "virtualsmartcard\win32\BixVReader\bin\Release\$env:MSBUILD_PLATFORM"
Write-Host "[build] looking for driver artifacts under: $BixBinDir"
if (Test-Path $BixBinDir) {
    Get-ChildItem -Path $BixBinDir -Recurse -File | ForEach-Object {
        Write-Host "  found: $($_.FullName)"
        Move-Item -Force $_.FullName "."
    }
} else {
    Write-Host "[build] WARNING: BixVReader bin dir not found: $BixBinDir"
    # fallback: 尝试 Release / Debug 两个配置
    foreach ($cfg in @("Release", "Debug")) {
        $alt = "virtualsmartcard\win32\BixVReader\bin\$cfg\$env:MSBUILD_PLATFORM"
        if (Test-Path $alt) {
            Write-Host "[build] using fallback: $alt"
            Get-ChildItem -Path $alt -Recurse -File | ForEach-Object {
                Move-Item -Force $_.FullName "."
            }
            break
        }
    }
}

& python --version
& python -m pip install -q --upgrade pip
& python -m pip install -q virtualenv
& python -m pip install -q -U setuptools
& python -m pip install -q pycryptodomex
& python -m pip install -q pbkdf2
& python -m pip install -q Pillow
& python -m pip install -q pyreadline3
& python -m pip install -q pyscard
& python -m pip install -q pyinstaller

& python -m PyInstaller --onefile virtualsmartcard\src\vpicc\vicc.in -i doc\_static\chip.ico
