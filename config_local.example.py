"""config_local.py 示例 —— 复制为 config_local.py 并填入本机真实值后再运行。

config_local.py 已被 .gitignore 忽略，其中的个人 wxid、群 chatroom ID、
本机绝对路径不会进入公开仓库。所有键均可省略，省略时使用 config.py 的占位默认值
（目录类默认值相对本仓库根目录）。
"""

# ---- 群列表：群名 -> chatroom ID（插入顺序即报告中的展示顺序） ----
GROUPS = {
    # "示例群A": "12345678901@chatroom",
    # "示例群B": "10987654321@chatroom",
}

# ---- 每群分析参数（键须与 GROUPS 的群名一致；可省略，省略时用默认值 8） ----
N_TOPICS = {}  # 群名 -> LDA 话题数
MIN_DF = {}    # 群名 -> CountVectorizer min_df

# ---- 话题展示标签：群名 -> 话题标签列表（可省略，缺省显示"话题N"） ----
TOPIC_LABELS = {}

# ---- 外部依赖仓库的本地路径（getkey.py 需要，填本机绝对路径） ----
WDA_DIR = ""     # WeChatDataAnalysis 仓库（含 scan.py / key_v4.py）
WX2BASE_DIR = ""  # wx2base 仓库（含 wx_decrypt_v4.py）

# ---- 本机微信 ----
DLL_PATH = ""    # 形如 <微信安装目录>\\Weixin.dll
WX_DB_DIR = ""   # 形如 <微信数据目录>\\<你的wxid>\\db_storage

# ---- matplotlib 中文字体（Windows 默认在 C 盘 Fonts 目录，可按需填写） ----
FONT_MAIN = ""   # 中文字体 .ttc/.ttf 完整路径，如 msyh.ttc 所在路径
FONT_EMOJI = ""  # emoji 回退字体完整路径，如 seguiemj.ttf 所在路径

# ---- extract.py（已废弃备选路径）的解密输出目录；省略则用 config.py 默认值 ----
# EXTRACT_OUT_DIR = ""
