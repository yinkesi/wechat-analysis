"""导出群聊（见 config_local.GROUPS）的全部消息为 CSV（含发言人解析、群名片、zstd 解压）"""
import csv
import datetime
import hashlib
import io
import logging
import os
import re
import sqlite3

import zstandard

from config import DATA_DIR, DECRYPTED_DIR, GROUPS

MSG_DBS = [os.path.join(DECRYPTED_DIR, "message", "message_0.db"),
           os.path.join(DECRYPTED_DIR, "message", "message_1.db")]
CONTACT_DB = os.path.join(DECRYPTED_DIR, "contact", "contact.db")

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
dctx = zstandard.ZstdDecompressor()


def decode_content(blob):
    """消息内容: zstd 压缩或明文"""
    if blob is None:
        return ""
    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    if isinstance(blob, bytes):
        if blob[:4] == ZSTD_MAGIC:
            try:
                return dctx.decompress(blob).decode("utf-8", errors="replace")
            except Exception:
                try:
                    with dctx.stream_reader(io.BytesIO(blob)) as r:
                        return r.read().decode("utf-8", errors="replace")
                except Exception:
                    return ""
        return blob.decode("utf-8", errors="replace")
    return str(blob)


def varint(raw, pos):
    val, shift = 0, 0
    while pos < len(raw):
        b = raw[pos]; pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, pos
        shift += 7
        if shift > 63:
            raise ValueError
    raise ValueError


def iter_fields(raw):
    i, n = 0, len(raw)
    while i < n:
        tag, i = varint(raw, i)
        fno, wt = tag >> 3, tag & 7
        if wt == 0:
            _, i = varint(raw, i)
        elif wt == 2:
            sz, i = varint(raw, i)
            yield fno, raw[i:i+sz]; i += sz
        elif wt == 1: i += 8
        elif wt == 5: i += 4
        else: raise ValueError


BAD_NICK_KEYWORDS = ("微信红包", "拍了拍", "加入群聊", "邀请你", "领取红包", "http", "@chatroom")


def looks_like_username(s):
    return bool(re.match(r"^(wxid_[A-Za-z0-9_-]+|[A-Za-z][A-Za-z0-9_-]{5,40}|gh_[A-Za-z0-9_-]+|.*@chatroom)$", s))


def sane_nick(s):
    if not s:
        return False
    if len(s) > 48 or len(s.strip()) == 0:
        return False
    if any(k in s for k in BAD_NICK_KEYWORDS):
        return False
    if looks_like_username(s):
        return False
    if s in ("：", ":", "…", "...", "。"):
        return False
    return True


def group_nicknames(chatroom):
    """ext_buffer: field1=成员username field2=群名片；带严格校验防错位"""
    con = sqlite3.connect(CONTACT_DB)
    row = con.execute("SELECT ext_buffer FROM chat_room WHERE username=?", (chatroom,)).fetchone()
    con.close()
    out = {}
    if not row or not row[0]:
        return out
    ext = bytes(row[0])
    try:
        for _, chunk in iter_fields(ext):
            try:
                fields = list(iter_fields(chunk))
            except Exception as e:
                logging.warning("群 %s: ext_buffer 成员块 protobuf 解析失败，跳过该块: %s: %r", chatroom, type(e).__name__, e)
                continue
            user, nick = None, None
            for fno, val in fields:
                if fno == 1 and user is None:
                    try:
                        u = val.decode("utf-8")
                        if looks_like_username(u):
                            user = u
                    except Exception as e:
                        logging.warning("群 %s: ext_buffer 字段1(成员username) 解码失败: %s: %r", chatroom, type(e).__name__, e)
                elif fno == 2 and nick is None:
                    try:
                        nick = val.decode("utf-8")
                    except Exception as e:
                        logging.warning("群 %s: ext_buffer 字段2(群名片) 解码失败: %s: %r", chatroom, type(e).__name__, e)
                        nick = None
            if user and sane_nick(nick):
                out[user] = nick
    except Exception as e:
        logging.warning("群 %s: ext_buffer 整体解析失败，群名片可能不完整: %s: %r", chatroom, type(e).__name__, e)
    return out


def contact_names():
    con = sqlite3.connect(CONTACT_DB)
    m = {u: (nick or alias or remark or u) for u, nick, alias, remark in
         con.execute("SELECT username, nick_name, alias, remark FROM contact")}
    con.close()
    return m


def name2id_map(db):
    con = sqlite3.connect(db)
    m = {rid: u for rid, u in con.execute("SELECT rowid, user_name FROM Name2Id")}
    con.close()
    return m


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
    for gname, room in GROUPS.items():
        table = "Msg_" + hashlib.md5(room.encode()).hexdigest()
        nicks = group_nicknames(room)
        names = contact_names()
        rows = {}
        for db in MSG_DBS:
            con = sqlite3.connect(db)
            n2i = name2id_map(db)
            tabs = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if table not in tabs:
                con.close(); continue
            q = con.execute(f'SELECT server_id, real_sender_id, create_time, local_type, message_content FROM "{table}"')
            for server_id, sid, ts, ltype, content in q:
                if server_id in rows:
                    continue
                rows[server_id] = (sid, ts, ltype, decode_content(content), n2i)
            con.close()
        # 输出
        out_rows = []
        for server_id, (sid, ts, ltype, content, n2i) in rows.items():
            wxid = n2i.get(sid, f"#{sid}")
            disp = nicks.get(wxid) or names.get(wxid) or wxid
            out_rows.append((int(ts), wxid, disp, int(ltype), content))
        out_rows.sort(key=lambda r: r[0])
        path = os.path.join(DATA_DIR, f"{gname}.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time", "wxid", "display_name", "type", "content"])
            for ts, wxid, disp, ltype, content in out_rows:
                w.writerow([datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                            wxid, disp, ltype, content.replace("\n", "␤")[:2000]])
        print(f"{gname}: {len(out_rows)} 条消息 -> {path}")
        senders = {}
        for ts, wxid, disp, ltype, content in out_rows:
            senders[disp] = senders.get(disp, 0) + 1
        top = sorted(senders.items(), key=lambda x: -x[1])[:12]
        print("  发言 Top12:", ", ".join(f"{d}:{c}" for d, c in top))


if __name__ == "__main__":
    main()
