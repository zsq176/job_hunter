"""流水线 Tool"""
import logging
from db.client import Database
from browser.operator import BossOperator

logger = logging.getLogger("tools.pipeline")


def pipeline_status() -> dict:
    """查看求职流水线"""
    db = Database()
    stats = db.get_pipeline_stats()

    ops = BossOperator()
    status = ops.check_status()
    login_info = {"logged_in": status.get("logged_in", False)}

    conversion = 0
    if stats.get("greeted", 0) > 0:
        conversion = round(stats.get("replied", 0) / stats.get("greeted", 0) * 100, 1)

    return {
        "ok": True,
        **stats,
        "conversion_rate": f"{conversion}%",
        "login_status": login_info,
    }
