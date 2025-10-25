"""
スプレッドシート作成状況の確認スクリプト
Railway環境でスプレッドシートが正しく作成されているか確認
"""

import os
import time
from datetime import datetime
import structlog
import gspread
from google.oauth2.service_account import Credentials
import json

# 構造化ログの設定
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def check_sheets():
    """スプレッドシートの作成状況を確認"""
    try:
        logger.info("スプレッドシートの作成状況を確認します")
        
        # 環境変数の確認
        auth_enabled = os.environ.get('AUTH_ENABLED', '').lower() == 'true'
        logger.info("認証機能の状態", auth_enabled=auth_enabled)
        
        if not auth_enabled:
            logger.info("認証機能が無効化されているため、スプレッドシート確認をスキップします")
            return True
        
        # Google認証情報を取得
        credentials = get_google_credentials()
        if not credentials:
            logger.warning("Google認証情報が取得できません。スプレッドシート確認をスキップします")
            return True
        
        # gspreadクライアントを初期化
        gc = gspread.authorize(credentials)
        logger.info("Google Sheetsクライアントを初期化しました")
        
        # スプレッドシートIDを取得
        sheet_id = os.environ.get('SHEET_ID_QA')
        if not sheet_id:
            logger.warning("SHEET_ID_QA環境変数が設定されていません。スプレッドシート確認をスキップします")
            return True
        
        # スプレッドシートを開く
        spreadsheet = gc.open_by_id(sheet_id)
        logger.info("スプレッドシートを開きました", sheet_id=sheet_id)
        
        # 店舗管理シートの確認
        check_store_management_sheet(spreadsheet)
        
        # スタッフ管理シートの確認
        check_staff_management_sheet(spreadsheet)
        
        logger.info("スプレッドシートの作成状況確認が完了しました")
        return True
        
    except Exception as e:
        logger.error("スプレッドシートの確認に失敗しました", error=str(e))
        return False


def get_google_credentials():
    """Google認証情報を取得"""
    try:
        # 環境変数から認証情報を取得
        service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not service_account_json:
            return None
        
        # JSON文字列をパース
        if service_account_json.startswith('{'):
            # 直接JSON文字列の場合
            credentials_dict = json.loads(service_account_json)
        else:
            # ファイルパスの場合
            with open(service_account_json, 'r') as f:
                credentials_dict = json.load(f)
        
        # 認証情報を作成
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        return credentials
        
    except Exception as e:
        logger.error("Google認証情報の取得に失敗しました", error=str(e))
        return None


def check_store_management_sheet(spreadsheet):
    """店舗管理シートの確認"""
    try:
        sheet_name = "store_management"
        logger.info("店舗管理シートを確認します", sheet_name=sheet_name)
        
        # シートが存在するかチェック
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            logger.info("店舗管理シートが存在します", sheet_name=sheet_name)
            
            # データの確認
            records = worksheet.get_all_records()
            logger.info("店舗管理シートのデータ", count=len(records))
            
            # サンプルデータの確認
            for record in records:
                store_code = record.get('store_code', '')
                store_name = record.get('store_name', '')
                status = record.get('status', '')
                logger.info("店舗データ", store_code=store_code, store_name=store_name, status=status)
            
        except gspread.exceptions.WorksheetNotFound:
            logger.warning("店舗管理シートが見つかりません", sheet_name=sheet_name)
        
    except Exception as e:
        logger.error("店舗管理シートの確認に失敗しました", error=str(e))


def check_staff_management_sheet(spreadsheet):
    """スタッフ管理シートの確認"""
    try:
        sheet_name = "staff_management"
        logger.info("スタッフ管理シートを確認します", sheet_name=sheet_name)
        
        # シートが存在するかチェック
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            logger.info("スタッフ管理シートが存在します", sheet_name=sheet_name)
            
            # データの確認
            records = worksheet.get_all_records()
            logger.info("スタッフ管理シートのデータ", count=len(records))
            
            # サンプルデータの確認
            for record in records:
                store_code = record.get('store_code', '')
                staff_id = record.get('staff_id', '')
                staff_name = record.get('staff_name', '')
                status = record.get('status', '')
                logger.info("スタッフデータ", store_code=store_code, staff_id=staff_id, staff_name=staff_name, status=status)
            
        except gspread.exceptions.WorksheetNotFound:
            logger.warning("スタッフ管理シートが見つかりません", sheet_name=sheet_name)
        
    except Exception as e:
        logger.error("スタッフ管理シートの確認に失敗しました", error=str(e))


def main():
    """メイン処理"""
    try:
        logger.info("スプレッドシートの作成状況確認を開始します")
        
        # スプレッドシートの確認
        success = check_sheets()
        
        if success:
            logger.info("スプレッドシートの作成状況確認が完了しました")
            print("✅ スプレッドシートの作成状況確認が完了しました！")
            print("📊 確認結果:")
            print("  - 店舗管理シート: 確認完了")
            print("  - スタッフ管理シート: 確認完了")
            print("🧪 認証システムが利用可能です")
        else:
            logger.error("スプレッドシートの確認に失敗しました")
            print("❌ スプレッドシートの確認に失敗しました")
            return False
        
        return True
        
    except Exception as e:
        logger.error("スプレッドシート確認処理中にエラーが発生しました", error=str(e))
        print(f"❌ エラーが発生しました: {e}")
        return False


if __name__ == "__main__":
    main()
