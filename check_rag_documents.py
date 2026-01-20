#!/usr/bin/env python3
"""
RAGデータベースの文書を確認
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# 環境変数の読み込み
load_dotenv()

def check_rag_documents():
    """RAGデータベースの文書を確認"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL環境変数が設定されていません")
        return

    try:
        print("=" * 60)
        print("RAGデータベース 文書確認")
        print("=" * 60)

        # データベース接続
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 文書の総数を確認
        cur.execute("SELECT COUNT(*) as count FROM documents")
        total = cur.fetchone()['count']
        print(f"\n📊 総文書数: {total}件")

        # 文書の詳細を取得
        cur.execute("""
            SELECT
                id,
                source_type,
                source_id,
                title,
                LEFT(content, 100) as content_preview,
                metadata,
                created_at,
                updated_at
            FROM documents
            ORDER BY created_at DESC
        """)

        documents = cur.fetchall()

        if not documents:
            print("\n⚠️ 文書が1件も登録されていません")
            print("\n💡 対処方法:")
            print("1. Railwayのログで文書収集のエラーを確認")
            print("2. 手動で文書収集を実行:")
            print("   curl -X POST https://your-domain.railway.app/admin/collect-documents \\")
            print("     -H 'X-API-Key: your_admin_api_key'")
            return

        print(f"\n📄 登録済み文書:")
        print("-" * 60)

        for i, doc in enumerate(documents, 1):
            print(f"\n{i}. 【{doc['source_type']}】 {doc['title']}")
            print(f"   ID: {doc['id']}")
            print(f"   Source ID: {doc['source_id']}")
            print(f"   内容プレビュー: {doc['content_preview']}...")
            print(f"   作成日時: {doc['created_at']}")
            print(f"   更新日時: {doc['updated_at']}")

            if doc['metadata']:
                print(f"   メタデータ:")
                for key, value in doc['metadata'].items():
                    print(f"     - {key}: {value}")

        # ソース別の統計
        print("\n" + "=" * 60)
        print("📊 ソース別統計:")
        print("-" * 60)
        cur.execute("""
            SELECT
                source_type,
                COUNT(*) as count
            FROM documents
            GROUP BY source_type
            ORDER BY count DESC
        """)

        stats = cur.fetchall()
        for stat in stats:
            print(f"  {stat['source_type']}: {stat['count']}件")

        # Embeddingの確認
        print("\n" + "=" * 60)
        print("🔍 Embedding確認:")
        print("-" * 60)
        cur.execute("SELECT COUNT(*) as count FROM document_embeddings")
        embedding_count = cur.fetchone()['count']
        print(f"  総Embedding数: {embedding_count}件")

        if embedding_count != total:
            print(f"  ⚠️ 文書数とEmbedding数が一致しません")
            print(f"     文書: {total}件 vs Embedding: {embedding_count}件")
        else:
            print(f"  ✅ 全ての文書にEmbeddingが生成されています")

        cur.close()
        conn.close()

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_rag_documents()
