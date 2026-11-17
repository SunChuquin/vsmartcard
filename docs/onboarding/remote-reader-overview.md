# remote-reader 子项目概览

> 生成时间：2026-11-17
> 目录：`remote-reader/`

## 1. 它解决什么问题

把 Android 手机变成一台 **无线 PC/SC 智能卡读写器**：

- Android 端：`remote-reader` app 通过手机 NFC 硬件读取真实智能卡
- PC 端：运行的 `vpcd` 通过 TCP 连接到手机上的 remote-reader
- 对 PC 上的上层应用来说，这就像在本地插了一个 PC/SC 智能卡读写器

## 2. Android 端关键类

| 类 | 职责 |
|---|---|
| `MainActivity` | UI：启动/停止服务、显示日志 |
| `SettingsActivity` | 配置服务 |
| **`VPCDWorker`** | ⭐ 核心：TCP server，监听 vpcd 命令；对每张 C-APDU 调用 SCReader，拿到 R-APDU 再返回 |
| `SCReader` | 接口：`transmit(apdu) → response` |
| `NFCReader` | 工厂：根据 Tag 类型选 IsoDepReader 或 NfcFReader |
| `IsoDepReader` | ISO-DEP 协议实现 |
| `NfcFReader` | NFC-F 协议实现 |
| `DummyReader` | 测试用，固定返回数据 |

## 3. 链路图

```
PC 上的 vpcd  ──── TCP ────>  VPCDWorker (Android)
                                 │
                                 ├─→ NFCReader → IsoDepReader / NfcFReader
                                 │                    │
                                 └─┐                  │
                                   └── APDU ──────>  物理 NFC 智能卡
```

## 4. 构建

```bash
cd remote-reader
./gradlew assembleDebug    # 或 build
```

需要 Android SDK。CI 在 Ubuntu 上构建 APK。
