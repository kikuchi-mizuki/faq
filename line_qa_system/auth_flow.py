"""
認証フロー処理
LINEログイン認証とスタッフ認証のフローを管理
"""

import os
import time
import urllib.parse
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from .config import Config
from .utils import hash_user_id

logger = structlog.get_logger(__name__)


class AuthFlow:
    """認証フロー処理"""
    
    def __init__(self):
        """初期化"""
        self.auth_service = None
        self.staff_service = None
        self.store_service = None
        self.line_client = None
        
        # LINEログイン設定
        self.line_login_channel_id = Config.LINE_LOGIN_CHANNEL_ID
        self.line_login_channel_secret = Config.LINE_LOGIN_CHANNEL_SECRET
        self.line_login_redirect_uri = Config.LINE_LOGIN_REDIRECT_URI
        
        logger.info("認証フローを初期化しました")
    
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
            
            # 認証フローの状態をチェック
            auth_state = self.auth_service.get_auth_state(user_id)
            
            if auth_state == 'not_started':
                # 認証開始
                self.send_auth_required_message(reply_token)
                self.auth_service.set_auth_state(user_id, 'auth_required')
                return True
                
            elif auth_state == 'auth_required':
                # 認証ボタンが押された場合
                if message_text.strip().lower() in ['認証', 'auth', 'ログイン', 'login']:
                    self.send_staff_verification_message(reply_token)
                    self.auth_service.set_auth_state(user_id, 'staff_verification')
                    return True
                else:
                    self.send_auth_required_message(reply_token)
                    return True
                    
            elif auth_state == 'staff_verification':
                # スタッフ認証の処理
                return self.process_staff_verification(user_id, message_text, reply_token)
                
            elif auth_state == 'store_code_input':
                # 店舗コード入力の処理
                return self.process_store_code_input(user_id, message_text, reply_token)
                
            elif auth_state == 'staff_id_input':
                # 社員番号入力の処理
                return self.process_staff_id_input(user_id, message_text, reply_token)
            
            return True
            
        except Exception as e:
            logger.error("認証フローの処理中にエラーが発生しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            return True
    
    def send_auth_required_message(self, reply_token: str):
        """認証が必要なメッセージを送信"""
        try:
            message = {
                "type": "template",
                "altText": "認証が必要です",
                "template": {
                    "type": "buttons",
                    "text": "このBotをご利用いただくには認証が必要です。\n\nスタッフの方は下のボタンを押して認証してください。",
                    "actions": [
                        {
                            "type": "postback",
                            "label": "認証する",
                            "data": "action=auth_start"
                        }
                    ]
                }
            }
            
            self.line_client.send_reply_message(reply_token, [message])
            
        except Exception as e:
            logger.error("認証必要メッセージの送信に失敗しました", error=str(e))
            # フォールバック: テキストメッセージ
            fallback_message = "このBotをご利用いただくには認証が必要です。\n\n「認証」と入力してください。"
            self.line_client.reply_text(reply_token, fallback_message)
    
    def send_staff_verification_message(self, reply_token: str):
        """スタッフ認証メッセージを送信"""
        try:
            message = {
                "type": "template",
                "altText": "スタッフ認証",
                "template": {
                    "type": "buttons",
                    "text": "スタッフ認証を行ってください。\n\n店舗コードと社員番号を入力してください。",
                    "actions": [
                        {
                            "type": "postback",
                            "label": "店舗コード入力",
                            "data": "action=store_code_input"
                        }
                    ]
                }
            }
            
            self.line_client.send_reply_message(reply_token, [message])
            
        except Exception as e:
            logger.error("スタッフ認証メッセージの送信に失敗しました", error=str(e))
            # フォールバック: テキストメッセージ
            fallback_message = "スタッフ認証を行ってください。\n\n店舗コードを入力してください。\n例：店舗コード:A123"
            self.line_client.reply_text(reply_token, fallback_message)
    
    def process_staff_verification(self, user_id: str, message_text: str, reply_token: str) -> bool:
        """スタッフ認証の処理"""
        try:
            if message_text.strip().lower() in ['店舗コード入力', 'store_code_input']:
                self.line_client.reply_text(reply_token, "店舗コードを入力してください。\n\n例：店舗コード:A123")
                self.auth_service.set_auth_state(user_id, 'store_code_input')
                return True
            
            return True
            
        except Exception as e:
            logger.error("スタッフ認証の処理中にエラーが発生しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            return True
    
    def process_store_code_input(self, user_id: str, message_text: str, reply_token: str) -> bool:
        """店舗コード入力の処理"""
        try:
            if message_text.startswith('店舗コード:'):
                store_code = message_text.replace('店舗コード:', '').strip()
                
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
                self.auth_service.set_temp_store_code(user_id, store_code)
                
                # 社員番号入力を要求
                self.line_client.reply_text(reply_token, 
                    f"店舗「{store['store_name']}」を確認しました。\n\n社員番号を入力してください。\n例：社員番号:1234")
                self.auth_service.set_auth_state(user_id, 'staff_id_input')
                return True
            
            else:
                self.line_client.reply_text(reply_token, 
                    "店舗コードを正しい形式で入力してください。\n\n例：店舗コード:A123")
                return True
                
        except Exception as e:
            logger.error("店舗コード入力の処理中にエラーが発生しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            return True
    
    def process_staff_id_input(self, user_id: str, message_text: str, reply_token: str) -> bool:
        """社員番号入力の処理"""
        try:
            if message_text.startswith('社員番号:'):
                staff_id = message_text.replace('社員番号:', '').strip()
                store_code = self.auth_service.get_temp_store_code(user_id)
                
                if not store_code:
                    self.line_client.reply_text(reply_token, 
                        "店舗コードが見つかりません。\n\n最初からやり直してください。")
                    self.auth_service.set_auth_state(user_id, 'staff_verification')
                    return True
                
                # スタッフ認証
                auth_result = self.verify_staff_credentials(store_code, staff_id)
                
                if auth_result['success']:
                    # 認証成功
                    self.complete_staff_auth(user_id, store_code, staff_id, auth_result['staff'])
                    
                    success_message = f"認証が完了しました！\n\n" \
                                    f"店舗: {auth_result['store']['store_name']}\n" \
                                    f"スタッフ: {auth_result['staff']['staff_name']}\n\n" \
                                    f"Botをご利用いただけます。"
                    self.line_client.reply_text(reply_token, success_message)
                    self.auth_service.set_auth_state(user_id, 'authenticated')
                    return True
                    
                else:
                    # 認証失敗
                    attempts = self.auth_service.get_auth_attempts(user_id)
                    self.auth_service.increment_auth_attempts(user_id)
                    
                    if attempts >= 2:  # 3回目で失敗
                        error_message = f"認証に失敗しました。\n\n" \
                                      f"理由: {auth_result['error']}\n\n" \
                                      f"3回の試行を超えました。\n" \
                                      f"管理者にお問い合わせください。"
                        self.auth_service.clear_auth_pending(user_id)
                    else:
                        error_message = f"認証に失敗しました。\n\n" \
                                      f"理由: {auth_result['error']}\n\n" \
                                      f"残り試行回数: {2 - attempts}回\n" \
                                      f"店舗コードと社員番号を確認してください。"
                    
                    self.line_client.reply_text(reply_token, error_message)
                    return True
                    
            else:
                self.line_client.reply_text(reply_token, 
                    "社員番号を正しい形式で入力してください。\n\n例：社員番号:1234")
                return True
                
        except Exception as e:
            logger.error("社員番号入力の処理中にエラーが発生しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            return True
    
    def verify_staff_credentials(self, store_code: str, staff_id: str) -> Dict[str, Any]:
        """スタッフの認証情報を検証"""
        try:
            # 店舗の存在確認
            store = self.store_service.get_store(store_code)
            if not store:
                return {'success': False, 'error': '店舗が見つかりません'}
            
            if store['status'] != 'active':
                return {'success': False, 'error': '店舗が利用できません'}
            
            # スタッフ情報の確認
            staff = self.staff_service.get_staff(store_code, staff_id)
            if not staff:
                return {'success': False, 'error': 'スタッフ情報が見つかりません'}
            
            if staff['status'] != 'active':
                return {'success': False, 'error': 'スタッフのステータスが無効です'}
            
            return {
                'success': True,
                'staff': staff,
                'store': store
            }
            
        except Exception as e:
            logger.error("スタッフ認証に失敗しました", 
                        store_code=store_code, 
                        staff_id=staff_id,
                        error=str(e))
            return {'success': False, 'error': '認証処理中にエラーが発生しました'}
    
    def complete_staff_auth(self, user_id: str, store_code: str, staff_id: str, staff_info: dict):
        """スタッフ認証完了処理"""
        try:
            # 認証完了処理
            self.auth_service.complete_auth(user_id, store_code, staff_id, staff_info)
            
            # スタッフの認証情報を更新
            self.staff_service.update_staff_auth(store_code, staff_id, user_id)
            
            logger.info("スタッフ認証が完了しました", 
                       user_id=hash_user_id(user_id),
                       store_code=store_code,
                       staff_id=staff_id)
            
        except Exception as e:
            logger.error("スタッフ認証完了処理に失敗しました", 
                        user_id=hash_user_id(user_id),
                        store_code=store_code,
                        staff_id=staff_id,
                        error=str(e))
    
    def send_restricted_message(self, reply_token: str):
        """未認証ユーザーへの制限メッセージ"""
        try:
            message = "このBotは関係者専用です。\n\n" \
                     "スタッフの方は認証を行ってください。\n" \
                     "不明な点は管理者にお問い合わせください。"
            
            self.line_client.reply_text(reply_token, message)
            
        except Exception as e:
            logger.error("制限メッセージの送信に失敗しました", error=str(e))
    
    def handle_postback(self, event: Dict[str, Any]) -> bool:
        """ポストバックイベントの処理"""
        try:
            user_id = event["source"]["userId"]
            data = event["postback"]["data"]
            reply_token = event["replyToken"]
            
            if data == "action=auth_start":
                # 認証開始
                self.send_staff_verification_message(reply_token)
                self.auth_service.set_auth_state(user_id, 'staff_verification')
                return True
                
            elif data == "action=store_code_input":
                # 店舗コード入力
                self.line_client.reply_text(reply_token, 
                    "店舗コードを入力してください。\n\n例：店舗コード:A123")
                self.auth_service.set_auth_state(user_id, 'store_code_input')
                return True
            
            return False
            
        except Exception as e:
            logger.error("ポストバック処理中にエラーが発生しました", 
                        user_id=hash_user_id(user_id), 
                        error=str(e))
            return False
