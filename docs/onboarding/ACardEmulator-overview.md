# ACardEmulator 子项目概览

> 生成时间：2026-11-17
> 目录：`ACardEmulator/`

## 1. 它解决什么问题

在 Android 上通过 **HCE（Host Card Emulation）** 把手机变成一张"智能卡"，让外部 NFC 读写器读到手机上跑的虚拟 Applet。

## 2. 与 vpicc 的定位对比

| | vpicc (virtualsmartcard) | ACardEmulator |
|---|---|---|
| 运行位置 | PC 上 Python 脚本 | Android 上 HCE 服务 |
| 通信方式 | TCP socket + vpcd | Android NFC HCE |
| Applet 引擎 | Python 自己写卡 | **jCardSim** (Java 卡仿真框架) |
| 现有卡实现 | nPA、cryptoflex、ePass、Relay | OpenPGP、OATH、PIV、GIDS、ISO、Muscle |

## 3. 它内置的 Applet（全来自 submodule）

| Applet | 来源 | 能力 |
|---|---|---|
| OpenPGP | `ykneo-openpgp` | OpenPGP 智能卡 |
| OATH | `ykneo-oath` | OTP 口令 |
| PIV | `PivApplet` | US 联邦 PIV |
| GIDS | `GidsApplet` | GIDS eID |
| ISO | `IsoApplet` | ISO 7816 兼容 |
| Muscle | `MuscleApplet` | Muscle 认证 |

## 4. 构建

```bash
cd ACardEmulator
./gradlew assembleDebug
```

需要 Android SDK + JDK。`build.gradle` 里把各个 submodule 作为源集直接 include 进来。
