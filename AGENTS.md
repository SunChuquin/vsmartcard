# vsmartcard 项目开发指南（AGENTS）

> 生成时间：2026-11-17
> 这份文档面向**新加进项目的人和 AI agent**。先读 [project-overview.md](project-overview.md) 建立心智模型，再回到这里。

---

## 1. 项目性质

**不是一个应用，是一个 umbrella 项目。** 6 个子项目各自独立构建、独立发布、依赖不同工具链。不要尝试一次性构建全部。

## 2. 子项目入口 — 你改哪个先跑哪个

```
virtualsmartcard/     核心  ← 大部分改动在这里
pcsc-relay/           中继
ccid/                 USB gadget（只 Linux）
remote-reader/        Android
ACardEmulator/        Android HCE
TCardEmulator/        Tizen（边缘）
```

## 3. 构建：先看 CI 脚本，不要猜

**任何时候想知道"这个子项目怎么构建"，优先看 `.github/workflows/ci.yml` 和 `.github/build-*.sh` / `build-*.ps1`。** README 里的构建命令可能过时，CI 脚本才是作者实际在跑的。

### Linux / macOS (autotools)
```bash
cd virtualsmartcard
autoreconf -vsi
./configure
make
```
pcsc-relay / ccid 同理，都是 `autoreconf -vsi && ./configure && make`。

### Windows (MSBuild + WDK)
```powershell
# 需要 Windows Driver Kit 10 + Visual Studio
choco install windowsdriverkit10 -y
# 然后打开 VS Developer Command Prompt
MSBuild virtualsmartcard/win32/BixVReader.sln
```
**本机环境（Windows 10 1903）没有 MSBuild 和 WDK，本地跑不了 Windows 构建。** 改了 Windows 相关代码就 push 上去让 CI 验证。

### Android (Gradle)
```bash
cd remote-reader    # 或 ACardEmulator
./gradlew assembleDebug
```
需要 JDK + Android SDK。

### Python (vpicc)
不需要构建。就是普通 Python 脚本。**唯一需要跑的测试：**
```bash
cd virtualsmartcard/src/vpicc
python -m unittest discover -s virtualsmartcard.tests -p *_test.py -v
```

## 4. 跨平台差异 — 最重要的事

vsmartcard **同一件事在不同平台上实现完全不同**。这是初学者最容易踩坑的地方：

| 层 | Linux / macOS | Windows |
|---|---|---|
| 上层 API | 系统 `pcsc-lite` + `ifd-vpcd.so` 插件 | 自带 `winscard.dll` |
| 驱动入口 | `ifd-vpcd` 的 `IFDHCreateChannel` / `IFDHTransmitToICC` | **UMDF 2.0** COM/ATL 驱动 (`BixVReader`) |
| 进程通信 | `vpcd` 守护进程 + TCP | UMDF 驱动内部，支持命名管道 / TCP / vicc 三种后端 |
| 锁 | `pthread_mutex` | WDF 设备锁 |
| 配置 | `reader.conf` | `BixVReader.ini` |

**如果你改了 APDU 处理逻辑，要同时检查 `ifd-vpcd/ifd-vpcd.c` 和 `win32/BixVReader/device.cpp`。** 两边代码独立演化。

## 5. Submodule 必须先拉全

```bash
git submodule update --init --recursive
```
漏了这步：
- OpenSC 子模块是空目录 → ccid 构建报找不到 OpenSC
- jcardsim 等是空目录 → ACardEmulator 构建直接失败

**每次换机器 clone 都要跑一次。**

## 6. PowerShell 5 注意事项（本机环境）

- ❌ 不支持 `&&`、`||` —— 用分号 `;` 或分开写两条命令
- ❌ 不支持 bash 语法（`mkdir -p`、`rm -rf`、`ls -la`）— 用 `New-Item -ItemType Directory -Force`、`Remove-Item -Recurse -Force`、`Get-ChildItem`
- ❌ `.ps1` 脚本默认被执行策略拦 —— 用 `.cmd` 版本或设置 `-ExecutionPolicy Bypass -Scope Process`
- ✅ `cd` 在 PowerShell 里会持久化到同一会话，所以不用写 `cd xxx && cmd`
- ✅ 路径有空格时加引号并用 `&` 调用符：`& "D:\path\to\msbuild.exe" /flag`

## 7. 代码风格约定（观察得到的）

| 子项目 | 风格 |
|---|---|
| C 代码（vpcd/pcsc-relay/ccid） | 4 空格缩进，`{` 另起行，驼峰函数名（`vicc_transmit`），头文件用 include guard |
| Python（vpicc） | 4 空格，类名大驼峰（`VirtualSmartcard`），函数蛇形（`send_to_vicc`） |
| C++/ATL（BixVReader） | 大驼峰类名（`CMyDevice`），成员函数驼峰，ATL 宏大量使用（`OBJECT_ENTRY_AUTO`） |
| Java（Android） | Android Studio 默认 |

没有统一 `.clang-format` / `.editorconfig`（除了 OpenSC 子模块自带）。

## 8. 常见陷阱清单

| 陷阱 | 表现 | 怎么避免 |
|---|---|---|
| 忘了 submodule init | OpenSC 目录是空的 | clone 后第一件事 `git submodule update --init --recursive` |
| 跑错脚本 | 在 Windows 上跑 `build-virtualsmartcard.sh` | Windows 用 `.ps1`，Linux/macOS 用 `.sh` |
| 改 APDU 只改了一边 | Linux/macOS 好了 Windows 崩了 | 改 APUD 处理同时检查 `ifd-vpcd` 和 `win32/BixVReader` |
| 以为 vicc 代码是共享的 | 改 `virtualsmartcard/src/vpcd/vpcd.c` 忘了 `pcsc-relay/src/vpcd/vpcd.c` | 这俩是独立拷贝，需要手动同步 |
| 没装 OpenPACE | `./configure` 报错 | Linux 上先 `apt install libopenpace-dev` 或从源码装 |
| WDK 版本对不上 | 驱动构建失败 | 跟 CI 里的版本保持一致，不要瞎升级 |
| ccid 在 Windows 上没用 | 白跑一遍构建 | ccid 只在 Linux + gadgetfs 下有意义，Windows 跳过 |

## 9. 调试技巧

| 场景 | 方法 |
|---|---|
| vpicc Python 卡行为不对 | 直接给 `VirtualSmartcard.py` 加 `print()` 重定向到文件，或用 logging |
| Windows UMDF 驱动崩溃 | 用 WinDbg 附加到 WudfHost.exe；Windows Event Viewer 的 System log |
| vpcd 收不到 vpicc 响应 | 开 tcpdump / Wireshark 抓本地 loopback 35963 |
| CI 里构建失败 | 直接点 GitHub Actions job，看 runner 的完整 stdout |
| 改了 Linux 构建但没 Linux 机 | push 上去让 GitHub Actions CI 跑 |

## 10. 推代码前的最小检查

1. `python -m unittest discover -s virtualsmartcard/src/vpicc/virtualsmartcard/tests`
2. 如果改了 shell 脚本 → push，等 CI
3. 如果改了 C 代码 → push，等 CI
4. 如果改了 Windows 驱动 → push，等 CI（本机没法构建）
