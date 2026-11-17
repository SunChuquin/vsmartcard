# vsmartcard — 项目总览

> 生成时间：2026-11-17
> 证据来源：根 README、`.github/workflows/ci.yml`、`.travis.yml`、`.gitmodules`、各子项目 `configure.ac` / `build.gradle` / `.vcxproj`

## 1. 项目定位

**vsmartcard 不是一个应用，是一个 umbrella 项目**，聚合了 6 个独立构建、独立发布的子项目，统一解决"虚拟智能卡"和"虚拟智能卡读写器"这个问题：

- 在没有真实智能卡的机器上模拟一张卡（vpcd + vpicc）
- 把真实手机 NFC 读写器暴露给远端 PC（remote-reader + pcsc-relay）
- 在 Android 手机上仿真各种智能卡 Applet（ACardEmulator）
- 把 USB CCID 卡接进系统（ccid）
- 在 Tizen 设备上仿真卡（TCardEmulator）

## 2. 子项目速查表

| 子项目 | 目录 | 语言 | 构建方式 | 核心职责 | 外部依赖 |
|---|---|---|---|---|---|
| **Virtual Smart Card (vpcd)** | `virtualsmartcard/` | C (守护进程) + Python (卡仿真) + C++/ATL (Windows UMDF) | autotools (Linux/macOS) + MSBuild + WDK (Windows) | 虚拟 PC/SC 读写器守护进程 + 虚拟 ICC 卡 | OpenPACE、PC/SC 系统库、Windows WDK |
| **PC/SC Relay** | `pcsc-relay/` | C | autotools (Linux/macOS) + MinGW (Windows) | 在两台机器/两个接口之间中继 APDU | libpcsclite、libnfc（可选） |
| **Remote Smart Card Reader** | `remote-reader/` | Java (Android) | Gradle | 把 Android NFC 读写器暴露给远端 vpcd | Android SDK、NFC API |
| **Android Smart Card Emulator** | `ACardEmulator/` | Java | Gradle | 在 Android 上仿真智能卡 Applet | jCardSim、Yubico applet、GidsApplet 等 submodule |
| **USB CCID Emulator** | `ccid/` | C | autotools + OpenSC submodule | 通过 USB gadget 暴露 CCID 接口 | OpenSC (子模块)、Linux gadgetfs、OpenSSL |
| **Tizen Card Emulator** | `TCardEmulator/` | C | Eclipse CDT + sdb | 在 Tizen 设备上仿真智能卡 | Tizen SDK |

## 3. Submodule 清单（9 个，全部已初始化 ✓）

| Submodule | 路径 | 用途 | 上游仓库 |
|---|---|---|---|
| jcardsim | `ACardEmulator/app/src/main/external/jcardsim` | Java 智能卡仿真框架 | `licel/jcardsim` |
| ykneo-openpgp | `ACardEmulator/app/src/main/external/ykneo-openpgp` | YubiKey OpenPGP Applet | `Yubico/ykneo-openpgp` |
| ykneo-oath | `ACardEmulator/app/src/main/external/ykneo-oath` | YubiKey OATH Applet | `Yubico/ykneo-oath` |
| IsoApplet | `ACardEmulator/app/src/main/external/IsoApplet` | ISO 7816 Applet | `philipWendland/IsoApplet` |
| MuscleApplet | `ACardEmulator/app/src/main/external/MuscleApplet` | Muscle Applet | `martinpaljak/MuscleApplet` |
| GidsApplet | `ACardEmulator/app/src/main/external/GidsApplet` | GIDS Applet | `vletoux/GidsApplet` |
| PivApplet | `ACardEmulator/app/src/main/external/PivApplet` | PIV Applet | `frankmorgner/PivApplet` |
| **OpenSC** | `ccid/src/OpenSC` | OpenSC 智能卡中间件（最大最重的子模块） | `OpenSC/OpenSC` |
| DevMsi | `virtualsmartcard/win32/DevMsi` | MSI 自定义动作，Windows 驱动安装 | `frankmorgner/DevMsi` |

**关键事实**：所有 submodule 在本地已初始化。OpenSC 当前版本 `0.26.1`，是整个项目最重量级的外部代码。

