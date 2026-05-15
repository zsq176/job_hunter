"""打招呼 Tool"""
import time
import random
from typing import Optional
from db.client import Database
from browser.operator import BossOperator
from engine.greeter import preview_greeting
from llm.client import LLMClient
from config import LLM_API_KEY

# 每日打招呼上限
DAILY_LIMIT = 50


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

    # 检查登录
    status = ops.check_status()
    if not status.get("logged_in"):
        return {"ok": False, "error": "AUTH_REQUIRED", "message": "请先登录 Boss直聘"}

    # 检查每日限额
    with db._conn() as conn:
        today_count = conn.execute(
            "SELECT COUNT(*) FROM greetings WHERE created_at >= datetime('now', 'start of day', 'localtime')"
        ).fetchone()[0]
    if today_count >= DAILY_LIMIT:
        return {"ok": False, "error": "DAILY_LIMIT", "message": f"今日已发 {today_count} 条，达到上限 {DAILY_LIMIT}"}

    resume = db.get_active_resume()
    resume_text = resume["raw_text"] if resume else ""

    results = []
    sent_count = 0
    for job_id in job_ids:
        if today_count + sent_count >= DAILY_LIMIT:
            break

        job = db.get_job(job_id)
        if not job:
            results.append({"job_id": job_id, "status": "failed", "error": "岗位不存在"})
            continue

        # 生成话术
        if custom_message:
            message = custom_message
        else:
            message = preview_greeting(job_id, "专业", resume_text, db, llm)

        if dry_run:
            results.append({"job_id": job_id, "status": "dry_run", "greeting": message})
            continue

        # 发送
        security_id = job.get("id", "")
        encrypt_job_id = job.get("job_id", "")
        resp = ops.greet(security_id, encrypt_job_id, message)

        if resp.get("ok"):
            db.record_greeting(job_id, "success", message)
            results.append({"job_id": job_id, "status": "success", "greeting": message})
            sent_count += 1
        else:
            error = resp.get("error", "UNKNOWN")
            db.record_greeting(job_id, "failed", message, error=str(resp))
            results.append({"job_id": job_id, "status": "failed", "error": error})
            if error == "RATE_LIMITED":
                break  # 限流了，停

        # 间隔 10-30 秒
        if sent_count < len(job_ids) and sent_count % 10 != 0:
            time.sleep(random.uniform(10, 30))
        elif sent_count % 10 == 0 and sent_count > 0:
            time.sleep(300)  # 每10条休息5分钟

    return {
        "ok": True,
        "sent": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }
