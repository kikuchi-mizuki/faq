"""
Railway起動時の自動セットアップスクリプト
認証システム用のスプレッドシートを自動作成
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


def auto_setup_auth_sheets():
    """認証システム用のスプレッドシートを自動作成"""
    try:
        logger.info("認証システム用スプレッドシートの自動作成を開始します")
        
        # 環境変数の確認
        if not os.environ.get('AUTH_ENABLED', '').lower() == 'true':
            logger.info("認証機能が無効化されているため、スプレッドシート作成をスキップします")
            return True
        
        # Google認証情報を取得
        credentials = get_google_credentials()
        if not credentials:
            logger.warning("Google認証情報が取得できません。スプレッドシート作成をスキップします")
            return True
        
        # gspreadクライアントを初期化
        gc = gspread.authorize(credentials)
        logger.info("Google Sheetsクライアントを初期化しました")
        
        # スプレッドシートIDを取得
        sheet_id = os.environ.get('SHEET_ID_QA')
        if not sheet_id:
            logger.warning("SHEET_ID_QA環境変数が設定されていません。スプレッドシート作成をスキップします")
            return True
        
        # スプレッドシートを開く
        spreadsheet = gc.open_by_id(sheet_id)
        logger.info("スプレッドシートを開きました", sheet_id=sheet_id)
        
        # 店舗管理シートの作成
        create_store_management_sheet(spreadsheet)
        
        # スタッフ管理シートの作成
        create_staff_management_sheet(spreadsheet)
        
        logger.info("認証システム用スプレッドシートの自動作成が完了しました")
        return True
        
    except Exception as e:
        logger.error("スプレッドシートの自動作成に失敗しました", error=str(e))
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


def create_store_management_sheet(spreadsheet):
    """店舗管理シートを作成"""
    try:
        sheet_name = "store_management"
        logger.info("店舗管理シートを作成します", sheet_name=sheet_name)
        
        # ヘッダー行のデータ
        headers = [
            "store_code",      # 店舗コード
            "store_name",      # 店舗名
            "status",          # ステータス
            "created_at",      # 作成日時
            "last_activity",   # 最終利用日時
            "notes",           # 備考
            "admin_notes",     # 管理者メモ
            "contact_info",    # 連絡先情報
            "location",        # 店舗所在地
            "manager_name"     # 店舗責任者名
        ]
        
        # サンプルデータ
        sample_data = [
            ["STORE001", "本店", "active", datetime.now().isoformat(), "", "本店", "", "03-1234-5678", "東京都渋谷区", "田中太郎"],
            ["STORE002", "渋谷店", "active", datetime.now().isoformat(), "", "渋谷店", "", "03-2345-6789", "東京都渋谷区", "佐藤花子"],
            ["STORE003", "新宿店", "suspended", datetime.now().isoformat(), "", "新宿店（一時休業）", "", "03-3456-7890", "東京都新宿区", "鈴木一郎"]
        ]
        
        # シートが存在するかチェック
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            logger.info("店舗管理シートは既に存在します", sheet_name=sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # シートが存在しない場合は作成
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="10")
            logger.info("店舗管理シートを作成しました", sheet_name=sheet_name)
        
        # ヘッダー行を設定
        worksheet.update('A1:J1', [headers])
        logger.info("店舗管理シートのヘッダーを設定しました")
        
        # サンプルデータを追加
        if worksheet.row_count == 1:  # ヘッダーのみの場合
            for row_data in sample_data:
                worksheet.append_row(row_data)
            logger.info("店舗管理シートのサンプルデータを追加しました", count=len(sample_data))
        
        logger.info("店舗管理シートの作成が完了しました", sheet_name=sheet_name)
        
    except Exception as e:
        logger.error("店舗管理シートの作成に失敗しました", error=str(e))
        raise


def create_staff_management_sheet(spreadsheet):
    """スタッフ管理シートを作成"""
    try:
        sheet_name = "staff_management"
        logger.info("スタッフ管理シートを作成します", sheet_name=sheet_name)
        
        # ヘッダー行のデータ
        headers = [
            "store_code",      # 店舗コード
            "staff_id",        # 社員番号
            "staff_name",      # スタッフ名
            "position",        # 役職
            "status",          # ステータス
            "created_at",      # 作成日時
            "last_activity",   # 最終利用日時
            "line_user_id",    # LINEユーザーID
            "auth_time",       # 認証日時
            "notes"            # 備考
        ]
        
        # サンプルデータ
        sample_data = [
            ["STORE001", "001", "田中太郎", "店長", "active", datetime.now().isoformat(), "", "", "", "本店店長"],
            ["STORE001", "002", "山田花子", "スタッフ", "active", datetime.now().isoformat(), "", "", "", "本店スタッフ"],
            ["STORE002", "003", "佐藤花子", "店長", "active", datetime.now().isoformat(), "", "", "", "渋谷店店長"],
            ["STORE002", "004", "鈴木一郎", "スタッフ", "suspended", datetime.now().isoformat(), "", "", "", "渋谷店スタッフ（一時停止）"]
        ]
        
        # シートが存在するかチェック
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            logger.info("スタッフ管理シートは既に存在します", sheet_name=sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # シートが存在しない場合は作成
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="10")
            logger.info("スタッフ管理シートを作成しました", sheet_name=sheet_name)
        
        # ヘッダー行を設定
        worksheet.update('A1:J1', [headers])
        logger.info("スタッフ管理シートのヘッダーを設定しました")
        
        # サンプルデータを追加
        if worksheet.row_count == 1:  # ヘッダーのみの場合
            for row_data in sample_data:
                worksheet.append_row(row_data)
            logger.info("スタッフ管理シートのサンプルデータを追加しました", count=len(sample_data))
        
        logger.info("スタッフ管理シートの作成が完了しました", sheet_name=sheet_name)
        
    except Exception as e:
        logger.error("スタッフ管理シートの作成に失敗しました", error=str(e))
        raise


def main():
    """メイン処理"""
    try:
        logger.info("認証システム用スプレッドシートの自動作成を開始します")
        
        # スプレッドシートの自動作成
        success = auto_setup_auth_sheets()
        
        if success:
            logger.info("認証システム用スプレッドシートの自動作成が完了しました")
            print("✅ 認証システム用スプレッドシートの自動作成が完了しました！")
            print("📊 作成されたシート:")
            print("  - store_management (店舗管理)")
            print("  - staff_management (スタッフ管理)")
            print("🧪 認証システムが利用可能になりました")
        else:
            logger.error("スプレッドシートの自動作成に失敗しました")
            print("❌ スプレッドシートの自動作成に失敗しました")
            return False
        
        return True
        
    except Exception as e:
        logger.error("スプレッドシート自動作成処理中にエラーが発生しました", error=str(e))
        print(f"❌ エラーが発生しました: {e}")
        return False


if __name__ == "__main__":
    main()
