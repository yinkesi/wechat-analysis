"""驱动脚本：扫描微信进程内存提取密钥并解密数据库"""
import sys, os, json, time

sys.path.insert(0, r"D:\code\wechat-analysis\wx2base")
from wx_decrypt_v4 import scan_memory_for_keys, decrypt_all

DB_DIR = r"D:\xwechat_files\wxid_zs6m4ozpeqv512_7fc6\db_storage"
OUT_DIR = r"D:\code\wechat-analysis\decrypted\wxid_zs6m4ozpeqv512_7fc6"

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
with open(r"D:\code\wechat-analysis\decrypted\index.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
