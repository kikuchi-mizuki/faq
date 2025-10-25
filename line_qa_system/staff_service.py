"""
スタッフ管理サービス
スタッフの認証・管理機能を提供
"""

import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

from .config import Config
from .utils import hash_user_id

logger = structlog.get_logger(__name__)


class StaffService:
    """スタッフ管理サービス"""
    
    def __init__(self):
        """初期化"""
        self.staff_data = {}  # スタッフデータのキャッシュ
        self.sheet_name = Config.STAFF_MANAGEMENT_SHEET
        
        # スプレッドシートからスタッフデータを読み込み
        self.load_staff_data()
        
        logger.info("スタッフ管理サービスを初期化しました", 
                   total_staff=len(self.staff_data),
                   sheet_name=self.sheet_name)
    
    def load_staff_data(self):
        """スプレッドシートからスタッフデータを読み込み"""
        try:
            # 直接Google Sheets APIを使用してデータを取得
            import gspread
            from google.oauth2.service_account import Credentials
            import json
            
            # 認証情報を取得
            service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
            if not service_account_json:
                logger.warning("GOOGLE_SERVICE_ACCOUNT_JSONが設定されていません")
                return
            
            # 認証情報を作成
            import base64
            try:
                if service_account_json.startswith('{'):
                    # 直接JSON文字列の場合
                    credentials_dict = json.loads(service_account_json)
                elif service_account_json.startswith('ewogICJ0eXBlIjo'):
                    # base64エンコードされた場合（Railway）
                    decoded_json = base64.b64decode(service_account_json).decode('utf-8')
                    credentials_dict = json.loads(decoded_json)
                else:
                    # ファイルパスの場合
                    with open(service_account_json, 'r') as f:
                        credentials_dict = json.load(f)
            except Exception as e:
                logger.error("認証情報の解析に失敗しました", error=str(e))
                return
            
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # gspreadクライアントを初期化
            gc = gspread.authorize(credentials)
            
            # スプレッドシートを開く
            sheet_id = os.environ.get('SHEET_ID_QA')
            if not sheet_id:
                logger.warning("SHEET_ID_QAが設定されていません")
                return
            
            spreadsheet = gc.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet(self.sheet_name)
            sheet_data = worksheet.get_all_values()
            
            if not sheet_data or len(sheet_data) < 2:
                logger.warning("スタッフ管理シートにデータがありません")
                return
            
            # ヘッダー行をスキップしてデータを処理
            for row in sheet_data[1:]:
                if len(row) >= 6:  # 最低限のデータがあるかチェック
                    store_code = row[0]
                    staff_id = row[1]
                    if store_code and staff_id:  # 店舗コードとスタッフIDが存在する場合のみ
                        key = f"{store_code}_{staff_id}"
                        self.staff_data[key] = {
                            'store_code': store_code,
                            'staff_id': staff_id,
                            'staff_name': row[2] if len(row) > 2 else '',
                            'position': row[3] if len(row) > 3 else '',
                            'status': row[4] if len(row) > 4 else 'active',
                            'created_at': row[5] if len(row) > 5 else datetime.now().isoformat(),
                            'last_activity': row[6] if len(row) > 6 else '',
                            'line_user_id': row[7] if len(row) > 7 else '',
                            'auth_time': row[8] if len(row) > 8 else '',
                            'notes': row[9] if len(row) > 9 else ''
                        }
            
            logger.info(f"スタッフデータを読み込みました: {len(self.staff_data)}件")
            
        except Exception as e:
            logger.error("スタッフデータの読み込みに失敗しました", error=str(e))
            # エラーが発生しても空の辞書で初期化
            self.staff_data = {}
    
    def get_staff(self, store_code: str, staff_id: str) -> Optional[Dict[str, Any]]:
        """スタッフ情報を取得"""
        key = f"{store_code}_{staff_id}"
        return self.staff_data.get(key)
    
    def staff_exists(self, store_code: str, staff_id: str) -> bool:
        """スタッフが存在するかチェック"""
        key = f"{store_code}_{staff_id}"
        return key in self.staff_data
    
    def get_staff_by_line_user_id(self, line_user_id: str) -> Optional[Dict[str, Any]]:
        """LINEユーザーIDでスタッフ情報を取得"""
        for staff in self.staff_data.values():
            if staff.get('line_user_id') == line_user_id:
                return staff
        return None
    
    def get_staff_list(self, store_code: Optional[str] = None, status: str = 'active') -> List[Dict[str, Any]]:
        """スタッフ一覧を取得"""
        try:
            staff_list = []
            
            for staff in self.staff_data.values():
                # 店舗コードでフィルタ
                if store_code and staff['store_code'] != store_code:
                    continue
                
                # ステータスでフィルタ
                if staff['status'] != status:
                    continue
                
                staff_list.append(staff)
            
            return staff_list
            
        except Exception as e:
            logger.error("スタッフ一覧の取得に失敗しました", error=str(e))
            return []
    
    def get_active_staff(self, store_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """アクティブなスタッフの取得"""
        return self.get_staff_list(store_code, 'active')
    
    def get_suspended_staff(self, store_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """停止中のスタッフの取得"""
        return self.get_staff_list(store_code, 'suspended')
    
    def get_total_staff(self) -> int:
        """総スタッフ数を取得"""
        return len(self.staff_data)
    
    def add_staff(self, store_code: str, staff_id: str, staff_name: str, **kwargs) -> Dict[str, Any]:
        """スタッフの追加"""
        try:
            # スタッフの重複チェック
            if self.staff_exists(store_code, staff_id):
                return {
                    'success': False,
                    'error': 'スタッフが既に存在します'
                }
            
            # 新しいスタッフデータを作成
            new_staff = {
                'store_code': store_code,
                'staff_id': staff_id,
                'staff_name': staff_name,
                'position': kwargs.get('position', ''),
                'status': kwargs.get('status', 'active'),
                'created_at': datetime.now().isoformat(),
                'last_activity': '',
                'line_user_id': '',
                'auth_time': '',
                'notes': kwargs.get('notes', '')
            }
            
            # メモリに追加
            key = f"{store_code}_{staff_id}"
            self.staff_data[key] = new_staff
            
            # スプレッドシートに追加
            self.add_staff_to_sheet(new_staff)
            
            logger.info("スタッフを追加しました", 
                       store_code=store_code, 
                       staff_id=staff_id,
                       staff_name=staff_name)
            
            return {
                'success': True,
                'staff': new_staff
            }
            
        except Exception as e:
            logger.error("スタッフの追加に失敗しました", 
                        store_code=store_code, 
                        staff_id=staff_id,
                        error=str(e))
            return {
                'success': False,
                'error': f'スタッフの追加に失敗しました: {str(e)}'
            }
    
    def update_staff_status(self, store_code: str, staff_id: str, status: str) -> Dict[str, Any]:
        """スタッフのステータス変更"""
        try:
            key = f"{store_code}_{staff_id}"
            if key not in self.staff_data:
                return {
                    'success': False,
                    'error': 'スタッフが見つかりません'
                }
            
            # ステータスの検証
            valid_statuses = ['active', 'suspended', 'inactive']
            if status not in valid_statuses:
                return {
                    'success': False,
                    'error': '無効なステータスです'
                }
            
            # ステータスを更新
            old_status = self.staff_data[key]['status']
            self.staff_data[key]['status'] = status
            
            # スプレッドシートに反映
            self.update_staff_in_sheet(store_code, staff_id, {'status': status})
            
            logger.info("スタッフのステータスを変更しました", 
                       store_code=store_code, 
                       staff_id=staff_id,
                       old_status=old_status, 
                       new_status=status)
            
            return {
                'success': True,
                'staff': self.staff_data[key]
            }
            
        except Exception as e:
            logger.error("スタッフステータスの変更に失敗しました", 
                        store_code=store_code, 
                        staff_id=staff_id,
                        error=str(e))
            return {
                'success': False,
                'error': f'ステータス変更に失敗しました: {str(e)}'
            }
    
    def update_auth_info(self, store_code: str, staff_id: str, user_id: str, auth_time: str):
        """スタッフの認証情報をスプレッドシートに更新"""
        try:
            key = f"{store_code}_{staff_id}"
            if key not in self.staff_data:
                logger.warning("認証情報更新対象のスタッフが見つかりません", 
                              store_code=store_code, 
                              staff_id=staff_id)
                return
            
            # 認証情報を更新
            self.staff_data[key]['line_user_id'] = user_id
            self.staff_data[key]['auth_time'] = auth_time
            self.staff_data[key]['last_activity'] = auth_time
            
            # スプレッドシートに反映
            self.update_staff_in_sheet(store_code, staff_id, {
                'line_user_id': user_id,
                'auth_time': auth_time,
                'last_activity': auth_time
            })
            
            # データを再読み込みして最新の状態を反映
            self.load_staff_data()
            
            logger.info("スタッフの認証情報を更新しました", 
                       store_code=store_code, 
                       staff_id=staff_id,
                       user_id=hash_user_id(user_id),
                       auth_time=auth_time)
            
        except Exception as e:
            logger.error("スタッフの認証情報更新に失敗しました", 
                        store_code=store_code, 
                        staff_id=staff_id,
                        error=str(e))
            raise
    
    def update_last_activity(self, store_code: str, staff_id: str):
        """スタッフの最終利用日時を更新"""
        try:
            key = f"{store_code}_{staff_id}"
            if key in self.staff_data:
                self.staff_data[key]['last_activity'] = datetime.now().isoformat()
                
                # スプレッドシートに反映
                self.update_staff_in_sheet(store_code, staff_id, {
                    'last_activity': datetime.now().isoformat()
                })
                
                logger.debug("スタッフの最終利用日時を更新しました", 
                           store_code=store_code, 
                           staff_id=staff_id)
                
        except Exception as e:
            logger.error("最終利用日時の更新に失敗しました", 
                        store_code=store_code, 
                        staff_id=staff_id,
                        error=str(e))
    
    def update_staff_auth(self, store_code: str, staff_id: str, line_user_id: str):
        """スタッフの認証情報を更新"""
        try:
            key = f"{store_code}_{staff_id}"
            if key in self.staff_data:
                self.staff_data[key]['line_user_id'] = line_user_id
                self.staff_data[key]['auth_time'] = datetime.now().isoformat()
                self.staff_data[key]['last_activity'] = datetime.now().isoformat()
                
                # スプレッドシートに反映
                self.update_staff_in_sheet(store_code, staff_id, {
                    'line_user_id': line_user_id,
                    'auth_time': datetime.now().isoformat(),
                    'last_activity': datetime.now().isoformat()
                })
                
                logger.info("スタッフ認証情報を更新しました", 
                           store_code=store_code, 
                           staff_id=staff_id,
                           line_user_id=line_user_id)
                
        except Exception as e:
            logger.error("スタッフ認証情報の更新に失敗しました", 
                        store_code=store_code, 
                        staff_id=staff_id,
                        error=str(e))
    
    def deauthenticate_staff(self, store_code: str, staff_id: str) -> bool:
        """スタッフの認証を無効化"""
        try:
            key = f"{store_code}_{staff_id}"
            if key in self.staff_data:
                # 認証情報をクリア
                self.staff_data[key]['line_user_id'] = ''
                self.staff_data[key]['auth_time'] = ''
                
                # スプレッドシートに反映
                self.update_staff_in_sheet(store_code, staff_id, {
                    'line_user_id': '',
                    'auth_time': ''
                })
                
                logger.info("スタッフの認証を無効化しました", 
                           store_code=store_code, 
                           staff_id=staff_id)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error("スタッフ認証の無効化に失敗しました", 
                        store_code=store_code, 
                        staff_id=staff_id,
                        error=str(e))
            return False
    
    def delete_staff(self, store_code: str, staff_id: str) -> Dict[str, Any]:
        """スタッフの削除"""
        try:
            key = f"{store_code}_{staff_id}"
            if key not in self.staff_data:
                return {
                    'success': False,
                    'error': 'スタッフが見つかりません'
                }
            
            # スタッフを削除
            deleted_staff = self.staff_data.pop(key)
            
            # スプレッドシートから削除
            self.remove_staff_from_sheet(store_code, staff_id)
            
            logger.info("スタッフを削除しました", 
                       store_code=store_code, 
                       staff_id=staff_id)
            
            return {
                'success': True,
                'staff': deleted_staff
            }
            
        except Exception as e:
            logger.error("スタッフの削除に失敗しました", 
                        store_code=store_code, 
                        staff_id=staff_id,
                        error=str(e))
            return {
                'success': False,
                'error': f'スタッフの削除に失敗しました: {str(e)}'
            }
    
    def search_staff(self, query: str, store_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """スタッフの検索"""
        try:
            query_lower = query.lower()
            results = []
            
            for staff in self.staff_data.values():
                # 店舗コードでフィルタ
                if store_code and staff['store_code'] != store_code:
                    continue
                
                # スタッフID、スタッフ名、役職で検索
                if (query_lower in staff['staff_id'].lower() or
                    query_lower in staff['staff_name'].lower() or
                    query_lower in staff['position'].lower()):
                    results.append(staff)
            
            return results
            
        except Exception as e:
            logger.error("スタッフ検索に失敗しました", query=query, error=str(e))
            return []
    
    def get_recent_activity(self, store_code: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """最近の活動を取得"""
        try:
            # 最終利用日時でソート
            sorted_staff = sorted(
                self.staff_data.values(),
                key=lambda x: x['last_activity'] or '',
                reverse=True
            )
            
            # 店舗コードでフィルタ
            if store_code:
                sorted_staff = [staff for staff in sorted_staff if staff['store_code'] == store_code]
            
            return sorted_staff[:limit]
            
        except Exception as e:
            logger.error("最近の活動の取得に失敗しました", error=str(e))
            return []
    
    def add_staff_to_sheet(self, staff_data: Dict[str, Any]):
        """スプレッドシートにスタッフを追加"""
        try:
            from .qa_service import QAService
            qa_service = QAService()
            
            # 新しい行のデータ
            new_row = [
                staff_data['store_code'],
                staff_data['staff_id'],
                staff_data['staff_name'],
                staff_data['position'],
                staff_data['status'],
                staff_data['created_at'],
                staff_data['last_activity'],
                staff_data['line_user_id'],
                staff_data['auth_time'],
                staff_data['notes']
            ]
            
            # スプレッドシートに追加
            qa_service.append_sheet_row(self.sheet_name, new_row)
            
            logger.info("スタッフをスプレッドシートに追加しました", 
                       store_code=staff_data['store_code'],
                       staff_id=staff_data['staff_id'])
            
        except Exception as e:
            logger.error("スプレッドシートへのスタッフ追加に失敗しました", 
                        store_code=staff_data['store_code'],
                        staff_id=staff_data['staff_id'],
                        error=str(e))
            raise
    
    def update_staff_in_sheet(self, store_code: str, staff_id: str, updates: Dict[str, Any]):
        """スプレッドシートのスタッフ情報を更新"""
        try:
            # 直接Google Sheets APIを使用してデータを取得・更新
            import gspread
            from google.oauth2.service_account import Credentials
            import json
            import base64
            
            # 認証情報を取得
            service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
            if not service_account_json:
                logger.warning("GOOGLE_SERVICE_ACCOUNT_JSONが設定されていません")
                return
            
            # 認証情報を作成
            try:
                if service_account_json.startswith('{'):
                    # 直接JSON文字列の場合
                    credentials_dict = json.loads(service_account_json)
                elif service_account_json.startswith('ewogICJ0eXBlIjo'):
                    # base64エンコードされた場合（Railway）
                    decoded_json = base64.b64decode(service_account_json).decode('utf-8')
                    credentials_dict = json.loads(decoded_json)
                else:
                    # ファイルパスの場合
                    with open(service_account_json, 'r') as f:
                        credentials_dict = json.load(f)
            except Exception as e:
                logger.error("認証情報の解析に失敗しました", error=str(e))
                return
            
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # gspreadクライアントを初期化
            gc = gspread.authorize(credentials)
            
            # スプレッドシートを開く
            sheet_id = os.environ.get('SHEET_ID_QA')
            if not sheet_id:
                logger.warning("SHEET_ID_QAが設定されていません")
                return
            
            spreadsheet = gc.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet(self.sheet_name)
            sheet_data = worksheet.get_all_values()
            
            if not sheet_data or len(sheet_data) < 2:
                logger.warning("スタッフ管理シートにデータがありません")
                return
            
            # 該当するスタッフの行を見つけて更新
            for i, row in enumerate(sheet_data[1:], start=2):  # ヘッダー行をスキップ
                if len(row) >= 2 and row[0] == store_code and row[1] == staff_id:
                    # 更新する列を特定
                    for key, value in updates.items():
                        if key == 'status':
                            row[4] = value
                        elif key == 'last_activity':
                            row[6] = value
                        elif key == 'line_user_id':
                            row[7] = value
                        elif key == 'auth_time':
                            row[8] = value
                        elif key == 'notes':
                            row[9] = value
                        # 他のフィールドも同様に処理
                    
                    # スプレッドシートを更新
                    worksheet.update(f'A{i}:J{i}', [row])
                    break
            
            logger.info("スタッフ情報をスプレッドシートで更新しました", 
                       store_code=store_code, 
                       staff_id=staff_id)
            
        except Exception as e:
            logger.error("スプレッドシートのスタッフ情報更新に失敗しました", 
                        store_code=store_code, 
                        staff_id=staff_id,
                        error=str(e))
    
    def remove_staff_from_sheet(self, store_code: str, staff_id: str):
        """スプレッドシートからスタッフを削除"""
        try:
            from .qa_service import QAService
            qa_service = QAService()
            
            # スプレッドシートから現在のデータを取得
            sheet_data = qa_service.get_sheet_data(self.sheet_name)
            
            if not sheet_data:
                logger.warning("スタッフ管理シートのデータが取得できません")
                return
            
            # 該当するスタッフの行を見つけて削除
            for i, row in enumerate(sheet_data[1:], start=2):  # ヘッダー行をスキップ
                if len(row) >= 2 and row[0] == store_code and row[1] == staff_id:
                    # 行を削除
                    qa_service.delete_sheet_row(self.sheet_name, i)
                    break
            
            logger.info("スタッフをスプレッドシートから削除しました", 
                       store_code=store_code, 
                       staff_id=staff_id)
            
        except Exception as e:
            logger.error("スプレッドシートからのスタッフ削除に失敗しました", 
                        store_code=store_code, 
                        staff_id=staff_id,
                        error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """スタッフ統計を取得"""
        try:
            return {
                'total_staff': len(self.staff_data),
                'active_staff': len(self.get_active_staff()),
                'suspended_staff': len(self.get_suspended_staff()),
                'authenticated_staff': len([s for s in self.staff_data.values() if s.get('line_user_id')]),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("スタッフ統計の取得に失敗しました", error=str(e))
            return {
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }
    
    def reload_staff(self):
        """スタッフデータを再読み込み"""
        try:
            self.load_staff_data()
            logger.info("スタッフデータを再読み込みしました")
            return True
            
        except Exception as e:
            logger.error("スタッフデータの再読み込みに失敗しました", error=str(e))
            return False
