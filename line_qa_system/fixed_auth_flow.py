"""
修正された認証フロー
完全に動作する認証システム
"""

import os
import time
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from .config import Config
from .line_client import LineClient
from .auth_service import AuthService
from .store_service import StoreService
from .staff_service import StaffService
from .utils import hash_user_id

logger = structlog.get_logger(__name__)


class FixedAuthFlow:
    """修正された認証フロー"""

    def __init__(self):
        """初期化"""
        self.line_client = LineClient()
        self.auth_service = AuthService()
        self.store_service = StoreService()
        self.staff_service = StaffService()
        logger.info("修正された認証フローを初期化しました")

    def process_auth_flow(self, event: Dict[str, Any]) -> bool:
        """
        認証フローを処理する。
        認証フローで処理が完了した場合はTrueを返す。
        """
        try:
            user_id = event["source"]["userId"]
            message_type = event["message"]["type"] if "message" in event else None
            message_text = event["message"]["text"] if message_type == "text" else None
            reply_token = event["replyToken"]

            hashed_user_id = hash_user_id(user_id)

            # 認証が有効でない場合は何もしない
            if not Config.AUTH_ENABLED:
                return False

            # 既に認証済みであれば何もしない
            if self.auth_service.is_authenticated(user_id):
                return False

            current_state = self.auth_service.get_auth_state(user_id)
            logger.debug("認証フロー処理中", user_id=hashed_user_id, current_state=current_state, message_text=message_text)

            # 認証開始コマンド
            if message_text and message_text.strip().lower() in ["認証", "auth", "ログイン", "login"]:
                if current_state is None or current_state == 'not_started':
                    self.send_store_code_prompt(reply_token)
                    self.auth_service.set_auth_state(user_id, 'store_code_input_pending')
                    logger.info("認証プロセスを開始しました", user_id=hashed_user_id)
                    return True
                else:
                    # 既に認証フロー中の場合は、現在の状態に応じたメッセージを再送
                    self.send_auth_required_message(reply_token, "認証プロセスが進行中です。")
                    return True

            # 店舗コード入力処理
            if current_state == 'store_code_input_pending':
                if message_text and (message_text.strip().startswith('店舗コード:') or message_text.strip().startswith('STORE')):
                    # 店舗コードを抽出
                    if message_text.strip().startswith('店舗コード:'):
                        store_code = message_text.strip().replace('店舗コード:', '').strip().upper()
                    else:
                        store_code = message_text.strip().upper()
                    
                    store = self.store_service.get_store(store_code)

                    if store and store['status'] == 'active':
                        self.auth_service.set_temp_store_code(user_id, store_code)
                        self.send_staff_id_prompt(reply_token, f"店舗「{store['store_name']}」を確認しました。社員番号を入力してください。")
                        self.auth_service.set_auth_state(user_id, 'staff_id_input_pending')
                        logger.info("店舗コードを確認しました", user_id=hashed_user_id, store_code=store_code)
                        return True
                    else:
                        self.auth_service.increment_auth_attempts(user_id)
                        attempts = self.auth_service.get_auth_attempts(user_id)
                        if attempts >= Config.AUTH_MAX_ATTEMPTS:
                            error_message = "店舗コードが正しくありません。\n\n" \
                                            f"{Config.AUTH_MAX_ATTEMPTS}回の試行を超えました。\n" \
                                            "管理者にお問い合わせください。"
                            self.auth_service.clear_auth_pending(user_id)
                            self.auth_service.set_auth_state(user_id, None)
                        else:
                            error_message = f"店舗コードが正しくないか、無効な店舗です。\n\n" \
                                            f"残り試行回数: {Config.AUTH_MAX_ATTEMPTS - attempts}回\n" \
                                            "再度入力してください。"
                        self.line_client.reply_text(reply_token, error_message)
                        logger.warning("無効な店舗コード", user_id=hashed_user_id, store_code=store_code, attempts=attempts)
                        return True
                else:
                    self.send_store_code_prompt(reply_token, "「店舗コード:XXXX」または「STORE004」の形式で入力してください。")
                    return True

            # 社員番号入力処理
            elif current_state == 'staff_id_input_pending':
                if message_text and (message_text.strip().startswith('社員番号:') or message_text.strip().isdigit()):
                    # 社員番号を抽出
                    if message_text.strip().startswith('社員番号:'):
                        staff_id = message_text.strip().replace('社員番号:', '').strip()
                    else:
                        staff_id = message_text.strip()
                    
                    store_code = self.auth_service.get_temp_store_code(user_id)

                    if not store_code:
                        logger.error("社員番号入力中に店舗コードが不足しています", user_id=hashed_user_id)
                        self.line_client.reply_text(reply_token, "認証情報が不足しています。最初からやり直してください。")
                        self.auth_service.clear_auth_pending(user_id)
                        self.auth_service.set_auth_state(user_id, None)
                        return True

                    staff = self.staff_service.get_staff(store_code, staff_id)

                    if staff and staff['status'] == 'active':
                        # 認証成功
                        self.auth_service.authenticated_users[user_id] = {
                            'store_code': store_code,
                            'staff_id': staff_id,
                            'store_name': store['store_name'] if 'store' in locals() else self.store_service.get_store(store_code)['store_name'],
                            'staff_name': staff['staff_name'],
                            'auth_time': datetime.now().isoformat()
                        }
                        
                        success_message = f"認証が完了しました！\n\n" \
                                        f"店舗: {self.auth_service.authenticated_users[user_id]['store_name']}\n" \
                                        f"スタッフ: {staff['staff_name']}\n\n" \
                                        f"Botをご利用いただけます。"
                        self.line_client.reply_text(reply_token, success_message)
                        logger.info("認証完了", user_id=hashed_user_id, store_code=store_code, staff_id=staff_id)
                        return True
                    else:
                        # 認証失敗
                        self.auth_service.increment_auth_attempts(user_id)
                        attempts = self.auth_service.get_auth_attempts(user_id)
                        if attempts >= Config.AUTH_MAX_ATTEMPTS:
                            error_message = "社員番号が正しくありません。\n\n" \
                                            f"{Config.AUTH_MAX_ATTEMPTS}回の試行を超えました。\n" \
                                            "管理者にお問い合わせください。"
                            self.auth_service.clear_auth_pending(user_id)
                            self.auth_service.set_auth_state(user_id, None)
                        else:
                            error_message = f"社員番号が正しくないか、無効なスタッフです。\n\n" \
                                            f"残り試行回数: {Config.AUTH_MAX_ATTEMPTS - attempts}回\n" \
                                            "再度入力してください。"
                        self.line_client.reply_text(reply_token, error_message)
                        logger.warning("無効な社員番号", user_id=hashed_user_id, store_code=store_code, staff_id=staff_id, attempts=attempts)
                        return True
                else:
                    self.send_staff_id_prompt(reply_token, "「社員番号:XXXX」または「004」の形式で入力してください。")
                    return True
            
            # 認証フローが開始されていない、または不明な状態の場合
            if current_state is None or current_state == 'not_started':
                self.send_auth_required_message(reply_token)
                self.auth_service.set_auth_state(user_id, 'auth_required')
                return True

            return False

        except Exception as e:
            logger.error("認証フローの処理に失敗しました", error=str(e))
            return False

    def send_auth_required_message(self, reply_token: str, additional_text: str = ""):
        """認証が必要な旨を伝えるメッセージを送信"""
        text = "このBotをご利用いただくには認証が必要です。\n\n" \
            "「認証」と入力してください。"
        if additional_text:
            text = additional_text + "\n\n" + text
        self.line_client.reply_text(reply_token, text)
        logger.info("認証が必要メッセージを送信しました")

    def send_store_code_prompt(self, reply_token: str, additional_text: str = ""):
        """店舗コード入力を促すメッセージを送信"""
        text = "店舗コードを入力してください。\n\n例：店舗コード:STORE001 または STORE001"
        if additional_text:
            text = additional_text + "\n\n" + text
        self.line_client.reply_text(reply_token, text)
        logger.info("店舗コード入力プロンプトを送信しました")

    def send_staff_id_prompt(self, reply_token: str, additional_text: str = ""):
        """社員番号入力を促すメッセージを送信"""
        text = "社員番号を入力してください。\n\n例：社員番号:001 または 001"
        if additional_text:
            text = additional_text + "\n\n" + text
        self.line_client.reply_text(reply_token, text)
        logger.info("社員番号入力プロンプトを送信しました")
