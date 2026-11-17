# -*- coding: utf-8 -*-
"""
MVP 验证：一卡多接口 — 两 socket 并发同连一张卡，验证卡状态被共享。

跑法：
    $env:PYTHONPATH = "<repo>/virtualsmartcard/src/vpicc"
    python virtualsmartcard/test-multi-interface.py
"""

import os, socket, select, struct, sys, threading, time

_PORT = 14000
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, "virtualsmartcard", "src", "vpicc"))

from virtualsmartcard.VirtualSmartcard import Iso7816OS  # noqa
from virtualsmartcard.SmartcardFilesystem import MF, TransparentStructureEF  # noqa

# -------- 构造卡 --------
_MF = MF(filedescriptor=0)
ef = TransparentStructureEF(parent=_MF, fid=0x0101, filedescriptor=0,
                             data=b"INITIAL")
_MF.append(ef)
_CARD_OS = Iso7816OS(_MF, sam=None)
_LOCK = threading.Lock()

# -------- server (含完整 EOF 处理) --------
def _recv_full(sock, n):
    """Loop recv until n bytes received; raises OSError on EOF."""
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise OSError("peer closed mid-frame")
        buf += chunk
    return buf

def _serve():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('', _PORT))
    srv.listen(16)
    conns = []
    while True:
        r = [srv] + conns
        rd, _, _ = select.select(r, [], [], 0.5)
        for s in rd:
            if s is srv:
                try:
                    c, _ = srv.accept(); c.settimeout(None); conns.append(c)
                except OSError:
                    pass
            else:
                try:
                    h = _recv_full(s, 2)
                    (sz,) = struct.unpack('!H', h)
                    body = _recv_full(s, sz) if sz else b''
                    if sz > 1:  # APDU path
                        with _LOCK:
                            try: resp = bytes(_CARD_OS.execute(body))
                            except Exception: resp = b'\x68\x00'
                        s.sendall(struct.pack('!H', len(resp)) + resp)
                    # sz==0 or sz==1 control: no response
                except OSError:
                    if s in conns: conns.remove(s); s.close()
                except Exception:
                    if s in conns: conns.remove(s); s.close()

# -------- client --------
def _open():
    s = socket.socket(); s.settimeout(5)
    s.connect(('127.0.0.1', _PORT)); return s

def _apdu(s, apdu):
    s.sendall(struct.pack('!H', len(apdu)) + apdu)
    h = _recv_full(s, 2)
    (sz,) = struct.unpack('!H', h)
    return _recv_full(s, sz) if sz else b''

# -------- 主流程 --------
def main():
    threading.Thread(target=_serve, daemon=True).start(); time.sleep(0.3)
    results = {}

    def client_a():
        try:
            s = _open()
            results['A-sel']   = _apdu(s, b'\x00\xa4\x00\x00\x02\x01\x01')
            results['A-write'] = _apdu(s, b'\x00\xd0\x00\x00\x05HELLO')
            results['A-read']  = _apdu(s, b'\x00\xb0\x00\x00\x20')
            s.close()
        except Exception as e: results['A-err'] = repr(e)

    def client_b():
        time.sleep(0.5)
        try:
            s = _open()
            results['B-sel']  = _apdu(s, b'\x00\xa4\x00\x00\x02\x01\x01')
            results['B-read'] = _apdu(s, b'\x00\xb0\x00\x00\x20')
            s.close()
        except Exception as e: results['B-err'] = repr(e)

    ta = threading.Thread(target=client_a); tb = threading.Thread(target=client_b)
    ta.start(); tb.start(); ta.join(10); tb.join(10)

    print("=" * 60)
    print("MVP multi-interface verification (一卡多接口)")
    print("=" * 60)
    def _show(k):
        v = results.get(k)
        if v is None: return f"  {k:12s} -> <missing>"
        if isinstance(v, str): return f"  {k:12s} -> ERR: {v}"
        sw = (v[-2], v[-1]) if len(v) >= 2 else (-1, -1)
        data = v[:-2] if len(v) >= 2 else v
        return f"  {k:12s} -> SW={sw[0]:02x}{sw[1]:02x}  data={data!r}"
    for k in ['A-sel', 'A-write', 'A-read', 'B-sel', 'B-read', 'A-err', 'B-err']:
        if k in results: print(_show(k))
    print("-" * 60)

    def _ok(v): return isinstance(v, bytes) and len(v) >= 2
    sw_a_wr = (results['A-write'][-2], results['A-write'][-1]) if _ok(results.get('A-write')) else (-1, -1)
    data_a  = results['A-read'][:-2]  if _ok(results.get('A-read'))  else b''
    data_b  = results['B-read'][:-2]  if _ok(results.get('B-read'))  else b''
    sw_b    = (results['B-read'][-2], results['B-read'][-1]) if _ok(results.get('B-read')) else (-1, -1)

    checks = [
        ("A WRITE  SW=9000",                      sw_a_wr == (0x90, 0x00)),
        ("A self-read 读到 HELLO",                b'HELLO' in data_a),
        ("B cross-read 读到 HELLO (跨 socket)",   b'HELLO' in data_b),
        ("B cross-read SW=90xx/62xx",             sw_b[0] in (0x90, 0x62)),
    ]
    all_ok = True
    for name, ok in checks:
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}]  {name}")
        if not ok: all_ok = False
    print("-" * 60)

    # 额外断言：B 读到的不是 INITIAL 而是 HELLO — 这就是跨接口共享卡状态！
    if b'HELLO' in data_b and b'INITIAL' not in data_b:
        print("  🎯 核心证据：B 跨 socket 读到了 A 写入的数据，")
        print("     证明多个 TCP 接口汇聚到同一张卡对象（非独立卡实例）。")

    if all_ok:
        print("✅ MVP PASS — 一卡多接口模型验证通过！")
        sys.exit(0)
    else:
        print("❌ MVP FAIL — 见上方 FAIL 项。")
        sys.exit(1)

if __name__ == "__main__":
    main()
