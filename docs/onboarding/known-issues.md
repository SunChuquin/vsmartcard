# 质量与风险评估

> 生成时间：2026-11-17
> 分级标准：Critical（系统级崩溃/安全洞）> High（严重问题难解决）> Medium（一般问题）> Low（瑕疵）> Unknown（没证据，待确认）

## Critical

### 1. OpenSC 供应链风险
- **证据**：`ccid/src/OpenSC` 是第三方 submodule，版本 `0.26.1`，上游活跃（OpenSC/OpenSC），体积巨大（数千文件）
- **影响**：上游发现的安全洞 / 远程代码执行 / 协议漏洞，会直接影响 ccid 子项目行为。如果 OpenSC 有 CVE，这里必须紧急升级。
- **当前状态**：Unknown — 不知道是否有已知 CVE 影响此版本
- **分级理由**：任何智能卡中间件的漏洞都直接关联 PKI 信任链，Critical

## High

### 2. 没有实现"一卡多接口"模型 — 每个接口背后是独立卡实例
- **真实硬件模型**：一张物理卡可以同时挂多个接口（7816 接触 + 14443 非接触 + SWP），**每个接口内部严格串行，但多个接口之间可以并发**，卡内部有仲裁器按优先级选择先处理哪条指令
- **vsmartcard 实际实现**：**每个 slot/reader 背后是独立卡对象**
  - Linux `ifd-vpcd.c:L127-L128`：每个 slot 连不同端口 `Channel + slot`（slot0→35963, slot1→35964, slot2→35965）
  - `VirtualSmartcard.py:L532-L533`：一个 vpicc 进程只在**一个端口 listen**，要多端口就要多进程
  - Windows `device.cpp:L238-L266`：`NumReaders` 个 reader 各起独立线程、各连独立 TCP 后端
- **后果**：
  - ✅ 同一接口内部串行 — 对的，vpicc 单线程 + `vicc_transmit` mutex + `WdfDeviceLevel` 约束都保证了这一点
  - ❌ 多接口并发 + 卡内部仲裁 — **完全没实现**。slot 0 和 slot 1 背后是两张完全独立的卡（各自独立的 SmartcardFilesystem、密钥、会话、ATR），根本没有共享状态，也就谈不上"并发到达、内部仲裁"
  - ❌ 无法模拟"卡同时挂 7816 + 14443"这种真实场景下的仲裁行为
- **改造成本**：要让多个 TCP socket 汇聚到**同一个卡对象**，需要 vpicc 层改成多 socket poll/select 模式 + 卡对象加跨接口锁 + 会话状态管理。工程量不小
- **分级理由**：这是**架构级能力缺失**，不是 bug，但意味着 vsmartcard 能模拟的边界比真实硬件窄 — 它模拟的是"多张独立虚拟卡"，不是"一张真实多接口卡"

### 3. UMDF 2.0 驱动异常 = 系统异常
- **证据**：`win32/BixVReader/device.cpp`、`driver.cpp` 是 UMDF（不是内核驱动但仍是内核驱动栈的一部分），COM/ATL 代码里存在大量 HRESULT 检查和 WDF 错误路径
- **影响**：UMDF 进程崩溃 → 设备栈异常 → Windows Smart Card 服务可能连带异常。不一定 BSOD（那是 WDM 内核驱动才会），但会导致 SCardSvr 挂掉、所有 PC/SC 设备不可用
- **现状**：没有发现 uncaught 异常路径，但 COM + WDF 组合本身就很脆
- **分级理由**：用户态驱动在 Windows 上的稳定性一直是难点

### 3. vicc 协议没有鉴权 / 加密
- **证据**：`vpcd/vpcd.c` 的 TCP socket 就是裸 `send()` / `recv()`，没有任何握手、TLS、或消息认证
- **影响**：同网段任意进程如果能连 35963，就可以：① 冒充虚拟卡（返回假 ATR / 假 APDU 响应）；② 冒充 vpcd 发送伪造的 C-APDU
- **现状**：没有看到任何加密层
- **分级理由**：智能卡协议本来就是用来放密钥和证书的，裸 TCP 让中间人攻击成为可能

