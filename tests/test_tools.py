"""Tools layer integration tests"""
import json
import tempfile
import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from tools.preference import preference_save, preference_get
from tools.login import boss_login
from tools.pipeline import pipeline_status
from tools.job import job_search, job_list, job_analyze


class TestPreferenceTools:
    def test_save_and_get_preferences(self):
        db_path = tempfile.mktemp(suffix=".db")
        try:
            with patch("tools.preference.Database") as mock_db_cls:
                mock_db = MagicMock()
                mock_db_cls.return_value = mock_db

                result = preference_save({"cities": ["北京"], "salary_min": 15})
                assert result["ok"] is True
                assert "cities" in result["saved"]

                mock_db.get_all_preferences.return_value = {"cities": ["北京"]}
                result = preference_get()
                assert result["ok"] is True
                assert "cities" in result["preferences"]
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_save_rejects_invalid_keys(self):
        with patch("tools.preference.Database") as mock_db_cls:
            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db
            result = preference_save({"cities": ["北京"], "invalid_key": "x"})
            assert "invalid_key" not in result["saved"]


class TestLoginTool:
    def test_login_status(self):
        with patch("tools.login.BossOperator") as mock_cls:
            mock_ops = MagicMock()
            mock_ops.check_status.return_value = {"logged_in": False}
            mock_cls.return_value = mock_ops

            result = boss_login(method="status")
            assert "logged_in" in result

    def test_login_failure(self):
        with patch("tools.login.BossOperator") as mock_cls:
            mock_ops = MagicMock()
            mock_ops.login.return_value = {"ok": False, "error": "auth failed"}
            mock_cls.return_value = mock_ops

            result = boss_login(method="auto")
            assert result["ok"] is False


class TestPipelineTool:
    def test_pipeline_status(self):
        with patch("tools.pipeline.BossOperator") as mock_boss:
            with patch("tools.pipeline.Database") as mock_db:
                mock_db_inst = MagicMock()
                mock_db_inst.get_pipeline_stats.return_value = {
                    "total_jobs": 100, "analyzed": 50, "matched_high": 30,
                    "greeted": 10, "replied": 3,
                }
                mock_db.return_value = mock_db_inst
                mock_boss_inst = MagicMock()
                mock_boss_inst.check_status.return_value = {"logged_in": True}
                mock_boss.return_value = mock_boss_inst

                result = pipeline_status()
                assert result["ok"] is True
                assert result["total_jobs"] == 100
                assert "conversion_rate" in result


class TestJobListTool:
    def test_job_list(self):
        with patch("tools.job.Database") as mock_db:
            mock_db_inst = MagicMock()
            mock_db_inst.list_jobs.return_value = {"total": 0, "jobs": []}
            mock_db.return_value = mock_db_inst

            result = job_list(status="new")
            assert result["ok"] is True
            assert result["total"] == 0
