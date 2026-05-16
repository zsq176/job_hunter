"""LLM client tests"""
import json
import pytest
from unittest.mock import MagicMock, patch

from llm.client import LLMClient


@pytest.fixture
def mock_httpx():
    with patch("llm.client.Client") as mock:
        yield mock


class TestLLMClient:
    def test_init_requires_api_key(self):
        with patch("llm.client.LLM_API_KEY", ""):
            with patch("llm.client.LLM_BASE_URL", "http://fake"):
                with patch("llm.client.LLM_MODEL", "fake"):
                    with pytest.raises(ValueError, match="LLM_API_KEY"):
                        LLMClient(api_key="")

    def test_analyze_jd_parses_json(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({
                "skills_required": ["Python"],
                "experience_required": "3年",
                "education_required": "本科",
                "key_responsibilities": ["开发"],
                "selling_points": ["远程"],
                "summary": "测试"
            })}}]
        }
        mock_httpx.return_value.post.return_value = mock_response

        # Patch module-level config
        with patch("llm.client.LLM_API_KEY", "test-key"):
            with patch("llm.client.LLM_BASE_URL", "http://test"):
                with patch("llm.client.LLM_MODEL", "test-model"):
                    client = LLMClient()
                    result = client.analyze_jd("招聘Python开发")
                    assert "skills_required" in result
                    assert result["skills_required"] == ["Python"]

    def test_match_score_parses_json(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({
                "total_score": 85,
                "dimensions": {},
                "tags": ["推荐"],
                "greeting_tone": "专业",
            })}}]
        }
        mock_httpx.return_value.post.return_value = mock_response

        with patch("llm.client.LLM_API_KEY", "test-key"):
            with patch("llm.client.LLM_BASE_URL", "http://test"):
                with patch("llm.client.LLM_MODEL", "test-model"):
                    client = LLMClient()
                    result = client.match_score("简历", "JD", "公司")
                    assert result["total_score"] == 85
                    assert "推荐" in result["tags"]

    def test_generate_greeting_returns_string(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "您好，我是Python开发..."}}]
        }
        mock_httpx.return_value.post.return_value = mock_response

        with patch("llm.client.LLM_API_KEY", "test-key"):
            with patch("llm.client.LLM_BASE_URL", "http://test"):
                with patch("llm.client.LLM_MODEL", "test-model"):
                    client = LLMClient()
                    result = client.generate_greeting("JD", "简历", "专业")
                    assert isinstance(result, str)
                    assert len(result) > 0

    def test_analyze_resume(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({
                "strengths": ["技术强"],
                "weaknesses": ["经验少"],
                "missing_keywords": ["Docker"],
                "suggestions": ["学习Docker"],
            })}}]
        }
        mock_httpx.return_value.post.return_value = mock_response

        with patch("llm.client.LLM_API_KEY", "test-key"):
            with patch("llm.client.LLM_BASE_URL", "http://test"):
                with patch("llm.client.LLM_MODEL", "test-model"):
                    client = LLMClient()
                    result = client.analyze_resume("简历内容", [
                        {"word": "python", "frequency": "80%"}
                    ])
                    assert "strengths" in result
                    assert len(result["strengths"]) > 0
