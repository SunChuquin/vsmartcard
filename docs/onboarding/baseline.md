# Baseline — 当前构建 / 测试状态快照

> 生成时间：2026-11-17
> 这是一份**不动环境**的快照。目的是"如果现在什么都不装、什么都不改，能跑到哪一步"。

## 1. 构建状态

| 子项目 | 理论能构建？ | 实际状态 | 阻塞项 |
|---|---|---|---|
| virtualsmartcard (Linux) | ✅ autotools | ⏸️ 未试 | 本机是 Windows |
| virtualsmartcard (Windows) | ✅ MSBuild + WDK | ❌ 构建不了 | 缺 MSBuild + WDK |
| pcsc-relay | ✅ autotools / MinGW | ⏸️ 未试 | 同上 |
| ccid | ✅ autotools + OpenSC | ❌ 无意义 | Windows 上 ccid 没用 |
| remote-reader | ✅ Gradle | ❌ 构建不了 | 缺 JDK |
| ACardEmulator | ✅ Gradle | ❌ 构建不了 | 缺 JDK |
| TCardEmulator | ✅ Eclipse CDT | ❌ 构建不了 | 缺 Tizen SDK |

## 2. 测试存在性

| 位置 | 类型 | 能跑吗 |
|---|---|---|
| `virtualsmartcard/src/vpicc/virtualsmartcard/tests/` | Python unittest | ✅ 应该能跑 |
| `remote-reader/app/src/test/...screaders/` | Android 测试 | ❌ 缺 JDK |
| `OpenSC/src/tests/` | C tests | ❌ 缺 autotools + gcc |
| `virtualsmartcard/win32/DevMsi/src/DevMsiTest/` | C++ test | ❌ 缺 MSBuild |
| `virtualsmartcard/test_vicc_with_*.sh` | Shell 集成测试 | ❌ 缺 bash |

**结论**：只有 Python 单元测试在理论上能直接跑。当前机器没有实际执行过任何测试，这里只做"存在性"记录。

## 3. CI 状态（远端）

GitHub Actions：全绿（最新 commit 见本地 git log）。
Coverity Scan：项目在跑，但 `coverity.yml` job 没在新版 CI 里保留。

## 4. Submodule 完整性

✅ 所有 submodule 已初始化并指向确定 commit hash，没有空指针。

## 5. 变更基线（下一步 onboarding 应该记住的）

- 最近一次 commit：`d29bcd5` — SM PACE Retail MAC padding fix
- 当前 HEAD 在 `master`，没有本地未提交变更（假设）
- OpenSC 固定在 `0.26.1` 子模块版本，不会被意外升级

## 6. 能做的最小验证

如果要建立"确实能编译"的信心，最容易实现的路径是：

1. **Python 单元测试**：`python -m unittest discover`（纯 Python，无依赖）
2. **GitHub Actions CI**：任何改动 push 上去后 CI 会自动跑全平台构建

这比在本机折腾 Windows 构建工具链靠谱得多。
