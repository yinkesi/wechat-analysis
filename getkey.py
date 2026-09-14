"""微信 4.1.13 密钥提取 + 全库解密驱动
流程: Weixin.dll 提取 internal_db_key (XOR key) -> 微信进程内存 YARA 扫描 raw key
      -> passphrase = raw ^ internal -> PBKDF2(256000) 派生每库 AES key -> 解密
"""
import sys, os, json, time, hashlib, hmac as hmac_mod, struct
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, r"D:\code\wechat-analysis\WeChatDataAnalysis")
sys.path.insert(0, r"D:\code\wechat-analysis\WeChatDataAnalysis\src\wechat_decrypt_tool")

import key_v4
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA512

WDA = r"D:\code\wechat-analysis\WeChatDataAnalysis"
DLL = r"C:\Program Files\Tencent\Weixin\4.1.13.65\Weixin.dll"
DB_DIR = r"D:\xwechat_files\wxid_zs6m4ozpeqv512_7fc6\db_storage"
OUT_DIR = r"D:\code\wechat-analysis\decrypted\v4"
PROBE_DB = os.path.join(DB_DIR, "contact", "contact.db")

PAGE_SZ, KEY_SZ, SALT_SZ, IV_SZ, HMAC_SZ = 4096, 32, 16, 16, 64
RESERVE_SZ = 80
ROUND_COUNT = 256000
SQLITE_HDR = b"SQLite format 3\x00"


def log(msg):
    print(msg, flush=True)


# ---------- 第 1 步: DLL 内嵌 XOR key ----------
def extract_dll_keys():
    keys_dir = os.path.join(os.getcwd(), "keys")
    os.makedirs(keys_dir, exist_ok=True)
    jsonl = os.path.join(keys_dir, "4.1.13.65.jsonl")
    if os.path.exists(jsonl):
        os.remove(jsonl)
    from scan import extract_xor_keys_multiprocess
    extract_xor_keys_multiprocess(DLL, version="4.1.13.65")
    cands = []
    if os.path.exists(jsonl):
        with open(jsonl, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cands.append(bytes.fromhex(json.loads(line)["key"].replace(" ", "")))
    log(f"[dll] 提取到 {len(cands)} 个 internal_db_key 候选")
    return cands


# ---------- 第 2 步: 内存扫描 raw key ----------
def get_wechat_pids():
    import subprocess
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Weixin.exe", "/FO", "CSV", "/NH"],
                       capture_output=True, text=True, timeout=10)
    pids = []
    for line in r.stdout.strip().split("\n"):
        p = line.strip('"').split('","')
        if len(p) >= 5:
            try:
                pids.append((int(p[1]), int(p[4].replace(",", "").replace(" K", "").strip() or 0)))
            except ValueError:
                pass
    pids.sort(key=lambda x: -x[1])
    return [p for p, _ in pids]


def find_passphrase(internal_cands):
    probe = open(PROBE_DB, "rb").read(PAGE_SZ)
    for pid in get_wechat_pids():
        log(f"[mem] 尝试 PID={pid} ...")
        for internal in [None] + internal_cands:
            tag = "none" if internal is None else internal.hex()[:12]
            try:
                key_hex = key_v4.recover_key(pid, PROBE_DB, internal)
            except Exception as e:
                log(f"    internal={tag} 异常: {e}")
                continue
            if key_hex:
                raw = bytes.fromhex(key_hex)
                if internal is None:
                    return raw.hex()
                passphrase = bytes(a ^ b for a, b in zip(raw, internal))
                log(f"[+] 找到! pid={pid} internal={tag}")
                return passphrase.hex()
        # 无 internal 时 raw 直接作为 passphrase 也可能成立（老方案）
    return None


