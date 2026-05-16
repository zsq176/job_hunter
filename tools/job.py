"""岗位搜索 & 列表 & 分析 Tool"""
import logging
from typing import Optional
from db.client import Database
from browser.operator import BossOperator
from engine.analyzer import analyze_jd
from llm.client import LLMClient
from config import LLM_API_KEY

logger = logging.getLogger("tools.job")


def job_search(keyword: str, city: Optional[str] = None, max_pages: int = 3) -> dict:
    """搜索岗位并入库"""
    ops = BossOperator()
    db = Database()

    all_jobs = []
    for page in range(1, max_pages + 1):
        result = ops.search_jobs(keyword, city=city, page=page)
        jobs = result.get("jobs", [])
        all_jobs.extend(jobs)
        if not jobs:
            break

    if not all_jobs:
        return {"ok": True, "total": 0, "new": 0, "message": "未找到匹配岗位"}

    stats = db.insert_jobs(all_jobs)
    logger.info("job_search keyword=%s total=%d new=%d", keyword, stats["total"], stats["new"])
    return {
        "ok": True,
        "total": stats["total"],
        "new": stats["new"],
        "duplicates": stats["duplicates"],
        "message": f"找到 {stats['total']} 个岗位，新增 {stats['new']} 个",
    }


def job_list(status: Optional[str] = None, score_min: Optional[int] = None,
             score_max: Optional[int] = None, sort_by: str = "created_at",
             order: str = "desc", limit: int = 20, offset: int = 0) -> dict:
    """查询岗位列表"""
    db = Database()
    result = db.list_jobs(
        status=status, score_min=score_min, score_max=score_max,
        sort_by=sort_by, order=order, limit=limit, offset=offset,
    )
    return {"ok": True, **result}


def job_analyze(job_ids: Optional[list[str]] = None) -> dict:
    """LLM 深度分析 JD"""
    db = Database()
    llm = LLMClient(api_key=LLM_API_KEY)

    if job_ids:
        jobs_to_analyze = [db.get_job(jid) for jid in job_ids]
        jobs_to_analyze = [j for j in jobs_to_analyze if j]
    else:
        jobs_to_analyze = db.get_unanalyzed_jobs()

    if not jobs_to_analyze:
        return {"ok": True, "analyzed": 0, "results": [], "message": "没有需要分析的岗位"}

    results = []
    for job in jobs_to_analyze:
        try:
            analysis = analyze_jd(job["id"], db, llm)
            if "error" not in analysis:
                results.append({
                    "job_id": job["id"],
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    **analysis,
                })
        except Exception as e:
            logger.warning("job_analyze failed for %s: %s", job.get("id"), e)
            results.append({"job_id": job["id"], "error": str(e)})

    return {"ok": True, "analyzed": len(results), "results": results}
