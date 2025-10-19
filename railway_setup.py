#!/usr/bin/env python3
"""
Railwayで自動実行するデータベースセットアップスクリプト
"""

import os
import sys
import time
import subprocess
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

def run_sql_command(sql_command):
    """SQLコマンドを実行"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL環境変数が設定されていません")
            return False
        
        # psqlコマンドで実行
        result = subprocess.run([
            'psql', database_url, '-c', sql_command
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"SQLコマンドが正常に実行されました: {sql_command[:50]}...")
            return True
        else:
            logger.error(f"SQLコマンドの実行に失敗しました: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("SQLコマンドの実行がタイムアウトしました")
        return False
    except Exception as e:
        logger.error(f"SQLコマンドの実行中にエラーが発生しました: {e}")
        return False

def setup_database():
    """データベースをセットアップ"""
    logger.info("🚀 データベースセットアップを開始します...")
    
    # 環境変数を確認
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL環境変数が設定されていません")
        return False
    
    logger.info(f"📊 データベースURL: {database_url[:20]}...")
    
    # 1. pgvector拡張を有効化
    logger.info("🔧 pgvector拡張を有効化中...")
    if not run_sql_command("CREATE EXTENSION IF NOT EXISTS vector;"):
        logger.error("pgvector拡張の有効化に失敗しました")
        return False
    
    # 2. 文書テーブルを作成
    logger.info("📋 文書テーブルを作成中...")
    create_documents_table = """
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
    """
    if not run_sql_command(create_documents_table):
        logger.error("文書テーブルの作成に失敗しました")
        return False
    
    # 3. ベクトルテーブルを作成
    logger.info("🔢 ベクトルテーブルを作成中...")
    create_embeddings_table = """
    CREATE TABLE IF NOT EXISTS document_embeddings (
        id SERIAL PRIMARY KEY,
        document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
        embedding vector(384),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    if not run_sql_command(create_embeddings_table):
        logger.error("ベクトルテーブルの作成に失敗しました")
        return False
    
    # 4. インデックスを作成
    logger.info("📊 ベクトルインデックスを作成中...")
    create_index = """
    CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector 
    ON document_embeddings USING ivfflat (embedding vector_cosine_ops);
    """
    if not run_sql_command(create_index):
        logger.error("ベクトルインデックスの作成に失敗しました")
        return False
    
    logger.info("✅ データベースセットアップが完了しました")
    return True

def verify_setup():
    """セットアップの確認"""
    logger.info("🔍 セットアップの確認中...")
    
    # pgvector拡張の確認
    if not run_sql_command("SELECT * FROM pg_extension WHERE extname = 'vector';"):
        logger.error("pgvector拡張の確認に失敗しました")
        return False
    
    # テーブルの確認
    if not run_sql_command("SELECT table_name FROM information_schema.tables WHERE table_name IN ('documents', 'document_embeddings');"):
        logger.error("テーブルの確認に失敗しました")
        return False
    
    logger.info("✅ セットアップの確認が完了しました")
    return True

if __name__ == "__main__":
    print("🚀 Railwayデータベースセットアップを開始します...")
    
    # データベースをセットアップ
    if setup_database():
        print("✅ データベースセットアップが完了しました")
        
        # セットアップの確認
        if verify_setup():
            print("✅ セットアップの確認が完了しました")
            print("🎉 データベースの準備が完了しました！")
            sys.exit(0)
        else:
            print("❌ セットアップの確認に失敗しました")
            sys.exit(1)
    else:
        print("❌ データベースセットアップに失敗しました")
        sys.exit(1)
