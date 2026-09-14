"""群聊统计：发言条数饼状图 + 话题分析"""
import csv, json, re, collections, datetime
import jieba
import jieba.analyse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

# 中文字体（加 emoji 回退）
font_manager.fontManager.addfont(r"C:\Windows\Fonts\msyh.ttc")
font_manager.fontManager.addfont(r"C:\Windows\Fonts\seguiemj.ttf")
plt.rcParams["font.family"] = ["Microsoft YaHei", "Segoe UI Emoji"]
plt.rcParams["axes.unicode_minus"] = False

STOP = set("""的 了 是 我 你 他 她 它 我们 你们 他们 他们 在 有 和 就 不 都 一 也 上 又 没 很 到 说 要 去 会 着 看 好 自 己 这 那 啊 呢 吧 吗 嗯 哦 噢 呀 哈 嘿 么 什么 怎么 这个 那个 现在 但是 因为 所以 还是 已经 可以 就是 不是 还是 时候 这样 那样 一个 一些 没有 大家 你们 咱们 哈哈 哈哈哈哈 哈哈哈哈 嗯嗯 好的 好吧 行吧 来 我去 真的 感觉 知道 觉得 应该 可能 或者 如果 虽然 然后 不过 而是 这些 那些 自己 大家 东西 地方 问题 直接 其实 果然 居然 另外 此外 比如 例如 等等 之类 左右 大概 也许 恐怕 的确 确定 一定 一起 一下 一直 一定 一般 一样 每次 每次 有时 经常 总是 从来 刚刚 刚才 马上 立刻 正在 刚刚 现在 以后 以前 最近 最早 最后 首先 其次 然后 接着 最后 另外 结果 于是 因此 总之 反正 确实 完全 特别 非常 十分 挺 太 最 更 比较 略 有点 有些 各种 直接 互相 一起 分别 各自 另外 共同 一起 自己 别人 他人 大家 众人 全部 所有 一切 任何 每 各 凡 唯 只有 只是 仅是 不过 是但 可是 然而 却 倒 倒是 其实 吧啦 呗 咯 喽 啦 咧 哟 喔 噶 咯 呗 咯. 图片 表情 语音 视频 红包 转账 消息 回复 转发 分享 链接 文件 群聊 群里 群友 群主 管理 群管理 哈哈 嘿嘿 呵呵 嘻嘻 呜呜 呜啊啊 emsp nbsp""".split())

emoji_re = re.compile(r"\[[\u4e00-\u9fa5A-Za-z]{1,8}\]")
wxid_re = re.compile(r"^[a-z0-9]{10,30}$")
at_re = re.compile(r"@[^\s@，。！？、\n]{1,30}")
xml_re = re.compile(r"<[^>]{1,200}>")
url_re = re.compile(r"https?://\S+")


def clean_text(t):
    t = xml_re.sub(" ", t)
    t = url_re.sub(" ", t)
    t = at_re.sub(" ", t)   # @提及（含 wxid）
    t = emoji_re.sub(" ", t)
    return t


def is_junk(tok):
    if len(tok) >= 10 and wxid_re.fullmatch(tok):
        return True
    if "wxid" in tok or "gh_" in tok:
        return True
    if re.fullmatch(r"[A-Za-z]+[0-9]+[A-Za-z0-9]*", tok) and len(tok) >= 12:
        return True
    return (tok in STOP or len(tok) < 2 or tok.isdigit() or not re.search(r"[\u4e00-\u9fa5A-Za-z]", tok)
            or emoji_re.fullmatch(tok))


