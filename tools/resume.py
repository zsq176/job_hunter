"""简历分析 Tool"""
from typing import Optional
from db.client import Database
from llm.client import LLMClient
from engine.analyzer import analyze_resume
from config import LLM_API_KEY


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
    salary_pref = db.get_preference("salary")
    salary_min = salary_pref.get("min", 0) if salary_pref else 0
    salary_max = salary_pref.get("max", 0) if salary_pref else 0

    # 市场薪资分布
    with db._conn() as conn:
        row = conn.execute(
            "SELECT AVG((salary_min + salary_max)/2.0) as median FROM jobs WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL"
        ).fetchone()
        market_median = round(row[0]) if row and row[0] else None

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
