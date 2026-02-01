"""
認証データベースのテストスクリプト
テーブルの存在確認とDB接続をテスト
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def test_connection():
    """データベース接続テスト"""
    print("\n=== データベース接続テスト ===")
    print(f"DATABASE_URL: {DATABASE_URL[:50]}..." if DATABASE_URL else "DATABASE_URL: 未設定")

    if not DATABASE_URL:
        print("❌ DATABASE_URLが設定されていません")
        return False

    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ データベース接続成功")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ データベース接続失敗: {e}")
        return False

def check_tables():
    """テーブルの存在確認"""
    print("\n=== テーブル存在確認 ===")

    if not DATABASE_URL:
        print("❌ DATABASE_URLが設定されていません")
        return False

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # テーブル一覧を取得
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        tables = cursor.fetchall()
        print(f"\n存在するテーブル:")
        for table in tables:
            print(f"  - {table['table_name']}")

        # authenticated_usersテーブルをチェック
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'authenticated_users'
            )
        """)

        result = cursor.fetchone()
        if result['exists']:
            print("\n✅ authenticated_usersテーブルが存在します")

            # テーブル構造を確認
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'authenticated_users'
                ORDER BY ordinal_position
            """)

            columns = cursor.fetchall()
            print("\nテーブル構造:")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']} (NULL: {col['is_nullable']})")
        else:
            print("\n❌ authenticated_usersテーブルが存在しません")
            print("\n以下のSQLを実行してテーブルを作成してください:")
            print("setup_supabase_auth.sql")

        # auth_logsテーブルをチェック
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'auth_logs'
            )
        """)

        result = cursor.fetchone()
        if result['exists']:
            print("\n✅ auth_logsテーブルが存在します")
        else:
            print("\n❌ auth_logsテーブルが存在しません")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ テーブル確認失敗: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_insert():
    """テストデータ挿入"""
    print("\n=== テストデータ挿入 ===")

    if not DATABASE_URL:
        print("❌ DATABASE_URLが設定されていません")
        return False

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # テストユーザーを挿入
        test_user_id = "test_user_123456"

        cursor.execute("""
            INSERT INTO authenticated_users
                (line_user_id, store_code, staff_id, staff_name, store_name, auth_time, expires_at, last_activity)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW() + INTERVAL '30 days', NOW())
            ON CONFLICT (line_user_id)
            DO UPDATE SET
                store_code = EXCLUDED.store_code,
                staff_id = EXCLUDED.staff_id,
                staff_name = EXCLUDED.staff_name,
                store_name = EXCLUDED.store_name,
                auth_time = NOW(),
                expires_at = EXCLUDED.expires_at,
                last_activity = NOW(),
                updated_at = NOW()
        """, (
            test_user_id,
            'STORE004',
            '004',
            'テストスタッフ',
            'テスト店舗',
        ))

        conn.commit()
        print("✅ テストデータ挿入成功")

        # データを確認
        cursor.execute("""
            SELECT line_user_id, store_code, staff_id, staff_name, store_name, auth_time
            FROM authenticated_users
            WHERE line_user_id = %s
        """, (test_user_id,))

        result = cursor.fetchone()
        if result:
            print(f"\n挿入されたデータ:")
            print(f"  - line_user_id: {result[0]}")
            print(f"  - store_code: {result[1]}")
            print(f"  - staff_id: {result[2]}")
            print(f"  - staff_name: {result[3]}")
            print(f"  - store_name: {result[4]}")
            print(f"  - auth_time: {result[5]}")

        # テストデータを削除
        cursor.execute("DELETE FROM authenticated_users WHERE line_user_id = %s", (test_user_id,))
        conn.commit()
        print("\n✅ テストデータ削除成功")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ テストデータ挿入失敗: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_auth_db_service():
    """AuthDBServiceのテスト"""
    print("\n=== AuthDBServiceのテスト ===")

    try:
        from line_qa_system.auth_db_service import AuthDBService

        auth_db = AuthDBService()
        print(f"is_enabled: {auth_db.is_enabled}")
        print(f"has_connection: {auth_db.connection is not None}")

        if not auth_db.is_enabled:
            print("❌ AuthDBServiceが無効化されています")
            return False

        # テストユーザーで認証情報を保存
        test_user_id = "test_user_service_123456"

        print(f"\nテストユーザー {test_user_id} を保存します...")
        success = auth_db.save_auth(
            line_user_id=test_user_id,
            store_code='STORE004',
            staff_id='004',
            staff_name='テストスタッフ',
            store_name='テスト店舗',
            expires_days=30
        )

        if success:
            print("✅ 認証情報保存成功")

            # データを確認
            auth = auth_db.get_auth(test_user_id)
            if auth:
                print(f"\n取得したデータ:")
                print(f"  - store_code: {auth['store_code']}")
                print(f"  - staff_id: {auth['staff_id']}")
                print(f"  - staff_name: {auth['staff_name']}")
                print(f"  - store_name: {auth['store_name']}")
                print(f"  - auth_time: {auth['auth_time']}")
            else:
                print("❌ データの取得に失敗しました")

            # テストデータを削除
            auth_db.delete_auth(test_user_id)
            print("\n✅ テストデータ削除成功")
            return True
        else:
            print("❌ 認証情報保存失敗")
            return False

    except Exception as e:
        print(f"❌ AuthDBServiceのテスト失敗: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("認証データベース診断スクリプト")
    print("=" * 60)

    # 1. 接続テスト
    if not test_connection():
        print("\n⚠️ データベース接続に失敗しました。DATABASE_URLを確認してください。")
        exit(1)

    # 2. テーブル確認
    if not check_tables():
        print("\n⚠️ テーブルの確認に失敗しました。")
        exit(1)

    # 3. テストデータ挿入
    if not test_insert():
        print("\n⚠️ テストデータの挿入に失敗しました。")
        exit(1)

    # 4. AuthDBServiceのテスト
    if not test_auth_db_service():
        print("\n⚠️ AuthDBServiceのテストに失敗しました。")
        exit(1)

    print("\n" + "=" * 60)
    print("✅ 全てのテストが成功しました！")
    print("=" * 60)