## 4. CI 矩阵

证据：[ci.yml](file:///c:/Users/sunck/home/projects/vsmartcard/.github/workflows/ci.yml) + [.travis.yml](file:///c:/Users/sunck/home/projects/vsmartcard/.travis.yml)

| Job | Runner | 构建目标 | 状态 |
|---|---|---|---|
| virtualsmartcard-macos | macOS-14 | `.dmg` | 活跃 |
| virtualsmartcard-ubuntu | Ubuntu 24.04 | `.tar.gz` | 活跃 |
| virtualsmartcard-windows x64/ARM64 | Windows 2025 | MSI 驱动包 + `vicc.exe` + `vpcd-config.exe` + 证书 | 活跃，含实际安装步骤 |
| ccid-ubuntu | Ubuntu 24.04 | `.tar.gz` | 活跃 |
| pcsc-relay-macos / ubuntu | 各自 | 对应发布包 | 活跃 |
| pcsc-relay-mingw-64 | Ubuntu 24.04 (cross) | `pcsc-relay.exe` | 活跃（mingw-32 被注释掉了） |
| remote-reader-ubuntu | Ubuntu 24.04 | APK | 活跃 |
| ACardEmulator-ubuntu | Ubuntu 24.04 | APK | 活跃 |

**旧 Travis CI 里还有 Coverity Scan**，但新的 GitHub Actions 里没保留 Coverity job。

## 5. 涉及的核心标准 / 协议

| 标准 | 用途 | 在代码中的体现 |
|---|---|---|
| PC/SC | Windows/macOS 原生智能卡 API | `pcsclite-vpcd/winscard.c`、`ifd-vpcd/ifd-vpcd.c`、`ccid/src/OpenSC/src/libopensc/reader-pcsc.c` |
| CCID | USB Chip/Smart Card Interface Devices | `ccid/` 整个子项目 |
| ISO 7816 | APDU / T=0 / T=1 协议 | `libopensc/iso7816.c`、`vpcd` 命令转发、所有虚拟卡 |
| ISO 14443 | NFC A/B/F 非接触卡 | `remote-reader/NFCReader.java`、`pcsc-relay` + libnfc |
| PACE / CWA 14890 | eID 双向认证 | `libopensc/pace.h`、`libopensc/cwa14890.c`、vpicc nPA 卡 |
| PKCS#15 / PIV / OpenPGP | 卡应用规范 | `libopensc/pkcs15*.c`、ACardEmulator 各 Applet |

## 6. 目录总览

```
vsmartcard/
├── .github/           CI scripts + workflows
├── virtualsmartcard/  [核心] 虚拟 PC/SC 读写器 + vpicc 虚拟卡
├── pcsc-relay/        [中继] 跨接口/跨机器 APDU 中继
├── remote-reader/     [Android] 把手机 NFC 暴露给远端 vpcd
├── ACardEmulator/     [Android] HCE 模式卡仿真
├── TCardEmulator/     [Tizen] 卡仿真
├── ccid/              [USB] CCID 仿真 + OpenSC 集成
├── eID_gui/ npa/      eID 相关辅助工具
├── docs/              Sphinx 生成的发布文档（已编译好）
├── doc/               源文档
└── README.md          Umbrella 说明 + 各子项目入口
```

## 7. 关键环境依赖

构建时必须先准备好（Linux/macOS 构建时的 apt 包，见 `.travis.yml`）：

```
libpcsclite-dev  libusb-dev  xutils-dev  gengetopt  help2man  swig
python-dev  libnfc  libssl-dev  openpace  mingw-w64 (交叉编译)
```

Windows 构建额外需要：**Windows Driver Kit 10**（`choco install windowsdriverkit10`），因为 BixVReader 是 UMDF 2.0 驱动。

## 8. 完成度判定

- ✅ 所有子项目已列出并映射语言/构建/职责
- ✅ 9 个 submodule 已确认初始化 + 定位
- ✅ CI 矩阵已完整映射
- ✅ 核心协议标准已枚举
- ⚠️ 遗留：每个子项目的模块拆分见后续各子项目 overview 文档
