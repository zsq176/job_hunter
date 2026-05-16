"""Boss直聘操作层 - 封装 boss-agent-cli 为 Python 库调用"""
import logging
from pathlib import Path
from typing import Optional
from config import BOSS_DATA_DIR

logger = logging.getLogger("browser")


class BossOperator:
    """Boss直聘浏览器操作封装"""

    def __init__(self, data_dir: Path = BOSS_DATA_DIR):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._auth = None

    @property
    def auth(self):
        """延迟初始化 AuthManager"""
        if self._auth is None:
            from boss_agent_cli.auth.manager import AuthManager
            from boss_agent_cli.output import Logger
            self._auth = AuthManager(self.data_dir, logger=Logger())
        return self._auth

    def login(self, method: str = "auto", timeout: int = 120) -> dict:
        """登录（4级降级）"""
        logger.info("login method=%s", method)
        try:
            if method == "cookie":
                from boss_agent_cli.auth.cookie_extract import extract_cookies
                token = extract_cookies(platform="zhipin")
            elif method == "status":
                token = self.auth.check_status()
                return {"ok": bool(token), "token": token}
            else:
                token = self.auth.login(timeout=timeout, force_cdp=(method == "cdp"))
            return {"ok": True, "method": token.get("_method", "unknown"), "token": token}
        except Exception as e:
            logger.error("login failed: %s", e)
            return {"ok": False, "error": str(e)}

    def check_status(self) -> dict:
        """检查登录状态"""
        try:
            token = self.auth.check_status()
            if token:
                valid = self.auth._verify_cookie(token)
                return {"logged_in": valid, "token": token if valid else None}
            return {"logged_in": False}
        except Exception as e:
            logger.warning("check_status failed: %s", e)
            return {"logged_in": False, "error": str(e)}

    def search_jobs(self, keyword: str, city: str = None, page: int = 1) -> dict:
        """搜索岗位"""
        from boss_agent_cli.platforms import get_platform
        logger.info("search_jobs keyword=%s city=%s page=%d", keyword, city, page)
        with get_platform("zhipin", self.auth) as platform:
            raw = platform.search_jobs(keyword, city=city, page=page)
            if platform.is_success(raw):
                data = platform.unwrap_data(raw) or {}
                return self._extract_jobs(data)
            return {"jobs": [], "error": str(raw)}

    def _extract_jobs(self, data: dict) -> dict:
        """从 API 返回中提取岗位列表"""
        job_list = data.get("jobList", [])
        jobs = []
        for item in job_list:
            jobs.append({
                "security_id": item.get("securityId", ""),
                "encrypt_job_id": item.get("encryptJobId", item.get("encryptBossId", "")),
                "title": item.get("jobName", item.get("title", "")),
                "company": item.get("brandName", ""),
                "salary": item.get("salaryDesc", item.get("salary", "")),
                "city": item.get("cityName", item.get("city", "")),
                "experience": item.get("jobExperience", item.get("experience", "")),
                "education": item.get("jobDegree", item.get("education", "")),
                "skills": item.get("skills", []),
                "welfare": item.get("welfareList", []),
                "jd_raw": item.get("jobDetail", item.get("jd_raw", "")),
                "company_info": {
                    "industry": item.get("brandIndustry", ""),
                    "scale": item.get("brandScaleName", ""),
                    "stage": item.get("brandStageName", ""),
                },
            })
        return {"jobs": jobs, "total": len(jobs), "page": data.get("page", 1)}

    def get_job_detail(self, security_id: str) -> Optional[dict]:
        """获取岗位详情"""
        from boss_agent_cli.platforms import get_platform
        with get_platform("zhipin", self.auth) as platform:
            raw = platform.job_detail(security_id)
            if platform.is_success(raw):
                data = platform.unwrap_data(raw) or {}
                return data
            return None

    def greet(self, security_id: str, job_id: str, message: str = "") -> dict:
        """打招呼"""
        from boss_agent_cli.platforms import get_platform
        from boss_agent_cli.auth.manager import AuthRequired
        logger.info("greet security_id=%s job_id=%s", security_id, job_id)
        try:
            with get_platform("zhipin", self.auth) as platform:
                resp = platform.greet(security_id, job_id, message)
                if platform.is_success(resp):
                    return {"ok": True}
                error_code, error_msg = platform.parse_error(resp)
                return {"ok": False, "error": error_code, "message": error_msg}
        except AuthRequired:
            return {"ok": False, "error": "AUTH_REQUIRED", "message": "请先登录"}
        except Exception as e:
            logger.error("greet failed: %s", e)
            return {"ok": False, "error": "UNKNOWN", "message": str(e)}
