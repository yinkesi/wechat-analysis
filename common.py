"""跨脚本共享的小工具：CSV 读取与消息文本清洗。"""
import csv
import re

# 微信表情 [xx]、wxid 形态 token、@提及、XML 片段、URL
emoji_re = re.compile(r"\[[\u4e00-\u9fa5A-Za-z]{1,8}\]")
wxid_re = re.compile(r"^[a-z0-9]{10,30}$")
at_re = re.compile(r"@[^\s@，。！？、\n]{1,30}")
xml_re = re.compile(r"<[^>]{1,200}>")
url_re = re.compile(r"https?://\S+")


def load_csv(path):
    """读取 UTF-8-SIG 编码的 CSV，返回字典列表。"""
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def clean_text(t, drop=False, strip=False):
    """清洗消息文本：去掉 XML 片段、URL、@提及、[xx] 表情。

    drop=False（默认）：命中处替换为单个空格 —— 用于分词/话题分析，避免词粘连；
    drop=True：命中处直接删除 —— 用于报告展示。
    strip=True 时额外去除首尾空白。
    """
    repl = "" if drop else " "
    t = xml_re.sub(" ", t)
    t = url_re.sub(" ", t)
    t = at_re.sub(repl, t)
    t = emoji_re.sub(repl, t)
    return t.strip() if strip else t
