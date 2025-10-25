"""
最適化された認証フロー
キャッシュベースでパフォーマンスを向上
"""

import os
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

from .config import Config
from .line_client import LineClient
from .store_service import StoreService
from .staff_service import StaffService
from .utils import hash_user_id

logger = structlog.get_logger(__name__)


class OptimizedAuthFlow:
    """最適化された認証フロー - キャッシュベース"""

    _instance = None
    _initialized = False

    def __new__(cls):
        """シングルトンパターン"""
        if cls._instance is None:
            cls._instance = super(OptimizedAuthFlow, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """初期化（一度だけ実行）"""
        if not self._initialized:
            self.line_client = LineClient()
            self.store_service = StoreService()
            self.staff_service = StaffService()
            
            # 認証状態の管理（メモリ内）
            self.auth_states = {}  # ユーザーID -> 認証状態
            self.temp_data = {}    # ユーザーID -> 一時データ
            self.authenticated_users = {}  # ユーザーID -> 認証情報
            
            # キャッシュ管理
            self.cache_expiry = 300  # 5分間のキャッシュ
            self.last_cache_update = 0
            self.cache_valid = False
            
            self._initialized = True
            logger.info("最適化認証フローを初期化しました（キャッシュベース）")

    def _is_cache_valid(self) -> bool:
        """キャッシュが有効かチェック"""
        if not self.cache_valid:
            return False
        
        current_time = time.time()
        return (current_time - self.last_cache_update) < self.cache_expiry

    def _update_cache_if_needed(self):
        """必要に応じてキャッシュを更新"""
        if not self._is_cache_valid():
            try:
                logger.info("キャッシュを更新しています...")
                self.store_service.load_stores_from_sheet()
                self.staff_service.load_staff_data()
                self.last_cache_update = time.time()
                self.cache_valid = True
                logger.info("キャッシュの更新が完了しました")
            except Exception as e:
                logger.error("キャッシュの更新に失敗しました", error=str(e))
                # エラーが発生してもキャッシュは無効化しない

    def process_auth_flow(self, event: Dict[str, Any]) -> bool:
        """
        認証フローを処理する。
        認証フローで処理が完了した場合はTrueを返す。
        """
        try:
            user_id = event["source"]["userId"]
            message_text = event["message"]["text"]
            reply_token = event["replyToken"]

            hashed_user_id = hash_user_id(user_id)

            # 認証が有効でない場合は何もしない
            if not Config.AUTH_ENABLED:
                return False

            # 既に認証済みであれば何もしない
            if self.is_authenticated(user_id):
                return False

            # キャッシュを更新（必要に応じて）
            self._update_cache_if_needed()

            # 現在の認証状態を取得
            current_state = self.auth_states.get(user_id, 'not_started')
            
            logger.info("最適化認証フロー処理中", 
                        user_id=hashed_user_id, 
                        current_state=current_state, 
                        message_text=message_text,
                        cache_valid=self._is_cache_valid())

            # 認証開始
            if message_text.strip().lower() in ["認証", "auth", "ログイン", "login"]:
                self.start_auth(user_id, reply_token)
                return True

            # 店舗コード入力
            elif current_state == 'store_code_input_pending':
                return self.handle_store_code_input(user_id, message_text, reply_token)

            # 社員番号入力
            elif current_state == 'staff_id_input_pending':
                return self.handle_staff_id_input(user_id, message_text, reply_token)

            # その他の場合は認証が必要
            else:
                self.send_auth_required_message(reply_token)
                return True

        except Exception as e:
            logger.error("最適化認証フローの処理に失敗しました", error=str(e))
            return False

    def start_auth(self, user_id: str, reply_token: str):
        """認証を開始"""
        try:
            self.auth_states[user_id] = 'store_code_input_pending'
            self.temp_data[user_id] = {}
            
            message = "認証を開始します。\n\n" \
                    "店舗コードを入力してください。\n" \
                    "例：STORE004"
            
            self.line_client.reply_text(reply_token, message)
            logger.info("認証を開始しました", user_id=hash_user_id(user_id))
            
        except Exception as e:
            logger.error("認証開始に失敗しました", error=str(e))

    def handle_store_code_input(self, user_id: str, message_text: str, reply_token: str) -> bool:
        """店舗コード入力を処理"""
        try:
            # 店舗コードを抽出
            store_code = message_text.strip().upper()
            
            # 店舗の存在確認（キャッシュから）
            store = self.store_service.get_store(store_code)
            if not store:
                self.line_client.reply_text(reply_token, 
                    f"店舗コード「{store_code}」が見つかりません。\n\n正しい店舗コードを入力してください。")
                return True

            if store['status'] != 'active':
                self.line_client.reply_text(reply_token, 
                    f"店舗「{store['store_name']}」は現在利用できません。\n\n管理者にお問い合わせください。")
                return True

            # 店舗コードを一時保存
            self.temp_data[user_id]['store_code'] = store_code
            
            # 認証状態を更新
            self.auth_states[user_id] = 'staff_id_input_pending'
            
            # 社員番号入力を促す
            message = f"店舗「{store['store_name']}」を確認しました。\n\n" \
                    "社員番号を入力してください。\n" \
                    "例：004"
            
            self.line_client.reply_text(reply_token, message)
            logger.info("店舗コードを確認しました", 
                       user_id=hash_user_id(user_id), 
                       store_code=store_code)
            return True

        except Exception as e:
            logger.error("店舗コード入力の処理に失敗しました", error=str(e))
            self.line_client.reply_text(reply_token, 
                "店舗コードの処理中にエラーが発生しました。再度お試しください。")
            return True

    def handle_staff_id_input(self, user_id: str, message_text: str, reply_token: str) -> bool:
        """社員番号入力を処理"""
        try:
            # 社員番号を抽出
            staff_id = message_text.strip()
            
            # 店舗コードを取得
            store_code = self.temp_data.get(user_id, {}).get('store_code')
            if not store_code:
                self.line_client.reply_text(reply_token, 
                    "店舗コードが見つかりません。\n\n最初から認証をやり直してください。")
                return True

            # スタッフの存在確認（キャッシュから）
            staff = self.staff_service.get_staff(store_code, staff_id)
            if not staff:
                self.line_client.reply_text(reply_token, 
                    f"社員番号「{staff_id}」が見つかりません。\n\n正しい社員番号を入力してください。")
                return True

            if staff['status'] != 'active':
                self.line_client.reply_text(reply_token, 
                    f"スタッフ「{staff['staff_name']}」は現在利用できません。\n\n管理者にお問い合わせください。")
                return True

            # 店舗情報を取得
            store = self.store_service.get_store(store_code)
            if not store:
                self.line_client.reply_text(reply_token, 
                    "店舗情報の取得に失敗しました。\n\n最初から認証をやり直してください。")
                return True

            # 認証完了
            logger.info("認証完了処理を開始します", 
                       user_id=hash_user_id(user_id), 
                       store_code=store_code, 
                       staff_id=staff_id)
            
            try:
                self.complete_auth(user_id, store_code, staff_id, store, staff)
                logger.info("認証完了処理が成功しました", 
                           user_id=hash_user_id(user_id))
            except Exception as e:
                logger.error("認証完了処理でエラーが発生しました", 
                           user_id=hash_user_id(user_id), 
                           error=str(e))
                self.line_client.reply_text(reply_token, 
                    "認証の完了処理中にエラーが発生しました。再度お試しください。")
                return True
            
            success_message = f"認証が完了しました！\n\n" \
                            f"店舗: {store['store_name']}\n" \
                            f"スタッフ: {staff['staff_name']}\n\n" \
                            f"Botをご利用いただけます。"
            
            self.line_client.reply_text(reply_token, success_message)
            logger.info("認証が完了しました", 
                       user_id=hash_user_id(user_id), 
                       store_code=store_code, 
                       staff_id=staff_id,
                       final_auth_state=self.auth_states.get(user_id),
                       is_authenticated=self.is_authenticated(user_id))
            return True

        except Exception as e:
            logger.error("社員番号入力の処理に失敗しました", error=str(e))
            self.line_client.reply_text(reply_token, 
                "社員番号の処理中にエラーが発生しました。再度お試しください。")
            return True

    def complete_auth(self, user_id: str, store_code: str, staff_id: str, store: Dict, staff: Dict):
        """認証を完了"""
        try:
            auth_time = datetime.now().isoformat()
            
            # 認証情報をメモリに保存
            self.authenticated_users[user_id] = {
                'store_code': store_code,
                'staff_id': staff_id,
                'store_name': store['store_name'],
                'staff_name': staff['staff_name'],
                'auth_time': auth_time
            }
            
            # 認証状態を完了に設定
            self.auth_states[user_id] = 'authenticated'
            
            # 一時データをクリア
            if user_id in self.temp_data:
                del self.temp_data[user_id]
            
            # スプレッドシートに認証情報を記録（非同期で実行）
            self.update_staff_auth_info_async(store_code, staff_id, user_id, auth_time)
            
            logger.info("認証情報を保存しました", 
                       user_id=hash_user_id(user_id), 
                       store_code=store_code, 
                       staff_id=staff_id,
                       auth_time=auth_time)
            
        except Exception as e:
            logger.error("認証完了処理に失敗しました", error=str(e))
            raise

    def update_staff_auth_info_async(self, store_code: str, staff_id: str, user_id: str, auth_time: str):
        """スタッフの認証情報をスプレッドシートに非同期で更新"""
        try:
            # バックグラウンドでスプレッドシートを更新
            import threading
            
            def update_task():
                try:
                    self.staff_service.update_auth_info(store_code, staff_id, user_id, auth_time)
                    logger.info("スプレッドシートに認証情報を記録しました", 
                               store_code=store_code, 
                               staff_id=staff_id, 
                               user_id=hash_user_id(user_id))
                except Exception as e:
                    logger.error("スプレッドシートの更新に失敗しました", 
                                error=str(e), 
                                store_code=store_code, 
                                staff_id=staff_id)
            
            # 非同期で実行
            thread = threading.Thread(target=update_task)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.error("非同期更新の開始に失敗しました", error=str(e))

    def is_authenticated(self, user_id: str) -> bool:
        """ユーザーが認証済みかチェック（ステータスも確認）"""
        try:
            if user_id not in self.authenticated_users:
                logger.debug("ユーザーが認証済みユーザーリストに存在しません", 
                           user_id=hash_user_id(user_id))
                return False
            
            # 認証済みユーザーのステータスをチェック
            auth_info = self.authenticated_users[user_id]
            store_code = auth_info.get('store_code')
            staff_id = auth_info.get('staff_id')
            
            logger.debug("認証済みユーザーのステータスをチェック中", 
                        user_id=hash_user_id(user_id), 
                        store_code=store_code, 
                        staff_id=staff_id)
            
            if store_code and staff_id:
                # キャッシュを更新（必要に応じて）
                self._update_cache_if_needed()
                
                # スタッフのステータスをチェック
                staff = self.staff_service.get_staff(store_code, staff_id)
                if not staff:
                    logger.warning("スタッフ情報が見つかりません", 
                                  user_id=hash_user_id(user_id), 
                                  store_code=store_code, 
                                  staff_id=staff_id)
                    self.deauthenticate_user(user_id)
                    return False
                
                staff_status = staff.get('status')
                logger.info("スタッフのステータスを確認", 
                           user_id=hash_user_id(user_id), 
                           store_code=store_code, 
                           staff_id=staff_id, 
                           status=staff_status)
                
                if staff_status != 'active':
                    # ステータスが無効な場合は認証を取り消し
                    logger.info("スタッフのステータスが無効になったため認証を取り消します", 
                               user_id=hash_user_id(user_id), 
                               store_code=store_code, 
                               staff_id=staff_id, 
                               status=staff_status)
                    self.deauthenticate_user(user_id)
                    return False
            
            logger.debug("認証チェック完了", 
                        user_id=hash_user_id(user_id), 
                        result=True)
            return True
            
        except Exception as e:
            logger.error("認証チェック中にエラーが発生しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            # エラーが発生した場合は安全のため認証を取り消し
            try:
                self.deauthenticate_user(user_id)
            except:
                pass
            return False

    def get_auth_info(self, user_id: str) -> Optional[Dict]:
        """認証情報を取得"""
        return self.authenticated_users.get(user_id)

    def send_auth_required_message(self, reply_token: str):
        """認証が必要な旨を伝えるメッセージを送信"""
        message = "このBotをご利用いただくには認証が必要です。\n\n" \
                "「認証」と入力してください。"
        try:
            self.line_client.reply_text(reply_token, message)
            logger.info("認証が必要メッセージを送信しました")
        except Exception as e:
            logger.error("認証が必要メッセージの送信に失敗しました", error=str(e))

    def deauthenticate_user(self, user_id: str) -> bool:
        """ユーザーの認証を取り消す"""
        try:
            if user_id in self.authenticated_users:
                # 認証情報を取得
                auth_info = self.authenticated_users[user_id]
                store_code = auth_info.get('store_code')
                staff_id = auth_info.get('staff_id')
                
                # メモリから認証情報を削除
                del self.authenticated_users[user_id]
                
                # 認証状態をリセット
                self.auth_states[user_id] = 'not_started'
                
                logger.info("ユーザーの認証を取り消しました", 
                           user_id=hash_user_id(user_id), 
                           store_code=store_code, 
                           staff_id=staff_id)
                return True
            else:
                logger.warning("認証取り消し対象のユーザーが見つかりません", 
                              user_id=hash_user_id(user_id))
                return False
                
        except Exception as e:
            logger.error("認証取り消しに失敗しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            return False

    def force_cache_update(self):
        """キャッシュを強制更新"""
        self.cache_valid = False
        self._update_cache_if_needed()

    def get_stats(self) -> Dict[str, Any]:
        """認証統計を取得"""
        return {
            'total_authenticated': len(self.authenticated_users),
            'pending_auth': len([s for s in self.auth_states.values() if s != 'authenticated']),
            'auth_states': dict(self.auth_states),
            'cache_valid': self._is_cache_valid(),
            'last_cache_update': self.last_cache_update,
            'last_updated': datetime.now().isoformat()
        }
