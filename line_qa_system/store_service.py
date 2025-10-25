"""
店舗管理サービス
店舗の追加・削除・管理機能を提供
"""

import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

from .config import Config

logger = structlog.get_logger(__name__)


class StoreService:
    """店舗管理サービス"""
    
    def __init__(self):
        """初期化"""
        self.stores = {}  # 店舗データのキャッシュ
        self.sheet_name = Config.STORE_MANAGEMENT_SHEET
        self.store_code_prefix = Config.STORE_CODE_PREFIX
        
        # スプレッドシートから店舗データを読み込み
        self.load_stores_from_sheet()
        
        logger.info("店舗管理サービスを初期化しました", 
                   total_stores=len(self.stores),
                   sheet_name=self.sheet_name)
    
    def load_stores_from_sheet(self):
        """スプレッドシートから店舗データを読み込み"""
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
            if service_account_json.startswith('{'):
                credentials_dict = json.loads(service_account_json)
            else:
                with open(service_account_json, 'r') as f:
                    credentials_dict = json.load(f)
            
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
                logger.warning("店舗管理シートにデータがありません")
                return
            
            # ヘッダー行をスキップしてデータを処理
            for row in sheet_data[1:]:
                if len(row) >= 6:  # 最低限のデータがあるかチェック
                    store_code = row[0]
                    if store_code:  # 店舗コードが存在する場合のみ
                        self.stores[store_code] = {
                            'store_code': store_code,
                            'store_name': row[1] if len(row) > 1 else '',
                            'status': row[2] if len(row) > 2 else 'active',
                            'created_at': row[3] if len(row) > 3 else datetime.now().isoformat(),
                            'last_activity': row[4] if len(row) > 4 else '',
                            'notes': row[5] if len(row) > 5 else '',
                            'admin_notes': row[6] if len(row) > 6 else '',
                            'contact_info': row[7] if len(row) > 7 else '',
                            'location': row[8] if len(row) > 8 else '',
                            'manager_name': row[9] if len(row) > 9 else ''
                        }
            
            logger.info(f"店舗データを読み込みました: {len(self.stores)}件")
            
        except Exception as e:
            logger.error("店舗データの読み込みに失敗しました", error=str(e))
            # エラーが発生しても空の辞書で初期化
            self.stores = {}
    
    def get_store(self, store_code: str) -> Optional[Dict[str, Any]]:
        """店舗情報を取得"""
        return self.stores.get(store_code)
    
    def store_exists(self, store_code: str) -> bool:
        """店舗が存在するかチェック"""
        return store_code in self.stores
    
    def get_all_stores(self) -> List[Dict[str, Any]]:
        """全店舗の取得"""
        return list(self.stores.values())
    
    def get_active_stores(self) -> List[Dict[str, Any]]:
        """アクティブな店舗の取得"""
        return [store for store in self.stores.values() if store['status'] == 'active']
    
    def get_suspended_stores(self) -> List[Dict[str, Any]]:
        """停止中の店舗の取得"""
        return [store for store in self.stores.values() if store['status'] == 'suspended']
    
    def get_expired_stores(self) -> List[Dict[str, Any]]:
        """期限切れの店舗の取得"""
        return [store for store in self.stores.values() if store['status'] == 'expired']
    
    def get_total_stores(self) -> int:
        """総店舗数を取得"""
        return len(self.stores)
    
    def add_store(self, store_code: str, store_name: str, **kwargs) -> Dict[str, Any]:
        """店舗の追加"""
        try:
            # 店舗コードの重複チェック
            if self.store_exists(store_code):
                return {
                    'success': False,
                    'error': '店舗コードが既に存在します'
                }
            
            # 新しい店舗データを作成
            new_store = {
                'store_code': store_code,
                'store_name': store_name,
                'status': kwargs.get('status', 'active'),
                'created_at': datetime.now().isoformat(),
                'last_activity': '',
                'notes': kwargs.get('notes', ''),
                'admin_notes': kwargs.get('admin_notes', ''),
                'contact_info': kwargs.get('contact_info', ''),
                'location': kwargs.get('location', ''),
                'manager_name': kwargs.get('manager_name', '')
            }
            
            # メモリに追加
            self.stores[store_code] = new_store
            
            # スプレッドシートに追加
            self.add_store_to_sheet(new_store)
            
            logger.info("店舗を追加しました", 
                       store_code=store_code, 
                       store_name=store_name)
            
            return {
                'success': True,
                'store': new_store
            }
            
        except Exception as e:
            logger.error("店舗の追加に失敗しました", 
                        store_code=store_code, 
                        error=str(e))
            return {
                'success': False,
                'error': f'店舗の追加に失敗しました: {str(e)}'
            }
    
    def update_store_status(self, store_code: str, status: str) -> Dict[str, Any]:
        """店舗のステータス変更"""
        try:
            if store_code not in self.stores:
                return {
                    'success': False,
                    'error': '店舗が見つかりません'
                }
            
            # ステータスの検証
            valid_statuses = ['active', 'suspended', 'expired']
            if status not in valid_statuses:
                return {
                    'success': False,
                    'error': '無効なステータスです'
                }
            
            # ステータスを更新
            old_status = self.stores[store_code]['status']
            self.stores[store_code]['status'] = status
            
            # スプレッドシートに反映
            self.update_store_in_sheet(store_code, {'status': status})
            
            logger.info("店舗のステータスを変更しました", 
                       store_code=store_code, 
                       old_status=old_status, 
                       new_status=status)
            
            return {
                'success': True,
                'store': self.stores[store_code]
            }
            
        except Exception as e:
            logger.error("店舗ステータスの変更に失敗しました", 
                        store_code=store_code, 
                        error=str(e))
            return {
                'success': False,
                'error': f'ステータス変更に失敗しました: {str(e)}'
            }
    
    def delete_store(self, store_code: str) -> Dict[str, Any]:
        """店舗の削除（利用停止）"""
        try:
            if store_code not in self.stores:
                return {
                    'success': False,
                    'error': '店舗が見つかりません'
                }
            
            # 店舗を削除
            deleted_store = self.stores.pop(store_code)
            
            # スプレッドシートから削除
            self.remove_store_from_sheet(store_code)
            
            logger.info("店舗を削除しました", store_code=store_code)
            
            return {
                'success': True,
                'store': deleted_store
            }
            
        except Exception as e:
            logger.error("店舗の削除に失敗しました", 
                        store_code=store_code, 
                        error=str(e))
            return {
                'success': False,
                'error': f'店舗の削除に失敗しました: {str(e)}'
            }
    
    def update_last_activity(self, store_code: str):
        """店舗の最終利用日時を更新"""
        try:
            if store_code in self.stores:
                self.stores[store_code]['last_activity'] = datetime.now().isoformat()
                
                # スプレッドシートに反映
                self.update_store_in_sheet(store_code, {
                    'last_activity': datetime.now().isoformat()
                })
                
                logger.debug("店舗の最終利用日時を更新しました", store_code=store_code)
                
        except Exception as e:
            logger.error("最終利用日時の更新に失敗しました", 
                        store_code=store_code, 
                        error=str(e))
    
    def get_store_detail(self, store_code: str) -> Optional[Dict[str, Any]]:
        """店舗の詳細情報取得"""
        return self.stores.get(store_code)
    
    def search_stores(self, query: str) -> List[Dict[str, Any]]:
        """店舗の検索"""
        try:
            query_lower = query.lower()
            results = []
            
            for store in self.stores.values():
                # 店舗コード、店舗名、所在地で検索
                if (query_lower in store['store_code'].lower() or
                    query_lower in store['store_name'].lower() or
                    query_lower in store['location'].lower()):
                    results.append(store)
            
            return results
            
        except Exception as e:
            logger.error("店舗検索に失敗しました", query=query, error=str(e))
            return []
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """最近の活動を取得"""
        try:
            # 最終利用日時でソート
            sorted_stores = sorted(
                self.stores.values(),
                key=lambda x: x['last_activity'] or '',
                reverse=True
            )
            
            return sorted_stores[:limit]
            
        except Exception as e:
            logger.error("最近の活動の取得に失敗しました", error=str(e))
            return []
    
    def add_store_to_sheet(self, store_data: Dict[str, Any]):
        """スプレッドシートに店舗を追加"""
        try:
            from .qa_service import QAService
            qa_service = QAService()
            
            # 新しい行のデータ
            new_row = [
                store_data['store_code'],
                store_data['store_name'],
                store_data['status'],
                store_data['created_at'],
                store_data['last_activity'],
                store_data['notes'],
                store_data['admin_notes'],
                store_data['contact_info'],
                store_data['location'],
                store_data['manager_name']
            ]
            
            # スプレッドシートに追加
            qa_service.append_sheet_row(self.sheet_name, new_row)
            
            logger.info("店舗をスプレッドシートに追加しました", 
                       store_code=store_data['store_code'])
            
        except Exception as e:
            logger.error("スプレッドシートへの店舗追加に失敗しました", 
                        store_code=store_data['store_code'], 
                        error=str(e))
            raise
    
    def update_store_in_sheet(self, store_code: str, updates: Dict[str, Any]):
        """スプレッドシートの店舗情報を更新"""
        try:
            from .qa_service import QAService
            qa_service = QAService()
            
            # スプレッドシートから現在のデータを取得
            sheet_data = qa_service.get_sheet_data(self.sheet_name)
            
            if not sheet_data:
                logger.warning("店舗管理シートのデータが取得できません")
                return
            
            # 該当する店舗の行を見つけて更新
            for i, row in enumerate(sheet_data[1:], start=2):  # ヘッダー行をスキップ
                if len(row) > 0 and row[0] == store_code:
                    # 更新する列を特定
                    for key, value in updates.items():
                        if key == 'status':
                            row[2] = value
                        elif key == 'last_activity':
                            row[4] = value
                        elif key == 'notes':
                            row[5] = value
                        # 他のフィールドも同様に処理
                    
                    # スプレッドシートを更新
                    qa_service.update_sheet_row(self.sheet_name, i, row)
                    break
            
            logger.info("店舗情報をスプレッドシートで更新しました", store_code=store_code)
            
        except Exception as e:
            logger.error("スプレッドシートの店舗情報更新に失敗しました", 
                        store_code=store_code, 
                        error=str(e))
    
    def remove_store_from_sheet(self, store_code: str):
        """スプレッドシートから店舗を削除"""
        try:
            from .qa_service import QAService
            qa_service = QAService()
            
            # スプレッドシートから現在のデータを取得
            sheet_data = qa_service.get_sheet_data(self.sheet_name)
            
            if not sheet_data:
                logger.warning("店舗管理シートのデータが取得できません")
                return
            
            # 該当する店舗の行を見つけて削除
            for i, row in enumerate(sheet_data[1:], start=2):  # ヘッダー行をスキップ
                if len(row) > 0 and row[0] == store_code:
                    # 行を削除
                    qa_service.delete_sheet_row(self.sheet_name, i)
                    break
            
            logger.info("店舗をスプレッドシートから削除しました", store_code=store_code)
            
        except Exception as e:
            logger.error("スプレッドシートからの店舗削除に失敗しました", 
                        store_code=store_code, 
                        error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """店舗統計を取得"""
        try:
            return {
                'total_stores': len(self.stores),
                'active_stores': len(self.get_active_stores()),
                'suspended_stores': len(self.get_suspended_stores()),
                'expired_stores': len(self.get_expired_stores()),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("店舗統計の取得に失敗しました", error=str(e))
            return {
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }
    
    def reload_stores(self):
        """店舗データを再読み込み"""
        try:
            self.load_stores_from_sheet()
            logger.info("店舗データを再読み込みしました")
            return True
            
        except Exception as e:
            logger.error("店舗データの再読み込みに失敗しました", error=str(e))
            return False
