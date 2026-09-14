"""集中配置。

本文件入库，只含占位默认值（相对路径 / 空字符串 / 空表结构）。
个人 wxid、群 chatroom ID、本机绝对路径等敏感信息一律放 `config_local.py`
（已被 .gitignore 忽略，不会提交）。首次使用请复制 `config_local.example.py`
为 `config_local.py` 并填入本机值 —— import 时它会覆盖本文件的同名变量。
"""
import os

# 仓库根目录（所有相对路径默认相对此处）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- 目录（默认相对仓库根；与现有脚本布局一致） ----
DATA_DIR = os.path.join(BASE_DIR, "data")                # CSV / PNG / JSON 产物
DECRYPTED_DIR = os.path.join(BASE_DIR, "decrypted", "v4")  # 解密后的 SQLite
DECRYPTED_ROOT = os.path.join(BASE_DIR, "decrypted")     # 解密输出根目录
OUT_DIR = DECRYPTED_DIR                                  # getkey.py 解密输出目录
EXTRACT_OUT_DIR = os.path.join(DECRYPTED_ROOT, "extract_out")  # extract.py（已废弃）输出目录
REPORT_HTML = os.path.join(BASE_DIR, "微信群聊分析报告.html")

# ---- 微信相关（占位；真实值见 config_local.py） ----
WDA_DIR = ""     # WeChatDataAnalysis 仓库本地路径（含 scan.py / key_v4.py）
WX2BASE_DIR = ""  # wx2base 仓库本地路径（含 wx_decrypt_v4.py）
DLL_PATH = ""    # 本机微信 Weixin.dll 完整路径
WX_DB_DIR = ""   # 微信本地 db_storage 目录（路径含个人 wxid，勿入库）

# ---- matplotlib 中文字体（占位；Windows 默认值见 config_local.py） ----
FONT_MAIN = ""   # 中文字体，如 msyh.ttc
FONT_EMOJI = ""  # emoji 回退字体，如 seguiemj.ttf

# ---- 密钥缓存（含密钥材料，已被 .gitignore 忽略，勿入库） ----
KEY_RESULT_FILE = os.path.join(BASE_DIR, "key_result.json")

# ---- 群列表：群名 -> chatroom ID（真实值在 config_local.py，保持插入顺序） ----
# 示例:
# GROUPS = {
#     "示例群A": "12345678901@chatroom",
#     "示例群B": "10987654321@chatroom",
# }
GROUPS = {}

# ---- 每群分析参数（键为群名） ----
N_TOPICS = {}  # 群名 -> LDA 话题数
MIN_DF = {}    # 群名 -> CountVectorizer min_df

# ---- 话题展示标签：群名 -> 话题标签列表（展示层配置，与 TOPIC 对齐） ----
TOPIC_LABELS = {}

# 报告「五群对比小结」正文（HTML <ul>…</ul>）；内容因群而异且常含群内昵称，放 config_local
GROUP_SUMMARY = ""

# ---- 本机私有覆盖：不存在则静默跳过 ----
try:
    from config_local import *  # noqa: F401,F403
except ImportError:
    pass
