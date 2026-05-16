# Job Hunter

AI 求职助手 —— 通过 MCP 协议将 Boss 直聘自动化求职流程暴露为 Agent 可调用的工具链。

## 项目简介

Job Hunter 是一个 MCP (Model Context Protocol) Server，将 Boss 直聘的岗位搜索、JD 解析、简历匹配、自动打招呼、流水线追踪等功能封装为 15 个标准化 Tool。用户通过自然语言即可驱动 Agent 完成全流程求职操作。

**核心能力**：两阶段匹配评分（规则过滤 + LLM 深度评估）；求职流水线状态机（`new → analyzed → matched → greeted → replied`）全链路可追溯；本地 SQLite 持久化，断连重启不丢数据；SHA-256 简历版本管理。

## 项目架构

```
job_hunter/
├── server.py              # MCP Server 入口，注册 15 个 Tool，asyncio.to_thread 异步调度
├── config.py              # 环境变量加载，评分配置/限流参数可调
├── .env.example           # 配置模板
│
├── tools/                 # MCP Tool 实现层 —— 每个 Tool 一个模块
│   ├── setup.py           # setup_status / setup_guide  —— 新用户引导
│   ├── login.py           # boss_login                    —— 登录
│   ├── preference.py      # preference_save / get         —— 意向管理
│   ├── job.py             # job_search / list / analyze   —— 岗位
│   ├── match.py           # job_match                     —— 匹配评分
│   ├── greeting.py        # greeting_preview / send       —— 打招呼
│   ├── pipeline.py        # pipeline_status               —— 流水线
│   ├── resume.py          # resume_analyze / suggest      —— 简历分析
│   └── report.py          # report_generate               —— 求职报告
│
├── engine/                # 业务逻辑引擎
│   ├── matcher.py         # rule_filter → llm_deep_match → hybrid_match
│   ├── analyzer.py        # analyze_jd / analyze_resume / generate_report
│   └── greeter.py         # preview_greeting
│
├── db/                    # SQLite 持久层
│   ├── schema.py          # 5 张表 + 索引 + 迁移脚本
│   └── client.py          # Database 类，全部 CRUD 封装
│
├── llm/                   # LLM API 客户端
│   └── client.py          # DeepSeek / OpenAI 兼容接口
│
├── browser/               # Boss 直聘操作封装
│   └── operator.py        # BossOperator —— boss-agent-cli 包装
│
└── tests/                 # 测试套件
    ├── test_db.py         # 数据库层（18 用例）
    ├── test_matcher.py    # 匹配引擎
    ├── test_llm.py        # LLM 客户端（mock）
    ├── test_browser.py    # 浏览器操作
    └── test_tools.py      # Tool 层集成
```

### 数据流

```
Agent (OpenClaw / Claude Code / OpenCode / Cline)
  │ MCP stdio (JSON-RPC)
  ▼
server.py ─── handle_list_tools / handle_call_tool
  │ asyncio.to_thread (非阻塞)
  ▼
tools/*.py ─── 参数校验，编排调用
  │         │           │
  ▼         ▼           ▼
engine/   browser/     llm/         db/
matcher   BossOperator LLMClient    Database
  │         │           │           │
  │         ▼           ▼           ▼
  │    boss-agent-cli  DeepSeek    SQLite
  │         │           API        (WAL)
  │         ▼
  └─── Boss 直聘 API
```

### 设计决策

| 决策 | 说明 |
|------|------|
| **两阶段匹配** | 规则快筛（免费）+ LLM 深度评分（付费），仅规则分 ≥ 50 的岗位进入 LLM |
| **评分公式** | 最终分 = 规则分 × 0.3 + LLM 分 × 0.7，全阈值可配置 |
| **异步调度** | `asyncio.to_thread` 将阻塞操作放入线程池，保证 MCP 事件循环不阻塞 |
| **WAL 模式** | SQLite 开启 WAL，支持并发读 |
| **简历去重** | SHA-256 哈希，相同内容复用旧 ID，修改后自动版本 +1 |

