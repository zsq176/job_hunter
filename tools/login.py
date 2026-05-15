"""登录 Tool"""
from browser.operator import BossOperator


def boss_login(method: str = "auto") -> dict:
    """登录 Boss直聘"""
    ops = BossOperator()

    if method == "status":
        status = ops.check_status()
        return status

    result = ops.login(method=method)
    if result.get("ok"):
        return {"ok": True, "method_used": result.get("method"), "message": "✅ 登录成功"}
    return {"ok": False, "error": result.get("error", "登录失败"),
            "message": "❌ 登录失败，请重试"}
