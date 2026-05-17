"""JD/简历分析引擎"""
import json
import logging
from datetime import datetime
from typing import Optional
from db.client import Database
from llm.client import LLMClient

logger = logging.getLogger("engine.analyzer")


def analyze_jd(job_id: str, db: Database, llm: LLMClient) -> dict:
    """分析岗位 JD，缓存结果"""
    job = db.get_job(job_id)
    if not job:
        return {"error": f"岗位 {job_id} 不存在"}

    if job.get("jd_analyzed"):
        try:
            return json.loads(job["jd_analyzed"])
        except (json.JSONDecodeError, TypeError):
            pass

    jd_text = job.get("jd_raw", "")
    if not jd_text:
        return {"error": "岗位 JD 为空"}

    try:
        result = llm.analyze_jd(jd_text)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.update_job(job_id, jd_analyzed=json.dumps(result, ensure_ascii=False),
                      jd_analyzed_at=now, status="analyzed")
        logger.info("analyze_jd done job_id=%s", job_id)
        return result
    except Exception as e:
        logger.error("analyze_jd failed job_id=%s: %s", job_id, e)
        return {"error": f"分析失败: {str(e)}"}


def analyze_resume(resume_text: str, db: Database, llm: LLMClient) -> dict:
    """分析简历"""
    resume_id = db.save_resume(resume_text)
    market_keywords = db.get_market_keywords(15)

    try:
        result = llm.analyze_resume(resume_text, market_keywords)
        full_report = json.dumps({
            "strengths": result.get("strengths", []),
            "weaknesses": result.get("weaknesses", []),
            "missing_keywords": result.get("missing_keywords", []),
        }, ensure_ascii=False)
        db.update_resume_analysis(
            resume_id,
            report=full_report,
            suggestions=json.dumps(result.get("suggestions", []), ensure_ascii=False),
        )
        result["market_keywords"] = market_keywords
        logger.info("analyze_resume done resume_id=%d", resume_id)
        return result
    except Exception as e:
        logger.error("analyze_resume failed: %s", e)
        return {"error": f"分析失败: {str(e)}"}


def generate_report(db: Database, llm: LLMClient, report_type: str = "weekly") -> str:
    """生成报告"""
    stats = db.get_pipeline_stats()
    greeting_history = db.get_recent_greetings(7)

    try:
        if report_type == "daily":
            return llm.generate_daily_report(stats, greeting_history)
        return llm.generate_weekly_report(stats, greeting_history)
    except Exception as e:
        logger.error("generate_report failed: %s", e)
        return f"生成报告失败: {str(e)}"