### 数据库表

| 表 | 列数 | 用途 |
|----|------|------|
| `jobs` | 30 | 岗位全量数据，`id=security_id` 主键，状态机字段 |
| `greetings` | 12 | 打招呼审计日志，含回复追踪与重试 |
| `pipeline_log` | 10 | 操作批次日志 |
| `resume_cache` | 8 | 简历版本历史，`is_active` 标记当前版本 |
| `preferences` | 3 | 键值对配置存储 |

## 安装

### 方式一：一句话安装（推荐）

将下面这句话发送给 OpenClaw / Claude Code / OpenCode / Cline 即可完成全部安装和配置：

```
帮我安装并配置 job_hunter 求职助手：https://github.com/zsq176/job_hunter
```

Agent 会自动执行：`git clone` → `pip install` → `patchright install chromium` → 创建 `.env` 并引导你填写 API Key → 配置 MCP Server → 验证安装。全程无需手动操作终端。

> OpenCode 用户也可以用 `/install https://github.com/zsq176/job_hunter` 触发安装。

### 方式二：手动安装

```bash
git clone https://github.com/zsq176/job_hunter.git
cd job_hunter
pip install boss-agent-cli
patchright install chromium
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填写 LLM_API_KEY=sk-your-key
```

### 注册到 Agent

安装完成后，在 Agent 的 MCP 配置中添加：

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

| Agent | 配置文件 |
|-------|---------|
| **OpenClaw** | `openclaw.json` → `mcpServers` |
| **Claude Code** | `~/.claude/claude_desktop_config.json` → `mcpServers`，或通过 `.claude/mcp.json` |
| **OpenCode** | `opencode.json` → `mcpServers` |
| **Cline** | VSCode 扩展设置 → MCP Server |

重启 Agent 后即可使用。向 Agent 说 "帮我检查一下配置状态" 验证是否正常运行。

## 配置参考

```bash
# .env 核心变量
LLM_API_KEY=sk-xxx            # 必填。DeepSeek API Key
LLM_MODEL=deepseek-chat       # 模型名称
LLM_BASE_URL=https://api.deepseek.com  # OpenAI 兼容端点（可切换为其他供应商）
LOG_LEVEL=INFO                # DEBUG / INFO / WARNING / ERROR
LLM_TIMEOUT=60                # API 超时秒数

# 匹配评分参数（可选，均保留默认值即可）
MATCH_CITY_SCORE=25
MATCH_SALARY_SCORE=25
MATCH_RULE_WEIGHT=0.3
MATCH_LLM_WEIGHT=0.7
MATCH_PASS_THRESHOLD=55
MATCH_HIGH_SCORE=70

# 打招呼限流参数
DAILY_GREET_LIMIT=50
GREET_INTERVAL_MIN=10
GREET_INTERVAL_MAX=30
GREET_BATCH_SIZE=10
GREET_BATCH_REST=300
```

## 交互示例

### 初次使用

```
用户: 帮我检查一下配置状态
AI:   检测完毕：
      ✅ Python 环境 ✅ Node.js ✅ Chrome ✅ boss-agent-cli ✅ .env ✅ API Key
      完成度 67%，剩余 3 项建议完成。

用户: 设置求职意向：杭州、北京，15-30K，Python后端，排除外包和单休
AI:   已保存 5 项配置。

用户: 帮我登录 Boss直聘
AI:   请用 Boss直聘 App 扫描屏幕上的二维码。✅ 登录成功。
```

### 日常求职

