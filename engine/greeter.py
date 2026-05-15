"""话术生成"""
from llm.client import LLMClient
from db.client import Database


def preview_greeting(job_id: str, tone: str, resume_text: str,
                     db: Database, llm: LLMClient) -> str:
    """预览打招呼话术"""
    job = db.get_job(job_id)
    if not job:
        return f"岗位 {job_id} 不存在"

    jd_text = job.get("jd_raw", "")
    try:
        return llm.generate_greeting(jd_text, resume_text, tone)
    except Exception as e:
        return f"生成话术失败: {str(e)}"
