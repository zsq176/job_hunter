"""新用户引导 Tool —— 首次安装后自动检测配置状态，引导用户完成设置"""
import os
import sys
import logging
from pathlib import Path
from config import PROJECT_ROOT, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL

logger = logging.getLogger("tools.setup")

BOSS_AGENT_CLI_INSTALLED = False
try:
    import boss_agent_cli  # noqa: F401
    BOSS_AGENT_CLI_INSTALLED = True
except ImportError:
    pass


def _check_command(cmd: str) -> bool:
    """检查系统命令是否可用"""
    import shutil
    return shutil.which(cmd) is not None


def setup_status() -> dict:
    """检测各项配置的完成状态，返回整体进度和待办列表"""
    env_file = PROJECT_ROOT / ".env"
    env_exists = env_file.exists()
    has_api_key = bool(LLM_API_KEY)
    has_boss_cli = BOSS_AGENT_CLI_INSTALLED
    has_node = _check_command("node")
    has_chrome = _check_command("chrome") or _check_command("google-chrome") or _check_command("chromium")

    db_path = Path(os.getenv("DB_PATH", str(PROJECT_ROOT / "data" / "boss_hunter.db")))
    db_exists = db_path.exists()

    from db.client import Database
    db = Database()
    prefs = db.get_all_preferences()
    has_preferences = bool(prefs)
    resume = db.get_active_resume()
    has_resume = bool(resume)

    try:
        ops_status = {"logged_in": False}
        if has_boss_cli:
            from browser.operator import BossOperator
            ops = BossOperator()
            ops_status = ops.check_status()
        logged_in = ops_status.get("logged_in", False)
    except Exception:
        logged_in = False

    steps = [
        {
            "step": "python_env",
            "label": "Python 环境",
            "description": "Python 3.10+ 运行环境",
            "status": "ok" if sys.version_info >= (3, 10) else "error",
            "detail": f"Python {sys.version}",
            "action": "需要安装 Python 3.10+：https://www.python.org/downloads/",
        },
        {
            "step": "node_env",
            "label": "Node.js 环境",
            "description": "运行 MCP Agent 需要 Node.js 18+",
            "status": "ok" if has_node else "warn",
            "detail": "已安装" if has_node else "未检测到",
            "action": "安装 Node.js 18+：https://nodejs.org/",
        },
        {
            "step": "chrome",
            "label": "Chrome 浏览器",
            "description": "Boss直聘登录需要本地 Chrome 浏览器",
            "status": "ok" if has_chrome else "warn",
            "detail": "已检测到" if has_chrome else "未检测到",
            "action": "安装 Chrome：https://www.google.com/chrome/",
        },
        {
            "step": "boss_cli",
            "label": "boss-agent-cli",
            "description": "Boss直聘 SDK，提供浏览器自动化与 API 封装",
            "status": "ok" if has_boss_cli else "error",
            "detail": "已安装" if has_boss_cli else "未安装",
            "action": "pip install boss-agent-cli && patchright install chromium",
        },
        {
            "step": "env_file",
            "label": ".env 配置文件",
            "description": "存储 LLM API Key 等环境变量",
            "status": "ok" if env_exists else "error",
            "detail": "已存在" if env_exists else "未创建",
            "action": "cp .env.example .env  然后编辑 .env 填入 LLM_API_KEY",
        },
        {
            "step": "api_key",
            "label": "LLM API Key",
            "description": f"DeepSeek/OpenAI 兼容 API Key（当前模型: {LLM_MODEL}）",
            "status": "ok" if has_api_key else "error",
            "detail": ("已配置" if has_api_key else "未配置") + f" → {LLM_BASE_URL}",
            "action": "编辑 .env 文件，设置 LLM_API_KEY=sk-your-key。获取地址: https://platform.deepseek.com/api_keys",
        },
        {
            "step": "login",
            "label": "Boss直聘登录",
            "description": "登录后即可搜索岗位、发送打招呼",
            "status": "ok" if logged_in else ("warn" if has_api_key and has_boss_cli else "pending"),
            "detail": "已登录" if logged_in else "未登录",
            "action": "使用 boss_login 工具登录（支持自动/扫码/Cookie）",
        },
        {
            "step": "preferences",
            "label": "求职意向",
            "description": "城市、薪资范围、关键词等偏好设置",
            "status": "ok" if has_preferences else ("warn" if has_api_key else "pending"),
            "detail": f"已保存 {len(prefs)} 项" if has_preferences else "未设置",
            "action": "使用 preference_save 工具设置求职意向",
        },
        {
            "step": "resume",
            "label": "简历上传",
            "description": "上传简历后可使用匹配评分和话术生成",
            "status": "ok" if has_resume else ("warn" if has_api_key else "pending"),
            "detail": "已上传" if has_resume else "未上传",
            "action": "使用 resume_analyze 工具上传并分析简历",
        },
    ]

    status_counts = {"ok": 0, "warn": 0, "error": 0, "pending": 0}
    for s in steps:
        status_counts[s["status"]] = status_counts.get(s["status"], 0) + 1
    total = len(steps)
    completed = status_counts["ok"]
    ready = completed + status_counts["warn"]

    return {
        "ok": True,
        "summary": {
            "total_steps": total,
            "completed": completed,
            "ready": ready,
            "percent": round(completed / total * 100),
            "is_ready": status_counts["error"] == 0,
            "can_search": has_api_key and has_boss_cli and logged_in,
            "can_match": has_api_key and has_resume,
            "can_greet": has_api_key and has_boss_cli and logged_in and has_resume,
        },
        "steps": steps,
        "next_actions": [s["action"] for s in steps if s["status"] in ("error", "warn")][:3],
    }


def setup_guide(topic: str = "all") -> dict:
    """获取指定步骤的详细操作指南。topic: all/apikey/login/preferences/resume/agent"""
    guides = {
        "all": """# Job Hunter 安装配置指南

## 1. 安装依赖
```bash
pip install boss-agent-cli
patchright install chromium
pip install -r requirements.txt
```

## 2. 配置 LLM API Key
```bash
cp .env.example .env
# 编辑 .env，填入: LLM_API_KEY=sk-your-key
```
获取 DeepSeek Key: https://platform.deepseek.com/api_keys

## 3. 配置 MCP Agent
根据你使用的 Agent，在配置文件中注册:

### OpenClaw / Claude Code / OpenCode / Cline
```json
{"mcpServers": {"job-hunter": {"command": "python", "args": ["<路径>/server.py"]}}}
```

所有兼容 Agent 使用相同的 Stdio MCP 配置格式。

## 4. 首次对话
配置完成后重启 Agent，对话中说:
- "帮我检查一下配置状态" → 调用 setup_status
- "设置求职意向" → 调用 preference_save
- "登录 Boss直聘" → 调用 boss_login
""",

        "apikey": """## 获取 LLM API Key

### DeepSeek（推荐，国内可访问）
1. 打开 https://platform.deepseek.com/api_keys
2. 注册/登录，创建 API Key
3. 复制 Key，在项目 .env 中设置: LLM_API_KEY=sk-xxx
4. 新用户通常有免费额度

### OpenAI / 其他兼容接口
1. 设置 LLM_BASE_URL=https://api.openai.com/v1
2. 设置 LLM_MODEL=gpt-4o-mini
3. 设置 LLM_API_KEY=sk-xxx
""",

        "login": """## Boss直聘登录方式

支持 4 种登录方式（自动降级）:
- `auto` — 先尝试 Cookie，失败则触发 CDP 扫码
- `cookie` — 从已登录的 Chrome 浏览器提取 Cookie（需日常使用 Chrome 登录过 Boss）
- `cdp` — 通过 CDP 协议打开浏览器扫码登录
- `status` — 仅检查当前登录状态

首次使用建议: 说 "用扫码方式登录 Boss直聘"
""",

        "preferences": """## 求职意向配置

使用 preference_save 工具保存配置，支持的字段:
- `cities`: 目标城市列表，如 ["北京", "上海", "广州"]
- `salary_min` / `salary_max`: 期望薪资范围(K)，如 15 / 30
- `keywords_must`: 必修关键词，如 ["Python", "后端"]
- `keywords_bonus`: 加分关键词，如 ["Docker", "Kubernetes"]
- `blacklist`: 排除词，如 ["外包", "单休"]
- `welfare`: 福利要求，如 ["五险一金", "双休"]

示例对话: "设置求职意向：杭州和北京，15-30K，Python后端，排除外包"
""",

        "resume": """## 上传简历

直接在对话中粘贴简历文本:
- "帮我分析这份简历：[粘贴简历内容]"
- 系统会自动缓存，后续匹配和话术生成都基于此版本
- 支持重复上传（修改后再次粘贴即可，自动版本管理）
""",

        "agent": """## 兼容的 MCP Agent

| Agent | 配置文件位置 |
|-------|-------------|
| **OpenClaw** | `openclaw.json` → `mcpServers` |
| **Claude Code** | `~/.claude/claude_desktop_config.json` 或 `.claude/mcp.json` → `mcpServers` |
| **OpenCode** | `opencode.json` → `mcpServers`，支持 `/install https://github.com/zsq176/job_hunter` 一键安装 |
| **Cline** | VSCode 扩展设置 → MCP Server |

通用配置格式（Stdio MCP）:
```json
{
  "mcpServers": {
    "job-hunter": {
      "command": "python",
      "args": ["<项目路径>/job_hunter/server.py"]
    }
  }
}
```
""",
    }

    topic = topic if topic in guides else "all"
    content = guides[topic].strip()

    return {
        "ok": True,
        "topic": topic,
        "content": content,
        "available_topics": list(guides.keys()),
    }