# ---------- 第 3 步: 派生 + 解密 ----------
def derive_and_verify(passphrase_hex, page1):
    salt = page1[:SALT_SZ]
    enc_key = PBKDF2(bytes.fromhex(passphrase_hex), salt, dkLen=KEY_SZ, count=ROUND_COUNT, hmac_hash_module=SHA512)
    mac_salt = bytes(b ^ 0x3A for b in salt)
    mac_key = PBKDF2(enc_key, mac_salt, dkLen=KEY_SZ, count=2, hmac_hash_module=SHA512)
    h = hmac_mod.new(mac_key, page1[SALT_SZ:PAGE_SZ - RESERVE_SZ + IV_SZ], SHA512)
    h.update(struct.pack("<I", 1))
    return enc_key, (h.digest() == page1[PAGE_SZ - RESERVE_SZ + IV_SZ:])


def decrypt_db(args):
    db_path, out_path, passphrase_hex = args
    size = os.path.getsize(db_path)
    if size < PAGE_SZ:
        return db_path, "skip_small"
    with open(db_path, "rb") as f:
        page1 = f.read(PAGE_SZ)
    enc_key, ok = derive_and_verify(passphrase_hex, page1)
    if not ok:
        return db_path, "key_mismatch"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(db_path, "rb") as fin, open(out_path, "wb") as fout:
        pgno = 0
        while True:
            page = fin.read(PAGE_SZ)
            if not page:
                break
            pgno += 1
            if len(page) < PAGE_SZ:
                break
            iv = page[PAGE_SZ - RESERVE_SZ:PAGE_SZ - RESERVE_SZ + IV_SZ]
            if pgno == 1:
                from Crypto.Cipher import AES
                dec = AES.new(enc_key, AES.MODE_CBC, iv).decrypt(page[SALT_SZ:PAGE_SZ - RESERVE_SZ])
                fout.write(SQLITE_HDR + dec + b"\x00" * RESERVE_SZ)
            else:
                from Crypto.Cipher import AES
                dec = AES.new(enc_key, AES.MODE_CBC, iv).decrypt(page[:PAGE_SZ - RESERVE_SZ])
                fout.write(dec + b"\x00" * RESERVE_SZ)
    return db_path, f"ok ({pgno} pages)"


def main():
    t0 = time.time()
    passphrase = None
    state_file = r"D:\code\wechat-analysis\key_result.json"

    if os.path.exists(state_file):
        passphrase = json.load(open(state_file))["passphrase_hex"]
        log(f"[resume] 使用已保存的 passphrase")
    else:
        internal_cands = extract_dll_keys()
        log(f"[{time.time()-t0:5.1f}s] 开始内存扫描 ...")
        passphrase = find_passphrase(internal_cands)
        if not passphrase:
            log("[-] 未能提取密钥")
            sys.exit(1)
        json.dump({"passphrase_hex": passphrase}, open(state_file, "w"))

    log(f"[+] passphrase = {passphrase[:16]}...")

    # 验证 probe
    probe = open(PROBE_DB, "rb").read(PAGE_SZ)
    _, ok = derive_and_verify(passphrase, probe)
    log(f"[verify] contact.db 校验: {'PASS' if ok else 'FAIL'}")
    if not ok:
        sys.exit(1)

    # 收集全部 DB
    tasks = []
    for root, _, files in os.walk(DB_DIR):
        for fn in files:
            if fn.endswith(".db"):
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, DB_DIR)
                tasks.append((p, os.path.join(OUT_DIR, rel), passphrase))
    log(f"[*] 待解密 {len(tasks)} 个数据库")

    results = {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        for db_path, status in ex.map(decrypt_db, tasks):
            results[os.path.relpath(db_path, DB_DIR)] = status
            log(f"    {status:>18}  {os.path.relpath(db_path, DB_DIR)}")
    ok_n = sum(1 for s in results.values() if s.startswith("ok"))
    log(f"[{time.time()-t0:5.1f}s] 解密完成: {ok_n}/{len(tasks)} 成功")


if __name__ == "__main__":
    main()
