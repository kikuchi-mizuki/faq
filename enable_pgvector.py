#!/usr/bin/env python3
"""
pgvector拡張を自動で有効化するスクリプト
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import structlog

# ログ設定
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

def enable_pgvector():
    """pgvector拡張を有効化"""
    try:
        # 環境変数からデータベースURLを取得
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL環境変数が設定されていません")
            return False
        
        logger.info("データベースに接続中...")
        
        # データベースに接続
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cursor:
            # pgvector拡張を有効化
            logger.info("pgvector拡張を有効化中...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # 拡張が有効化されたか確認
            cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
            result = cursor.fetchone()
            
            if result:
                logger.info("✅ pgvector拡張が正常に有効化されました")
                return True
            else:
                logger.error("❌ pgvector拡張の有効化に失敗しました")
                return False
                
    except Exception as e:
        logger.error("pgvector拡張の有効化中にエラーが発生しました", error=str(e))
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def create_tables():
    """必要なテーブルを作成"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL環境変数が設定されていません")
            return False
        
        logger.info("データベースに接続中...")
        
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cursor:
            # 文書テーブル
            logger.info("文書テーブルを作成中...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    source_type VARCHAR(50) NOT NULL,
                    source_id VARCHAR(100) NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    chunk_index INTEGER DEFAULT 0,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # ベクトルテーブル
            logger.info("ベクトルテーブルを作成中...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_embeddings (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                    embedding vector(384),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # インデックスの作成
            logger.info("ベクトルインデックスを作成中...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector 
                ON document_embeddings USING ivfflat (embedding vector_cosine_ops);
            """)
            
            logger.info("✅ データベーステーブルが正常に作成されました")
            return True
            
    except Exception as e:
        logger.error("テーブル作成中にエラーが発生しました", error=str(e))
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 pgvector拡張の有効化を開始します...")
    
    # pgvector拡張を有効化
    if enable_pgvector():
        print("✅ pgvector拡張の有効化が完了しました")
        
        # テーブルを作成
        if create_tables():
            print("✅ データベーステーブルの作成が完了しました")
            print("🎉 データベースの準備が完了しました！")
        else:
            print("❌ テーブル作成に失敗しました")
    else:
        print("❌ pgvector拡張の有効化に失敗しました")
