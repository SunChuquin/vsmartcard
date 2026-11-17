# virtualsmartcard 子项目概览

> 生成时间：2026-11-17
> 目录：`virtualsmartcard/`
> 核心地位：**本项目的心脏**。所有其他子项目最终都和 vpcd / vpicc 交互。

## 1. 它解决什么问题

在一台没有物理智能卡读写器的机器上，给 PC/SC / CCID 上层应用一张"假"卡。
通过一个虚拟守护进程 (`vpcd`) + 一个虚拟 ICC 实现 (`vpicc`，Python)，把 PC/SC 调用重定向到 Python 脚本里的模拟卡上。

## 2. 关键源文件与职责

```
virtualsmartcard/
├── src/
│   ├── vpcd/           ← 核心守护进程 (C)
│   │   ├── vpcd.c      入口 + TCP socket 读写 + vicc_init/vicc_transmit/vicc_getatr
│   │   ├── vpcd.h      vicc_ctx + VPCDPORT 等对外接口
│   │   ├── lock.c/h    线程锁 (pthread_mutex 版本)
│   │   └── Makefile.am
│   ├── ifd-vpcd/       ← Linux/macOS pcsc-lite 的 IFD handler
│   │   ├── ifd-vpcd.c  IFDHCreateChannel / IFDHTransmitToICC 导出
│   │   └── reader.conf.in
│   ├── pcsclite-vpcd/  ← 在没 pcsc-lite 的平台上提供 winscard API
│   │   ├── winscard.c  SCardEstablishContext / SCardTransmit 实现
│   │   └── PCSC/       头文件副本 (wintypes.h, winscard.h 等)
│   ├── vpcd-config/    ← 配置工具 (inet_ntop, local-ip, qransi)
│   └── vpicc/          ← 虚拟 ICC 实现 (Python)
│       ├── vicc.in              vpicc 启动脚本
│       └── virtualsmartcard/   Python 包
│           ├── VirtualSmartcard.py   VirtualICC 主循环
│           ├── SmartcardFilesystem.py 卡文件系统模拟
│           ├── CryptoUtils.py         加解密工具
│           ├── SWutils.py / SEutils.py / TLVutils.py 协议辅助
│           └── cards/                 各具体卡实现
│               ├── Relay.py / RelayMiddleman.py  中继用
│               ├── nPA.py                         德国 eID
│               ├── cryptoflex.py                  CryptoFlex
│               ├── ePass.py                       ePassport
│               └── HandlerTest.py
├── win32/              ← Windows 端 (完全独立的一套实现)
│   ├── BixVReader/     UMDF 2.0 + ATL COM 驱动
│   ├── DevMsi/         MSI 自定义动作 submodule
│   └── BixVReaderInstaller/ WiX 安装包
├── MacOSX/             ← macOS 打包 postinstall 脚本
├── npa-example-data/   nPA 示例证书/密钥
└── doc/                Sphinx 文档源
```

## 3. 关键入口点

| 入口 | 位置 | 语言 | 类型 |
|---|---|---|---|
| `vpcd` 守护进程 main | `src/vpcd/vpcd.c:L300` | C | `main()` |
| vpicc 主循环 | `src/vpicc/virtualsmartcard/VirtualSmartcard.py:L577` | Python | `VirtualICC.run()` |
| pcsc-lite IFD 入口 | `src/ifd-vpcd/ifd-vpcd.c:L118` | C | `IFDHCreateChannel` |
| Windows UMDF 驱动入口 | `win32/BixVReader/driver.cpp:L15` | C++/ATL | `CMyDriver::OnDeviceAdd` |
| Windows `SCardTransmit` | `src/pcsclite-vpcd/winscard.c:L509` | C | `SCardTransmit` |

## 4. vpcd —— vpicc 通信协议

证据：`vpcd/vpcd.c` 里的 `sendToVICC` / `recvFromVICC`

- TCP socket，默认端口 **35963**（`VPCDPORT`）
- 消息格式：**2 字节大端长度头 + 完整 APDU**
- `vicc_ctx` 持有 socket fd + 锁
- 每收到 APDU，vpcd 加锁后转发给 vpicc，等响应再解锁
- 支持两种方向：vpcd 监听等 vpicc 连入；或 vpcd 主动连 vpicc

## 5. Windows 端的重要事实

**vsmartcard 在 Windows 上不是用 vpcd + ifd-vpcd 这套 C 代码，而是完全独立的 BixVReader UMDF 2.0 驱动 + ATL COM**。

- 驱动注册 `SmartCardReaderGuid` 设备接口
- 实现 `IOCTL_SMARTCARD_*` 全套 IOCTL（属性、状态、电源、协议、传输）
- 启动时读 `BixVReader.ini` 配置 `NumReaders` 和 `RPC_TYPE`
- 支持 3 种后端：`PipeReader`（命名管道）、`TcpIpReader`（TCP）、`VpcdReader`（走 `vicc_transmit` 接口）
- WDF 设备锁约束通过 `WdfDeviceInitSetIoInCallerContextCallback` + `WdfDeviceInitSetPowerPolicyOwnership` 设置

> 这是**多平台差异最大的地方**。Linux/macOS 是 pcsc-lite + ifd handler，Windows 是原生 UMDF 驱动。两边的代码完全不共享。

## 6. 构建命令

### Linux / macOS
```bash
cd virtualsmartcard
autoreconf -vsi
./configure          # 需要 OpenPACE 预先安装
make
```

### Windows
```powershell
# 需要: WDK 10 + MSBuild + Visual Studio
# 参考 .github/build-virtualsmartcard.ps1
choco install windowsdriverkit10 -y
# 用 VS Developer Command Prompt 打开
# MSBuild virtualsmartcard/win32/BixVReader.sln
```

## 7. 完成度判定

- ✅ 完整目录树已列出
- ✅ 5 个核心入口点已定位
- ✅ vpcd ↔ vpicc 协议已描述
- ✅ Windows vs Linux 双架构差异已明确
- ✅ 构建命令已给出
