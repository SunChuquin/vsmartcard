# 核心通信链路追踪

> 生成时间：2026-11-17
> 每条链路都跟到了具体源文件和函数。

---

## 链路 1：APDU 调用链（最核心）

这是"PC 上一个应用调 `SCardTransmit`，APDU 最终被 Python 虚拟卡处理"的完整路径。

### Linux / macOS 路径

```
应用代码
  │  SCardTransmit(hContext, hCard, &pciSendCtl, sendApdu, &sendApduLen, &pciRecvCtl, recvApdu, &recvApduLen)
  ▼
┌───────────────────────────────────────────────┐
│  pcsc-lite (系统库，非本项目代码)               │
│  加载 ifd-vpcd.so                             │
└───────────────────────────────────────────────┘
  │  IOCTL_SMARTCARD_TRANSMIT
  ▼
virtualsmartcard/src/ifd-vpcd/ifd-vpcd.c:L425
  IFDHTransmitToICC()
    ├── 把 pcsc-lite 传过来的 APDU 塞到 vpcd 请求结构里
    ├── vicc_transmit(&channel->vicc, sendApdu, sendLen, recvApdu, &recvLen)
    └── 从 vicc 拿回 R-APDU 写回调用方
      │
      ▼
virtualsmartcard/src/vpcd/vpcd.c:L368
  vicc_transmit()
    ├── pthread_mutex_lock(&vicc->lock)     ← ⚠️ 加锁！
    ├── sendToVICC(vicc, apdu, apduLen)    ← 发 2B 长度头 + APDU 到 TCP socket
    ├── recvFromVICC(vicc, resp, respLen)  ← 读回 R-APDU
    └── pthread_mutex_unlock(&vicc->lock)
      │
      ▼  TCP (默认 35963)
virtualsmartcard/src/vpicc/virtualsmartcard/VirtualSmartcard.py:L577
  VirtualICC.run() 主循环
    ├── recv_apdu()   ← 读 socket (2B len + APDU)
    ├── card.execute(apdu)   ← ⭐ 虚拟卡收到 C-APDU，生成 R-APDU
    └── send_apdu(response)   ← 写回 socket
```

### Windows 路径（**完全不同的一套**）

```
应用代码
  │  SCardTransmit(...)         ← Windows 自带 winscard.dll
  ▼
┌───────────────────────────────────────────────┐
│  内核 Smart Card 服务 (scardsvr.sys)           │
│  通过 WMI 加载 UMDF 驱动 BixVReader           │
└───────────────────────────────────────────────┘
  │  IOCTL_SMARTCARD_TRANSMIT via WDF
  ▼
virtualsmartcard/win32/BixVReader/device.cpp:L91
  CMyDevice::OnIoInCallerContext()
    ├── switch(ControlCode) → IOCTL_SMARTCARD_TRANSMIT
    ├── Reader->QueryTransmit(...)
    │
    ▼
virtualsmartcard/win32/BixVReader/reader.cpp 或 VpcdReader.cpp
  CReader::QueryTransmit()
    └── vicc_transmit()   ← 跟 Linux/vpcd 用同一个头文件的函数！
        │
        ▼
    TCP → 要么连本地 vpcd，要么连 Android remote-reader
```

> **重要事实**：Windows 端 BixVReader 的 `VpcdReader.cpp` 直接调用 `vicc_transmit()` —— 这意味着 **Windows UMDF 驱动和 Linux 的 vpcd 守护进程用的是同一套 vicc 协议代码**。但入口点（pcsc-lite vs WDF）完全不同。

---

## 链路 2：远程读写器链（Android → PC）

这是"手机 NFC 卡被 PC 上的应用读到"的完整路径。

```
物理 NFC 智能卡
  │  ISO-DEP / NFC-F
  ▼
Android NFC Service
  │
  ▼
remote-reader/.../screaders/IsoDepReader.java
  IsoDepReader.transmit(apdu)
    └── isoDep.transceive(apduBytes)   ← 直接 Android NFC API
      │
      ▼  C-APDU 字节串
remote-reader/.../VPCDWorker.java:L85
  VPCDWorker.onReceive(apdu)
    ├── reader.transmit(apdu) → 得到 R-APDU
    └── 把 R-APDU 写回 TCP socket
      │
      ▼  TCP socket (vpcd 连进来)
PC 上的 vpcd（virtualsmartcard）
  │ vicc_transmit() 反方向
  ▼
PC 上的 BixVReader (Windows) / ifd-vpcd (Linux)
  │ IOCTL_SMARTCARD_TRANSMIT
  ▼
PC 上的应用 SCardTransmit()   ← 就像本地插了一张 NFC 卡
```

---

## 链路 3：CCID 仿真链（Linux USB gadget）

```
其他设备 (USB Host)
  │ USB CCID Class Request + Bulk Transfer
  ▼
Linux gadgetfs (内核)
  │
  ▼
ccid/ 子项目
  │ 通过 gadgetfs 设备节点读写 USB payload
  ▼
OpenSC src/libopensc/reader-pcsc.c
  │ 实现 PC/SC reader 接口
  ▼
本机器上的其他应用
  │ SCardTransmit()
  ▼
OpenSC libopensc → ccid gadgetfs → USB → 远端 Host
```

> ccid 是单向的：**本机器上的智能卡被伪装成一个 USB CCID 设备给远端用**。和链路 1/2 的方向相反。

---

## 链路 4：PC/SC Relay 链（跨接口中继）

```
emulator 端（可以是 libnfc / vpcd / openpicc）
  │ recv C-APDU
  ▼
pcsc-relay 主循环 pcsc-relay.c:L202
  │
  ├── C-APDU → connector（pcsc.c:SCAardTransmit → 真实物理卡）
  ├── card 返回 R-APDU
  └── R-APDU → send 回 emulator
```

pcsc-relay 是一个**纯用户态的 APDU 中间盒**，不直接进内核驱动。

---

## 共性观察

1. **所有链路最终都收束到 `vicc_transmit()` + TCP socket + `card.execute(apdu)`** 这个核心三元组。
2. **vicc 协议**就是 2B 长度头 + APDU 字节串，极其简单。
3. **锁的位置**：`vpcd.c` 里 `vicc_transmit` 加的是 `pthread_mutex`；Windows UMDF 侧是 WDF 设备锁。
4. **vicc 通信层被复制了两次**（`virtualsmartcard/src/vpcd/vpcd.{c,h}` 和 `pcsc-relay/src/vpcd.{c,h}`），修改需要手动同步。
