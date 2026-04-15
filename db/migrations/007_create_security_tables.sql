-- 安全相关数据库表

-- ==================== 用户表 ====================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_role CHECK (role IN ('admin', 'trader', 'analyst', 'viewer'))
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

COMMENT ON TABLE users IS '系统用户表';
COMMENT ON COLUMN users.role IS '用户角色: admin, trader, analyst, viewer';
COMMENT ON COLUMN users.failed_login_attempts IS '连续失败登录次数';
COMMENT ON COLUMN users.locked_until IS '账户锁定直到（防止暴力破解）';


-- ==================== 审计日志表 ====================
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100),
    resource_id VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

COMMENT ON TABLE audit_logs IS '用户操作审计日志';
COMMENT ON COLUMN audit_logs.action IS '操作类型: LOGIN, LOGOUT, CREATE_ORDER, DELETE_STRATEGY, etc.';
COMMENT ON COLUMN audit_logs.resource IS '资源类型: ORDER, STRATEGY, BACKTEST, USER, etc.';
COMMENT ON COLUMN audit_logs.details IS '操作详细信息（JSON格式）';


-- ==================== API Token 表（可选，用于 API Key 认证）====================
CREATE TABLE IF NOT EXISTS api_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    permissions JSONB,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_api_tokens_user ON api_tokens(user_id);
CREATE INDEX idx_api_tokens_hash ON api_tokens(token_hash);

COMMENT ON TABLE api_tokens IS 'API 访问令牌表';
COMMENT ON COLUMN api_tokens.permissions IS '令牌权限范围（JSON数组）';


-- ==================== IP 黑名单表 ====================
CREATE TABLE IF NOT EXISTS ip_blacklist (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(45) UNIQUE NOT NULL,
    reason VARCHAR(255),
    blocked_by INTEGER REFERENCES users(id),
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ip_blacklist_ip ON ip_blacklist(ip_address);
CREATE INDEX idx_ip_blacklist_active ON ip_blacklist(is_active);

COMMENT ON TABLE ip_blacklist IS 'IP 黑名单表';
COMMENT ON COLUMN ip_blacklist.expires_at IS '封禁过期时间（NULL 表示永久）';


-- ==================== 会话表（用于管理用户会话）====================
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token_hash VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);

COMMENT ON TABLE user_sessions IS '用户会话表';
COMMENT ON COLUMN user_sessions.refresh_token_hash IS '刷新令牌的哈希值';


-- ==================== 插入默认管理员账户 ====================
-- 密码: admin123 (需要在应用启动时修改)
INSERT INTO users (username, email, password_hash, role)
VALUES (
    'admin',
    'admin@iquant.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYILp92S.0i',  -- bcrypt hash of 'admin123'
    'admin'
) ON CONFLICT (username) DO NOTHING;


-- ==================== 视图：最近登录活动 ====================
CREATE OR REPLACE VIEW recent_login_activity AS
SELECT
    u.username,
    u.email,
    u.role,
    al.ip_address,
    al.created_at as login_time,
    al.details->>'user_agent' as user_agent
FROM audit_logs al
JOIN users u ON al.user_id = u.id
WHERE al.action = 'LOGIN'
ORDER BY al.created_at DESC
LIMIT 100;


-- ==================== 视图：安全事件统计 ====================
CREATE OR REPLACE VIEW security_events_summary AS
SELECT
    DATE(created_at) as event_date,
    action,
    COUNT(*) as event_count,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT ip_address) as unique_ips
FROM audit_logs
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), action
ORDER BY event_date DESC, event_count DESC;
