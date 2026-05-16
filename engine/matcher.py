"""匹配评分引擎（规则 + LLM 混合）"""
import json
import logging
from datetime import datetime
from typing import Optional
from db.client import Database
from llm.client import LLMClient
from config import (
    MATCH_CITY_SCORE, MATCH_SALARY_SCORE, MATCH_MUST_KEYWORD_SCORE,
    MATCH_BONUS_KEYWORD_SCORE, MATCH_WELFARE_SCORE,
    MATCH_KEYWORD_CAP, MATCH_WELFARE_CAP,
    MATCH_RULE_LLM_THRESHOLD, MATCH_RULE_WEIGHT, MATCH_LLM_WEIGHT,
    MATCH_PASS_THRESHOLD,
)

logger = logging.getLogger("engine.matcher")


def rule_filter(job: dict, prefs: dict) -> tuple[bool, int, str]:
    """规则层过滤评分（快）"""
    reasons = []
    score = 0

    cities = prefs.get("cities", [])
    if cities and job.get("city"):
        matched = any(c in job.get("city", "") for c in cities if c)
        if matched:
            score += MATCH_CITY_SCORE
            reasons.append("城市匹配")
        else:
            return False, 0, "城市不匹配"

    salary_min = prefs.get("salary_min")
    salary_max = prefs.get("salary_max")
    job_salary_min = job.get("salary_min")
    job_salary_max = job.get("salary_max")

    if salary_min and job_salary_max and job_salary_max < salary_min:
        return False, 0, f"薪资上限{job_salary_max}K低于期望{salary_min}K"
    if salary_max and job_salary_min and job_salary_min > salary_max:
        return False, 0, f"薪资下限{job_salary_min}K高于上限{salary_max}K"
    if salary_min or salary_max:
        score += MATCH_SALARY_SCORE
        reasons.append("薪资在范围内")

    blacklist = prefs.get("blacklist", [])
    jd_text = (job.get("title", "") + " " + job.get("jd_raw", "") + " " +
               job.get("company", "")).lower()
    for word in blacklist:
        if word.lower() in jd_text:
            return False, 0, f"命中排除词: {word}"

    must_keywords = prefs.get("keywords_must", [])
    bonus_keywords = prefs.get("keywords_bonus", [])
    combined_text = (job.get("title", "") + " " + job.get("jd_raw", "")).lower()

    keyword_hits = 0
    for kw in must_keywords:
        if kw.lower() in combined_text:
            keyword_hits += 1
    if keyword_hits > 0:
        score += min(keyword_hits * MATCH_MUST_KEYWORD_SCORE, MATCH_KEYWORD_CAP)
        reasons.append(f"命中{keyword_hits}个必需词")

    for kw in bonus_keywords:
        if kw.lower() in combined_text:
            score += MATCH_BONUS_KEYWORD_SCORE
            reasons.append(f"加分词: {kw}")

    welfare = prefs.get("welfare", [])
    job_welfare = job.get("welfare", "")
    if isinstance(job_welfare, str):
        try:
            welfare_list = json.loads(job_welfare)
            welfare_hits = sum(1 for w in welfare if any(w in item for item in welfare_list))
        except (json.JSONDecodeError, TypeError):
            welfare_hits = sum(1 for w in welfare if w in job_welfare)
    elif isinstance(job_welfare, list):
        welfare_hits = sum(1 for w in welfare if any(w in item for item in job_welfare))
    else:
        welfare_hits = 0

    if welfare_hits > 0:
        score += min(welfare_hits * MATCH_WELFARE_SCORE, MATCH_WELFARE_CAP)
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
        logger.warning("llm_deep_match failed for %s: %s", job.get("id"), e)
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
        score_detail = json.dumps({"reason": rule_reason}, ensure_ascii=False)
        db.update_job(job["id"], status="excluded", score_detail=score_detail)
        return None

    if rule_score >= MATCH_RULE_LLM_THRESHOLD and resume_text:
        llm_result = llm_deep_match(job, resume_text, llm)
        llm_score = llm_result.get("total_score", 0)
        total = int(rule_score * MATCH_RULE_WEIGHT + llm_score * MATCH_LLM_WEIGHT)
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

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.update_job(
        job["id"],
        score=total,
        score_detail=json.dumps(llm_result.get("dimensions", {}), ensure_ascii=False),
        tags=json.dumps(llm_result.get("tags", []), ensure_ascii=False),
        status="matched" if total >= MATCH_PASS_THRESHOLD else "analyzed",
        score_updated_at=now,
    )

    return result
