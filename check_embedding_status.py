#!/usr/bin/env python3
"""
Embedding生成状況を確認するスクリプト
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_embedding_status():
    """Embedding生成状況を確認"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URLが設定されていません")
        return

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # 1. 全文書数
        cursor.execute("SELECT COUNT(*) FROM documents WHERE chunk_index >= 0")
        total_docs = cursor.fetchone()[0]
        print(f"📊 全文書数（チャンクのみ）: {total_docs}件")

        # 2. Embedding生成済み文書数
        cursor.execute("""
            SELECT COUNT(DISTINCT d.id)
            FROM documents d
            JOIN document_embeddings de ON d.id = de.document_id
            WHERE d.chunk_index >= 0
        """)
        embedded_docs = cursor.fetchone()[0]
        print(f"✅ Embedding生成済み: {embedded_docs}件")

        # 3. Embedding未生成文書数
        cursor.execute("""
            SELECT COUNT(DISTINCT d.id)
            FROM documents d
            LEFT JOIN document_embeddings de ON d.id = de.document_id
            WHERE d.chunk_index >= 0
              AND de.document_id IS NULL
        """)
        pending_docs = cursor.fetchone()[0]
        print(f"⏳ Embedding未生成: {pending_docs}件")

        # 4. 最新5件のファイル
        print("\n📄 最新5件のファイル:")
        cursor.execute("""
            SELECT
                d.title,
                d.chunk_index,
                CASE WHEN de.id IS NOT NULL THEN 'あり' ELSE 'なし' END as embedding
            FROM documents d
            LEFT JOIN document_embeddings de ON d.id = de.document_id
            WHERE d.chunk_index >= 0
            ORDER BY d.created_at DESC
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  - {row[0]} (chunk_index={row[1]}, Embedding={row[2]})")

        # 5. サポート情報ファイルの確認
        print("\n🔍 'サポート' を含むファイル:")
        cursor.execute("""
            SELECT
                d.title,
                d.content[:100] as content_preview,
                CASE WHEN de.id IS NOT NULL THEN 'あり' ELSE 'なし' END as embedding
            FROM documents d
            LEFT JOIN document_embeddings de ON d.id = de.document_id
            WHERE d.chunk_index >= 0
              AND d.title LIKE '%サポート%'
            ORDER BY d.created_at DESC
        """)
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"  - タイトル: {row[0]}")
                print(f"    内容: {row[1]}...")
                print(f"    Embedding: {row[2]}")
        else:
            print("  見つかりませんでした")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    check_embedding_status()
