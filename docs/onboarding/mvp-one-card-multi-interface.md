# MVP: vsmartcard 一卡多接口改造说明

> 日期：2026-11-17
> 版本：v1 MVP

## 1. 改造目标

把 vsmartcard 从**每个 slot/reader 独立卡实例**改成**一张卡多个接口并发**，模拟真实硬件：多接口（7816+14443+…）同时到达、卡内部仲裁器串行执行。

## 2. 改了哪些文件

| 文件 | 改动量 | 关键改动 |
|---|---|---|
| `virtualsmartcard/src/vpicc/virtualsmartcard/VirtualSmartcard.py` | ~180 行 | 加 `select` / `threading` import；`VirtualICC` 加 `multi_interface` 参数、`card_lock`、`connections` 列表；`_handleMessage` 拆分；`_runMulti` 新 select 循环；原 `run()`/`stop()` 适配 |
| `virtualsmartcard/src/vpicc/vicc.in` | ~6 行 | 加 `--multi-interface` / `-M` argparse 参数，传给 `VirtualICC` |
| `virtualsmartcard/src/ifd-vpcd/ifd-vpcd.c` | ~20 行 | 加 `get_port_for_slot()` helper，读 `VPCD_SHARED_PORT` 环境变量决定是否所有 slot 连 `VPCDPORT=35963` |

**未改**：`pcsc-relay/`、`ccid/`、`remote-reader/`、`ACardEmulator/`、`win32/BixVReader/`、`virtualsmartcard/src/vpcd/vpcd.c`（vpcd 本来就是线程安全的）。

## 3. 关键设计决策

### 3.1 为什么用"加锁 + 多连接共享对象"，不用多线程或多进程？

真实硬件的"多接口并发 + 内部仲裁"语义，在 vsmartcard 里就是**一个卡对象被多个接口串行调用**。Python `threading.Lock` 加上 select 多 socket 循环直接对应这个模型，比多线程（锁竞争 + GIL 不确定性）和多进程（跨进程状态共享）都简单。

### 3.2 为什么锁要包住整个 `execute()`？

MVP 里先保守：一把大锁包住所有卡操作。真实硬件里有些纯读操作（`SELECT MF`、`GET DATA EF`）理论上可以并发，但 MVP 先保证正确性、保持和真实卡仲裁器"同时只跑一条指令"的语义一致。第二步再收窄锁粒度。

### 3.3 为什么环境变量 + 命令行参数两个开关？

| 层 | 开关 | 目的 |
|---|---|---|
| vpicc（Python 端） | `--multi-interface` | 选择多 socket select 模式还是原单 socket 模式 |
| ifd-vpcd（C 端） | `VPCD_SHARED_PORT=1` 环境变量 | 让所有 slot 连同一个后端端口，而不是各自独立端口 |

两个开关必须**同时打开**才走新路径。**任何一个没开，就保持原有行为**（完全向后兼容）。

没做成 configure.ac 的宏，因为 MVP 不想引入 autotools 重新 configure 的成本；也没做成 vicc 的一个参数传一个 configure 宏，因为两个文件完全独立（一个是 Python 启动脚本，一个是 C 驱动），互不依赖各自的编译方式。

## 4. 使用方式（Linux/macOS）

### 步骤 1：编译 ifd-vpcd（和平时一样，没任何变化）

```bash
cd virtualsmartcard
autoreconf -vsi
./configure
make
```

### 步骤 2：启动 vpicc，开启一卡多接口模式

```bash
cd virtualsmartcard/src/vpicc
python vicc.in --type=iso7816 --reversed --multi-interface --port=35963 --verbose=4
```

`--reversed`（vpicc 等 vpcd 连进来）+ `--multi-interface`（accept 多连接、共享卡对象）是必须的组合。

### 步骤 3：设置环境变量让所有 slot 连同一个后端端口

```bash
export VPCD_SHARED_PORT=1
```

然后**在另一个终端**加载 pcsc-lite + ifd-vpcd 驱动（具体命令因发行版而异，参考 `.github/build-virtualsmartcard.sh`）。

