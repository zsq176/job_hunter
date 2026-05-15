"""配置加载模块"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

# LLM 配置
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")

# 数据库
DB_PATH = os.getenv("DB_PATH", str(PROJECT_ROOT / "data" / "boss_hunter.db"))

# 运行模式
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Boss直聘 cookie 存储目录
BOSS_DATA_DIR = PROJECT_ROOT / "data"
