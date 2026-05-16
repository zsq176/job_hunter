"""登录 Tool"""
import logging
from browser.operator import BossOperator

logger = logging.getLogger("tools.login")


def boss_login(method: str = "auto") -> dict:
    """登录 Boss直聘"""
    ops = BossOperator()

    if method == "status":
        return ops.check_status()

    result = ops.login(method=method)
    if result.get("ok"):
        logger.info("boss_login success method=%s", method)
        return {"ok": True, "method_used": result.get("method"), "message": "登录成功"}
    logger.error("boss_login failed: %s", result.get("error"))
    return {"ok": False, "error": result.get("error", "登录失败"),
            "message": "登录失败，请重试"}
