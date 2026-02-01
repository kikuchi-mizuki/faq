#!/usr/bin/env python3
"""
RAG検索の動作テスト
実際にベクトル検索が動作するか確認
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# プロジェクトのパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from line_qa_system.rag_service import RAGService

print("=" * 80)
print("🔍 RAG検索の動作テスト")
print("=" * 80)

# RAGServiceを初期化
print("\n1️⃣ RAGServiceを初期化しています...")
rag = RAGService()

print(f"\n  初期化結果:")
print(f"    is_enabled: {rag.is_enabled}")
print(f"    db_pool: {rag.db_pool is not None}")
print(f"    embedding_model: {rag.embedding_model is not None}")
print(f"    gemini_model: {rag.gemini_model is not None}")

if not rag.is_enabled:
    print("\n❌ RAG機能が無効です。テストを中止します。")
    sys.exit(1)

# テストクエリ
test_queries = [
    "配送にはどれくらい時間がかかる？",
    "配送時間",
    "お届けまでの日数",
]

print("\n2️⃣ ベクトル検索のテスト")
print("-" * 80)

for query in test_queries:
    print(f"\n📝 クエリ: 「{query}」")
    print("-" * 80)

    try:
        # search_similar_documentsを呼び出し
        results = rag.search_similar_documents(query, limit=5)

        print(f"  検索結果: {len(results)}件")

        if results:
            for i, doc in enumerate(results, 1):
                print(f"\n  [{i}] タイトル: {doc.get('title', 'N/A')}")
                print(f"      内容（先頭100文字）: {doc.get('content', '')[:100]}...")
                print(f"      類似度: {doc.get('similarity', 0):.4f}")
                print(f"      ソース: {doc.get('source_type', 'N/A')} - {doc.get('source_id', 'N/A')}")
        else:
            print("  ⚠️ 検索結果が見つかりませんでした")

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("テスト完了")
print("=" * 80)
