"""SQLite 表结构定义"""
SCHEMA_SQL = """
-- 岗位表
CREATE TABLE IF NOT EXISTS jobs (
    id                TEXT PRIMARY KEY,
    platform          TEXT DEFAULT 'zhipin',
    search_keyword    TEXT,
    title             TEXT NOT NULL,
    company           TEXT,
    salary_raw        TEXT,
    salary_min        INTEGER,
    salary_max        INTEGER,
    city              TEXT,
    experience        TEXT,
    education         TEXT,
    welfare           TEXT,
    jd_raw            TEXT,
    jd_analyzed       TEXT,
    jd_analyzed_at    TEXT,
    company_info      TEXT,
    status            TEXT DEFAULT 'new',
    score             INTEGER,
    score_detail      TEXT,
    score_updated_at  TEXT,
    tags              TEXT,
    greeting_sent     INTEGER DEFAULT 0,
    greeting_text     TEXT,
    greeting_sent_at  TEXT,
    greeting_status   TEXT,
    created_at        TEXT DEFAULT (datetime('now','localtime')),
    updated_at        TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs(city);

-- 打招呼记录表
CREATE TABLE IF NOT EXISTS greetings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id            TEXT NOT NULL,
    batch_id          TEXT,
    status            TEXT NOT NULL,
    message           TEXT,
    reply_text        TEXT,
    reply_at          TEXT,
    error             TEXT,
    retry_count       INTEGER DEFAULT 0,
    next_retry_at     TEXT,
    created_at        TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE INDEX IF NOT EXISTS idx_greetings_status ON greetings(status);
CREATE INDEX IF NOT EXISTS idx_greetings_job ON greetings(job_id);

-- 流水线日志表
CREATE TABLE IF NOT EXISTS pipeline_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id          TEXT NOT NULL,
    action            TEXT NOT NULL,
    total             INTEGER DEFAULT 0,
    success           INTEGER DEFAULT 0,
    failed            INTEGER DEFAULT 0,
    detail            TEXT,
    duration_ms       INTEGER,
    error             TEXT,
    created_at        TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_pipeline_action ON pipeline_log(action);
CREATE INDEX IF NOT EXISTS idx_pipeline_batch ON pipeline_log(batch_id);

-- 简历缓存表
CREATE TABLE IF NOT EXISTS resume_cache (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    hash              TEXT NOT NULL UNIQUE,
    filename          TEXT,
    raw_text          TEXT NOT NULL,
    analyzed_report   TEXT,
    suggestions       TEXT,
    is_active         INTEGER DEFAULT 1,
    version           INTEGER DEFAULT 1,
    created_at        TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_resume_active ON resume_cache(is_active);

-- 意向配置表
CREATE TABLE IF NOT EXISTS preferences (
    key               TEXT PRIMARY KEY,
    value             TEXT NOT NULL,
    updated_at        TEXT DEFAULT (datetime('now','localtime'))
);
"""
