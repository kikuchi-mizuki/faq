#!/usr/bin/env python3
"""
データベースセットアップスクリプト
Railwayで実行するための簡易版
"""

import os
import subprocess
import sys

def setup_database():
    """データベースをセットアップ"""
    print("🚀 データベースセットアップを開始します...")
    
    # 環境変数を確認
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL環境変数が設定されていません")
        return False
    
    print(f"📊 データベースURL: {database_url[:20]}...")
    
    # psqlコマンドで直接実行
    try:
        # pgvector拡張を有効化
        print("🔧 pgvector拡張を有効化中...")
        result = subprocess.run([
            'psql', database_url, '-c', 'CREATE EXTENSION IF NOT EXISTS vector;'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ pgvector拡張が有効化されました")
        else:
            print(f"❌ pgvector拡張の有効化に失敗: {result.stderr}")
            return False
        
        # テーブルを作成
        print("📋 テーブルを作成中...")
        
        # 文書テーブル
        subprocess.run([
            'psql', database_url, '-c', '''
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
            '''
        ])
        
        # ベクトルテーブル
        subprocess.run([
            'psql', database_url, '-c', '''
            CREATE TABLE IF NOT EXISTS document_embeddings (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                embedding vector(384),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            '''
        ])
        
        # インデックス
        subprocess.run([
            'psql', database_url, '-c', '''
            CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector 
            ON document_embeddings USING ivfflat (embedding vector_cosine_ops);
            '''
        ])
        
        print("✅ データベースセットアップが完了しました")
        return True
        
    except Exception as e:
        print(f"❌ セットアップ中にエラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    if setup_database():
        print("🎉 データベースの準備が完了しました！")
        sys.exit(0)
    else:
        print("❌ データベースセットアップに失敗しました")
        sys.exit(1)
