"""
認証サービス
LINEログイン認証とスタッフ認証を管理
"""

import os
import time
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import structlog

from .config import Config
from .utils import hash_user_id

logger = structlog.get_logger(__name__)


class AuthService:
    """認証サービス"""
    
    def __init__(self):
        """初期化"""
        self.auth_enabled = Config.AUTH_ENABLED
        self.auth_timeout = Config.AUTH_TIMEOUT
        self.auth_max_attempts = Config.AUTH_MAX_ATTEMPTS
        self.auth_session_days = Config.AUTH_SESSION_DAYS
        
        # 認証状態の管理
        self.auth_states = {}  # 認証フローの状態管理
        self.pending_auth = {}  # 認証待ちのユーザー
        self.temp_data = {}  # 一時的な認証データ
        
        logger.info("認証サービスを初期化しました", 
                   auth_enabled=self.auth_enabled,
                   auth_timeout=self.auth_timeout,
                   auth_max_attempts=self.auth_max_attempts)
    
    def is_authenticated(self, user_id: str) -> bool:
        """ユーザーが認証済みかチェック"""
        if not self.auth_enabled:
            return True  # 認証が無効な場合は常に認証済み
        
        try:
            # セッションから認証状態を確認
            from .session_service import SessionService
            session_service = SessionService()
            session = session_service.get_session(user_id)
            
            if not session:
                return False
            
            # 認証済みフラグの確認
            if not session.get('authenticated', False):
                return False
            
            # セッションの有効期限確認
            expires_at = session.get('expires_at')
            if expires_at and datetime.now() > datetime.fromisoformat(expires_at):
                logger.info("セッションが期限切れです", user_id=hash_user_id(user_id))
                return False
            
            # 店舗・スタッフ情報の確認
            store_code = session.get('store_code')
            staff_id = session.get('staff_id')
            
            if not store_code or not staff_id:
                return False
            
            # スタッフの現在のステータス確認
            from .staff_service import StaffService
            staff_service = StaffService()
            staff = staff_service.get_staff(store_code, staff_id)
            
            if not staff or staff['status'] != 'active':
                logger.info("スタッフのステータスが無効です", 
                           user_id=hash_user_id(user_id),
                           store_code=store_code,
                           staff_id=staff_id)
                return False
            
            return True
            
        except Exception as e:
            logger.error("認証チェック中にエラーが発生しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            return False
    
    def get_auth_state(self, user_id: str) -> str:
        """認証フローの状態を取得"""
        return self.auth_states.get(user_id, 'not_started')
    
    def set_auth_state(self, user_id: str, state: str):
        """認証フローの状態を設定"""
        self.auth_states[user_id] = state
        logger.debug("認証状態を設定しました", 
                    user_id=hash_user_id(user_id), 
                    state=state)
    
    def start_auth_process(self, user_id: str) -> str:
        """認証プロセスを開始"""
        try:
            # 認証待ちリストに追加
            self.pending_auth[user_id] = {
                'started_at': datetime.now(),
                'attempts': 0,
                'state': 'line_login_required'
            }
            
            # 認証状態を設定
            self.set_auth_state(user_id, 'line_login_required')
            
            logger.info("認証プロセスを開始しました", user_id=hash_user_id(user_id))
            
            return "認証が必要です。\n\n" \
                   "スタッフの方は下のボタンを押して認証してください。"
            
        except Exception as e:
            logger.error("認証プロセスの開始に失敗しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            return "認証の開始に失敗しました。管理者にお問い合わせください。"
    
    def is_auth_pending(self, user_id: str) -> bool:
        """認証待ちかチェック"""
        return user_id in self.pending_auth
    
    def get_auth_attempts(self, user_id: str) -> int:
        """認証試行回数を取得"""
        if user_id in self.pending_auth:
            return self.pending_auth[user_id]['attempts']
        return 0
    
    def increment_auth_attempts(self, user_id: str):
        """認証試行回数を増加"""
        if user_id in self.pending_auth:
            self.pending_auth[user_id]['attempts'] += 1
    
    def clear_auth_pending(self, user_id: str):
        """認証待ちをクリア"""
        if user_id in self.pending_auth:
            del self.pending_auth[user_id]
        if user_id in self.auth_states:
            del self.auth_states[user_id]
        if user_id in self.temp_data:
            del self.temp_data[user_id]
    
    def set_temp_store_code(self, user_id: str, store_code: str):
        """一時的な店舗コードを設定"""
        if user_id not in self.temp_data:
            self.temp_data[user_id] = {}
        self.temp_data[user_id]['store_code'] = store_code
    
    def get_temp_store_code(self, user_id: str) -> Optional[str]:
        """一時的な店舗コードを取得"""
        if user_id in self.temp_data:
            return self.temp_data[user_id].get('store_code')
        return None
    
    def complete_auth(self, user_id: str, store_code: str, staff_id: str, staff_info: dict) -> bool:
        """認証完了処理"""
        try:
            # セッションに認証情報を保存
            from .session_service import SessionService
            session_service = SessionService()
            
            expires_at = datetime.now() + timedelta(days=self.auth_session_days)
            
            session_data = {
                'authenticated': True,
                'store_code': store_code,
                'staff_id': staff_id,
                'staff_name': staff_info.get('staff_name', ''),
                'store_name': staff_info.get('store_name', ''),
                'auth_time': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat()
            }
            
            # セッションに保存（30日間有効）
            session_service.set_session(user_id, session_data, ttl=2592000)
            
            # スタッフの最終利用日時を更新
            from .staff_service import StaffService
            staff_service = StaffService()
            staff_service.update_last_activity(store_code, staff_id)
            
            # 認証待ちをクリア
            self.clear_auth_pending(user_id)
            
            logger.info("認証が完了しました", 
                       user_id=hash_user_id(user_id),
                       store_code=store_code,
                       staff_id=staff_id)
            
            return True
            
        except Exception as e:
            logger.error("認証完了処理に失敗しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            return False
    
    def get_store_name(self, user_id: str) -> str:
        """店舗名を取得"""
        try:
            from .session_service import SessionService
            session_service = SessionService()
            session = session_service.get_session(user_id)
            
            if session:
                return session.get('store_name', '')
            return ''
            
        except Exception as e:
            logger.error("店舗名の取得に失敗しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            return ''
    
    def deauthenticate_user(self, user_id: str) -> bool:
        """ユーザーの認証を無効化"""
        try:
            # セッションを削除
            from .session_service import SessionService
            session_service = SessionService()
            session_service.delete_session(user_id)
            
            # 認証状態をクリア
            self.clear_auth_pending(user_id)
            
            logger.info("ユーザーの認証を無効化しました", user_id=hash_user_id(user_id))
            return True
            
        except Exception as e:
            logger.error("認証の無効化に失敗しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            return False
    
    def get_auth_stats(self) -> Dict[str, Any]:
        """認証統計を取得"""
        try:
            from .session_service import SessionService
            session_service = SessionService()
            
            # 認証済みユーザー数（概算）
            # 実際の実装では、より詳細な統計を取得可能
            
            return {
                'auth_enabled': self.auth_enabled,
                'pending_auth_count': len(self.pending_auth),
                'auth_states_count': len(self.auth_states),
                'temp_data_count': len(self.temp_data)
            }
            
        except Exception as e:
            logger.error("認証統計の取得に失敗しました", error=str(e))
            return {
                'auth_enabled': self.auth_enabled,
                'error': str(e)
            }
