"""简历分析 Tool"""
import logging
from typing import Optional
from db.client import Database
from llm.client import LLMClient
from engine.analyzer import analyze_resume
from config import LLM_API_KEY

logger = logging.getLogger("tools.resume")


def resume_analyze(resume_text: Optional[str] = None) -> dict:
    """分析简历"""
    db = Database()
    llm = LLMClient(api_key=LLM_API_KEY)

    if not resume_text:
        resume = db.get_active_resume()
        if not resume:
            return {"ok": False, "error": "请提供简历文本"}
        resume_text = resume["raw_text"]

    result = analyze_resume(resume_text, db, llm)
    return {"ok": True, **result}


def resume_suggest() -> dict:
    """基于市场数据的简历改进建议"""
    db = Database()
    llm = LLMClient(api_key=LLM_API_KEY)

    resume = db.get_active_resume()
    if not resume:
        return {"ok": False, "error": "请先上传简历"}

    market_keywords = db.get_market_keywords(10)
    salary_min = db.get_preference("salary_min") or 0
    salary_max = db.get_preference("salary_max") or 0

    market_median = db.get_market_salary_median()

    result = llm.analyze_resume(resume["raw_text"], market_keywords)

    return {
        "ok": True,
        "market_keywords": market_keywords,
        "salary_position": {
            "your_expectation": salary_max or "未设置",
            "market_median": market_median if market_median else "数据不足",
        },
        **result,
    }
