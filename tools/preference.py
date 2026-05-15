"""意向管理 Tool"""
import json
from db.client import Database
from typing import Any


def preference_save(preferences: dict) -> dict:
    """保存求职意向配置"""
    db = Database()
    valid_keys = {
        "cities", "salary_min", "salary_max", "keywords_must", "keywords_bonus",
        "blacklist", "company", "welfare", "daily_greet_limit", "min_match_score"
    }
    saved = []
    for key, value in preferences.items():
        if key in valid_keys:
            db.save_preference(key, value)
            saved.append(key)
    return {"ok": True, "saved": saved, "message": f"已保存 {len(saved)} 项配置"}


def preference_get() -> dict:
    """查看当前意向配置"""
    db = Database()
    prefs = db.get_all_preferences()
    if not prefs:
        return {"ok": True, "preferences": {}, "message": "暂无配置，请先使用 preference_save 设置"}
    return {"ok": True, "preferences": prefs}
