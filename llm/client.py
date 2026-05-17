"""LLM API 封装（兼容 OpenAI 格式）"""
import json
import logging
from typing import Optional
from httpx import Client, Timeout

from config import LLM_API_KEY, LLM_MODEL, LLM_BASE_URL, LLM_TIMEOUT

logger = logging.getLogger("llm")


class LLMClient:
    """LLM API 客户端（兼容 OpenAI 格式）"""

    def __init__(self, api_key: str = LLM_API_KEY, model: str = LLM_MODEL,
                 base_url: str = LLM_BASE_URL):
        if not api_key:
            raise ValueError("LLM_API_KEY 未配置，请在 .env 中填写")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=Timeout(LLM_TIMEOUT),
        )

    def _call(self, messages: list[dict], response_format: Optional[dict] = None) -> str:
        """调 LLM API"""
        body = {"model": self.model, "messages": messages}
        if response_format:
            body["response_format"] = response_format
        logger.debug("LLM call model=%s msg_count=%d", self.model, len(messages))
        resp = self.client.post("/v1/chat/completions", json=body)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def analyze_jd(self, jd_text: str) -> dict:
        """分析 JD，提取结构化信息"""
        prompt = f"""分析以下招聘 JD，提取结构化信息并返回 JSON：

JD 内容：
{jd_text}

返回格式：
{{
  "skills_required": ["技能1", "技能2"],
  "experience_required": "3-5年",
  "education_required": "本科",
  "key_responsibilities": ["职责1", "职责2"],
  "selling_points": ["卖点1", "卖点2"],
  "summary": "一句话总结"
}}"""
        logger.info("analyze_jd len=%d", len(jd_text))
        result = self._call([
            {"role": "system", "content": "你是一个专业的 JD 分析助手。请提取结构化信息返回 JSON。"},
            {"role": "user", "content": prompt},
        ], response_format={"type": "json_object"})
        return json.loads(result)

    def match_score(self, resume_text: str, jd_text: str, company_info: str = "") -> dict:
        """简历匹配评分"""
        prompt = f"""## 候选人简历
{resume_text}

## 目标岗位 JD
{jd_text}

## 公司信息
{company_info if company_info else "无"}

请评估该候选人与岗位的匹配度，返回 JSON：
{{
  "total_score": 85,
  "dimensions": {{
    "skill_match": {{"score": 35, "max": 40, "reason": "..."}},
    "experience_match": {{"score": 25, "max": 30, "reason": "..."}},
    "education_match": {{"score": 8, "max": 10, "reason": "..."}},
    "company_appeal": {{"score": 17, "max": 20, "reason": "..."}}
  }},
  "tags": ["强烈推荐", "薪资匹配"],
  "greeting_tone": "专业",
  "greeting_suggestion": "建议话术方向"
}}"""
        logger.info("match_score jd_len=%d resume_len=%d", len(jd_text), len(resume_text))
        result = self._call([
            {"role": "system", "content": "你是一个专业的求职顾问。严格、客观评估岗位匹配度。只返回 JSON。"},
            {"role": "user", "content": prompt},
        ], response_format={"type": "json_object"})
        return json.loads(result)

    def generate_greeting(self, jd_text: str, resume_text: str, tone: str = "专业") -> str:
        """生成打招呼话术"""
        prompt = f"""基于以下信息生成一段打招呼话术：

## JD 内容
{jd_text}

## 简历摘要
{resume_text}

## 语气
{tone}

要求：
1. 基于 JD 内容定制，不要用通用模板
2. 突出候选人与岗位的匹配点
3. 简洁（30-60字）
4. 附上一句'附上简历供您参考'"""
        logger.info("generate_greeting tone=%s", tone)
        result = self._call([
            {"role": "system", "content": f"你是一个求职助手。用{tone}的语气生成一段 30-60 字的打招呼话术。"},
            {"role": "user", "content": prompt},
        ])
        return result.strip()

    def analyze_resume(self, resume_text: str, market_keywords: list[dict] = None) -> dict:
        """分析简历，给出改进建议"""
        market_data = ""
        if market_keywords:
            market_data = "\n".join(
                [f"- {kw['word']}: {kw['frequency']}" for kw in market_keywords]
            )

        prompt = f"""
## 简历内容
{resume_text}

## 市场高频关键词（目标岗位中出现频率）
{market_data if market_data else "暂无市场数据"}

请分析简历，返回 JSON：
{{
  "strengths": ["优势1", "优势2"],
  "weaknesses": ["不足1", "不足2"],
  "missing_keywords": ["缺少的关键词"],
  "suggestions": ["建议1", "建议2", "建议3"]
}}"""
        logger.info("analyze_resume len=%d", len(resume_text))
        result = self._call([
            {"role": "system", "content": "你是一个专业的简历顾问。分析简历优缺点，给出具体可行的改进建议。返回 JSON。"},
            {"role": "user", "content": prompt},
        ], response_format={"type": "json_object"})
        return json.loads(result)

    def generate_weekly_report(self, stats: dict, greeting_history: list[dict]) -> str:
        """生成求职周报"""
        import datetime
        today = datetime.date.today()
        start_of_week = today - datetime.timedelta(days=today.weekday())

        prompt = f"""
## 本周统计（{start_of_week} ~ {today}）
- 总岗位数: {stats.get('total_jobs', 0)}
- 已分析: {stats.get('analyzed', 0)}
- 高匹配: {stats.get('matched_high', 0)}
- 已打招呼: {stats.get('greeted', 0)}
- 有回复: {stats.get('replied', 0)}

## 打招呼记录
{json.dumps(greeting_history, ensure_ascii=False, indent=2) if greeting_history else "暂无"}

请生成一份简洁的求职周报，包含：
1. 本周求职进度摘要
2. 关键数据
3. 下周行动建议"""
        logger.info("generate_weekly_report")
        return self._call([
            {"role": "system", "content": "你是一个求职助手。生成简洁、有数据支撑的求职周报。"},
            {"role": "user", "content": prompt},
        ])

    def generate_daily_report(self, stats: dict, greeting_history: list[dict]) -> str:
        """生成求职日报"""
        import datetime
        today = datetime.date.today()

        prompt = f"""
## 今日统计（{today}）
- 总岗位数: {stats.get('total_jobs', 0)}
- 已分析: {stats.get('analyzed', 0)}
- 高匹配: {stats.get('matched_high', 0)}
- 已打招呼: {stats.get('greeted', 0)}
- 有回复: {stats.get('replied', 0)}

## 今日打招呼记录
{json.dumps(greeting_history, ensure_ascii=False, indent=2) if greeting_history else "暂无"}

请生成一份简洁的求职日报，包含：
1. 今日求职进度摘要
2. 关键数据
3. 明日行动建议"""
        logger.info("generate_daily_report")
        return self._call([
            {"role": "system", "content": "你是一个求职助手。生成简洁、有数据支撑的求职日报。"},
            {"role": "user", "content": prompt},
        ])
