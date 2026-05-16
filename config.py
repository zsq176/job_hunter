"""配置加载模块"""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")

DB_PATH = os.getenv("DB_PATH", str(PROJECT_ROOT / "data" / "boss_hunter.db"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

BOSS_DATA_DIR = PROJECT_ROOT / "data"

# ── 匹配评分配置 ──
MATCH_CITY_SCORE = int(os.getenv("MATCH_CITY_SCORE", "25"))
MATCH_SALARY_SCORE = int(os.getenv("MATCH_SALARY_SCORE", "25"))
MATCH_MUST_KEYWORD_SCORE = int(os.getenv("MATCH_MUST_KEYWORD_SCORE", "5"))
MATCH_BONUS_KEYWORD_SCORE = int(os.getenv("MATCH_BONUS_KEYWORD_SCORE", "3"))
MATCH_WELFARE_SCORE = int(os.getenv("MATCH_WELFARE_SCORE", "3"))
MATCH_KEYWORD_CAP = int(os.getenv("MATCH_KEYWORD_CAP", "15"))
MATCH_WELFARE_CAP = int(os.getenv("MATCH_WELFARE_CAP", "10"))
MATCH_RULE_LLM_THRESHOLD = int(os.getenv("MATCH_RULE_LLM_THRESHOLD", "50"))
MATCH_RULE_WEIGHT = float(os.getenv("MATCH_RULE_WEIGHT", "0.3"))
MATCH_LLM_WEIGHT = float(os.getenv("MATCH_LLM_WEIGHT", "0.7"))
MATCH_PASS_THRESHOLD = int(os.getenv("MATCH_PASS_THRESHOLD", "55"))
MATCH_HIGH_SCORE = int(os.getenv("MATCH_HIGH_SCORE", "70"))

# ── 打招呼配置 ──
DAILY_GREET_LIMIT = int(os.getenv("DAILY_GREET_LIMIT", "50"))
GREET_INTERVAL_MIN = float(os.getenv("GREET_INTERVAL_MIN", "10"))
GREET_INTERVAL_MAX = float(os.getenv("GREET_INTERVAL_MAX", "30"))
GREET_BATCH_SIZE = int(os.getenv("GREET_BATCH_SIZE", "10"))
GREET_BATCH_REST = int(os.getenv("GREET_BATCH_REST", "300"))

# ── LLM 配置 ──
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
