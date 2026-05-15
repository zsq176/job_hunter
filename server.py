"""Boss Hunter MCP Server - AI 求职助手

通过 MCP 协议暴露 12 个求职工具，供 OpenClaw/Claude Desktop 调用。
"""
import json
import sys
import argparse
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from tools.login import boss_login
from tools.preference import preference_save, preference_get
from tools.job import job_search, job_list, job_analyze
from tools.match import job_match
from tools.greeting import greeting_preview, greeting_send
from tools.pipeline import pipeline_status
from tools.resume import resume_analyze, resume_suggest
from tools.report import report_generate

server = Server("job-hunter")


# ── Tool 定义 ──

TOOLS = [
    Tool(
        name="boss_login",
        description="登录 Boss直聘。支持多种方式：auto(自动降级)、status(仅检查状态)",
        inputSchema={
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "登录方式：auto/cookie/cdp/status",
                    "default": "auto",
                }
            },
        },
    ),
    Tool(
        name="preference_save",
        description="保存求职意向配置（城市/薪资/关键词/黑名单等）",
        inputSchema={
            "type": "object",
            "properties": {
                "cities": {"type": "array", "items": {"type": "string"}, "description": "目标城市列表"},
                "salary_min": {"type": "integer", "description": "期望最低薪资(K)"},
                "salary_max": {"type": "integer", "description": "期望最高薪资(K)"},
                "keywords_must": {"type": "array", "items": {"type": "string"}, "description": "必需关键词"},
                "keywords_bonus": {"type": "array", "items": {"type": "string"}, "description": "加分关键词"},
                "blacklist": {"type": "array", "items": {"type": "string"}, "description": "排除关键词(外包/单休等)"},
                "welfare": {"type": "array", "items": {"type": "string"}, "description": "福利要求"},
            },
        },
    ),
    Tool(
        name="preference_get",
        description="查看当前求职意向配置",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="job_search",
        description="在 Boss直聘搜索岗位并存入数据库。支持关键词、城市筛选",
        inputSchema={
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"},
                "city": {"type": "string", "description": "城市名称"},
                "max_pages": {"type": "integer", "description": "最大翻页数", "default": 3},
            },
            "required": ["keyword"],
        },
    ),
    Tool(
        name="job_list",
        description="查询已存储的岗位列表，支持按状态/评分筛选和分页",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "筛选状态: new/analyzed/matched/greeted"},
                "score_min": {"type": "integer", "description": "最低评分"},
                "score_max": {"type": "integer", "description": "最高评分"},
                "sort_by": {"type": "string", "description": "排序字段: score/created_at/salary", "default": "score"},
                "order": {"type": "string", "description": "排序方向: desc/asc", "default": "desc"},
                "limit": {"type": "integer", "description": "每页数量", "default": 20},
                "offset": {"type": "integer", "description": "偏移量", "default": 0},
            },
        },
    ),
    Tool(
        name="job_analyze",
        description="用 LLM 深度分析岗位 JD，提取技能要求/职责/卖点。不传 job_ids 则分析所有未分析的",
        inputSchema={
            "type": "object",
            "properties": {
                "job_ids": {
                    "type": "array", "items": {"type": "string"},
                    "description": "要分析的岗位ID列表(空=分析所有未分析的)",
                },
            },
        },
    ),
    Tool(
        name="job_match",
        description="简历匹配评分。规则过滤+LLM深度评分混合。不传 job_ids 则匹配所有已分析未评分的岗位",
        inputSchema={
            "type": "object",
            "properties": {
                "resume_text": {"type": "string", "description": "简历文本(首次传，后续会自动缓存)"},
                "job_ids": {"type": "array", "items": {"type": "string"}, "description": "要评分的岗位ID"},
                "min_score": {"type": "integer", "description": "最低返回分数", "default": 70},
            },
        },
    ),
    Tool(
        name="greeting_preview",
        description="预览打招呼话术(不发送)",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "岗位ID"},
                "tone": {"type": "string", "description": "语气: 专业/友好/简洁", "default": "专业"},
            },
            "required": ["job_id"],
        },
    ),
    Tool(
        name="greeting_send",
        description="发送打招呼消息。支持批量、自定义消息、dry_run模式",
        inputSchema={
            "type": "object",
            "properties": {
                "job_ids": {"type": "array", "items": {"type": "string"}, "description": "岗位ID列表"},
                "custom_message": {"type": "string", "description": "自定义消息(不传则AI基于JD生成)"},
                "dry_run": {"type": "boolean", "description": "仅模拟不发送", "default": False},
            },
            "required": ["job_ids"],
        },
    ),
    Tool(
        name="pipeline_status",
        description="查看求职流水线概览（总数/分析/匹配/打招呼/回复率）",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="resume_analyze",
        description="分析简历优缺点和改进建议。不传 resume_text 则使用已缓存的简历",
        inputSchema={
            "type": "object",
            "properties": {
                "resume_text": {"type": "string", "description": "简历文本"},
            },
        },
    ),
    Tool(
        name="resume_suggest",
        description="基于市场数据分析简历，给出改进建议（关键词缺口/薪资定位）",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="report_generate",
        description="生成求职周报/日报",
        inputSchema={
            "type": "object",
            "properties": {
                "report_type": {"type": "string", "description": "报告类型: weekly/daily", "default": "weekly"},
            },
        },
    ),
]


def _call_tool(name: str, args: dict[str, Any]) -> str:
    """调用对应 Tool 函数"""
    try:
        if name == "boss_login":
            result = boss_login(**args)
        elif name == "preference_save":
            result = preference_save(args)
        elif name == "preference_get":
            result = preference_get()
        elif name == "job_search":
            result = job_search(**args)
        elif name == "job_list":
            result = job_list(**args)
        elif name == "job_analyze":
            result = job_analyze(**args)
        elif name == "job_match":
            result = job_match(**args)
        elif name == "greeting_preview":
            result = greeting_preview(**args)
        elif name == "greeting_send":
            result = greeting_send(**args)
        elif name == "pipeline_status":
            result = pipeline_status()
        elif name == "resume_analyze":
            result = resume_analyze(**args)
        elif name == "resume_suggest":
            result = resume_suggest()
        elif name == "report_generate":
            result = report_generate(**args)
        else:
            result = {"ok": False, "error": f"未知 Tool: {name}"}

        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    result = _call_tool(name, arguments)
    return [TextContent(type="text", text=result)]


def main():
    parser = argparse.ArgumentParser(description="Boss Hunter MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio"])
    args = parser.parse_args()

    import asyncio
    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
