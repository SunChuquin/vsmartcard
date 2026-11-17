# TCardEmulator 子项目概览

> 生成时间：2026-11-17
> 目录：`TCardEmulator/`

## 1. 它解决什么问题

在 **Tizen** 设备（三星 Gear 手表等）上仿真智能卡。相比 ACardEmulator，TCardEmulator 的覆盖面和社区活动都要小得多。

## 2. 构建和工具链

- Eclipse CDT（`.cproject` / `.project` / `.tproject`）
- sdb（Tizen SDK）
- 没有 CI job（`.github/workflows/ci.yml` 里完全没提到 TCardEmulator）
- 没有 `.gitmodules` 条目（不依赖外部 submodule）

## 3. 源文件

| 文件 | 职责 |
|---|---|
| `src/tcardemulator.c` | 主入口 |
| `src/sap.c` | SAP（Smartcard Access Provider）实现 |
| `inc/tcardemulator.h` / `inc/sap_app.h` | 头文件 |

## 4. 现状评估

**低活跃、低维护**。README 很简短，没有独立 CI，没有 submodule，没有测试。
这是一个边缘子项目，大多数贡献者不会碰它。除非你的目标明确要支持 Tizen，否则可以先不花时间在这里。
