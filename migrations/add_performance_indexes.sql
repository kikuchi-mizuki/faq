-- パフォーマンス改善のためのインデックス追加
-- 作成日: 2026-01-24
-- 目的: 文書一覧クエリと検索クエリの高速化

-- 1. documentsテーブルのインデックス
-- source_type, source_id による検索を高速化
CREATE INDEX IF NOT EXISTS idx_documents_source
ON documents(source_type, source_id);

-- created_at での降順ソートを高速化
CREATE INDEX IF NOT EXISTS idx_documents_created_at
ON documents(created_at DESC);

-- is_full_text_chunk によるフィルタリングを高速化
CREATE INDEX IF NOT EXISTS idx_documents_full_text_flag
ON documents(is_full_text_chunk)
WHERE is_full_text_chunk IS NOT NULL;

-- 複合インデックス: source_type, source_id, created_at
-- 文書一覧取得クエリ全体を最適化
CREATE INDEX IF NOT EXISTS idx_documents_composite
ON documents(source_type, source_id, created_at DESC);

-- 2. document_embeddingsテーブルのインデックス
-- document_id による JOIN を高速化
CREATE INDEX IF NOT EXISTS idx_document_embeddings_doc_id
ON document_embeddings(document_id);

-- 既存のベクトル検索インデックスは create_tables() で作成済み
-- (ivfflat インデックス)

-- 3. VACUUM ANALYZE でテーブル統計を更新
-- クエリプランナーが最適なプランを選択できるようにする
VACUUM ANALYZE documents;
VACUUM ANALYZE document_embeddings;
