"""JD/简历分析引擎"""
from typing import Optional
from db.client import Database
from llm.client import LLMClient


def analyze_jd(job_id: str, db: Database, llm: LLMClient) -> dict:
    """分析岗位 JD，缓存结果"""
    job = db.get_job(job_id)
    if not job:
        return {"error": f"岗位 {job_id} 不存在"}

    # 检查是否已有分析结果
    if job.get("jd_analyzed"):
        import json
        try:
            return json.loads(job["jd_analyzed"])
        except (json.JSONDecodeError, TypeError):
            pass

    jd_text = job.get("jd_raw", "")
    if not jd_text:
        return {"error": "岗位 JD 为空"}

    try:
        result = llm.analyze_jd(jd_text)
        import json
        db.update_job(job_id, jd_analyzed=json.dumps(result, ensure_ascii=False),
                      jd_analyzed_at=__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      status="analyzed")
        return result
    except Exception as e:
        return {"error": f"分析失败: {str(e)}"}


def analyze_resume(resume_text: str, db: Database, llm: LLMClient) -> dict:
    """分析简历"""
    # 保存简历
    resume_id = db.save_resume(resume_text)

    # 获取市场关键词
    market_keywords = db.get_market_keywords(15)

    try:
        result = llm.analyze_resume(resume_text, market_keywords)
        import json
        db.update_resume_analysis(
            resume_id,
            report=json.dumps(result.get("strengths", []), ensure_ascii=False),
            suggestions=json.dumps(result.get("suggestions", []), ensure_ascii=False),
        )
        result["market_keywords"] = market_keywords
        return result
    except Exception as e:
        return {"error": f"分析失败: {str(e)}"}


def generate_report(db: Database, llm: LLMClient, report_type: str = "weekly") -> str:
    """生成报告"""
    stats = db.get_pipeline_stats()
    import json
    with db._conn() as conn:
        rows = conn.execute(
            "SELECT * FROM greetings WHERE created_at >= datetime('now', '-7 days', 'localtime')"
        ).fetchall()
        greeting_history = [dict(r) for r in rows]

    try:
        return llm.generate_weekly_report(stats, greeting_history)
    except Exception as e:
        return f"生成报告失败: {str(e)}"
