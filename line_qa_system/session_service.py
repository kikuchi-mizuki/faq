"""
セッション管理サービス（Redis）
"""

import json
import time
from typing import Optional, Dict, Any
import structlog
import redis
from .config import Config

logger = structlog.get_logger(__name__)


class SessionService:
    """Redisを使用したセッション管理サービス"""

    def __init__(self):
        """初期化"""
        # Redis無効化設定をチェック
        if not Config.REDIS_ENABLED:
            logger.info("Redis無効化設定のため、メモリキャッシュモードで起動します")
            self.redis_client = None
            self._memory_cache: Dict[str, tuple[Any, float]] = {}
            return

        try:
            # Redisクライアントの初期化
            self.redis_client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                password=Config.REDIS_PASSWORD,
                db=Config.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

            # 接続テスト
            self.redis_client.ping()
            logger.info("Redisに接続しました", host=Config.REDIS_HOST, port=Config.REDIS_PORT)

        except Exception as e:
            logger.error("Redisの初期化に失敗しました", error=str(e))
            # Redisが利用できない場合はメモリキャッシュにフォールバック
            self.redis_client = None
            self._memory_cache: Dict[str, tuple[Any, float]] = {}
            logger.warning("メモリキャッシュモードで動作します")

    def set_session(
        self, user_id: str, session_data: Dict[str, Any], ttl: int = 1800
    ) -> bool:
        """
        セッションデータを保存

        Args:
            user_id: ユーザーID
            session_data: セッションデータ
            ttl: 有効期限（秒）デフォルト30分

        Returns:
            成功した場合はTrue
        """
        try:
            key = f"session:{user_id}"
            value = json.dumps(session_data, ensure_ascii=False)
            
            if self.redis_client:
                self.redis_client.setex(key, ttl, value)
            else:
                # メモリキャッシュ
                expire_at = time.time() + ttl
                self._memory_cache[key] = (session_data, expire_at)
            
            logger.debug("セッションを保存しました", user_id=user_id, ttl=ttl)
            return True
            
        except Exception as e:
            logger.error("セッションの保存に失敗しました", user_id=user_id, error=str(e))
            return False

    def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        セッションデータを取得

        Args:
            user_id: ユーザーID

        Returns:
            セッションデータ（存在しない場合はNone）
        """
        try:
            key = f"session:{user_id}"
            
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                # メモリキャッシュ
                if key in self._memory_cache:
                    session_data, expire_at = self._memory_cache[key]
                    if time.time() < expire_at:
                        return session_data
                    else:
                        # 期限切れのため削除
                        del self._memory_cache[key]
            
            return None
            
        except Exception as e:
            logger.error("セッションの取得に失敗しました", user_id=user_id, error=str(e))
            return None

    def delete_session(self, user_id: str) -> bool:
        """
        セッションを削除

        Args:
            user_id: ユーザーID

        Returns:
            成功した場合はTrue
        """
        try:
            key = f"session:{user_id}"
            
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                # メモリキャッシュ
                if key in self._memory_cache:
                    del self._memory_cache[key]
            
            logger.debug("セッションを削除しました", user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("セッションの削除に失敗しました", user_id=user_id, error=str(e))
            return False

    def update_session(
        self, user_id: str, updates: Dict[str, Any], ttl: int = 1800
    ) -> bool:
        """
        セッションデータを更新

        Args:
            user_id: ユーザーID
            updates: 更新する内容
            ttl: 有効期限（秒）

        Returns:
            成功した場合はTrue
        """
        try:
            session = self.get_session(user_id)
            if session is None:
                session = {}
            
            session.update(updates)
            return self.set_session(user_id, session, ttl)
            
        except Exception as e:
            logger.error("セッションの更新に失敗しました", user_id=user_id, error=str(e))
            return False

    def clear_expired_sessions(self):
        """期限切れセッションのクリーンアップ（メモリキャッシュモード用）"""
        if self.redis_client:
            return  # Redisモードでは自動削除されるため不要
        
        try:
            current_time = time.time()
            expired_keys = [
                key for key, (_, expire_at) in self._memory_cache.items()
                if current_time >= expire_at
            ]
            
            for key in expired_keys:
                del self._memory_cache[key]
            
            if expired_keys:
                logger.info("期限切れセッションをクリーンアップしました", count=len(expired_keys))
                
        except Exception as e:
            logger.error("セッションクリーンアップ中にエラー", error=str(e))

    def health_check(self) -> bool:
        """
        ヘルスチェック

        Returns:
            正常な場合はTrue
        """
        try:
            if self.redis_client:
                self.redis_client.ping()
                return True
            else:
                # メモリキャッシュモードは常にTrue
                return True
                
        except Exception as e:
            logger.error("Redisヘルスチェックに失敗しました", error=str(e))
            return False

