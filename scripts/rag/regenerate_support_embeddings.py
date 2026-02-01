#!/usr/bin/env python3
"""
サポート情報のEmbeddingを再生成するスクリプト
"""
import os
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

def regenerate_embeddings():
    """サポート情報のEmbeddingを再生成"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URLが設定されていません")
        return

    # Embeddingモデルを読み込み
    print("📚 Embeddingモデルを読み込んでいます...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print("✅ モデル読み込み完了")

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Embedding未生成のサポート情報を取得
        cursor.execute("""
            SELECT d.id, d.title, d.content
            FROM documents d
            LEFT JOIN document_embeddings de ON d.id = de.document_id
            WHERE d.title LIKE '%サポート%'
              AND d.chunk_index >= 0
              AND de.document_id IS NULL
            ORDER BY d.created_at DESC
        """)

        pending_docs = cursor.fetchall()
        print(f"📊 Embedding未生成のサポート情報: {len(pending_docs)}件")

        for doc_id, title, content in pending_docs:
            print(f"\n🔄 処理中: {title} (ID: {doc_id})")
            print(f"   内容（先頭200文字）: {content[:200]}...")

            # Embeddingを生成
            embedding = model.encode(content)
            embedding_list = embedding.tolist()
            embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'

            print(f"   ✅ Embedding生成完了: shape={embedding.shape}")

            # データベースに保存
            cursor.execute(
                "INSERT INTO document_embeddings (document_id, embedding) VALUES (%s, %s::vector)",
                (doc_id, embedding_str)
            )
            conn.commit()
            print(f"   ✅ データベースに保存完了")

        print(f"\n✅ 全{len(pending_docs)}件のEmbedding生成が完了しました")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    regenerate_embeddings()
