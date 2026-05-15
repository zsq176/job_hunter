# Job Hunter

基于 MCP 协议的 AI 求职助手，支持 Boss 直聘自动化求职流程：岗位搜索、JD 解析、简历匹配、自动打招呼。

## 功能

- **岗位搜索**：关键词/城市筛选，自动入库去重持久化
- **JD 深度解析**：LLM 提取技能要求、核心职责、公司卖点
- **简历匹配评分**：两阶段评分（规则过滤 + LLM 深度评估）
- **自动打招呼**：基于 JD 生成定制话术，带限流策略
- **流水线追踪**：每个岗位的完整状态流转
- **简历分析**：市场关键词缺口分析，薪资定位建议
- **求职周报**：投递漏斗与转化率统计

## 前置依赖

- Python 3.10+
- Node.js 18+（运行 OpenClaw）
- Chrome 浏览器（用于登录）
- DeepSeek API Key（或兼容 OpenAI 接口的 LLM）

## 安装

```bash
pip install boss-agent-cli
patchright install chromium

git clone https://github.com/zsq176/job_hunter.git
cd job_hunter
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY
```

## 使用方式

### MCP Server

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

然后在聊天中通过自然语言交互：

> "搜一下广州的 Golang 岗位"  
> "分析这些岗位和我的简历匹配度"  
> "给 Top 10 的岗位打招呼"  
> "看看这周的求职报告"

### 可用工具

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

## 配置

环境变量（`.env`）：

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` | DeepSeek 或 OpenAI API Key |
| `LLM_MODEL` | 模型名称（默认 deepseek-chat） |
| `LOG_LEVEL` | 日志级别 DEBUG/INFO/WARNING/ERROR |

## 协议

[MIT](LICENSE)