def load(name):
    rows = []
    with open(rf"D:\code\wechat-analysis\data\{name}.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def label_of(wxid, disp, used):
    d = disp.strip() or "(未设置昵称)"
    if d in used and used[d] != wxid:
        d = f"{d}({wxid[-4:]})"
    used[d] = wxid
    return d


def pie(name, rows):
    counts = collections.Counter()
    disp_of = {}
    for r in rows:
        wxid = r["wxid"]
        counts[wxid] += 1
        disp_of[wxid] = r["display_name"]
    total = sum(counts.values())
    used = {}
    items = sorted(counts.items(), key=lambda x: -x[1])
    TOPN = 14
    top = items[:TOPN]
    other = items[TOPN:]
    labels = [label_of(wx, disp_of[wx], used) for wx, _ in top]
    sizes = [c for _, c in top]
    if other:
        labels.append(f"其他({len(other)}人)")
        sizes.append(sum(c for _, c in other))
    colors = plt.cm.tab20.colors + plt.cm.tab20b.colors
    fig, ax = plt.subplots(figsize=(11.5, 8.5))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct=lambda p: f"{p:.1f}%\n({int(round(p*total/100))}条)",
        startangle=90, counterclock=False, colors=colors[:len(sizes)],
        textprops={"fontsize": 10}, pctdistance=0.78, labeldistance=1.06)
    for t in autotexts:
        t.set_fontsize(8)
    tmin = min(r["time"] for r in rows)
    tmax = max(r["time"] for r in rows)
    ax.set_title(f"“{name}”群 成员发言条数占比\n总计 {total:,} 条 · {tmin[:10]} ~ {tmax[:10]} · 发言成员 {len(items)} 人",
                 fontsize=15, pad=18)
    ax.axis("equal")
    out = rf"D:\code\wechat-analysis\data\{name}_pie.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[pie] {out}")
    return counts, disp_of, (tmin, tmax)


N_TOPICS = {"up": 8, "2537": 8, "DDBg": 4, "苟富贵毋相忘": 5, "机机交流群": 7}
MIN_DF = {"up": 8, "2537": 8, "DDBg": 4, "苟富贵毋相忘": 5, "机机交流群": 6}


def topics(name, rows, n_topics=8):
    texts = []
    for r in rows:
        if r["type"] == "1":
            t = clean_text(r["content"]).strip()
            if len(t) >= 4:
                texts.append(t)
    print(f"[topics] {name}: 文本消息 {len(texts)} 条")
    n_topics = N_TOPICS.get(name, 8)
    toks = [" ".join(w for w in jieba.cut(t) if not is_junk(w)) for t in texts]
    toks = [t for t in toks if t.strip()]
    tf = CountVectorizer(max_df=0.6, min_df=MIN_DF.get(name, 8), max_features=30000, token_pattern=r"\S+")
    X = tf.fit_transform(toks)
    lda = LatentDirichletAllocation(n_components=n_topics, max_iter=20, learning_method="online",
                                    random_state=42, n_jobs=-1)
    lda.fit(X)
    words = tf.get_feature_names_out()
    result = []
    for k, comp in enumerate(lda.components_):
        top_idx = comp.argsort()[::-1][:12]
        result.append([words[i] for i in top_idx])
    # 全局关键词
    corpus = " ".join(toks)
    kw = jieba.analyse.extract_tags(corpus, topK=30, withWeight=True)
    return result, kw, len(texts)


for gname in ["up", "2537", "DDBg", "苟富贵毋相忘", "机机交流群"]:
    rows = load(gname)
    counts, disp_of, trange = pie(gname, rows)
    tp, kw, n_text = topics(gname, rows)
    data = {
        "group": gname,
        "total": len(rows),
        "time_range": trange,
        "members": len(counts),
        "text_msgs": n_text,
        "ranking": [(disp_of.get(wx, wx), c) for wx, c in counts.most_common()],
        "keywords": [[w, round(s, 4)] for w, s in kw],
        "topics": tp,
    }
    with open(rf"D:\code\wechat-analysis\data\{gname}_stats.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"[done] {gname}: 关键词 top10 =", "、".join(w for w, _ in kw[:10]))
    for i, t in enumerate(tp):
        print(f"  话题{i+1}: " + " / ".join(t[:10]))
