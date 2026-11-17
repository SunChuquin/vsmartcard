# ccid 子项目概览

> 生成时间：2026-11-17
> 目录：`ccid/`

## 1. 它解决什么问题

把一台 Linux 机器上真实的 PC/SC 智能卡读写器，**伪装成一个标准 USB CCID 设备**暴露出来。其他设备（比如 Windows PC）插上这个 USB "CCID 卡"就能直接用。

## 2. 依赖关系

- **强依赖** Linux `gadgetfs`（USB gadget 内核模块）—— 所以 ccid **只在 Linux 上有用**
- **强依赖** OpenSSL / libcrypto（`configure.ac` 检查 `EVP_read_pw_string_min`）
- **OpenSC 子模块** (`ccid/src/OpenSC`) —— 提供 CCID 设备注册 + PACE 认证集成

## 3. 构建

```bash
cd ccid
autoreconf -vsi
./configure        # 检查 gadgetfs、pthread、OpenSSL
make
```

## 4. OpenSC 子模块的角色

OpenSC 是智能卡中间件，提供：
- `libopensc` —— 智能卡通信核心（ISO 7816、PKCS#15、reader-pcsc）
- `pkcs11/` —— PKCS#11 接口层
- `src/libopensc/reader-pcsc.c` —— 把 ccid 的 USB CCID 暴露给 PC/SC 上层

ccid 这个子项目本身代码量不大，绝大部分工作其实在 OpenSC 子模块里完成。
这也意味着 **OpenSC 升级 = ccid 行为可能变动**。

## 5. 局限性

- 必须 Linux + 支持 gadgetfs 内核模块
- 不支持 macOS / Windows（macOS/Windows 用户不会用 gadgetfs）
- CI 也只在 `ubuntu` job 上构建 ccid
