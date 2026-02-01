#!/usr/bin/env python3
"""
「送料」クエリの類似度テスト
セクション分割後の改善を確認
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from line_qa_system.rag_service import RAGService

print("=" * 80)
print("🔍 送料クエリの類似度テスト")
print("=" * 80)

# RAGServiceを初期化
print("\n1️⃣ RAGServiceを初期化しています...")
rag = RAGService()

if not rag.is_enabled or not rag.embedding_model:
    print("❌ RAG機能が無効です")
    sys.exit(1)

# テストクエリ
query = "送料はいくらですか？"
print(f"\n2️⃣ クエリ: 「{query}」")

# クエリのEmbeddingを生成
query_embedding = rag._generate_embedding(query)
embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'

print(f"  ✅ Embedding生成完了: shape={query_embedding.shape}")

# データベースから全文書の類似度を取得
print("\n3️⃣ 全文書の類似度スコアを計算中...")

conn = rag.db_pool.getconn()
try:
    with conn.cursor() as cursor:
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
            LIMIT 15
        """, (embedding_str,))

        results = cursor.fetchall()

        print(f"\n📊 類似度TOP15:")
        print("-" * 80)

        for i, row in enumerate(results, 1):
            marker = ""
            if '配送' in row[1] or '送料' in row[1] or 'FAQ' in row[1]:
                marker = " ⭐ <- 新しいセクション"

            print(f"{i:2d}. [{row[4]:.4f}] {row[1]}{marker}")
            if marker:
                print(f"     内容: {row[3]}...")

        # 類似度閾値の確認
        print(f"\n📏 現在の類似度閾値: {rag.similarity_threshold}")

        # 新しいセクションのスコア
        section_docs = [r for r in results if '配送' in r[1] or '支払' in r[1] or '返品' in r[1]]
        if section_docs:
            print(f"\n⭐ 新しいセクションのスコア:")
            for doc in section_docs:
                is_above_threshold = doc[4] > rag.similarity_threshold
                status = "✅ 閾値以上" if is_above_threshold else "❌ 閾値未満"
                rank = results.index(doc) + 1
                print(f"  - {doc[1]}: {doc[4]:.4f} {status} (順位: {rank}位)")

finally:
    rag.db_pool.putconn(conn)

print("\n" + "=" * 80)
print("診断完了")
print("=" * 80)
