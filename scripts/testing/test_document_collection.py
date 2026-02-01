#!/usr/bin/env python3
"""
文書収集機能のテスト
"""

import os
import sys
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# パスを追加
sys.path.insert(0, os.path.dirname(__file__))

def test_document_collection():
    """文書収集機能のテスト"""

    print("=" * 60)
    print("文書収集機能のテスト")
    print("=" * 60)

    # RAGサービスの初期化
    from line_qa_system.rag_service import RAGService

    print("\n🔧 RAGServiceを初期化中...")
    rag_service = RAGService()

    if not rag_service.is_enabled:
        print("❌ RAGサービスが有効になっていません")
        return

    print(f"✅ RAGサービスが有効です")
    print(f"   モード: {'完全RAG' if hasattr(rag_service, 'embedding_model') and rag_service.embedding_model else '代替RAG'}")

    # DocumentCollectorの初期化
    from line_qa_system.document_collector import DocumentCollector

    print("\n🔧 DocumentCollectorを初期化中...")
    collector = DocumentCollector(rag_service)

    if not collector.credentials:
        print("❌ Google認証情報が取得できませんでした")
        return

    print("✅ Google認証情報を取得しました")

    # 文書収集を実行
    print("\n📚 文書収集を開始します...")
    print("-" * 60)

    try:
        # Google Sheetsから収集
        print("\n1️⃣ Google Sheetsから収集中...")
        collector._collect_sheets_documents()
        print("   ✅ Google Sheets収集完了")

        # Google Docsから収集
        print("\n2️⃣ Google Docsから収集中...")
        collector._collect_docs_documents()
        print("   ✅ Google Docs収集完了")

        # Google Driveから収集
        print("\n3️⃣ Google Driveから収集中...")
        print("   検索クエリ:")
        print("     - text/plain")
        print("     - text/csv")
        print("     - application/pdf")
        print("     - application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        print("     - application/vnd.ms-excel")

        collector._collect_drive_documents()
        print("   ✅ Google Drive収集完了")

        print("\n" + "=" * 60)
        print("✅ 文書収集が完了しました")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_document_collection()
