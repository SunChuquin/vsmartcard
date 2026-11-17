# 环境评估（当前机器：Windows）

> 生成时间：2026-11-17
> 评估对象：本机 Windows 10 (5.1.18362.145)

## 1. 操作系统

| 项 | 值 | 证据 |
|---|---|---|
| 系统 | Windows 10 Build 18362 (1903) | `$PSVersionTable.PSVersion = 5.1.18362.145` |
| Shell | PowerShell 5 | 不支持 `&&`、`||`、数组 splatting |
| SCardSvr 服务 | **Stopped** | `Get-Service *scard*` 返回 Stopped |

> ⚠️ **注意**：1903 是比较老的 Win10 版本（2019 年中发布）。UMDF 2.0 驱动在这个版本上应该能跑，但新版 WDK 可能要求更高版本 Windows 做驱动签名测试。

## 2. 构建工具链

| 工具 | 状态 | 备注 |
|---|---|---|
| **MSBuild / Visual Studio** | ❌ 不在 PATH | `msbuild.exe` command not found。Windows 构建跑不了 |
| **Windows Driver Kit** | ❌ 未安装 | CI 里用 `choco install windowsdriverkit10`，本机没有 |
| **Python** | ✅ Python 3.10.11 | vpcd 的 Python 端能跑 |
| **Java** | ❌ 不在 PATH | ACardEmulator / remote-reader 构建不了 |
| **pkg-config** | ❌ 不在 PATH | OpenPACE 依赖检查跑不了 |
| **autotools** | ❌ 未查 | Linux/macOS 构建相关，Windows 不重要 |

## 3. Git + Submodule

| 项 | 值 |
|---|---|
| 当前分支 | `master` |
| HEAD commit | `d29bcd5` — "SM: pad SSC to the DES block size in the Retail MAC (#344)" |
| 所有 submodule | ✅ 已初始化 | 10 个 submodule 全部有 commit hash（不是空指针） |

**特别检查：ccid/src/OpenSC** — 版本 `0.26.1`，已 init ✓

## 4. OpenPACE / OpenSSL 依赖

Windows 端 OpenPACE 不一定需要（Linux/macOS 才用它做 PACE）。但如果要在 Windows 上构建 vpicc 的某些卡实现（比如 nPA），可能需要。

## 5. PC/SC 系统组件

| 项 | 状态 |
|---|---|
| SCardSvr 服务 | Stopped（没有物理读写器也正常） |
| winscard.dll | 应该存在（Windows 自带） |
| 虚拟 PC/SC reader | 未安装 BixVReader 驱动 |

## 6. 当前机器能跑什么

| 能跑 | 不能跑 |
|---|---|
| vpcd + vpicc（Python 端 + TCP 通信，纯用户态） | Windows UMDF 驱动（缺 MSBuild + WDK） |
| Python 单元测试 | ACardEmulator / remote-reader（缺 JDK + Android SDK） |
| 读源码、改源码 | ccid（缺 Linux gadgetfs） |

## 7. 建议补充的工具

1. **Visual Studio Build Tools 2022** + MSBuild + Windows 10 SDK
2. **Windows Driver Kit 10**（`choco install windowsdriverkit10`）
3. **JDK 17** + Android SDK（如果要碰 Android 子项目）
4. **OpenPACE**（如果要在 Windows 上试 eID 流程）
