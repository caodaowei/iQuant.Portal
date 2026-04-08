-- 创建验证表，用于测试数据库连接和基本操作
CREATE TABLE IF NOT EXISTS verification_tests (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(100) NOT NULL,
    test_type VARCHAR(50) NOT NULL,
    test_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 添加注释
COMMENT ON TABLE verification_tests IS '验证测试表，用于验证数据库连接和基本操作';
COMMENT ON COLUMN verification_tests.test_name IS '测试名称';
COMMENT ON COLUMN verification_tests.test_type IS '测试类型';
COMMENT ON COLUMN verification_tests.test_data IS '测试数据(JSON格式)';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_verification_tests_type ON verification_tests(test_type);
CREATE INDEX IF NOT EXISTS idx_verification_tests_created ON verification_tests(created_at);
