#!/usr/bin/env python3
"""
サポート情報の類似度スコアを確認
なぜ「配送時間」の質問でサポート情報が検索されないのかを診断
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from line_qa_system.rag_service import RAGService
import psycopg2
from psycopg2.extras import RealDictCursor

print("=" * 80)
print("🔍 サポート情報の類似度診断")
print("=" * 80)

# RAGServiceを初期化
print("\n1️⃣ RAGServiceを初期化しています...")
rag = RAGService()

if not rag.is_enabled or not rag.embedding_model:
    print("❌ RAG機能が無効です")
    sys.exit(1)

# テストクエリ
query = "配送にはどれくらい時間がかかる？"
print(f"\n2️⃣ クエリのEmbeddingを生成: 「{query}」")

# クエリのEmbeddingを生成
query_embedding = rag._generate_embedding(query)
embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'

print(f"  ✅ Embedding生成完了: shape={query_embedding.shape}")

# データベースから全文書の類似度を取得
print("\n3️⃣ 全文書の類似度スコアを計算中...")

conn = rag.db_pool.getconn()
try:
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT
                d.id,
                d.title,
                d.source_type,
                SUBSTRING(d.content, 1, 100) as content_preview,
                1 - (de.embedding <=> %s::vector) as similarity
            FROM documents d
            JOIN document_embeddings de ON d.id = de.document_id
            WHERE d.chunk_index >= 0
            ORDER BY similarity DESC
        """, (embedding_str,))

        results = cursor.fetchall()

        print(f"\n📊 全{len(results)}件の類似度スコア:")
        print("-" * 80)

        for i, row in enumerate(results, 1):
            marker = ""
            if 'サポート' in row['title']:
                marker = " ⭐ <- サポート情報"

            print(f"{i:2d}. [{row['similarity']:.4f}] {row['title']}{marker}")
            if marker:
                print(f"     内容: {row['content_preview']}...")

        # 類似度閾値の確認
        print(f"\n📏 現在の類似度閾値: {rag.similarity_threshold}")

        # サポート情報のスコア
        support_docs = [r for r in results if 'サポート' in r['title']]
        if support_docs:
            print(f"\n⭐ サポート情報のスコア:")
            for doc in support_docs:
                is_above_threshold = doc['similarity'] > rag.similarity_threshold
                status = "✅ 閾値以上" if is_above_threshold else "❌ 閾値未満"
                print(f"  - {doc['title']}: {doc['similarity']:.4f} {status}")

finally:
    rag.db_pool.putconn(conn)

print("\n" + "=" * 80)
print("診断完了")
print("=" * 80)
