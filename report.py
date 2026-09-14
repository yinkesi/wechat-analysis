"""生成最终 HTML 报告"""
import base64
import collections
import datetime
import json
import os

from common import clean_text, load_csv
from config import DATA_DIR, GROUP_SUMMARY, GROUPS, REPORT_HTML, TOPIC_LABELS


def b64img(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def load(name):
    with open(os.path.join(DATA_DIR, f"{name}_stats.json"), encoding="utf-8") as f:
        return json.load(f)


def load_rows(name):
    return load_csv(os.path.join(DATA_DIR, f"{name}.csv"))


def clean(t):
    return clean_text(t, drop=True, strip=True)


def fmt_range(tr):
    return f"{tr[0][:10]} ~ {tr[1][:10]}"


def group_section(g):
    d = load(g)
    rows = load_rows(g)
    total, tr, mem = d["total"], d["time_range"], d["members"]
    ranking = d["ranking"]
    kw = d["keywords"]
    topics = d["topics"]
    labels = TOPIC_LABELS.get(g, g)

    # 类型分布
    types = collections.Counter(r["type"] for r in rows)
    type_names = {"1": "文本", "3": "图片", "34": "语音", "43": "视频", "47": "表情包",
                  "48": "位置", "26682": "合并转发"}
    type_str = "、".join(f"{type_names.get(k, '其他')} {v:,}" for k, v in types.most_common(6))

    # 每话题找 2 条代表性消息（含话题 top 词、长度适中）
    samples = []
    for ti, words in enumerate(topics):
        wset = set(words[:6])
        cands = []
        for r in rows:
            if r["type"] != "1":
                continue
            t = clean(r["content"])
            if not (6 <= len(t) <= 60):
                continue
            hit = sum(1 for w in wset if w in t)
            if hit >= 2:
                cands.append((hit, -abs(len(t) - 25), t[:50], r["display_name"]))
        cands.sort(reverse=True)
        seen, picks = set(), []
        for c in cands:
            if c[2] not in seen:
                seen.add(c[2]); picks.append(c)
            if len(picks) == 2:
                break
        samples.append(picks)

    # 最活跃的一天 & 时段（空数据时输出占位，不崩）
    days = collections.Counter(r["time"][:10] for r in rows)
    if days:
        top_day, top_day_n = days.most_common(1)[0]
    else:
        top_day, top_day_n = "（无数据）", 0
    hours = collections.Counter(int(r["time"][11:13]) for r in rows)
    peak_hour = hours.most_common(1)[0] if hours else (0, 0)

    rank_rows = "".join(
        f"<tr><td>{i+1}</td><td>{n}</td><td>{c:,}</td><td>{c/total*100:.1f}%</td></tr>"
        for i, (n, c) in enumerate(ranking))
    kw_str = "、".join(w for w, _ in kw[:30])
    topic_html = ""
    for i, words in enumerate(topics):
        lab = labels[i] if i < len(labels) else f"话题{i+1}"
        ex = "".join(f'<div class="ex">「{t}」 <span class="who">—— {who}</span></div>'
                     for _, _, t, who in (samples[i] if i < len(samples) else []))
        topic_html += f'<div class="topic"><div class="tl">话题{i+1} · {lab}</div><div class="tw">' + \
            " / ".join(words[:10]) + f"</div>{ex}</div>"

    return f"""
<h2>“{g}”群</h2>
<table class="kv">
<tr><td>时间范围</td><td>{fmt_range(tr)}（约 {(datetime.date.fromisoformat(tr[1][:10]) - datetime.date.fromisoformat(tr[0][:10])).days} 天）</td></tr>
<tr><td>消息总数</td><td><b>{total:,}</b> 条（文本 {d['text_msgs']:,}）</td></tr>
<tr><td>发言成员</td><td>{mem} 人</td></tr>
<tr><td>消息类型</td><td>{type_str}</td></tr>
<tr><td>最活跃一天</td><td>{top_day}（{top_day_n:,} 条）</td></tr>
<tr><td>高峰时段</td><td>{peak_hour[0]}:00–{peak_hour[0]+1}:00（{peak_hour[1]:,} 条）</td></tr>
</table>
<img class="pie" src="{b64img(os.path.join(DATA_DIR, f'{g}_pie.png'))}">
<h3>发言条数完整排行</h3>
<table class="rank"><tr><th>#</th><th>成员</th><th>条数</th><th>占比</th></tr>{rank_rows}</table>
<h3>话题分析</h3>
<p class="kw"><b>高频词 Top30：</b>{kw_str}</p>
<div class="topics">{topic_html}</div>
"""


def main():
    stats = {g: load(g) for g in GROUPS}
    rows_all = {g: load_rows(g) for g in GROUPS}
    ids = {g: {r["wxid"] for r in rows_all[g]} for g in GROUPS}
    common_all = set.intersection(*ids.values())
    header = " &nbsp;·&nbsp; ".join(
        f"<b>{g}</b>（{stats[g]['total']:,} 条）" for g in GROUPS)

    sections = "".join(group_section(g) for g in GROUPS)
    group_summary = ("<h2>五群对比小结</h2>\n" + GROUP_SUMMARY) if GROUP_SUMMARY else ""

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>微信群聊统计分析 · 五群</title>
<style>
body{{font-family:"Microsoft YaHei",sans-serif;max-width:960px;margin:24px auto;padding:0 16px;color:#222;line-height:1.6}}
h1{{border-bottom:3px solid #07c160;padding-bottom:8px}}
h2{{color:#07c160;margin-top:40px}} h3{{margin-top:28px}}
table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ddd;padding:6px 10px;font-size:14px}}
.kv td:first-child{{width:120px;background:#f6faf7;font-weight:bold}}
.rank th{{background:#07c160;color:#fff}} .rank td:nth-child(n+3){{text-align:right}}
img.pie{{max-width:100%;border:1px solid #eee;border-radius:8px;margin:12px 0}}
.topics{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.topic{{border:1px solid #e3e8e3;border-radius:8px;padding:10px 14px;background:#fbfdfb}}
.tl{{font-weight:bold;color:#0a7d43}} .tw{{color:#555;font-size:13px;margin:4px 0}}
.ex{{font-size:13px;color:#333;background:#f4f8f4;border-radius:6px;padding:4px 8px;margin:4px 0}}
.who{{color:#999}}
.note{{background:#fff8e6;border-left:4px solid #f0b429;padding:10px 14px;font-size:13px;border-radius:4px}}
small{{color:#888}}
</style></head><body>
<h1>微信群聊统计分析报告</h1>
<p>{header} &nbsp;·&nbsp; 五群都在的成员：<b>{len(common_all)} 人</b>
&nbsp;·&nbsp;生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<div class="note">数据来源：本机微信 4.1.13 本地数据库（SQLCipher）→ 进程内存密钥提取 → 解密 → 解析。
仅含本地已漫游的聊天记录；未包含未从云端同步的历史。仅供个人分析使用。</div>
{sections}
{group_summary}
<h2>工具与流程</h2>
<p><small>1) 密钥：Weixin.dll 内嵌 XOR key（<a href="https://github.com/LifeArchiveProject/WeChatDataAnalysis">LifeArchiveProject/WeChatDataAnalysis</a> 的 scan.py 特征码）⊕ 进程内存 YARA 扫描 raw key → PBKDF2-SHA512×256000 派生；2) 解密：AES-CBC 逐页（参数参考 <a href="https://github.com/jiangsheng-lab/wx2base">jiangsheng-lab/wx2base</a>）；3) 解析：contact.db / message_*.db（会话分表 Msg_md5，zstd 压缩内容）；4) 分析：jieba 分词 + TF-IDF 关键词 + LDA 主题模型，matplotlib 饼图。全流程脚本在本仓库根目录。</small></p>
</body></html>"""

    with open(REPORT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print("report ->", REPORT_HTML)


if __name__ == "__main__":
    main()