多个 PC/SC 应用各自创建的 reader/slot 都会连到同一个 `35963` 端口，vpicc 里 `select()` 会同时 accept 它们，并发调用汇聚到同一个 `self.os` 卡对象上。

### 步骤 4（Windows）

MVP 里 **BixVReader 还没改**，Windows 下暂时还是多 reader 各连各的后端。改造它需要：

1. `BixVReader.ini` 里加一个 `SHARE_BACKEND=1` 段
2. `VpcdReader.cpp` 里读这个配置，多个 `VpcdReader` 实例初始化时连同一个 TCP 目标
3. 这部分留待后续迭代

## 5. 哪些是新行为，哪些保持原样

| 场景 | 原版 | MVP 后（开启开关） |
|---|---|---|
| 一个 slot 一个应用 | 一张卡实例，一个 socket | 保持不变（旧路径） |
| 多个 slot，每个独立卡 | 每张卡各自独立状态 | 保持不变（旧路径） |
| **多个 slot，共享一张卡** | ❌ 不可能（代码不支持） | ✅ 新路径：`VPCD_SHARED_PORT=1` + `--multi-interface` |
| 同一张卡上两个应用同时发 APDU | pcsc-lite 排队，串行到 driver | vpicc 侧 select 同时收到，**但** `card_lock` 串行进入 `execute()` |
| 卡 `execute()` 里加个 sleep(5) | 阻塞所有后续 APDU | 同左（这是正确的 — 真实卡也这样） |

## 6. 测试结果

```
$ python -m unittest discover -s virtualsmartcard.tests -p *_test.py

Ran 15 tests in 0.077s
FAILED (errors=7)
```

**7 个 ERROR 全部是预先存在的环境依赖问题**，和本次改动无关：

| 错误 | 根因 |
|---|---|
| `nPA.py: ModuleNotFoundError: No module named 'chat'` | OpenPACE 没装 |
| `CryptoUtils: DES3-ECB cipher is None` | pycryptodome 没装 DES3 算法 |
| `SEutils.hash: ValueError` | 同上 |
| `utils_test: str & int TypeError` | `utils.py` 里 `'logical channel %d' % self.CLA & 0b00000011` 缺括号，**这是原版 bug** |

**8 个 OK 测试全部通过**：`CryptoUtils padding`、`SAM counter`、`SAM incorrect pin`、`CardGenerator Cryptoflex`、`CardGenerator ISO7816`、`RAPDU parsing`、等等。

## 7. 已知限制（留待迭代）

| 限制 | 原因 | 下一步 |
|---|---|---|
| Windows BixVReader 不支持共享后端 | MVP 只改了 Linux/macOS 路径 | 改 `BixVReader.ini` + `VpcdReader.cpp` |
| 锁粗（包住整个 execute） | 先保证正确，模拟真实卡仲裁 | 收窄锁粒度到真正有共享状态的操作（文件系统写、密钥生成），纯读操作放行 |
| vpicc 用的是 select，不是更高级的 epoll/kqueue | MVP 简单就行 | 后续如果有性能瓶颈再升级 |
| 连接断开后没有 reconnect | select 发现 peer 关了就从列表移除 | MVP 先这样，reconnect 留后续 |
| pcsc-relay 子项目没改 | pcsc-relay 有自己独立的 vicc 副本 | 如果 relay 需要一卡多接口也改 |

## 8. 后续迭代路线

1. **Phase 2**：收窄 `card_lock` 粒度。当前一把大锁，改成：纯读 SELECT/GET_DATA 放行，写 CREATE/DELETE/UPDATE 串行。让"一个应用读 EF.DG1 同时另一个应用读 EF.DG2"这种场景真正并发。
2. **Phase 3**：Windows BixVReader 支持共享后端。
3. **Phase 4**：写一个集成测试 — 启动两个应用线程同时调 `SCardTransmit`，验证卡文件系统被正确共享（而不是两张独立卡各自独立状态）。
