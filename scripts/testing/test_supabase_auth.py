"""
Supabase認証データベースの診断スクリプト
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_database_connection():
    """データベース接続テスト"""
    print("=" * 60)
    print("Supabase認証データベース診断")
    print("=" * 60)

    # 環境変数の確認
    database_url = os.getenv('DATABASE_URL')
    print(f"\n1. DATABASE_URL設定: {'✅ あり' if database_url else '❌ なし'}")

    if not database_url:
        print("\n❌ DATABASE_URLが設定されていません。")
        print("   .envファイルまたは環境変数を確認してください。")
        return False

    # 接続情報の表示（パスワードは隠す）
    masked_url = database_url.split('@')[1] if '@' in database_url else 'unknown'
    print(f"   接続先: {masked_url}")

    # データベース接続テスト
    try:
        import psycopg2
        print("\n2. psycopg2インポート: ✅ 成功")
    except ImportError as e:
        print(f"\n2. psycopg2インポート: ❌ 失敗 - {e}")
        print("   pip install psycopg2-binary を実行してください")
        return False

    # 接続テスト
    try:
        print("\n3. データベース接続テスト...")
        conn = psycopg2.connect(database_url)
        print("   ✅ 接続成功")

        # テーブル存在確認
        print("\n4. テーブル存在確認...")
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('authenticated_users', 'auth_logs')
                ORDER BY table_name
            """)
            tables = cursor.fetchall()

            if len(tables) == 2:
                print("   ✅ authenticated_users テーブル")
                print("   ✅ auth_logs テーブル")
            elif len(tables) == 1:
                print(f"   ⚠️  {tables[0][0]} テーブルのみ存在")
                print("   ❌ もう一方のテーブルが見つかりません")
            else:
                print("   ❌ テーブルが見つかりません")
                print("\n📝 setup_supabase_auth.sql をSupabase SQL Editorで実行してください")
                conn.close()
                return False

        # データ確認
        print("\n5. 認証データ確認...")
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM authenticated_users")
            count = cursor.fetchone()[0]
            print(f"   認証済みユーザー数: {count}")

            if count > 0:
                cursor.execute("""
                    SELECT line_user_id, store_code, staff_id, staff_name, auth_time
                    FROM authenticated_users
                    ORDER BY auth_time DESC
                    LIMIT 5
                """)
                users = cursor.fetchall()
                print("\n   最新の認証ユーザー:")
                for user in users:
                    line_id_masked = user[0][:10] + "..." if len(user[0]) > 10 else user[0]
                    print(f"   - {line_id_masked} | {user[1]} | {user[2]} | {user[3]} | {user[4]}")

        # ログ確認
        print("\n6. 認証ログ確認...")
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM auth_logs")
            log_count = cursor.fetchone()[0]
            print(f"   ログ件数: {log_count}")

            if log_count > 0:
                cursor.execute("""
                    SELECT action, success, created_at
                    FROM auth_logs
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                logs = cursor.fetchall()
                print("\n   最新のログ:")
                for log in logs:
                    status = "✅" if log[1] else "❌"
                    print(f"   {status} {log[0]} | {log[2]}")

        conn.close()

        print("\n" + "=" * 60)
        print("✅ 診断完了: データベースは正常に動作しています")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        print("\n考えられる原因:")
        print("1. DATABASE_URLが正しくない")
        print("2. Supabaseプロジェクトが停止している")
        print("3. ネットワーク接続の問題")
        print("4. テーブルが作成されていない")
        return False


def test_auth_db_service():
    """AuthDBServiceのテスト"""
    print("\n" + "=" * 60)
    print("AuthDBServiceテスト")
    print("=" * 60)

    try:
        from line_qa_system.auth_db_service import AuthDBService

        auth_db = AuthDBService()
        print(f"\n1. AuthDBService初期化: {'✅ 成功' if auth_db.is_enabled else '❌ 失敗'}")

        if not auth_db.is_enabled:
            print("   データベースが無効化されています")
            return False

        # ヘルスチェック
        print("\n2. ヘルスチェック...")
        if auth_db.health_check():
            print("   ✅ 正常")
        else:
            print("   ❌ 異常")
            return False

        # テストユーザーの作成
        print("\n3. テストユーザー作成...")
        test_user_id = "TEST_USER_123456"
        success = auth_db.save_auth(
            line_user_id=test_user_id,
            store_code="STORE999",
            staff_id="999",
            staff_name="テストユーザー",
            store_name="テスト店舗"
        )

        if success:
            print("   ✅ 作成成功")
        else:
            print("   ❌ 作成失敗")
            return False

        # 認証確認
        print("\n4. 認証確認...")
        if auth_db.is_authenticated(test_user_id):
            print("   ✅ 認証済みと判定")
        else:
            print("   ❌ 認証されていないと判定")
            return False

        # データ取得
        print("\n5. データ取得...")
        auth_data = auth_db.get_auth(test_user_id)
        if auth_data:
            print(f"   ✅ 取得成功")
            print(f"      店舗: {auth_data['store_name']}")
            print(f"      スタッフ: {auth_data['staff_name']}")
        else:
            print("   ❌ 取得失敗")
            return False

        # クリーンアップ
        print("\n6. テストユーザー削除...")
        if auth_db.delete_auth(test_user_id):
            print("   ✅ 削除成功")
        else:
            print("   ❌ 削除失敗")

        print("\n" + "=" * 60)
        print("✅ AuthDBServiceテスト完了")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # データベース接続テスト
    db_ok = test_database_connection()

    if db_ok:
        # AuthDBServiceテスト
        test_auth_db_service()
    else:
        print("\n⚠️  データベース接続に問題があるため、AuthDBServiceテストをスキップします")
