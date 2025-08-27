-- Two Very Auto v3.0 - PostgreSQL 초기화 스크립트
-- 고급 분석 및 보고용 데이터베이스 스키마

-- 확장 기능 설치
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 게임 데이터 테이블 (SQLite에서 마이그레이션)
CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    player_cards JSONB NOT NULL,
    banker_cards JSONB NOT NULL,
    player_total INTEGER NOT NULL,
    banker_total INTEGER NOT NULL,
    result VARCHAR(20) NOT NULL,
    has_pair BOOLEAN NOT NULL DEFAULT FALSE,
    pair_type VARCHAR(20),
    prediction_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- AI 예측 결과 테이블
CREATE TABLE IF NOT EXISTS ai_predictions (
    id SERIAL PRIMARY KEY,
    game_id INTEGER REFERENCES games(id),
    predicted_result VARCHAR(20) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    model_version VARCHAR(20),
    prediction_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    actual_result VARCHAR(20),
    is_correct BOOLEAN,
    validated_at TIMESTAMP WITH TIME ZONE
);

-- 모델 성능 추적 테이블
CREATE TABLE IF NOT EXISTS model_performance (
    id SERIAL PRIMARY KEY,
    model_type VARCHAR(50) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    accuracy DECIMAL(5,4) NOT NULL,
    precision_score DECIMAL(5,4),
    recall_score DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    total_predictions INTEGER NOT NULL,
    correct_predictions INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 시스템 메트릭 테이블
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    cpu_percent DECIMAL(5,2) NOT NULL,
    memory_percent DECIMAL(5,2) NOT NULL,
    disk_usage_percent DECIMAL(5,2),
    network_io_bytes BIGINT,
    active_connections INTEGER,
    games_processed_per_hour INTEGER,
    ai_prediction_latency_ms INTEGER
);

-- 알림 로그 테이블
CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL,
    profile_name VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    channel VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'sent',
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    game_id INTEGER REFERENCES games(id),
    metadata JSONB
);

-- 사용자 세션 테이블
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_agent TEXT,
    ip_address INET,
    session_start TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    session_end TIMESTAMP WITH TIME ZONE,
    page_views INTEGER DEFAULT 1,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_games_timestamp ON games(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_games_table_name ON games(table_name);
CREATE INDEX IF NOT EXISTS idx_games_result ON games(result);
CREATE INDEX IF NOT EXISTS idx_games_has_pair ON games(has_pair);

CREATE INDEX IF NOT EXISTS idx_predictions_game_id ON ai_predictions(game_id);
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON ai_predictions(prediction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_model_type ON ai_predictions(model_type);

CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_sent_at ON notification_logs(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_start ON user_sessions(session_start DESC);

-- 뷰 생성 (일반적인 분석 쿼리)
CREATE OR REPLACE VIEW game_statistics AS
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as total_games,
    COUNT(CASE WHEN has_pair THEN 1 END) as pairs_count,
    COUNT(CASE WHEN result = 'player' THEN 1 END) as player_wins,
    COUNT(CASE WHEN result = 'banker' THEN 1 END) as banker_wins,
    COUNT(CASE WHEN result = 'tie' THEN 1 END) as ties,
    ROUND(AVG(player_total), 2) as avg_player_total,
    ROUND(AVG(banker_total), 2) as avg_banker_total
FROM games
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY hour DESC;

CREATE OR REPLACE VIEW ai_performance_summary AS
SELECT 
    model_type,
    model_version,
    COUNT(*) as total_predictions,
    COUNT(CASE WHEN is_correct = true THEN 1 END) as correct_predictions,
    ROUND(
        COUNT(CASE WHEN is_correct = true THEN 1 END)::DECIMAL / 
        NULLIF(COUNT(CASE WHEN is_correct IS NOT NULL THEN 1 END), 0) * 100, 
        2
    ) as accuracy_percentage,
    ROUND(AVG(confidence), 4) as avg_confidence,
    MIN(prediction_timestamp) as first_prediction,
    MAX(prediction_timestamp) as last_prediction
FROM ai_predictions
WHERE is_correct IS NOT NULL
GROUP BY model_type, model_version
ORDER BY accuracy_percentage DESC;

-- 함수 생성 (데이터 정리용)
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- 30일 이상 된 게임 데이터 삭제
    DELETE FROM ai_predictions 
    WHERE prediction_timestamp < NOW() - INTERVAL '30 days';
    
    DELETE FROM games 
    WHERE timestamp < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- 7일 이상 된 시스템 메트릭 삭제
    DELETE FROM system_metrics 
    WHERE timestamp < NOW() - INTERVAL '7 days';
    
    -- 30일 이상 된 알림 로그 삭제
    DELETE FROM notification_logs 
    WHERE sent_at < NOW() - INTERVAL '30 days';
    
    -- 통계 업데이트
    ANALYZE games;
    ANALYZE ai_predictions;
    ANALYZE system_metrics;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 초기 사용자 및 권한 설정
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO two_auto_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO two_auto_user;
GRANT EXECUTE ON FUNCTION cleanup_old_data() TO two_auto_user;

-- 성공 메시지
DO $$
BEGIN
    RAISE NOTICE 'Two Very Auto v3.0 데이터베이스 초기화 완료!';
    RAISE NOTICE '테이블 생성: ✅';
    RAISE NOTICE '인덱스 생성: ✅';
    RAISE NOTICE '뷰 생성: ✅';
    RAISE NOTICE '권한 설정: ✅';
END;
$$;