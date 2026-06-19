-- ============================================
-- StylePianoDiff Web 平台数据库脚本
-- DBMS: SQL Server
-- 说明：包含建表、触发器、存储过程、视图、索引
-- ============================================

-- 1. 创建数据库
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'StylePianoDB')
    CREATE DATABASE StylePianoDB;
GO

USE StylePianoDB;
GO

-- ============================================
-- 2. 数据表创建（共 6 张表）
-- ============================================

-- 2.1 用户表
CREATE TABLE users (
    user_id         INT IDENTITY(1,1) PRIMARY KEY,
    username        NVARCHAR(50) NOT NULL UNIQUE,
    email           NVARCHAR(100) NOT NULL UNIQUE,
    password_hash   NVARCHAR(255) NOT NULL,
    avatar_url      NVARCHAR(500) NULL,          -- 头像图片 URL
    created_at      DATETIME2 DEFAULT GETDATE(),
    last_login      DATETIME2 NULL
);
GO

-- 2.2 作曲家风格表
CREATE TABLE composer_styles (
    composer_id     INT IDENTITY(1,1) PRIMARY KEY,
    name            NVARCHAR(50) NOT NULL,         -- 如 Chopin, Debussy
    era             NVARCHAR(50) NULL,            -- 如 Romantic, Impressionist
    description     NVARCHAR(500) NULL,
    avatar_image    VARBINARY(MAX) NULL,          -- 作曲家头像图片（二进制）
    prototype_vector NVARCHAR(MAX) NULL,           -- 风格向量 JSON
    is_active       BIT DEFAULT 1,
    created_at      DATETIME2 DEFAULT GETDATE()
);
GO

