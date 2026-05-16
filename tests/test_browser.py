"""Browser operator tests"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from browser.operator import BossOperator


class TestBossOperator:
    @patch("browser.operator.BOSS_DATA_DIR")
    def test_init_creates_dir(self, mock_dir):
        from pathlib import Path
        import tempfile, os
        fd, path = tempfile.mkstemp()
        os.close(fd)
        os.unlink(path)
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            op = BossOperator(data_dir=tmp_dir)
            assert tmp_dir.exists()
        finally:
            import shutil
            shutil.rmtree(str(tmp_dir), ignore_errors=True)

    def test_extract_jobs(self, mock_auth=None):
        op = BossOperator.__new__(BossOperator)
        op.data_dir = MagicMock()
        op._auth = None

        data = {
            "jobList": [
                {
                    "securityId": "sid_1",
                    "encryptJobId": "enc_1",
                    "jobName": "Python开发",
                    "brandName": "测试公司",
                    "salaryDesc": "20K-30K",
                    "cityName": "北京",
                    "jobExperience": "3-5年",
                    "jobDegree": "本科",
                    "skills": ["Python"],
                    "welfareList": ["五险一金"],
                    "brandIndustry": "互联网",
                    "brandScaleName": "100-499人",
                    "brandStageName": "B轮",
                    "jobDetail": "招聘Python开发工程师",
                }
            ],
            "page": 1,
        }
        result = op._extract_jobs(data)
        assert result["total"] == 1
        assert len(result["jobs"]) == 1
        job = result["jobs"][0]
        assert job["security_id"] == "sid_1"
        assert job["encrypt_job_id"] == "enc_1"
        assert job["title"] == "Python开发"
        assert job["company"] == "测试公司"
        assert "company_info" in job
        assert job["company_info"]["industry"] == "互联网"
        assert job["company_info"]["scale"] == "100-499人"
        assert job["company_info"]["stage"] == "B轮"

    def test_extract_jobs_fallback_encrypt_id(self):
        op = BossOperator.__new__(BossOperator)
        op.data_dir = MagicMock()
        op._auth = None

        data = {
            "jobList": [
                {
                    "securityId": "sid_2",
                    "encryptBossId": "boss_1",
                    "jobName": "测试",
                    "brandName": "公司",
                }
            ],
            "page": 1,
        }
        result = op._extract_jobs(data)
        assert result["jobs"][0]["encrypt_job_id"] == "boss_1"

    def test_check_status_not_logged_in(self):
        with patch.object(BossOperator, "auth", new_callable=PropertyMock) as mock_auth_prop:
            mock_auth = MagicMock()
            mock_auth.check_status.return_value = None
            mock_auth_prop.return_value = mock_auth

            op = BossOperator.__new__(BossOperator)
            op.data_dir = MagicMock()
            op._auth = None

            result = op.check_status()
            assert result["logged_in"] is False
