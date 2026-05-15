# Job Hunter

AI-powered job hunting assistant for Boss Zhipin. Automates job search, JD analysis, resume matching, and candidate outreach through MCP protocol.

## Features

- **Job Search**: Search and persist job listings with structured filtering
- **JD Analysis**: Extract skills, requirements, and selling points via LLM
- **Resume Matching**: Two-phase scoring (rule filter + LLM deep evaluation)
- **Auto Outreach**: Customized greeting messages with rate limiting
- **Pipeline Tracking**: End-to-end status flow per position
- **Resume Audit**: Keyword gap analysis against market data
- **Weekly Report**: Application funnel and conversion metrics

## Prerequisites

- Python 3.10+
- Node.js 18+ (for OpenClaw)
- Chrome browser (for login)
- DeepSeek API key (or any OpenAI-compatible LLM)

## Installation

```bash
pip install boss-agent-cli
patchright install chromium

git clone https://github.com/zsq176/job_hunter.git
cd job_hunter
pip install -r requirements.txt

cp .env.example .env
# Edit .env: set LLM_API_KEY
```

## Usage

### MCP Server

Register in your OpenClaw configuration:

```json
{
  "mcpServers": {
    "job-hunter": {
      "command": "python",
      "args": ["<path>/job_hunter/server.py"]
    }
  }
}
```

Then interact via natural language:

> "Search Golang jobs in Guangzhou"  
> "Analyze job matching for my resume"  
> "Send greetings to top 10 matched positions"  
> "Show my weekly application report"

### Tools

| Tool | Description |
|------|-------------|
| `boss_login` | Authenticate with Boss Zhipin (4-tier fallback) |
| `preference_save` | Save job preferences (city, salary, keywords, blacklist) |
| `preference_get` | View current preferences |
| `job_search` | Search jobs and persist to database |
| `job_list` | Query stored jobs with filters and pagination |
| `job_analyze` | Deep JD analysis via LLM |
| `job_match` | Resume-job matching (rules + LLM hybrid) |
| `greeting_preview` | Preview AI-generated greeting text |
| `greeting_send` | Send greetings with rate limiting |
| `pipeline_status` | Application pipeline overview |
| `resume_analyze` | Resume strengths, weaknesses, suggestions |
| `resume_suggest` | Market-driven resume improvement advice |
| `report_generate` | Weekly application summary |

## Architecture

```
Agent (OpenClaw) <-> MCP Server <-> Tools <-> BossOperator -> boss-agent-cli -> Zhipin API
                                          <-> LLM Client     -> DeepSeek API
                                          <-> Database       -> SQLite
```

## Configuration

Environment variables (`.env`):

| Variable | Description |
|----------|-------------|
| `LLM_API_KEY` | DeepSeek or OpenAI API key |
| `LLM_MODEL` | Model name (default: deepseek-chat) |
| `LOG_LEVEL` | DEBUG/INFO/WARNING/ERROR |

## License

[MIT](LICENSE)
