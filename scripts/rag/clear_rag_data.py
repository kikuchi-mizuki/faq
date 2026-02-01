#!/usr/bin/env python3
"""
Supabase RAGデータクリアスクリプト
重複データを削除して、データベースをクリーンな状態にします
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def clear_rag_data(auto_confirm=False):
    """RAGデータベースの全データをクリア"""
    print("=" * 60)
    print("🧹 Supabase RAGデータのクリアを開始します")
    print("=" * 60)

    # 環境変数を確認
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL環境変数が設定されていません")
        print("💡 .envファイルを確認してください")
        return False

    print(f"📊 データベースURL: {database_url[:30]}...")

    try:
        # データベースに接続
        print("🔌 データベースに接続中...")
        conn = psycopg2.connect(database_url, connect_timeout=10)

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # 現在のデータ数を確認
            print("\n📊 クリア前のデータ数:")
            cursor.execute("SELECT COUNT(*) as count FROM documents;")
            doc_count = cursor.fetchone()['count']
            print(f"  - documents: {doc_count}件")

            cursor.execute("SELECT COUNT(*) as count FROM document_embeddings;")
            emb_count = cursor.fetchone()['count']
            print(f"  - document_embeddings: {emb_count}件")

            if doc_count == 0 and emb_count == 0:
                print("\n✅ データベースは既に空です")
                return True

            # 確認プロンプト
            print(f"\n⚠️  合計 {doc_count}件の文書と{emb_count}件のEmbeddingを削除します")

            if not auto_confirm:
                response = input("本当に削除しますか？ (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    print("❌ キャンセルされました")
                    return False
            else:
                print("✅ 自動確認モード: 削除を実行します")

            # データを削除
            print("\n🗑️  データを削除中...")

            # document_embeddingsを先に削除（外部キー制約のため）
            cursor.execute("DELETE FROM document_embeddings;")
            print("  ✅ document_embeddingsを削除しました")

            # documentsを削除
            cursor.execute("DELETE FROM documents;")
            print("  ✅ documentsを削除しました")

            # シーケンスをリセット（IDを1から再開）
            cursor.execute("ALTER SEQUENCE documents_id_seq RESTART WITH 1;")
            cursor.execute("ALTER SEQUENCE document_embeddings_id_seq RESTART WITH 1;")
            print("  ✅ IDシーケンスをリセットしました")

            conn.commit()

            # 削除後のデータ数を確認
            print("\n📊 クリア後のデータ数:")
            cursor.execute("SELECT COUNT(*) as count FROM documents;")
            doc_count = cursor.fetchone()['count']
            print(f"  - documents: {doc_count}件")

            cursor.execute("SELECT COUNT(*) as count FROM document_embeddings;")
            emb_count = cursor.fetchone()['count']
            print(f"  - document_embeddings: {emb_count}件")

        conn.close()

        print("\n" + "=" * 60)
        print("✅ RAGデータのクリアが完了しました！")
        print("=" * 60)
        print("\n💡 次のステップ:")
        print("  1. Webフォームでファイルをアップロード:")
        print("     https://line-qa-system-production.up.railway.app/upload")
        print("  2. または、スクリプトでアップロード:")
        print("     ./upload_file_to_rag.sh path/to/file.pdf")
        print("  3. 文書収集を実行:")
        print("     curl -X POST https://your-domain.com/admin/collect-documents \\")
        print("       -H 'X-API-Key: your_admin_api_key'")
        print()

        return True

    except psycopg2.Error as e:
        print(f"❌ データベースエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return False

def show_current_data():
    """現在のRAGデータを表示（削除前確認用）"""
    print("=" * 60)
    print("📋 現在のRAGデータ一覧")
    print("=" * 60)

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL環境変数が設定されていません")
        return False

    try:
        conn = psycopg2.connect(database_url, connect_timeout=10)

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # 文書一覧を取得
            cursor.execute("""
                SELECT
                    source_type,
                    source_id,
                    title,
                    COUNT(*) as chunk_count,
                    MIN(created_at) as created_at
                FROM documents
                GROUP BY source_type, source_id, title
                ORDER BY created_at DESC;
            """)

            documents = cursor.fetchall()

            if not documents:
                print("\n📭 データベースは空です")
                return True

            print(f"\n合計 {len(documents)}種類の文書:")
            print()

            for i, doc in enumerate(documents, 1):
                print(f"{i}. {doc['source_type']}: {doc['title']}")
                print(f"   - ソースID: {doc['source_id']}")
                print(f"   - チャンク数: {doc['chunk_count']}")
                print(f"   - 作成日時: {doc['created_at']}")
                print()

        conn.close()
        return True

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    # コマンドライン引数をチェック
    if len(sys.argv) > 1 and sys.argv[1] == '--show':
        # データ一覧表示モード
        show_current_data()
    elif len(sys.argv) > 1 and sys.argv[1] in ['--yes', '-y']:
        # 自動確認モード
        if clear_rag_data(auto_confirm=True):
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        # データクリアモード（確認プロンプトあり）
        if clear_rag_data(auto_confirm=False):
            sys.exit(0)
        else:
            sys.exit(1)
