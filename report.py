"""生成最终 HTML 报告"""
import json, base64, csv, re, collections, datetime, random

random.seed(7)
emoji_re = re.compile(r"\[[\u4e00-\u9fa5A-Za-z]{1,8}\]")


def b64img(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def load(name):
    with open(rf"D:\code\wechat-analysis\data\{name}_stats.json", encoding="utf-8") as f:
        return json.load(f)


def load_rows(name):
    with open(rf"D:\code\wechat-analysis\data\{name}.csv", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


TOPIC_LABELS = {
    "up": ["英雄与皮肤讨论", "KPL 强强对话（ag/ksg）", "巅峰赛与队友吐槽", "狼队、wb 观赛夜",
           "对局细节与名场面", "王者荣耀·KPL 赛季话题", "组排开黑与冲分", "英雄打法（马超/中路）"],
    "2537": ["军训生活", "课业与考试（早八/期末）", "同学日常吐槽", "高中回忆与感情话题",
             "作业与明天赶due", "大学生活感受", "校园·宿舍·高数", "互勉与日常沙雕"],
    "DDBg": ["游戏·VPN·开宇杂聊", "氪金攻略与手机（ds/模型）", "AI 话题与日常闲聊", "学校日常与吃喝"],
    "苟富贵毋相忘": ["晚上·周末约时间", "复旦·codex·蛋糕", "约饭与周末出行", "研究方向闲聊（开宇/贤崇）", "学校·上海日常"],
    "机机交流群": ["项目 bug 与测试", "AI 配置与 agent（flash）", "Claude 代码与 skill", "插件更新与使用",
                  "模型订阅（gpt/kimi）", "DeepSeek·服务器·价格", "Codex/opencode 额度与重置"],
}
GROUPS = ["up", "2537", "DDBg", "苟富贵毋相忘", "机机交流群"]


def clean(t):
    t = emoji_re.sub("", t)
    t = re.sub(r"@[^\s@，。！？、\n]{1,30}", "", t)
    t = re.sub(r"<[^>]{1,200}>", " ", t)
    t = re.sub(r"https?://\S+", " ", t)
    return t.strip()


def fmt_range(tr):
    return f"{tr[0][:10]} ~ {tr[1][:10]}"


def group_section(g):
    d = load(g)
    rows = load_rows(g)
    total, tr, mem = d["total"], d["time_range"], d["members"]
    ranking = d["ranking"]
    kw = d["keywords"]
    topics = d["topics"]
    labels = TOPIC_LABELS[g]

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

    # 最活跃的一天 & 时段
    days = collections.Counter(r["time"][:10] for r in rows)
    top_day, top_day_n = days.most_common(1)[0]
    hours = collections.Counter(int(r["time"][11:13]) for r in rows)
    peak_hour = hours.most_common(1)[0]

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
<img class="pie" src="{b64img(rf'D:\code\wechat-analysis\data\{g}_pie.png')}">
<h3>发言条数完整排行</h3>
<table class="rank"><tr><th>#</th><th>成员</th><th>条数</th><th>占比</th></tr>{rank_rows}</table>
<h3>话题分析</h3>
<p class="kw"><b>高频词 Top30：</b>{kw_str}</p>
<div class="topics">{topic_html}</div>
"""


stats = {g: load(g) for g in GROUPS}
rows_all = {g: load_rows(g) for g in GROUPS}
ids = {g: {r["wxid"] for r in rows_all[g]} for g in GROUPS}
common_all = set.intersection(*ids.values())
header = " &nbsp;·&nbsp; ".join(
    f"<b>{g}</b>（{stats[g]['total']:,} 条）" for g in GROUPS)

sections = "".join(group_section(g) for g in GROUPS)

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
<h2>五群对比小结</h2>
<ul>
<li><b>up 群</b>：话题高度聚焦 <b>王者荣耀 / KPL 电竞</b>——战队（AG、狼队、TTG、WB、KSG）、选手（一诺）、位置与英雄（打野、射手、马超、钟馗）刷屏；发言集中度高，第一名 刘鲁豪 一人占 22.5%，前 4 人合计过半，是典型的"核心老哥带节奏"群。</li>
<li><b>2537 群</b>：<b>大学生活群</b>——军训、上课、考试、作业、高数、早八、宿舍、放假是主线，夹杂 武汉/长沙/NUDT 等地点与学校梗；发言分散，40 人发言、前 3 名各占 8%~12%，是全员闲聊型班级群。</li>
<li><b>DDBg 群</b>：5 人小群，游戏（含氪金攻略）、VPN、AI 模型杂聊；音克思... 与 只因... 两人合计占 64.6%。</li>
<li><b>苟富贵毋相忘 群</b>：5 人挚友群（群名出自陈胜典故），主题是<b>约饭、周末聚会</b>（蛋糕、复旦、上海）兼聊 codex/AI 与研究方向；音克思... 41.7% 为主心骨。</li>
<li><b>机机交流群 群</b>：2026-06-08 建群，三个月聊了 6,136 条，密度最高。纯粹的 <b>AI 工具/编程交流群</b>——codex、opencode、claude、gpt、deepseek(ds)、token 额度、插件、订阅价格；'...'、'：'、音克思... 三人合计 95.4%。</li>
<li>昵称极简（"..."、"："、emoji）不影响统计——全部按账号 ID 去重。</li>
</ul>
<h2>工具与流程</h2>
<p><small>1) 密钥：Weixin.dll 内嵌 XOR key（<a href="https://github.com/LifeArchiveProject/WeChatDataAnalysis">LifeArchiveProject/WeChatDataAnalysis</a> 的 scan.py 特征码）⊕ 进程内存 YARA 扫描 raw key → PBKDF2-SHA512×256000 派生；2) 解密：AES-CBC 逐页（参数参考 <a href="https://github.com/jiangsheng-lab/wx2base">jiangsheng-lab/wx2base</a>）；3) 解析：contact.db / message_*.db（会话分表 Msg_md5，zstd 压缩内容）；4) 分析：jieba 分词 + TF-IDF 关键词 + LDA 主题模型，matplotlib 饼图。全流程脚本在 D:\\code\\wechat-analysis\\。</small></p>
</body></html>"""

out = r"D:\code\wechat-analysis\微信群聊分析报告.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("report ->", out)
