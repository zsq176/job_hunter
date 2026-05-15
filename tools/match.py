"""匹配评分 Tool"""
from typing import Optional
from db.client import Database
from llm.client import LLMClient
from engine.matcher import hybrid_match
from config import LLM_API_KEY


def job_match(resume_text: Optional[str] = None, job_ids: Optional[list[str]] = None,
              min_score: int = 70) -> dict:
    """简历匹配评分（规则+LLM 混合）"""
    db = Database()
    llm = LLMClient(api_key=LLM_API_KEY)

    # 获取简历
    if not resume_text:
        resume = db.get_active_resume()
        if not resume:
            return {"ok": False, "error": "请先上传简历", "matched": 0, "results": []}
        resume_text = resume["raw_text"]

    # 获取岗位
    if job_ids:
        jobs = [db.get_job(jid) for jid in job_ids]
        jobs = [j for j in jobs if j]
    else:
        # 所有已分析但未评分的
        with db._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE jd_analyzed IS NOT NULL AND jd_analyzed != '' AND (score IS NULL)"
            ).fetchall()
            jobs = [dict(r) for r in rows]

    if not jobs:
        return {"ok": True, "matched": 0, "results": [], "message": "没有需要评分的岗位"}

    prefs = db.get_all_preferences()
    results = []
    for job in jobs:
        result = hybrid_match(job, resume_text, prefs, llm, db)
        if result and result.get("score", 0) >= min_score:
            results.append(result)

    results.sort(key=lambda x: -x.get("score", 0))
    return {
        "ok": True,
        "matched": len(results),
        "results": results,
    }
