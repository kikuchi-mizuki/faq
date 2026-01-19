"""
認証データベースサービス
Supabaseに認証情報を永続化
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog
import psycopg2
from psycopg2.extras import RealDictCursor

from .config import Config
from .utils import hash_user_id

logger = structlog.get_logger(__name__)


class AuthDBService:
    """認証データベースサービス"""

    def __init__(self):
        """初期化"""
        self.database_url = os.getenv('DATABASE_URL')
        self.connection = None
        self.is_enabled = False

        if self.database_url:
            try:
                self._connect()
                self.is_enabled = True
                logger.info("認証データベースサービスを初期化しました")
            except Exception as e:
                logger.error("認証データベースの接続に失敗しました", error=str(e))
                logger.warning("認証データはメモリのみで管理されます")
        else:
            logger.warning("DATABASE_URLが設定されていません。認証データはメモリのみで管理されます")

    def _connect(self):
        """データベースに接続"""
        try:
            self.connection = psycopg2.connect(self.database_url)
            logger.info("認証データベースに接続しました")
        except Exception as e:
            logger.error("データベース接続エラー", error=str(e))
            raise

    def _ensure_connection(self):
        """接続が有効か確認し、必要に応じて再接続"""
        if not self.is_enabled:
            return False

        try:
            if self.connection is None or self.connection.closed:
                self._connect()
            else:
                # 接続テスト
                with self.connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("データベース接続確認エラー", error=str(e))
            try:
                self._connect()
                return True
            except:
                return False

    def save_auth(
        self,
        line_user_id: str,
        store_code: str,
        staff_id: str,
        staff_name: str = "",
        store_name: str = "",
        expires_days: int = 30
    ) -> bool:
        """認証情報を保存"""
        if not self._ensure_connection():
            return False

        try:
            expires_at = datetime.now() + timedelta(days=expires_days)

            with self.connection.cursor() as cursor:
                # UPSERTクエリ（既存の場合は更新、新規の場合は挿入）
                query = """
                INSERT INTO authenticated_users
                    (line_user_id, store_code, staff_id, staff_name, store_name, auth_time, expires_at, last_activity)
                VALUES (%s, %s, %s, %s, %s, NOW(), %s, NOW())
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
                """

                cursor.execute(query, (
                    line_user_id,
                    store_code,
                    staff_id,
                    staff_name,
                    store_name,
                    expires_at
                ))

            self.connection.commit()

            # 認証ログを記録
            self._log_auth_action(line_user_id, 'login', store_code, staff_id, success=True)

            logger.info("認証情報を保存しました",
                       user_id=hash_user_id(line_user_id),
                       store_code=store_code,
                       staff_id=staff_id)

            return True

        except Exception as e:
            logger.error("認証情報の保存に失敗しました",
                        user_id=hash_user_id(line_user_id),
                        error=str(e))
            if self.connection:
                self.connection.rollback()
            return False

    def get_auth(self, line_user_id: str) -> Optional[Dict[str, Any]]:
        """認証情報を取得"""
        if not self._ensure_connection():
            return None

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                SELECT
                    line_user_id,
                    store_code,
                    staff_id,
                    staff_name,
                    store_name,
                    auth_time,
                    expires_at,
                    last_activity
                FROM authenticated_users
                WHERE line_user_id = %s
                AND (expires_at IS NULL OR expires_at > NOW())
                """

                cursor.execute(query, (line_user_id,))
                result = cursor.fetchone()

                if result:
                    # 最終アクティビティを更新
                    self._update_last_activity(line_user_id)

                    return dict(result)

                return None

        except Exception as e:
            logger.error("認証情報の取得に失敗しました",
                        user_id=hash_user_id(line_user_id),
                        error=str(e))
            return None

    def is_authenticated(self, line_user_id: str) -> bool:
        """認証済みかチェック"""
        auth = self.get_auth(line_user_id)
        return auth is not None

    def delete_auth(self, line_user_id: str) -> bool:
        """認証情報を削除"""
        if not self._ensure_connection():
            return False

        try:
            with self.connection.cursor() as cursor:
                query = "DELETE FROM authenticated_users WHERE line_user_id = %s"
                cursor.execute(query, (line_user_id,))

            self.connection.commit()

            # 認証ログを記録
            self._log_auth_action(line_user_id, 'logout', success=True)

            logger.info("認証情報を削除しました", user_id=hash_user_id(line_user_id))
            return True

        except Exception as e:
            logger.error("認証情報の削除に失敗しました",
                        user_id=hash_user_id(line_user_id),
                        error=str(e))
            if self.connection:
                self.connection.rollback()
            return False

    def _update_last_activity(self, line_user_id: str):
        """最終アクティビティ時刻を更新"""
        try:
            with self.connection.cursor() as cursor:
                query = """
                UPDATE authenticated_users
                SET last_activity = NOW()
                WHERE line_user_id = %s
                """
                cursor.execute(query, (line_user_id,))

            self.connection.commit()

        except Exception as e:
            logger.debug("最終アクティビティの更新に失敗しました",
                        user_id=hash_user_id(line_user_id),
                        error=str(e))
            # エラーは無視（重要ではない）

    def _log_auth_action(
        self,
        line_user_id: str,
        action: str,
        store_code: str = None,
        staff_id: str = None,
        success: bool = True,
        error_message: str = None
    ):
        """認証アクションをログに記録"""
        if not self._ensure_connection():
            return

        try:
            with self.connection.cursor() as cursor:
                query = """
                INSERT INTO auth_logs
                    (line_user_id, action, store_code, staff_id, success, error_message)
                VALUES (%s, %s, %s, %s, %s, %s)
                """

                cursor.execute(query, (
                    line_user_id,
                    action,
                    store_code,
                    staff_id,
                    success,
                    error_message
                ))

            self.connection.commit()

        except Exception as e:
            logger.debug("認証ログの記録に失敗しました", error=str(e))
            # エラーは無視（重要ではない）

    def get_all_authenticated_users(self) -> List[Dict[str, Any]]:
        """全ての認証済みユーザーを取得"""
        if not self._ensure_connection():
            return []

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                SELECT
                    line_user_id,
                    store_code,
                    staff_id,
                    staff_name,
                    store_name,
                    auth_time,
                    expires_at,
                    last_activity
                FROM authenticated_users
                WHERE expires_at IS NULL OR expires_at > NOW()
                ORDER BY last_activity DESC
                """

                cursor.execute(query)
                results = cursor.fetchall()

                return [dict(row) for row in results]

        except Exception as e:
            logger.error("認証済みユーザー一覧の取得に失敗しました", error=str(e))
            return []

    def cleanup_expired_auth(self) -> int:
        """期限切れの認証情報を削除"""
        if not self._ensure_connection():
            return 0

        try:
            with self.connection.cursor() as cursor:
                query = """
                DELETE FROM authenticated_users
                WHERE expires_at IS NOT NULL
                AND expires_at < NOW()
                """

                cursor.execute(query)
                deleted_count = cursor.rowcount

            self.connection.commit()

            if deleted_count > 0:
                logger.info("期限切れ認証情報を削除しました", count=deleted_count)

            return deleted_count

        except Exception as e:
            logger.error("期限切れ認証情報の削除に失敗しました", error=str(e))
            if self.connection:
                self.connection.rollback()
            return 0

    def health_check(self) -> bool:
        """ヘルスチェック"""
        return self._ensure_connection()

    def __del__(self):
        """デストラクタ: 接続をクローズ"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.debug("認証データベース接続をクローズしました")
