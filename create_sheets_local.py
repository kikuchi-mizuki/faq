"""
Cursorからローカルでスプレッドシートを作成するスクリプト
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


def create_sheets_from_cursor():
    """Cursorからスプレッドシートを作成"""
    try:
        print("🚀 Cursorからスプレッドシート作成を開始します...")
        logger.info("Cursorからスプレッドシート作成を開始します")
        
        # 環境変数の確認
        auth_enabled = os.environ.get('AUTH_ENABLED', 'true').lower() == 'true'
        print(f"📋 認証機能の状態: {auth_enabled}")
        
        if not auth_enabled:
            print("⚠️ 認証機能が無効化されています。AUTH_ENABLED=trueに設定してください")
            return False
        
        # Google認証情報を取得
        credentials = get_google_credentials()
        if not credentials:
            print("❌ Google認証情報が取得できません")
            return False
        
        print("✅ Google認証情報を取得しました")
        
        # gspreadクライアントを初期化
        gc = gspread.authorize(credentials)
        print("✅ Google Sheetsクライアントを初期化しました")
        
        # スプレッドシートIDを取得
        sheet_id = os.environ.get('SHEET_ID_QA')
        if not sheet_id:
            print("❌ SHEET_ID_QA環境変数が設定されていません")
            return False
        
        print(f"📊 スプレッドシートID: {sheet_id}")
        
        # スプレッドシートを開く
        try:
            spreadsheet = gc.open_by_key(sheet_id)
            print(f"✅ スプレッドシートを開きました: {spreadsheet.title}")
        except Exception as e:
            print(f"❌ スプレッドシートを開けませんでした: {e}")
            return False
        
        # 店舗管理シートの作成
        print("\n🏪 店舗管理シートを作成します...")
        create_store_management_sheet(spreadsheet)
        
        # スタッフ管理シートの作成
        print("\n👥 スタッフ管理シートを作成します...")
        create_staff_management_sheet(spreadsheet)
        
        print("\n🎉 スプレッドシートの作成が完了しました！")
        logger.info("Cursorからスプレッドシート作成が完了しました")
        return True
        
    except Exception as e:
        print(f"❌ スプレッドシートの作成に失敗しました: {e}")
        logger.error("スプレッドシートの作成に失敗しました", error=str(e))
        return False


def get_google_credentials():
    """Google認証情報を取得"""
    try:
        # 環境変数から認証情報を取得
        service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not service_account_json:
            print("❌ GOOGLE_SERVICE_ACCOUNT_JSON環境変数が設定されていません")
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
        print(f"❌ Google認証情報の取得に失敗しました: {e}")
        logger.error("Google認証情報の取得に失敗しました", error=str(e))
        return None


def create_store_management_sheet(spreadsheet):
    """店舗管理シートを作成"""
    try:
        sheet_name = "store_management"
        print(f"  📋 シート名: {sheet_name}")
        
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
            print(f"  ✅ 店舗管理シートは既に存在します")
        except gspread.exceptions.WorksheetNotFound:
            # シートが存在しない場合は作成
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="10")
            print(f"  ✅ 店舗管理シートを作成しました")
        
        # ヘッダー行を設定
        worksheet.update('A1:J1', [headers])
        print(f"  ✅ ヘッダー行を設定しました")
        
        # サンプルデータを追加
        if worksheet.row_count == 1:  # ヘッダーのみの場合
            for row_data in sample_data:
                worksheet.append_row(row_data)
            print(f"  ✅ サンプルデータを追加しました ({len(sample_data)}件)")
        
        print(f"  🎉 店舗管理シートの作成が完了しました")
        
    except Exception as e:
        print(f"  ❌ 店舗管理シートの作成に失敗しました: {e}")
        raise


def create_staff_management_sheet(spreadsheet):
    """スタッフ管理シートを作成"""
    try:
        sheet_name = "staff_management"
        print(f"  📋 シート名: {sheet_name}")
        
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
            print(f"  ✅ スタッフ管理シートは既に存在します")
        except gspread.exceptions.WorksheetNotFound:
            # シートが存在しない場合は作成
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="10")
            print(f"  ✅ スタッフ管理シートを作成しました")
        
        # ヘッダー行を設定
        worksheet.update('A1:J1', [headers])
        print(f"  ✅ ヘッダー行を設定しました")
        
        # サンプルデータを追加
        if worksheet.row_count == 1:  # ヘッダーのみの場合
            for row_data in sample_data:
                worksheet.append_row(row_data)
            print(f"  ✅ サンプルデータを追加しました ({len(sample_data)}件)")
        
        print(f"  🎉 スタッフ管理シートの作成が完了しました")
        
    except Exception as e:
        print(f"  ❌ スタッフ管理シートの作成に失敗しました: {e}")
        raise


def main():
    """メイン処理"""
    try:
        print("=" * 60)
        print("🚀 Cursorからスプレッドシート作成を開始します")
        print("=" * 60)
        
        # スプレッドシートの作成
        success = create_sheets_from_cursor()
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 スプレッドシートの作成が完了しました！")
            print("=" * 60)
            print("📊 作成されたシート:")
            print("  - store_management (店舗管理)")
            print("  - staff_management (スタッフ管理)")
            print("\n🧪 認証システムが利用可能になりました")
            print("🎯 次のステップ: Botの動作確認")
        else:
            print("\n" + "=" * 60)
            print("❌ スプレッドシートの作成に失敗しました")
            print("=" * 60)
            print("🔧 確認事項:")
            print("  - 環境変数の設定")
            print("  - Google認証情報")
            print("  - スプレッドシートID")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        return False


if __name__ == "__main__":
    main()
