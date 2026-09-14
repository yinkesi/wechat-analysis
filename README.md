# 微信聊天记录提取与分析工具链

本机微信 4.1.13（Windows）聊天记录的提取、解密、统计一套流程。
生成于 2026-09-14，统计目标：群「up」与「2537」。

## 交付物

| 文件 | 说明 |
|---|---|
| `微信群聊分析报告.html` | 最终报告（饼图 + 完整排行 + 关键词 + 话题聚类） |
| `data/up_pie.png` `data/2537_pie.png` | 每人群成员发言条数饼状图 |
| `data/up.csv` `data/2537.csv` | 两个群的全量消息（时间/发言人/类型/内容） |
| `data/*_stats.json` | 排行、关键词、话题的机器可读结果 |
| `decrypted/v4/` | 解密后的全部 23 个数据库（SQLite 可直接打开） |

## 流水线（可复跑）

```
1. getkey.py        密钥提取 + 全库解密
   ├─ scan.py 特征码扫 Weixin.dll 提取内嵌 XOR key（来自 WeChatDataAnalysis）
   ├─ key_v4.py YARA 扫微信进程内存取 raw key（同上）
   ├─ passphrase = raw_key XOR internal_db_key
   ├─ 每库 AES key = PBKDF2-SHA512(passphrase, salt, 256000)
   └─ 逐页 AES-CBC 解密（SQLCipher4, page=4096, reserve=80）
2. extract_groups.py  定位群（contact.db: nick_name→username@chatroom→Msg_md5 表），
                      zstd 解压消息内容，解析群名片（chat_room.ext_buffer protobuf）
3. analyze.py         发言计数饼图（matplotlib）+ jieba/TF-IDF/LDA 话题
4. report.py          汇总 HTML
```

依赖：`pip install pycryptodome pymem yara-python pefile zstandard jieba matplotlib scikit-learn`
运行前提：微信正在本机登录（密钥在进程内存里），Python 3.12。

## 使用的开源项目

- **LifeArchiveProject/WeChatDataAnalysis**（⭐2.7k，2026-09 仍在维护）——4.x 密钥提取技术（DLL 特征码 + YARA 内存扫描 + PBKDF2 256000 轮派生）
- **jiangsheng-lab/wx2base**（2026-09 更新）——4.x SQLCipher 参数与解密实现参考
- **xiaozhang959/chatlog**（sjzar/chatlog 下架前 fork，2025-10 快照）——已编译为 `chatlog.exe` 备用；本机 4.1.13 用其老方案取不到 key，最终未走此路

## 注意

- 仅用于备份/分析**自己设备、自己账号**的数据；请勿用于侵犯他人隐私或商业用途。
- 微信更新可能改变密钥方案导致流程失效（2026-01 腾讯曾对同类工具发起 DMCA 维权潮）。
- 未解密 `-wal` 文件，最近未落盘的少量消息可能缺失。
