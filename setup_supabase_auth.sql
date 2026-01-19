-- Supabase認証テーブルのセットアップスクリプト
-- このスクリプトをSupabase SQL Editorで実行してください

-- 1. 認証済みユーザーテーブル
CREATE TABLE IF NOT EXISTS authenticated_users (
    id SERIAL PRIMARY KEY,
    line_user_id VARCHAR(255) UNIQUE NOT NULL,
    store_code VARCHAR(50) NOT NULL,
    staff_id VARCHAR(50) NOT NULL,
    staff_name VARCHAR(255),
    store_name VARCHAR(255),
    auth_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックスの作成（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_authenticated_users_line_user_id ON authenticated_users(line_user_id);
CREATE INDEX IF NOT EXISTS idx_authenticated_users_store_code ON authenticated_users(store_code);
CREATE INDEX IF NOT EXISTS idx_authenticated_users_expires_at ON authenticated_users(expires_at);

-- 2. 認証ログテーブル（監査用）
CREATE TABLE IF NOT EXISTS auth_logs (
    id SERIAL PRIMARY KEY,
    line_user_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL, -- 'login', 'logout', 'refresh', 'revoke'
    store_code VARCHAR(50),
    staff_id VARCHAR(50),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_auth_logs_line_user_id ON auth_logs(line_user_id);
CREATE INDEX IF NOT EXISTS idx_auth_logs_created_at ON auth_logs(created_at);

-- 3. updated_atを自動更新するトリガー
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_authenticated_users_updated_at
    BEFORE UPDATE ON authenticated_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 4. 期限切れ認証の自動削除（オプション）
-- 注意: Supabaseの無料プランでは定期実行機能が制限されている場合があります
CREATE OR REPLACE FUNCTION cleanup_expired_auth()
RETURNS void AS $$
BEGIN
    DELETE FROM authenticated_users
    WHERE expires_at IS NOT NULL
    AND expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Row Level Security (RLS) の無効化（アプリケーションレベルで認証を管理）
ALTER TABLE authenticated_users DISABLE ROW LEVEL SECURITY;
ALTER TABLE auth_logs DISABLE ROW LEVEL SECURITY;

-- 完了メッセージ
DO $$
BEGIN
    RAISE NOTICE '✅ 認証テーブルのセットアップが完了しました';
    RAISE NOTICE '📊 テーブル: authenticated_users, auth_logs';
    RAISE NOTICE '🔐 RLS: 無効（アプリケーションレベルで管理）';
END $$;