### 4. pcsc-relay 代码复制
- **证据**：`pcsc-relay/src/vpcd.{c,h}` 和 `virtualsmartcard/src/vpcd/vpcd.{c,h}` 是两份独立拷贝
- **影响**：任何协议 bug 修在一边忘修另一边，会导致 relay 用的是旧协议，而 vpcd 已经变了 → APDU 传输错乱
- **现状**：目前两边代码看起来一致，但这是人工维护的
- **分级理由**：维护两份协议实现 = 技术债 + 未来 bug 源头

## Medium

### 5. Windows 构建依赖闭源工具链
- **证据**：`.github/build-virtualsmartcard.ps1` 里 `choco install windowsdriverkit10` + MSBuild，这些不是跨平台构建
- **影响**：没 Windows 机器 + 闭源工具链的贡献者无法验证 Windows 侧改动；驱动签名需要 Authenticode 证书
- **分级理由**：构建可复现性在 Windows 上最弱

### 6. ccid 只支持 Linux
- **证据**：`ccid/configure.ac` 检查 `gadgetfs`，CI 只在 ubuntu job 构建 ccid
- **影响**：macOS / Windows 用户没法构建 ccid；这个子项目在非 Linux 平台上等于不存在
- **分级理由**：不是 bug，但意味着这个子项目有明确的平台硬边界

### 7. 锁实现不统一
- **证据**：Linux/macOS 侧 `vpcd/lock.c` 是 `pthread_mutex`；Windows UMDF 侧是 WDF 设备锁 (`WdfDeviceInitSetIoInCallerContextCallback`)；pcsc-relay 的 `lock.c` 又是一份 pthread 版本
- **影响**：并发语义在各平台上可能有微妙差异；debug 时要同时记三套锁 API
- **分级理由**：跨平台代码的常见问题

### 8. Travis CI 还有但 Coverity 已迁出
- **证据**：`.travis.yml` 仍在，但 GitHub Actions 是主力；Coverity 只在 `coverity.yml` 里
- **影响**：新增贡献者可能困惑"到底用哪个 CI"；Coverity 扫描是否还有效不明
- **分级理由**：CI 维护的一致性问题

## Low

### 9. Python 测试只覆盖工具函数
- **证据**：`virtualsmartcard/src/vpicc/virtualsmartcard/tests/` 只有 `CardGenerator_test.py`、`CryptoUtils_test.py`、`SmartcardSAM_test.py`、`utils_test.py` —— 没有任何测试跑完整 APDU 链路
- **影响**：改 `VirtualSmartcard.py` 的主循环、改卡实现的 `execute()` 都没有自动化回归保护
- **分级理由**：不是"没有测试"，但测试覆盖严重偏斜

### 10. TCardEmulator 无 CI 无活跃维护
- **证据**：`.github/workflows/ci.yml` 完全没有 TCardEmulator job；没有 submodule；源码只有几文件
- **影响**：改了 TCardEmulator 很难确认没破；实际上可能没人在用它
- **分级理由**：边缘子项目

### 11. 没有统一日志层
- **证据**：vpicc Python 有自己的 logger；vpcd C 代码自己打印 stderr；Windows 驱动用 WDF 日志；OpenSC 自己有 log。没有统一的跨组件日志格式
- **影响**：出问题时串联一条完整链路的日志很痛苦
- **分级理由**：可观测性问题

## Unknown

### 12. 是否存在已知 OpenSC 版本 CVE
- **需要查**：OpenSC 0.26.1 是否有公开 CVE
- **证据**：本项目没 pin 安全更新说明

### 13. PowerShell 5 与 `.sh` 脚本
- **证据**：CI 脚本全是 `.sh`（`build-virtualsmartcard.sh` 等），Windows 上只 `build-virtualsmartcard.ps1`
- **影响**：Windows 本地调试时，直接跑 Linux 脚本会失败。但这是 PowerShell 5 限制，不是 bug
- **后续**：AGENTS.md 里会专门记录 PowerShell 5 注意事项

### 14. 远程分支中"callable"、"nfc-f"、"robust"、"pyinstaller"
- **证据**：`git branch -r` 列出 `remotes/origin/callable`、`nfc-f`、`robust`、`pyinstaller`
- **影响**：这些分支是什么？是否有未合入的功能？不知道
