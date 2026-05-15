# Job Hunter

基于 MCP 协议的 AI 求职助手，支持 Boss 直聘自动化求职流程：岗位搜索、JD 解析、简历匹配、自动打招呼。

## 功能

- 岗位搜索：关键词/城市筛选，自动入库去重持久化
- JD 深度解析：LLM 提取技能要求、核心职责、公司卖点
- 简历匹配评分：两阶段评分（规则过滤 + LLM 深度评估）
- 自动打招呼：基于 JD 生成定制话术，带限流策略
- 流水线追踪：每个岗位的完整状态流转
- 简历分析：市场关键词缺口分析，薪资定位建议
- 求职周报：投递漏斗与转化率统计

## 前置依赖

- Python 3.10+
- Node.js 18+（运行 OpenClaw）
- Chrome 浏览器（用于登录）
- DeepSeek API Key（或兼容 OpenAI 接口的 LLM）

## 依赖说明

| 依赖 | 用途 | 为什么需要 |
|------|------|-----------|
| `boss-agent-cli` | Python 库 | 封装 Boss 直聘的 API 调用、Cookie 提取、扫码登录 |
| `patchright install chromium` | 浏览器驱动 | Boss 直聘登录需要操作本地 Chrome 浏览器（扫码） |
| `LLM_API_KEY` | DeepSeek API | JD 分析、简历匹配、话术生成、周报全靠 LLM |

## 安装

本机执行：

```bash
# 1. 安装底层 Boss 直聘 SDK（用于调用其 API 和登录）
pip install boss-agent-cli

# 2. 安装 Chromium 浏览器驱动（扫码登录用，装一次即可）
patchright install chromium

# 3. 安装本项目 Python 依赖
pip install -r requirements.txt
```

## 配置

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY
```

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` | DeepSeek 或 OpenAI API Key |
| `LLM_MODEL` | 模型名称（默认 deepseek-chat） |
| `LOG_LEVEL` | 日志级别 |

## 使用

在 OpenClaw 配置中注册：

```json
{
  "mcpServers": {
    "job-hunter": {
      "command": "python",
      "args": ["<路径>/job_hunter/server.py"]
    }
  }
}
```

### 对话示例

```
用户：搜一下广州的 Golang 岗位
AI：正在搜索...
    找到 48 个岗位，新增 35 个。
    需要我分析匹配度吗？

用户：分析一下，给匹配度高的打招呼
AI：分析完成。强烈推荐 5 个：
    - Shopee 后端开发 25-40K 评分 92
    - 字节跳动 Go后端 30-50K 评分 88
    已发送 5 个打招呼。

用户：看看我的求职进度
AI：搜索 187 → 分析 156 → 匹配 42 → 已打 28 → 回复 8
    回复率 28.6%

用户：分析一下简历
AI：建议补充"高并发"关键词（87%的目标岗位要求）
    项目描述增加量化数据
    薪资期望 25K，市场中位数 22K
```

### 工具列表

| 工具 | 说明 |
|------|------|
| `boss_login` | 登录 Boss 直聘（四级降级链路） |
| `preference_save` | 保存求职意向配置 |
| `preference_get` | 查看当前配置 |
| `job_search` | 搜索岗位并入库 |
| `job_list` | 查询已存储的岗位列表 |
| `job_analyze` | LLM 深度分析 JD |
| `job_match` | 简历匹配评分（规则+LLM 混合） |
| `greeting_preview` | 预览 AI 生成的打招呼话术 |
| `greeting_send` | 发送打招呼（含限流） |
| `pipeline_status` | 求职流水线概览 |
| `resume_analyze` | 简历优缺点分析 |
| `resume_suggest` | 基于市场数据的简历改进建议 |
| `report_generate` | 生成求职周报 |

## 架构

```
Agent (OpenClaw) <-> MCP Server <-> Tools <-> BossOperator -> boss-agent-cli -> Boss直聘 API
                                          <-> LLM Client     -> DeepSeek API
                                          <-> Database       -> SQLite
```

## 参考项目

- [boss-agent-cli](https://github.com/can4hou6joeng4/boss-agent-cli)：Boss 直聘 CLI 客户端，提供浏览器自动化与 API 封装
- [Auto-JobHunter](https://github.com/jolie-z/Auto-JobHunter)：多平台自动求职系统，LangGraph 多 Agent 架构
- [boss-zhipin-mcp](https://github.com/Snseam/boss-zhipin-mcp)：Boss 直聘 MCP Server，招聘者端自动化
- [boss-resume-filter](https://github.com/yaoyouzhong/boss-resume-filter)：候选人自动筛选工具，LLM 评分匹配

## 协议

MIT
