#!/usr/bin/env python3
"""
RAGServiceの初期化状態を診断するスクリプト
Railway環境での問題の原因を特定する
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("📊 RAGService初期化診断")
print("=" * 80)

# 1. 環境変数の確認
print("\n1️⃣ 環境変数の確認")
print("-" * 80)

env_vars = {
    "GEMINI_API_KEY": os.getenv('GEMINI_API_KEY'),
    "DATABASE_URL": os.getenv('DATABASE_URL'),
    "RAG_LIGHTWEIGHT_MODE": os.getenv('RAG_LIGHTWEIGHT_MODE', 'false'),
    "EMBEDDING_MODEL": os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
    "SIMILARITY_THRESHOLD": os.getenv('SIMILARITY_THRESHOLD', '0.15'),
}

for key, value in env_vars.items():
    if key in ["GEMINI_API_KEY", "DATABASE_URL"]:
        # 機密情報はマスク
        display_value = "✅ 設定あり" if value else "❌ 未設定"
    else:
        display_value = value
    print(f"  {key}: {display_value}")

# 2. 依存関係の確認
print("\n2️⃣ 依存関係の確認")
print("-" * 80)

dependencies = {
    "sentence-transformers": None,
    "numpy": None,
    "psycopg2": None,
    "google-generativeai": None,
}

for package_name in dependencies.keys():
    try:
        module_name = package_name.replace('-', '_')
        if module_name == "google_generativeai":
            module_name = "google.generativeai"

        __import__(module_name)
        dependencies[package_name] = "✅ インストール済み"
    except ImportError as e:
        dependencies[package_name] = f"❌ インストールされていません: {e}"

for package, status in dependencies.items():
    print(f"  {package}: {status}")

# 3. RAGServiceの初期化テスト
print("\n3️⃣ RAGServiceの初期化テスト")
print("-" * 80)

try:
    # プロジェクトのパスを追加
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from line_qa_system.rag_service import RAGService

    print("  RAGServiceをインポートしています...")
    rag = RAGService()

    print(f"\n  初期化結果:")
    print(f"    is_enabled: {rag.is_enabled}")
    print(f"    db_pool: {rag.db_pool is not None}")
    print(f"    embedding_model: {rag.embedding_model is not None}")
    print(f"    gemini_model: {rag.gemini_model is not None}")

    # 4. 診断結果のサマリー
    print("\n4️⃣ 診断結果")
    print("-" * 80)

    if rag.is_enabled and rag.embedding_model and rag.db_pool:
        print("  ✅ 完全RAG機能: 正常に動作しています")
    elif rag.is_enabled and rag.gemini_model:
        print("  ⚠️ 代替RAG機能（Geminiのみ）: ベクトル検索は利用できません")
        print("     → これが現在の問題の原因です！")
    else:
        print("  ❌ RAG機能: 無効化されています")

    # 5. 推奨される対応
    print("\n5️⃣ 推奨される対応")
    print("-" * 80)

    if os.getenv('RAG_LIGHTWEIGHT_MODE', 'false').lower() == 'true':
        print("  ⚠️ RAG_LIGHTWEIGHT_MODE=true が設定されています")
        print("     → Railway環境変数から削除してください")
        print("     → コマンド: railway variables delete RAG_LIGHTWEIGHT_MODE")

    if not rag.embedding_model:
        print("  ⚠️ Embeddingモデルが初期化されていません")
        print("     → 原因:")
        print("       - RAG_LIGHTWEIGHT_MODE=trueが設定されている")
        print("       - sentence-transformersがインストールされていない")
        print("       - メモリ不足でモデルがロードできない")
        print("     → 対策:")
        print("       1. Railway環境変数を確認")
        print("       2. Railwayのメモリを確認（推奨: 1GB以上）")
        print("       3. 依存関係を再インストール（poetry install）")

    if not rag.db_pool:
        print("  ⚠️ データベース接続プールが初期化されていません")
        print("     → DATABASE_URLが正しく設定されているか確認してください")

except Exception as e:
    print(f"  ❌ エラーが発生しました: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("診断完了")
print("=" * 80)
