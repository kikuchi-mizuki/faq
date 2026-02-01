#!/usr/bin/env python3
"""
テストファイルのアップロードスクリプト
"""

import os
import sys
import time
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from line_qa_system.rag_service import RAGService

def upload_test_files():
    """テストファイルをアップロード"""

    print("=" * 60)
    print("📤 テストファイルアップロード開始")
    print("=" * 60)

    # RAGServiceを初期化
    print("\n🔧 RAGServiceを初期化中...")
    rag_service = RAGService()

    if not rag_service.is_enabled:
        print("❌ RAGServiceが無効です")
        return False

    print(f"✅ RAGService初期化完了")
    print(f"   - DB接続: {rag_service.db_connection is not None}")
    print(f"   - Embeddingモデル: {rag_service.embedding_model is not None}")

    # テストデータディレクトリ
    test_dir = Path(__file__).parent / "test_data"

    if not test_dir.exists():
        print(f"❌ テストデータディレクトリが見つかりません: {test_dir}")
        return False

    # テストファイルのリスト
    test_files = list(test_dir.glob("*.txt"))

    if not test_files:
        print(f"❌ テストファイルが見つかりません: {test_dir}")
        return False

    print(f"\n📁 テストファイル: {len(test_files)}件")
    for f in test_files:
        size_kb = f.stat().st_size / 1024
        print(f"   - {f.name} ({size_kb:.2f}KB)")

    # ファイルをアップロード
    print("\n" + "=" * 60)
    print("📤 アップロード開始")
    print("=" * 60)

    success_count = 0

    for file_path in test_files:
        print(f"\n📄 {file_path.name}")

        # ファイルサイズ
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"   サイズ: {file_size_mb:.4f}MB")

        # 自動生成の判定（1MB未満）
        auto_generate = file_size_mb < 1.0
        print(f"   自動Embedding生成: {'はい' if auto_generate else 'いいえ'}")

        # ファイルを読み込み
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"   ❌ ファイル読み込みエラー: {e}")
            continue

        # アップロード
        try:
            import hashlib
            file_hash = hashlib.md5(content.encode()).hexdigest()

            success = rag_service.add_document(
                source_type="test_upload",
                source_id=f"test_{file_hash}",
                title=file_path.stem,  # ファイル名（拡張子なし）
                content=content,
                metadata={
                    "filename": file_path.name,
                    "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "file_type": "txt",
                    "content_size_mb": round(file_size_mb, 4),
                    "test_data": True
                },
                generate_embeddings=auto_generate
            )

            if success:
                print(f"   ✅ アップロード成功")
                success_count += 1
            else:
                print(f"   ❌ アップロード失敗")

        except Exception as e:
            print(f"   ❌ アップロードエラー: {e}")
            import traceback
            traceback.print_exc()

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 アップロード結果")
    print("=" * 60)
    print(f"成功: {success_count}/{len(test_files)}件")

    # データベースの状態を確認
    if rag_service.db_connection:
        print("\n" + "=" * 60)
        print("🔍 データベース確認")
        print("=" * 60)

        try:
            with rag_service.db_connection.cursor() as cursor:
                # 文書数
                cursor.execute("SELECT COUNT(*) FROM documents WHERE source_type='test_upload';")
                doc_count = cursor.fetchone()[0]
                print(f"📚 テスト文書数: {doc_count}件")

                # Embedding数
                cursor.execute("""
                    SELECT COUNT(DISTINCT e.document_id)
                    FROM document_embeddings e
                    JOIN documents d ON e.document_id = d.id
                    WHERE d.source_type = 'test_upload';
                """)
                embedding_count = cursor.fetchone()[0]
                print(f"🔢 Embedding生成済み: {embedding_count}件")

                # 未生成
                pending_count = doc_count - embedding_count
                if pending_count > 0:
                    print(f"⚠️ Embedding未生成: {pending_count}件")
                    print(f"   → /upload 画面で「Embedding生成」ボタンをクリックしてください")

        except Exception as e:
            print(f"❌ データベース確認エラー: {e}")

    print("\n" + "=" * 60)
    print("✅ テスト完了")
    print("=" * 60)

    return success_count == len(test_files)


if __name__ == "__main__":
    success = upload_test_files()
    sys.exit(0 if success else 1)
