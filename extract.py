"""[已废弃备选路径] 通过 wx2base 扫描微信进程内存提取密钥并解密数据库。

现役流程为 getkey.py（WeChatDataAnalysis 的 scan.py + key_v4.py 路线）。
本脚本保留仅作备用；路径等配置见 config.py / config_local.py。
"""
import json
import os
import sys
import time

import config

if config.WX2BASE_DIR:
    sys.path.insert(0, config.WX2BASE_DIR)
from wx_decrypt_v4 import scan_memory_for_keys, decrypt_all

DB_DIR = config.WX_DB_DIR
OUT_DIR = config.EXTRACT_OUT_DIR


def main():
    t0 = time.time()
    print(f"[{time.time()-t0:6.1f}s] 扫描进程内存提取密钥 ...", flush=True)
    keys = scan_memory_for_keys(DB_DIR, log_callback=lambda m: print(f"  {m}", flush=True))
    print(f"[{time.time()-t0:6.1f}s] 共找到 {len(keys)} 个数据库的密钥", flush=True)

    if not keys:
        print("未提取到任何密钥，退出")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    result = decrypt_all(keys, OUT_DIR, log_callback=lambda m: print(f"  {m}", flush=True))
    print(f"[{time.time()-t0:6.1f}s] 解密完成，成功 {len(result)} 个:", flush=True)
    for rel, path in result.items():
        print(f"  {rel} -> {path}", flush=True)
    with open(os.path.join(config.DECRYPTED_ROOT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
