"""周报 Tool"""
from db.client import Database
from engine.analyzer import generate_report
from llm.client import LLMClient
from config import LLM_API_KEY


def report_generate(report_type: str = "weekly") -> dict:
    """生成求职报告"""
    db = Database()
    llm = LLMClient(api_key=LLM_API_KEY)

    try:
        content = generate_report(db, llm, report_type)
        return {"ok": True, "type": report_type, "content": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}
