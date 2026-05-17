"""Matching engine tests"""
import json
import pytest
from unittest.mock import MagicMock, patch

from engine.matcher import rule_filter, hybrid_match
from config import MATCH_PASS_THRESHOLD


class TestRuleFilter:
    def test_city_match(self):
        job = {"city": "北京朝阳", "title": "Python", "jd_raw": "", "company": ""}
        prefs = {"cities": ["北京"]}
        passed, score, reason = rule_filter(job, prefs)
        assert passed
        assert score >= 20

    def test_city_no_match_rejected(self):
        job = {"city": "上海", "title": "Python", "jd_raw": "", "company": ""}
        prefs = {"cities": ["北京"]}
        passed, score, reason = rule_filter(job, prefs)
        assert not passed
        assert "城市不匹配" in reason

    def test_salary_rejected_low(self):
        job = {"salary_min": 5, "salary_max": 10, "title": "Python", "jd_raw": "", "company": ""}
        prefs = {"salary_min": 15}
        passed, score, reason = rule_filter(job, prefs)
        assert not passed
        assert "薪资" in reason

    def test_salary_rejected_high(self):
        job = {"salary_min": 40, "salary_max": 60, "title": "Python", "jd_raw": "", "company": ""}
        prefs = {"salary_max": 30}
        passed, score, reason = rule_filter(job, prefs)
        assert not passed

    def test_blacklist_filter(self):
        job = {"title": "测试外包", "jd_raw": "招收外包人员", "company": "外包公司"}
        prefs = {"blacklist": ["外包"]}
        passed, score, reason = rule_filter(job, prefs)
        assert not passed
        assert "外包" in reason

    def test_keyword_match(self):
        job = {"title": "Python开发", "jd_raw": "需要Python和Django经验"}
        prefs = {"keywords_must": ["Python", "Django"]}
        passed, score, reason = rule_filter(job, prefs)
        assert passed
        assert score > 0

    def test_welfare_match(self):
        job = {"title": "测试", "welfare": json.dumps(["五险一金", "双休"]),
               "jd_raw": "", "company": ""}
        prefs = {"welfare": ["五险一金"]}
        passed, score, reason = rule_filter(job, prefs)
        assert passed
        assert "福利" in reason

    def test_welfare_list_type(self):
        job = {"title": "测试", "welfare": ["五险一金", "双休"],
               "jd_raw": "", "company": ""}
        prefs = {"welfare": ["双休"]}
        passed, score, reason = rule_filter(job, prefs)
        assert passed

    def test_empty_prefs_passes(self):
        job = {"title": "测试", "jd_raw": "", "company": ""}
        prefs = {}
        passed, score, reason = rule_filter(job, prefs)
        assert passed

    def test_no_city_with_cities_set(self):
        job = {"city": "", "title": "测试", "jd_raw": "", "company": ""}
        prefs = {"cities": ["北京"]}
        passed, score, reason = rule_filter(job, prefs)
        assert passed


class TestHybridMatch:
    def test_excluded_job_returns_none(self):
        db = MagicMock()
        llm = MagicMock()
        job = {"id": "x1", "city": "上海", "title": "Java", "jd_raw": "", "company": ""}
        prefs = {"cities": ["北京"]}
        result = hybrid_match(job, "resume", prefs, llm, db)
        assert result is None
        db.update_job.assert_called_once()

    def test_passed_job_stores_score(self):
        db = MagicMock()
        llm = MagicMock()
        llm.match_score.return_value = {
            "total_score": 80,
            "dimensions": {},
            "tags": ["推荐"],
            "greeting_tone": "专业",
        }
        job = {
            "id": "x2", "title": "Python", "company": "Acme",
            "jd_raw": "需要Python", "company_info": "{}",
            "city": "北京",
        }
        prefs = {"cities": ["北京"], "salary_min": 15, "salary_max": 40}
        result = hybrid_match(job, "resume", prefs, llm, db)
        assert result is not None
        assert result["score"] > 0
        assert db.update_job.called

    def test_score_detail_is_valid_json(self):
        db = MagicMock()
        llm = MagicMock()
        llm.match_score.return_value = {
            "total_score": 60,
            "dimensions": {"skill_match": {"score": 30, "max": 40, "reason": "ok"}},
            "tags": [],
            "greeting_tone": "专业",
        }
        job = {"id": "x3", "title": "Go", "company": "X", "jd_raw": "Go", "company_info": "{}"}
        result = hybrid_match(job, "resume", {}, llm, db)
        call_args = db.update_job.call_args
        score_detail = call_args[1].get("score_detail", "")
        parsed = json.loads(score_detail)
        assert isinstance(parsed, dict)
