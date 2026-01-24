-- ファイル全文を保存するカラムを追加（Gems方式の学習機能）
-- 実行日時: 2026-01-24

-- documentsテーブルにfull_contentカラムを追加
ALTER TABLE documents ADD COLUMN IF NOT EXISTS full_content TEXT;

-- is_full_text_chunk フラグを追加（全文チャンクかどうか）
ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_full_text_chunk BOOLEAN DEFAULT FALSE;

-- インデックスを追加（全文チャンク検索の高速化）
CREATE INDEX IF NOT EXISTS idx_documents_full_text ON documents(source_id, is_full_text_chunk) WHERE is_full_text_chunk = TRUE;

-- コメント
COMMENT ON COLUMN documents.full_content IS 'ファイルの全文（Gems方式の学習用）';
COMMENT ON COLUMN documents.is_full_text_chunk IS '全文チャンクフラグ（TRUE=全文、FALSE=通常チャンク）';
