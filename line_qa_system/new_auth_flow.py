"""
新しい認証フロー
シンプルで確実に動作する認証システム
"""

import os
import time
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from .config import Config
from .line_client import LineClient
from .store_service import StoreService
from .staff_service import StaffService
from .utils import hash_user_id

logger = structlog.get_logger(__name__)


class NewAuthFlow:
    """新しい認証フロー - シンプルで確実"""

    def __init__(self):
        """初期化"""
        self.line_client = LineClient()
        self.store_service = StoreService()
        self.staff_service = StaffService()
        
        # 認証状態の管理（メモリ内）
        self.auth_states = {}  # ユーザーID -> 認証状態
        self.temp_data = {}    # ユーザーID -> 一時データ
        self.authenticated_users = {}  # ユーザーID -> 認証情報
        
        logger.info("新しい認証フローを初期化しました")

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

            # 現在の認証状態を取得
            current_state = self.auth_states.get(user_id, 'not_started')
            
            logger.debug("認証フロー処理中", 
                        user_id=hashed_user_id, 
                        current_state=current_state, 
                        message_text=message_text)

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
            logger.error("認証フローの処理に失敗しました", error=str(e))
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
            
            # 店舗の存在確認
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

            # スタッフの存在確認
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
            self.complete_auth(user_id, store_code, staff_id, store, staff)
            
            success_message = f"認証が完了しました！\n\n" \
                            f"店舗: {store['store_name']}\n" \
                            f"スタッフ: {staff['staff_name']}\n\n" \
                            f"Botをご利用いただけます。"
            
            self.line_client.reply_text(reply_token, success_message)
            logger.info("認証が完了しました", 
                       user_id=hash_user_id(user_id), 
                       store_code=store_code, 
                       staff_id=staff_id)
            return True

        except Exception as e:
            logger.error("社員番号入力の処理に失敗しました", error=str(e))
            self.line_client.reply_text(reply_token, 
                "社員番号の処理中にエラーが発生しました。再度お試しください。")
            return True

    def complete_auth(self, user_id: str, store_code: str, staff_id: str, store: Dict, staff: Dict):
        """認証を完了"""
        try:
            # 認証情報を保存
            self.authenticated_users[user_id] = {
                'store_code': store_code,
                'staff_id': staff_id,
                'store_name': store['store_name'],
                'staff_name': staff['staff_name'],
                'auth_time': datetime.now().isoformat()
            }
            
            # 認証状態を完了に設定
            self.auth_states[user_id] = 'authenticated'
            
            # 一時データをクリア
            if user_id in self.temp_data:
                del self.temp_data[user_id]
            
            logger.info("認証情報を保存しました", 
                       user_id=hash_user_id(user_id), 
                       store_code=store_code, 
                       staff_id=staff_id)
            
        except Exception as e:
            logger.error("認証完了処理に失敗しました", error=str(e))
            raise

    def is_authenticated(self, user_id: str) -> bool:
        """ユーザーが認証済みかチェック"""
        return user_id in self.authenticated_users

    def get_auth_info(self, user_id: str) -> Optional[Dict]:
        """認証情報を取得"""
        return self.authenticated_users.get(user_id)

    def send_auth_required_message(self, reply_token: str):
        """認証が必要な旨を伝えるメッセージを送信"""
        message = "このBotをご利用いただくには認証が必要です。\n\n" \
                "「認証」と入力してください。"
        self.line_client.reply_text(reply_token, message)
        logger.info("認証が必要メッセージを送信しました")

    def get_stats(self) -> Dict[str, Any]:
        """認証統計を取得"""
        return {
            'total_authenticated': len(self.authenticated_users),
            'pending_auth': len([s for s in self.auth_states.values() if s != 'authenticated']),
            'auth_states': dict(self.auth_states),
            'last_updated': datetime.now().isoformat()
        }
