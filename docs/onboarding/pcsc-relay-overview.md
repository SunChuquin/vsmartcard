# pcsc-relay 子项目概览

> 生成时间：2026-11-17
> 目录：`pcsc-relay/`

## 1. 它解决什么问题

在 **非接触接口** 和 **接触式卡** 之间搭一座桥：

- 一边是 libnfc (真实 NFC 读写器) 或 openpicc (虚拟 NFC) 或 vpcd (虚拟 reader)
- 另一边是真实 PC/SC reader 或虚拟 vicc

典型场景：用 Android NFC 读卡器读一张非接触卡，把 APDU 转发给桌面的 PC/SC 智能卡。

## 2. 架构：双抽象层

| 抽象层 | 职责 | 实现文件 |
|---|---|---|
| **Emulator** (发卡方) | 收 C-APDU 进来，回 R-APDU 出去 | `src/vpcd-driver.c`、`src/opicc.c`、`src/lnfc.c` |
| **Connector** (接卡方) | 把 C-APDU 发出去，收 R-APDU 回来 | `src/pcsc.c`、`src/vicc.c` |

命令行选项（证据：[pcsc-relay.ggo.in](file:///c:/Users/sunck/home/projects/vsmartcard/pcsc-relay/src/pcsc-relay.ggo.in)）：
- `--emulator={vpcd|openpicc|libnfc}`
- `--connector={pcsc|vicc}`
- `--reader=NUM`
- `--vpcd-host` / `--vpcd-port` / `--atr`

## 3. 核心循环

证据：`pcsc-relay.c:L202`

```
main()
  ├── 解析 args → emulator + connector 选定
  ├── connector 初始化 (pcsc: SCardEstablishContext → list readers → connect)
  ├── emulator 初始化 (vpcd: vicc_init → vicc_poweron)
  └── while true:
        emulator → recv C-APDU
        connector → transmit C-APDU → R-APDU
        emulator → send R-APDU
```

## 4. 源文件职责

| 文件 | 职责 |
|---|---|
| `pcsc-relay.c` | main + 参数解析 + 主循环 |
| `pcsc.c` | 真实 PC/SC connector（建 context、枚举 reader、`SCardTransmit`） |
| `vpcd-driver.c` | 虚拟 smart card connector（`vicc_init` / `vicc_transmit`） |
| `vicc.c` | 虚拟 reader emulator（反方向，作为 vpcd 的 server 端） |
| `opicc.c` | openpicc emulator |
| `lnfc.c` | libnfc emulator |
| `vpcd.c / vpcd.h` | 从 virtualsmartcard 复制过来的 vicc 通信底层 |
| `lock.c / lock.h` | pthread 锁 |

## 5. 构建

```bash
cd pcsc-relay
autoreconf -vsi
./configure         # 需要 libpcsclite；--enable-libnfc 则还需 libnfc
make
```

Windows 版本通过 MinGW 交叉编译（CI 用的）：
```bash
./configure --host=x86_64-w64-mingw32 PCSC_CFLAGS="-I/usr/x86_64-w64-mingw32/include" PCSC_LIBS="-lwinscard"
```

## 6. 与 virtualsmartcard 的代码共享

`pcsc-relay/src/vpcd.{c,h}` 和 `lock.{c,h}` 是从 `virtualsmartcard/src/vpcd/` 复制（不是共享子模块）。
这意味着两边如果锁实现或 vicc 协议改了，需要手动同步。

> ⚠️ **技术债**：同一份代码维护两份副本。
