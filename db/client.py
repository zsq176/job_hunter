"""SQLite 数据库操作封装"""
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from contextlib import contextmanager

from config import DB_PATH
from db.schema import SCHEMA_SQL


class Database:
    """数据库操作封装"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA_SQL)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── 岗位操作 ──

    def insert_jobs(self, jobs: list[dict]) -> dict:
        """批量插入岗位，返回 {total, new, duplicates}"""
        new_count = 0
        dup_count = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._conn() as conn:
            for job in jobs:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO jobs
                        (id, platform, title, company, salary_raw, salary_min, salary_max,
                         city, experience, education, welfare, jd_raw, company_info, created_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            job.get("security_id") or job.get("id", ""),
                            job.get("platform", "zhipin"),
                            job.get("title", ""),
                            job.get("company", ""),
                            job.get("salary", ""),
                            self._parse_salary(job.get("salary", ""))[0],
                            self._parse_salary(job.get("salary", ""))[1],
                            job.get("city", ""),
                            job.get("experience", ""),
                            job.get("education", ""),
                            json.dumps(job.get("welfare", []), ensure_ascii=False),
                            job.get("jd_raw", ""),
                            json.dumps(job.get("company_info", {}), ensure_ascii=False),
                            now,
                        ),
                    )
                    if conn.total_changes > 0:
                        new_count += 1
                    else:
                        dup_count += 1
                except sqlite3.IntegrityError:
                    dup_count += 1

        return {"total": len(jobs), "new": new_count, "duplicates": dup_count}

    def _parse_salary(self, salary_str: str) -> tuple:
        """解析 '25K-40K' → (25, 40)"""
        if not salary_str:
            return (None, None)
        try:
            parts = salary_str.replace("K", "").replace("k", "").split("-")
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
            return (None, None)
        except (ValueError, AttributeError):
            return (None, None)

    def update_job(self, job_id: str, **kwargs):
        """更新岗位字段"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        kwargs["updated_at"] = now
        sets = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [job_id]
        with self._conn() as conn:
            conn.execute(f"UPDATE jobs SET {sets} WHERE id=?", values)

    def get_job(self, job_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            return dict(row) if row else None

    def list_jobs(self, status: str = None, score_min: int = None,
                  score_max: int = None, sort_by: str = "created_at",
                  order: str = "desc", limit: int = 20, offset: int = 0) -> dict:
        """查询岗位列表，支持筛选分页"""
        where = []
        params = []
        if status:
            where.append("status=?")
            params.append(status)
        if score_min is not None:
            where.append("score>=?")
            params.append(score_min)
        if score_max is not None:
            where.append("score<=?")
            params.append(score_max)

        where_clause = " AND ".join(where) if where else "1=1"
        order_dir = "DESC" if order == "desc" else "ASC"

        with self._conn() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {where_clause}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM jobs WHERE {where_clause} ORDER BY {sort_by} {order_dir} LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()

        return {"total": total, "jobs": [dict(r) for r in rows]}

    def get_unanalyzed_jobs(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE (jd_analyzed IS NULL OR jd_analyzed = '') AND jd_raw != ''"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_ungreeted_jobs(self, min_score: int = 70) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE greeting_sent=0 AND score>=? ORDER BY score DESC",
                (min_score,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── 打招呼操作 ──

    def record_greeting(self, job_id: str, status: str, message: str = "",
                        error: str = "", batch_id: str = ""):
        with self._conn() as conn:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """INSERT INTO greetings (job_id, batch_id, status, message, error, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (job_id, batch_id, status, message, error, now),
            )
            conn.execute(
                "UPDATE jobs SET greeting_sent=1, greeting_text=?, greeting_status=?, greeting_sent_at=? WHERE id=?",
                (message, status, now, job_id),
            )

    # ── 流水线统计 ──

    def get_pipeline_stats(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            analyzed = conn.execute("SELECT COUNT(*) FROM jobs WHERE jd_analyzed IS NOT NULL AND jd_analyzed != ''").fetchone()[0]
            matched = conn.execute("SELECT COUNT(*) FROM jobs WHERE score>=70").fetchone()[0]
            greeted = conn.execute("SELECT COUNT(*) FROM jobs WHERE greeting_sent=1").fetchone()[0]
            replied = conn.execute("SELECT COUNT(*) FROM greetings WHERE reply_text IS NOT NULL").fetchone()[0]
            return {
                "total_jobs": total,
                "analyzed": analyzed,
                "matched_high": matched,
                "greeted": greeted,
                "replied": replied,
            }

    def log_pipeline(self, batch_id: str, action: str, total: int,
                     success: int, failed: int, detail: str = "", error: str = "",
                     duration_ms: int = 0):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO pipeline_log (batch_id, action, total, success, failed, detail, error, duration_ms)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (batch_id, action, total, success, failed, detail, error, duration_ms),
            )

    # ── 简历操作 ──

    def save_resume(self, raw_text: str, filename: str = "") -> int:
        text_hash = hashlib.sha256(raw_text.encode()).hexdigest()
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT id, version FROM resume_cache WHERE hash=?", (text_hash,)
            ).fetchone()
            if existing:
                return existing["id"]

            conn.execute(
                "UPDATE resume_cache SET is_active=0"
            )
            conn.execute(
                """INSERT INTO resume_cache (hash, filename, raw_text, is_active, version)
                   VALUES (?,?,?,1, COALESCE((SELECT MAX(version)+1 FROM resume_cache), 1))""",
                (text_hash, filename, raw_text),
            )
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_active_resume(self) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM resume_cache WHERE is_active=1 ORDER BY version DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def update_resume_analysis(self, resume_id: int, report: str, suggestions: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE resume_cache SET analyzed_report=?, suggestions=? WHERE id=?",
                (report, suggestions, resume_id),
            )

    # ── 偏好配置 ──

    def save_preference(self, key: str, value: Any):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn() as conn:
            conn.execute(
                "REPLACE INTO preferences (key, value, updated_at) VALUES (?,?,?)",
                (key, json.dumps(value, ensure_ascii=False), now),
            )

    def get_preference(self, key: str) -> Optional[Any]:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else None

    def get_all_preferences(self) -> dict:
        with self._conn() as conn:
            rows = conn.execute("SELECT key, value FROM preferences").fetchall()
            return {r["key"]: json.loads(r["value"]) for r in rows}

    # ── 市场数据分析 ──

    def get_market_keywords(self, top_n: int = 10) -> list[dict]:
        """从已分析的 JD 中统计关键词频率"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT jd_analyzed FROM jobs WHERE jd_analyzed IS NOT NULL AND jd_analyzed != ''"
            ).fetchall()

        freq = {}
        total = len(rows)
        for row in rows:
            try:
                data = json.loads(row["jd_analyzed"])
                skills = data.get("skills_required", [])
                for skill in skills:
                    skill = skill.strip().lower()
                    freq[skill] = freq.get(skill, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue

        sorted_words = sorted(freq.items(), key=lambda x: -x[1])
        return [
            {"word": w, "count": c, "frequency": f"{c/total*100:.0f}%"}
            for w, c in sorted_words[:top_n]
        ]
