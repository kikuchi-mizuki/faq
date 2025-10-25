"""
簡略化された認証フロー処理
LINE Botでの認証フローを簡潔に実装
"""

import os
import time
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from .config import Config
from .utils import hash_user_id

logger = structlog.get_logger(__name__)


class SimpleAuthFlow:
    """簡略化された認証フロー処理"""
    
    def __init__(self):
        """初期化"""
        self.auth_service = None
        self.staff_service = None
        self.store_service = None
        self.line_client = None
        
        logger.info("簡略化認証フローを初期化しました")
    
    def initialize_services(self):
        """サービスを初期化"""
        try:
            from .auth_service import AuthService
            from .staff_service import StaffService
            from .store_service import StoreService
            from .line_client import LineClient
            
            self.auth_service = AuthService()
            self.staff_service = StaffService()
            self.store_service = StoreService()
            self.line_client = LineClient()
            
            logger.info("認証フローサービスを初期化しました")
            
        except Exception as e:
            logger.error("認証フローサービスの初期化に失敗しました", error=str(e))
    
    def process_auth_flow(self, event: Dict[str, Any]) -> bool:
        """認証フローの処理"""
        try:
            if not self.auth_service:
                self.initialize_services()
            
            user_id = event["source"]["userId"]
            message_text = event["message"]["text"]
            reply_token = event["replyToken"]
            
            # 認証状態のチェック
            if self.auth_service.is_authenticated(user_id):
                # 既に認証済み
                return False  # 通常のBot処理に進む
            
            # 認証フローの処理
            if message_text.strip().lower() in ['認証', 'auth', 'ログイン', 'login']:
                # 認証開始
                self.send_staff_verification_message(reply_token)
                return True
            elif message_text.strip().startswith('店舗コード:'):
                # 店舗コード入力
                return self.process_store_code_input(user_id, message_text, reply_token)
            elif message_text.strip().startswith('社員番号:'):
                # 社員番号入力
                return self.process_staff_id_input(user_id, message_text, reply_token)
            elif message_text.strip().startswith('STORE'):
                # 店舗コードのみの入力（STORE004など）
                store_code = message_text.strip()
                return self.process_store_code_input(user_id, f"店舗コード:{store_code}", reply_token)
            else:
                # 認証が必要
                self.send_auth_required_message(reply_token)
                return True
                
        except Exception as e:
            logger.error("認証フローの処理に失敗しました", error=str(e))
            return False
    
    def send_auth_required_message(self, reply_token: str):
        """認証が必要な旨を伝えるメッセージを送信"""
        try:
            message = "このBotは関係者専用です。\n\n" \
                    "スタッフの方は「認証」と入力して認証を行ってください。\n" \
                    "不明な点は管理者にお問い合わせください。"
            self.line_client.reply_text(reply_token, message)
            logger.info("認証が必要メッセージを送信しました")
        except Exception as e:
            logger.error("認証が必要メッセージの送信に失敗しました", error=str(e))
    
    def send_staff_verification_message(self, reply_token: str):
        """スタッフ認証メッセージを送信"""
        try:
            message = "認証を開始します。\n\n" \
                    "店舗コードを入力してください。\n" \
                    "例：店舗コード:STORE001"
            self.line_client.reply_text(reply_token, message)
            logger.info("スタッフ認証メッセージを送信しました")
        except Exception as e:
            logger.error("スタッフ認証メッセージの送信に失敗しました", error=str(e))
    
    def process_store_code_input(self, user_id: str, message_text: str, reply_token: str) -> bool:
        """店舗コード入力の処理"""
        try:
            # 店舗コードを抽出
            store_code = message_text.strip().replace('店舗コード:', '').strip()
            
            # 店舗の存在確認
            store = self.store_service.get_store(store_code)
            if not store:
                self.line_client.reply_text(reply_token, f"店舗コード「{store_code}」が見つかりません。\n\n正しい店舗コードを入力してください。")
                return True
            
            if store['status'] != 'active':
                self.line_client.reply_text(reply_token, f"店舗「{store['store_name']}」は現在利用できません。\n\n管理者にお問い合わせください。")
                return True
            
            # 店舗コードを一時保存
            self.auth_service.set_temp_store_code(user_id, store_code)
            
            # 社員番号入力を促す
            message = f"店舗「{store['store_name']}」を確認しました。\n\n" \
                    "社員番号を入力してください。\n" \
                    "例：社員番号:001"
            self.line_client.reply_text(reply_token, message)
            
            logger.info("店舗コード入力を処理しました", user_id=user_id, store_code=store_code)
            return True
            
        except Exception as e:
            logger.error("店舗コード入力の処理に失敗しました", error=str(e))
            self.line_client.reply_text(reply_token, "店舗コードの処理中にエラーが発生しました。再度お試しください。")
            return True
    
    def process_staff_id_input(self, user_id: str, message_text: str, reply_token: str) -> bool:
        """社員番号入力の処理"""
        try:
            # 社員番号を抽出
            staff_id = message_text.strip().replace('社員番号:', '').strip()
            
            # 店舗コードを取得
            store_code = self.auth_service.get_temp_store_code(user_id)
            if not store_code:
                self.line_client.reply_text(reply_token, "店舗コードが見つかりません。\n\n最初から認証をやり直してください。")
                return True
            
            # スタッフの存在確認
            staff = self.staff_service.get_staff(store_code, staff_id)
            if not staff:
                self.line_client.reply_text(reply_token, f"社員番号「{staff_id}」が見つかりません。\n\n正しい社員番号を入力してください。")
                return True
            
            if staff['status'] != 'active':
                self.line_client.reply_text(reply_token, f"スタッフ「{staff['staff_name']}」は現在利用できません。\n\n管理者にお問い合わせください。")
                return True
            
            # 認証完了
            store = self.store_service.get_store(store_code)
            success_message = f"認証が完了しました！\n\n" \
                            f"店舗: {store['store_name']}\n" \
                            f"スタッフ: {staff['staff_name']}\n\n" \
                            f"Botをご利用いただけます。"
            self.line_client.reply_text(reply_token, success_message)
            
            # 認証情報を簡略化して保存
            try:
                # 認証状態を直接設定
                self.auth_service.set_auth_state(user_id, 'authenticated')
                
                # 認証情報をメモリに保存
                self.auth_service.authenticated_users[user_id] = {
                    'store_code': store_code,
                    'staff_id': staff_id,
                    'store_name': store['store_name'],
                    'staff_name': staff['staff_name'],
                    'auth_time': datetime.now().isoformat()
                }
                
                logger.info("認証が完了しました", user_id=user_id, store_code=store_code, staff_id=staff_id)
            except Exception as e:
                logger.error("認証情報の保存に失敗しました", error=str(e))
                # エラーが発生しても認証完了メッセージは送信済み
            
            return True
            
        except Exception as e:
            logger.error("社員番号入力の処理に失敗しました", error=str(e))
            self.line_client.reply_text(reply_token, "社員番号の処理中にエラーが発生しました。再度お試しください。")
            return True
