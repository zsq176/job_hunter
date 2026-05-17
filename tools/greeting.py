"""打招呼 Tool"""
import time
import random
import uuid
import logging
from typing import Optional
from db.client import Database
from browser.operator import BossOperator
from engine.greeter import preview_greeting
from llm.client import LLMClient
from config import (
    LLM_API_KEY, DAILY_GREET_LIMIT,
    GREET_INTERVAL_MIN, GREET_INTERVAL_MAX,
    GREET_BATCH_SIZE, GREET_BATCH_REST,
)

logger = logging.getLogger("tools.greeting")


def greeting_preview(job_id: str, tone: str = "专业") -> dict:
    """预览打招呼话术"""
    db = Database()
    llm = LLMClient(api_key=LLM_API_KEY)
    resume = db.get_active_resume()
    resume_text = resume["raw_text"] if resume else ""

    greeting = preview_greeting(job_id, tone, resume_text, db, llm)
    job = db.get_job(job_id)
    return {
        "ok": True,
        "job_id": job_id,
        "title": job.get("title", "") if job else "",
        "company": job.get("company", "") if job else "",
        "greeting": greeting,
    }


def greeting_send(job_ids: list[str], custom_message: Optional[str] = None,
                  dry_run: bool = False) -> dict:
    """发送打招呼"""
    db = Database()
    ops = BossOperator()
    llm = LLMClient(api_key=LLM_API_KEY)

    status = ops.check_status()
    if not status.get("logged_in"):
        return {"ok": False, "error": "AUTH_REQUIRED", "message": "请先登录 Boss直聘"}

    today_count = db.get_today_greeting_count()
    if today_count >= DAILY_GREET_LIMIT:
        return {"ok": False, "error": "DAILY_LIMIT",
                "message": f"今日已发 {today_count} 条，达到上限 {DAILY_GREET_LIMIT}"}

    resume = db.get_active_resume()
    resume_text = resume["raw_text"] if resume else ""
    batch_id = uuid.uuid4().hex[:12]

    results = []
    sent_count = 0
    for idx, job_id in enumerate(job_ids):
        if today_count + sent_count >= DAILY_GREET_LIMIT:
            break

        job = db.get_job(job_id)
        if not job:
            results.append({"job_id": job_id, "status": "failed", "error": "岗位不存在"})
            continue

        if custom_message:
            message = custom_message
        else:
            message = preview_greeting(job_id, "专业", resume_text, db, llm)

        if dry_run:
            results.append({"job_id": job_id, "status": "dry_run", "greeting": message})
            continue

        security_id = job.get("id", "")
        encrypt_job_id = job.get("encrypt_job_id", "") or security_id
        resp = ops.greet(security_id, encrypt_job_id, message)

        if resp.get("ok"):
            db.record_greeting(job_id, "success", message, batch_id=batch_id)
            results.append({"job_id": job_id, "status": "success", "greeting": message})
            sent_count += 1
            logger.info("greeting sent job_id=%s", job_id)
        else:
            error_code = resp.get("error", "UNKNOWN")
            db.record_greeting(job_id, "failed", message, error=error_code, batch_id=batch_id)
            results.append({"job_id": job_id, "status": "failed", "error": error_code})
            logger.warning("greeting failed job_id=%s error=%s", job_id, error_code)
            if error_code == "RATE_LIMITED":
                break

        if idx < len(job_ids) - 1 and sent_count > 0:
            if sent_count % GREET_BATCH_SIZE == 0:
                logger.info("batch rest %ds after %d sends", GREET_BATCH_REST, sent_count)
                time.sleep(GREET_BATCH_REST)
            else:
                time.sleep(random.uniform(GREET_INTERVAL_MIN, GREET_INTERVAL_MAX))

    return {
        "ok": True,
        "batch_id": batch_id,
        "sent": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }
