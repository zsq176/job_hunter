"""匹配评分引擎（规则 + LLM 混合）"""
from typing import Optional
from db.client import Database
from llm.client import LLMClient


def rule_filter(job: dict, prefs: dict) -> tuple[bool, int, str]:
    """规则层过滤评分（快），复用 boss-agent-cli 类似逻辑"""
    reasons = []
    score = 0

    # 城市匹配
    cities = prefs.get("cities", [])
    if cities and job.get("city"):
        for c in cities:
            if c in job.get("city", ""):
                score += 25
                reasons.append("城市匹配")
                break
        else:
            return False, 0, "城市不匹配"

    # 薪资检查
    salary_min = prefs.get("salary_min")
    salary_max = prefs.get("salary_max")
    job_salary_min = job.get("salary_min")
    job_salary_max = job.get("salary_max")

    if salary_min and job_salary_max and job_salary_max < salary_min:
        return False, 0, f"薪资上限{job_salary_max}K低于期望{salary_min}K"
    if salary_max and job_salary_min and job_salary_min > salary_max:
        return False, 0, f"薪资下限{job_salary_min}K高于上限{salary_max}K"
    if salary_min or salary_max:
        score += 25
        reasons.append("薪资在范围内")

    # 黑名单过滤
    blacklist = prefs.get("blacklist", [])
    jd_text = (job.get("title", "") + " " + job.get("jd_raw", "") + " " +
               job.get("company", "")).lower()
    for word in blacklist:
        if word.lower() in jd_text:
            return False, 0, f"命中排除词: {word}"

    # 关键词匹配（加分）
    must_keywords = prefs.get("keywords_must", [])
    bonus_keywords = prefs.get("keywords_bonus", [])
    combined_text = (job.get("title", "") + " " + job.get("jd_raw", "")).lower()

    keyword_hits = 0
    for kw in must_keywords:
        if kw.lower() in combined_text:
            keyword_hits += 1
    if keyword_hits > 0:
        score += min(keyword_hits * 5, 15)
        reasons.append(f"命中{keyword_hits}个必需词")

    for kw in bonus_keywords:
        if kw.lower() in combined_text:
            score += 3
            reasons.append(f"加分词: {kw}")

    # 福利加分
    welfare = prefs.get("welfare", [])
    job_welfare = job.get("welfare", "")
    if isinstance(job_welfare, str):
        welfare_hits = sum(1 for w in welfare if w in job_welfare)
    else:
        welfare_hits = sum(1 for w in welfare if w in str(job_welfare))
    if welfare_hits > 0:
        score += min(welfare_hits * 3, 10)
        reasons.append(f"福利匹配{welfare_hits}项")

    return True, min(score, 100), "; ".join(reasons) if reasons else "基础匹配"


def llm_deep_match(job: dict, resume_text: str, llm: LLMClient) -> dict:
    """LLM 深度评分"""
    try:
        result = llm.match_score(
            resume_text=resume_text,
            jd_text=job.get("jd_raw", ""),
            company_info=job.get("company_info", ""),
        )
        return result
    except Exception as e:
        return {
            "total_score": 0,
            "dimensions": {},
            "tags": ["评分失败"],
            "error": str(e),
        }


def hybrid_match(job: dict, resume_text: str, prefs: dict,
                 llm: LLMClient, db: Database) -> Optional[dict]:
    """混合评分：先规则快筛，通不过直接 pass"""
    passed, rule_score, rule_reason = rule_filter(job, prefs)
    if not passed:
        db.update_job(job["id"], status="excluded",
                      score_detail=f'{{"reason": "{rule_reason}"}}')
        return None

    # 规则分 >= 50 才进入 LLM 评分
    if rule_score >= 50 and resume_text:
        llm_result = llm_deep_match(job, resume_text, llm)
        llm_score = llm_result.get("total_score", 0)
        total = int(rule_score * 0.3 + llm_score * 0.7)
    else:
        llm_result = {"tags": ["规则评分"]}
        total = rule_score

    result = {
        "job_id": job["id"],
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "score": total,
        "rule_score": rule_score,
        "rule_reason": rule_reason,
        "llm_detail": llm_result.get("dimensions", {}),
        "tags": llm_result.get("tags", []),
        "greeting_tone": llm_result.get("greeting_tone", "专业"),
    }

    # 存 DB
    db.update_job(
        job["id"],
        score=total,
        score_detail=str(llm_result.get("dimensions", {})),
        tags=str(llm_result.get("tags", [])),
        status="matched" if total >= 55 else "analyzed",
        score_updated_at=__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    return result
