"""Database layer tests"""
import json
import os
import tempfile
import pytest

from db.schema import SCHEMA_SQL
from db.client import Database


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db_inst = Database(db_path=path)
        yield db_inst
    finally:
        os.unlink(path)


class TestDatabase:
    def test_init_creates_schema(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            import sqlite3
            Database(db_path=path)
            conn = sqlite3.connect(path)
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {t[0] for t in tables}
            assert "jobs" in table_names
            assert "greetings" in table_names
            assert "pipeline_log" in table_names
            assert "resume_cache" in table_names
            assert "preferences" in table_names
            conn.close()
        finally:
            os.unlink(path)

    def test_insert_jobs_new_and_duplicate(self, db):
        jobs = [
            {
                "security_id": "sid_001",
                "encrypt_job_id": "enc_001",
                "title": "Python开发",
                "company": "测试公司",
                "salary": "20K-30K",
                "city": "北京",
                "experience": "3-5年",
                "education": "本科",
                "welfare": ["五险一金", "双休"],
                "jd_raw": "招聘Python开发...",
                "company_info": {"industry": "互联网"},
            }
        ]
        result = db.insert_jobs(jobs)
        assert result["total"] == 1
        assert result["new"] == 1
        assert result["duplicates"] == 0

        result2 = db.insert_jobs(jobs)
        assert result2["total"] == 1
        assert result2["new"] == 0
        assert result2["duplicates"] == 1

    def test_insert_jobs_stores_encrypt_job_id(self, db):
        jobs = [{"security_id": "sid_e", "encrypt_job_id": "enc_xyz", "title": "测试"}]
        db.insert_jobs(jobs)
        job = db.get_job("sid_e")
        assert job["encrypt_job_id"] == "enc_xyz"

    def test_get_job_exists(self, db):
        jobs = [{"security_id": "sid_002", "title": "后端开发", "salary": "25K-35K"}]
        db.insert_jobs(jobs)
        job = db.get_job("sid_002")
        assert job is not None
        assert job["title"] == "后端开发"

    def test_get_job_not_exists(self, db):
        job = db.get_job("nonexistent")
        assert job is None

    def test_list_jobs_sort_by_whitelist(self, db):
        for i in range(3):
            db.insert_jobs([{"security_id": f"sid_{i}", "title": f"职位{i}"}])
        result = db.list_jobs(sort_by="title", order="asc", limit=10)
        assert result["total"] >= 3
        assert len(result["jobs"]) >= 3

    def test_list_jobs_invalid_sort_falls_back(self, db):
        result = db.list_jobs(sort_by="1; DROP TABLE jobs;--", order="asc")
        assert result is not None

    def test_get_unanalyzed_jobs(self, db):
        db.insert_jobs([
            {"security_id": "sid_u1", "title": "无JD"},
            {"security_id": "sid_u2", "title": "有JD", "jd_raw": "需要Python"},
        ])
        jobs = db.get_unanalyzed_jobs()
        assert all(j["jd_raw"] for j in jobs)
        assert all(not j["jd_analyzed"] for j in jobs)

    def test_record_greeting(self, db):
        jobs = [{"security_id": "sid_g", "title": "测试岗位"}]
        db.insert_jobs(jobs)
        db.record_greeting("sid_g", "success", "您好", batch_id="batch_1")
        job = db.get_job("sid_g")
        assert job["greeting_sent"] == 1
        assert job["greeting_status"] == "success"

    def test_save_resume_dedup(self, db):
        id1 = db.save_resume("简历内容A")
        id2 = db.save_resume("简历内容A")
        id3 = db.save_resume("简历内容B")
        assert id1 == id2
        assert id3 != id1

    def test_get_active_resume(self, db):
        db.save_resume("活跃简历")
        resume = db.get_active_resume()
        assert resume is not None
        assert resume["is_active"] == 1

    def test_preferences(self, db):
        db.save_preference("cities", ["北京", "上海"])
        val = db.get_preference("cities")
        assert val == ["北京", "上海"]

    def test_get_all_preferences(self, db):
        db.save_preference("cities", ["北京"])
        db.save_preference("salary_min", 15)
        prefs = db.get_all_preferences()
        assert "cities" in prefs
        assert "salary_min" in prefs

    def test_get_jobs_for_matching(self, db):
        db.insert_jobs([
            {"security_id": "sid_m1", "title": "已分析", "jd_raw": "JD内容"},
            {"security_id": "sid_m2", "title": "未分析"},
        ])
        db.update_job("sid_m1", jd_analyzed='{"skills_required": ["Python"]}')
        jobs = db.get_jobs_for_matching()
        assert len(jobs) >= 1
        assert all(j["jd_analyzed"] for j in jobs)
        assert all(j["score"] is None for j in jobs)

    def test_get_market_salary_median(self, db):
        result = db.get_market_salary_median()
        assert result is None
        db.insert_jobs([{
            "security_id": "sid_sal1",
            "title": "岗位",
            "salary": "10K-20K",
        }])
        median = db.get_market_salary_median()
        assert median is not None
        assert median == 15

    def test_get_today_greeting_count(self, db):
        jobs = [{"security_id": "sid_tgc", "title": "测试"}]
        db.insert_jobs(jobs)
        db.record_greeting("sid_tgc", "success", "消息")
        count = db.get_today_greeting_count()
        assert count >= 1

    def test_pipeline_stats(self, db):
        stats = db.get_pipeline_stats()
        assert "total_jobs" in stats
        assert "analyzed" in stats
        assert "matched_high" in stats
        assert "greeted" in stats
        assert "replied" in stats

    def test_parse_salary(self, db):
        assert db._parse_salary("25K-40K") == (25, 40)
        assert db._parse_salary("15k-25k") == (15, 25)
        assert db._parse_salary("") == (None, None)
        assert db._parse_salary("面议") == (None, None)