```
用户: 搜一下北京和杭州的 Python 后端岗位
AI:   搜索"Python 后端"，北京 → 新增 42 个，杭州 → 新增 28 个。共 70 个岗位。

用户: 分析 JD，然后和我的简历匹配一下
AI:   JD 分析完成。需要你的简历来做匹配评分。

用户: [粘贴简历内容]
AI:   简历已缓存（v1）。匹配完成：≥70 分 12 个，≥80 分 5 个。
     最高: 字节跳动 后端开发 30-50K 评分 91

用户: 给评分最高的 5 个打招呼
AI:   已发送 5 个打招呼。今日 5/50。

用户: 看看求职进度
AI:   搜索 187 → 分析 156 → 匹配 42 → 已打招呼 28 → 回复 8
     回复率 28.6%
```

## 功能解析

### 匹配评分

两阶段混合评分，规则迅速筛掉不匹配项，LLM 仅对候选岗位深度评估：

```
rule_filter(job, prefs)
  ├── 城市匹配 +25（不匹配直接排除）
  ├── 薪资检查 ±25（超出范围直接排除）
  ├── 黑名单过滤（命中直接排除）
  ├── 必需关键词匹配（每命中 +5，上限 +15）
  ├── 加分关键词匹配（每命中 +3）
  └── 福利匹配（每命中 +3，上限 +10）

规则分 ≥ 50 → llm_deep_match()
  ├── skill_match       满分 40
  ├── experience_match   满分 30
  ├── education_match    满分 10
  └── company_appeal     满分 20

最终分 = rule_score × 0.3 + llm_score × 0.7
≥ 55 → "matched"，< 55 → "analyzed"
```

### 打招呼

LLM 基于 JD 生成 30-60 字定制话术。默认每日 50 条上限，发送间隔随机 10-30 秒，每 10 条休息 5 分钟防限流。支持 `dry_run` 预览模式，`RATE_LIMITED` 自动暂停。

### 简历分析

`resume_analyze` 分析优缺点与缺失关键词，SHA-256 自动版本管理。`resume_suggest` 从已分析 JD 统计市场高频词，计算薪资中位数给出定位参考。

### 流水线与报告

`pipeline_status` 实时统计各阶段数量与回复转化率。`report_generate` 由 LLM 生成周报/日报（进度摘要 + 关键数据 + 下周建议）。

### 登录

4 级降级链路：`auto`（Cookie → CDP 扫码）→ `cookie`（提取已登录 Chrome）→ `cdp`（打开浏览器扫码）→ `status`（仅检查）。

### 新用户引导

`setup_status` 检测 9 项配置状态并返回完成度百分比。`setup_guide` 提供 6 类分步操作指南。

## 可用工具

| 工具 | 说明 |
|------|------|
| `setup_status` | 检测环境配置状态，引导完成初次配置 |
| `setup_guide` | 获取分步配置指南 |
| `boss_login` | 登录 Boss 直聘（四级降级链路） |
| `preference_save` | 保存求职意向（城市/薪资/关键词/黑名单） |
| `preference_get` | 查看当前意向配置 |
| `job_search` | 搜索岗位并入库去重 |
| `job_list` | 查询已存储的岗位列表（筛选/排序/分页） |
| `job_analyze` | LLM 深度解析 JD 提取技能/职责/卖点 |
| `job_match` | 简历与岗位混合匹配评分 |
| `greeting_preview` | 预览 AI 生成打招呼话术 |
| `greeting_send` | 发送打招呼（限流保护，支持批量与 dry_run） |
| `pipeline_status` | 求职流水线概览与转化率 |
| `resume_analyze` | 简历优缺点与改进建议 |
| `resume_suggest` | 基于市场数据的简历优化建议 |
| `report_generate` | 生成求职周报/日报 |

## 依赖

```
boss-agent-cli>=0.6.0  # Boss 直聘浏览器自动化与 API 封装
mcp>=1.6.0             # MCP 协议库
python-dotenv>=1.0.0   # 环境变量加载
httpx>=0.28.0          # LLM API HTTP 客户端
```

- Python 3.10+ / Chrome 浏览器
- DeepSeek API Key（或任意 OpenAI 兼容接口）

## License

MIT