-- 2.3 MIDI 种子文件表
CREATE TABLE midi_files (
    file_id         INT IDENTITY(1,1) PRIMARY KEY,
    user_id         INT NOT NULL,
    file_name       NVARCHAR(255) NOT NULL,
    file_data       VARBINARY(MAX) NOT NULL,      -- MIDI 文件二进制存储
    composer_tag    NVARCHAR(50) NULL,            -- 用户标注的作曲家标签
    duration_sec    FLOAT NULL,
    upload_time     DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_midi_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
GO

-- 2.4 生成任务表（触发器候选：状态自动变更）
CREATE TABLE generation_jobs (
    job_id          INT IDENTITY(1,1) PRIMARY KEY,
    user_id         INT NOT NULL,
    file_id         INT NOT NULL,
    composer_id     INT NOT NULL,
    status          NVARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','running','done','failed')),
    alpha           FLOAT DEFAULT 1.0,            -- 风格强度
    temperature     FLOAT DEFAULT 1.0,            -- 采样温度
    target_bars     INT DEFAULT 8,                -- 生成小节数
    result_file     VARBINARY(MAX) NULL,           -- 生成结果 MIDI 文件
    result_preview  NVARCHAR(MAX) NULL,            -- 生成结果元数据 JSON
    error_message   NVARCHAR(500) NULL,
    created_at      DATETIME2 DEFAULT GETDATE(),
    started_at      DATETIME2 NULL,
    finished_at     DATETIME2 NULL,
    CONSTRAINT fk_job_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_job_file FOREIGN KEY (file_id) REFERENCES midi_files(file_id),
    CONSTRAINT fk_job_composer FOREIGN KEY (composer_id) REFERENCES composer_styles(composer_id)
);
GO

-- 2.5 生成历史/收藏表
CREATE TABLE generation_history (
    history_id      INT IDENTITY(1,1) PRIMARY KEY,
    user_id         INT NOT NULL,
    job_id          INT NOT NULL,
    is_favorite     BIT DEFAULT 0,
    rating          INT NULL CHECK (rating BETWEEN 1 AND 5),
    note            NVARCHAR(500) NULL,
    viewed_at       DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_hist_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_hist_job FOREIGN KEY (job_id) REFERENCES generation_jobs(job_id)
);
GO

-- 2.6 模型版本管理表
CREATE TABLE model_checkpoints (
    checkpoint_id   INT IDENTITY(1,1) PRIMARY KEY,
    version         NVARCHAR(20) NOT NULL,
    stage           INT NOT NULL CHECK (stage IN (1,2,3)),
    file_path       NVARCHAR(500) NOT NULL,
    description     NVARCHAR(500) NULL,
    is_active       BIT DEFAULT 0,
    created_at      DATETIME2 DEFAULT GETDATE()
);
GO

-- ============================================
-- 3. 索引创建
-- ============================================

CREATE INDEX idx_midi_user ON midi_files(user_id);
CREATE INDEX idx_midi_upload ON midi_files(upload_time);
CREATE INDEX idx_job_user_status ON generation_jobs(user_id, status);
CREATE INDEX idx_job_created ON generation_jobs(created_at);
CREATE INDEX idx_hist_user_fav ON generation_history(user_id, is_favorite);
CREATE INDEX idx_composer_active ON composer_styles(is_active);
GO

-- ============================================
-- 4. 触发器：生成任务状态自动更新
-- ============================================

-- 触发器 1：当 result_file 被更新时，自动将状态改为 'done'
CREATE TRIGGER trg_job_auto_done
ON generation_jobs
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF UPDATE(result_file)
    BEGIN
        UPDATE generation_jobs
        SET status = 'done',
            finished_at = GETDATE()
        WHERE job_id IN (SELECT job_id FROM inserted WHERE result_file IS NOT NULL)
          AND status <> 'done';
    END
END;
GO

-- 触发器 2：当 error_message 被更新时，自动将状态改为 'failed'
CREATE TRIGGER trg_job_auto_fail
ON generation_jobs
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF UPDATE(error_message)
    BEGIN
        UPDATE generation_jobs
        SET status = 'failed',
            finished_at = GETDATE()
        WHERE job_id IN (SELECT job_id FROM inserted WHERE error_message IS NOT NULL)
          AND status <> 'failed';
    END
END;
GO

-- ============================================
-- 5. 存储过程
-- ============================================

-- 存储过程 1：统计用户生成概况
CREATE PROCEDURE sp_user_generation_summary
    @user_id INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        u.username,
        COUNT(DISTINCT j.job_id) AS total_jobs,
        SUM(CASE WHEN j.status = 'done' THEN 1 ELSE 0 END) AS success_count,
        SUM(CASE WHEN j.status = 'failed' THEN 1 ELSE 0 END) AS fail_count,
        AVG(CAST(h.rating AS FLOAT)) AS avg_rating,
        MAX(j.created_at) AS last_generate_time
    FROM users u
    LEFT JOIN generation_jobs j ON u.user_id = j.user_id
    LEFT JOIN generation_history h ON j.job_id = h.job_id AND h.user_id = u.user_id
    WHERE u.user_id = @user_id
    GROUP BY u.user_id, u.username;
END;
GO

-- 存储过程 2：统计作曲家风格使用热度
CREATE PROCEDURE sp_composer_usage_stats
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        c.composer_id,
        c.name,
        c.era,
        COUNT(j.job_id) AS usage_count,
        AVG(j.alpha) AS avg_alpha,
        SUM(CASE WHEN j.status = 'done' THEN 1 ELSE 0 END) AS success_count
    FROM composer_styles c
    LEFT JOIN generation_jobs j ON c.composer_id = j.composer_id
    WHERE c.is_active = 1
    GROUP BY c.composer_id, c.name, c.era
    ORDER BY usage_count DESC;
END;
GO

-- 存储过程 3：清理过期失败任务（维护用）
CREATE PROCEDURE sp_cleanup_failed_jobs
    @days_old INT = 7
AS
BEGIN
    SET NOCOUNT ON;
    DELETE FROM generation_jobs
    WHERE status = 'failed'
      AND created_at < DATEADD(DAY, -@days_old, GETDATE());
    SELECT @@ROWCOUNT AS deleted_count;
END;
GO

-- ============================================
-- 6. 视图
-- ============================================

-- 视图 1：用户生成摘要（联合查询）
CREATE VIEW vw_user_generation_summary AS
SELECT
    u.user_id,
    u.username,
    u.email,
    u.created_at AS user_created,
    COUNT(DISTINCT j.job_id) AS total_jobs,
    COUNT(DISTINCT mf.file_id) AS total_uploads,
    COUNT(DISTINCT CASE WHEN h.is_favorite = 1 THEN h.history_id END) AS favorite_count,
    MAX(j.created_at) AS last_job_time
FROM users u
LEFT JOIN midi_files mf ON u.user_id = mf.user_id
LEFT JOIN generation_jobs j ON u.user_id = j.user_id
LEFT JOIN generation_history h ON u.user_id = h.user_id
GROUP BY u.user_id, u.username, u.email, u.created_at;
GO

-- 视图 2：任务详情（含用户、文件、作曲家信息）
CREATE VIEW vw_job_details AS
SELECT
    j.job_id,
    j.status,
    j.alpha,
    j.temperature,
    j.target_bars,
    j.created_at,
    j.started_at,
    j.finished_at,
    DATEDIFF(SECOND, j.started_at, j.finished_at) AS duration_seconds,
    u.username,
    u.email,
    mf.file_name AS seed_file_name,
    c.name AS composer_name,
    c.era AS composer_era
FROM generation_jobs j
JOIN users u ON j.user_id = u.user_id
JOIN midi_files mf ON j.file_id = mf.file_id
JOIN composer_styles c ON j.composer_id = c.composer_id;
GO

-- 视图 3：热门生成作品（按收藏和评分）
CREATE VIEW vw_popular_generations AS
SELECT
    j.job_id,
    j.result_preview,
    j.created_at,
    c.name AS composer_name,
    u.username,
    COUNT(h.history_id) AS view_count,
    SUM(CAST(h.is_favorite AS INT)) AS favorite_count,
    AVG(CAST(h.rating AS FLOAT)) AS avg_rating
FROM generation_jobs j
JOIN composer_styles c ON j.composer_id = c.composer_id
JOIN users u ON j.user_id = u.user_id
LEFT JOIN generation_history h ON j.job_id = h.job_id
WHERE j.status = 'done'
GROUP BY j.job_id, j.result_preview, j.created_at, c.name, u.username
HAVING COUNT(h.history_id) > 0;
GO

-- ============================================
-- 7. 初始化数据：作曲家风格
-- ============================================

INSERT INTO composer_styles (name, era, description, is_active) VALUES
('Bach', 'Baroque', '约翰·塞巴斯蒂安·巴赫，巴洛克时期代表人物，复调与对位法大师', 1),
('Mozart', 'Classical', '沃尔夫冈·阿马德乌斯·莫扎特，古典主义时期，旋律优美结构均衡', 1),
('Beethoven', 'Classical/Romantic', '路德维希·范·贝多芬，古典向浪漫过渡，情感强烈动力充沛', 1),
('Chopin', 'Romantic', '弗雷德里克·肖邦，浪漫主义钢琴诗人，细腻装饰音与 rubato', 1),
('Debussy', 'Impressionist', '克劳德·德彪西，印象派，色彩和声与模糊调性', 1),
('Liszt', 'Romantic', '弗朗茨·李斯特，浪漫主义炫技派，宏大结构与复杂和声', 1);
GO

PRINT '数据库初始化完成！';
GO
