"""
スプレッドシートに店舗・スタッフ情報を追加登録するスクリプト
認証システム用のデータを追加
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


def add_store_staff_data():
    """店舗・スタッフ情報を追加登録"""
    try:
        print("🚀 スプレッドシートに店舗・スタッフ情報を追加登録します...")
        logger.info("店舗・スタッフ情報の追加登録を開始します")
        
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
        
        # 店舗情報の追加
        print("\n🏪 店舗情報を追加します...")
        add_store_data(spreadsheet)
        
        # スタッフ情報の追加
        print("\n👥 スタッフ情報を追加します...")
        add_staff_data(spreadsheet)
        
        print("\n🎉 店舗・スタッフ情報の追加登録が完了しました！")
        logger.info("店舗・スタッフ情報の追加登録が完了しました")
        return True
        
    except Exception as e:
        print(f"❌ 店舗・スタッフ情報の追加登録に失敗しました: {e}")
        logger.error("店舗・スタッフ情報の追加登録に失敗しました", error=str(e))
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


def add_store_data(spreadsheet):
    """店舗情報を追加"""
    try:
        sheet_name = "store_management"
        print(f"  📋 シート名: {sheet_name}")
        
        # 追加する店舗データ
        additional_stores = [
            ["STORE004", "池袋店", "active", datetime.now().isoformat(), "", "池袋店", "", "03-4567-8901", "東京都豊島区", "高橋太郎"],
            ["STORE005", "横浜店", "active", datetime.now().isoformat(), "", "横浜店", "", "045-123-4567", "神奈川県横浜市", "佐々木花子"],
            ["STORE006", "大阪店", "active", datetime.now().isoformat(), "", "大阪店", "", "06-7890-1234", "大阪府大阪市", "山田次郎"],
            ["STORE007", "名古屋店", "suspended", datetime.now().isoformat(), "", "名古屋店（改装中）", "", "052-345-6789", "愛知県名古屋市", "鈴木三郎"]
        ]
        
        # シートを取得
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            print(f"  ✅ 店舗管理シートを取得しました")
        except gspread.exceptions.WorksheetNotFound:
            print(f"  ❌ 店舗管理シートが見つかりません")
            return
        
        # データを追加
        for store_data in additional_stores:
            worksheet.append_row(store_data)
            print(f"  ✅ 店舗を追加しました: {store_data[0]} - {store_data[1]}")
        
        print(f"  🎉 店舗情報の追加が完了しました ({len(additional_stores)}件)")
        
    except Exception as e:
        print(f"  ❌ 店舗情報の追加に失敗しました: {e}")
        raise


def add_staff_data(spreadsheet):
    """スタッフ情報を追加"""
    try:
        sheet_name = "staff_management"
        print(f"  📋 シート名: {sheet_name}")
        
        # 追加するスタッフデータ
        additional_staff = [
            # 池袋店のスタッフ
            ["STORE004", "004", "高橋太郎", "店長", "active", datetime.now().isoformat(), "", "", "", "池袋店店長"],
            ["STORE004", "005", "田中美咲", "スタッフ", "active", datetime.now().isoformat(), "", "", "", "池袋店スタッフ"],
            ["STORE004", "006", "伊藤健太", "スタッフ", "active", datetime.now().isoformat(), "", "", "", "池袋店スタッフ"],
            
            # 横浜店のスタッフ
            ["STORE005", "007", "佐々木花子", "店長", "active", datetime.now().isoformat(), "", "", "", "横浜店店長"],
            ["STORE005", "008", "中村由美", "スタッフ", "active", datetime.now().isoformat(), "", "", "", "横浜店スタッフ"],
            ["STORE005", "009", "小林正雄", "スタッフ", "suspended", datetime.now().isoformat(), "", "", "", "横浜店スタッフ（一時停止）"],
            
            # 大阪店のスタッフ
            ["STORE006", "010", "山田次郎", "店長", "active", datetime.now().isoformat(), "", "", "", "大阪店店長"],
            ["STORE006", "011", "松本さくら", "スタッフ", "active", datetime.now().isoformat(), "", "", "", "大阪店スタッフ"],
            ["STORE006", "012", "加藤大輔", "スタッフ", "active", datetime.now().isoformat(), "", "", "", "大阪店スタッフ"],
            
            # 名古屋店のスタッフ（停止中）
            ["STORE007", "013", "鈴木三郎", "店長", "suspended", datetime.now().isoformat(), "", "", "", "名古屋店店長（改装中）"],
            ["STORE007", "014", "吉田恵子", "スタッフ", "suspended", datetime.now().isoformat(), "", "", "", "名古屋店スタッフ（改装中）"]
        ]
        
        # シートを取得
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            print(f"  ✅ スタッフ管理シートを取得しました")
        except gspread.exceptions.WorksheetNotFound:
            print(f"  ❌ スタッフ管理シートが見つかりません")
            return
        
        # データを追加
        for staff_data in additional_staff:
            worksheet.append_row(staff_data)
            print(f"  ✅ スタッフを追加しました: {staff_data[0]}_{staff_data[1]} - {staff_data[2]}")
        
        print(f"  🎉 スタッフ情報の追加が完了しました ({len(additional_staff)}件)")
        
    except Exception as e:
        print(f"  ❌ スタッフ情報の追加に失敗しました: {e}")
        raise


def main():
    """メイン処理"""
    try:
        print("=" * 60)
        print("🚀 スプレッドシートに店舗・スタッフ情報を追加登録します")
        print("=" * 60)
        
        # 店舗・スタッフ情報の追加
        success = add_store_staff_data()
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 店舗・スタッフ情報の追加登録が完了しました！")
            print("=" * 60)
            print("📊 追加されたデータ:")
            print("  🏪 店舗情報:")
            print("    - STORE004: 池袋店（active）")
            print("    - STORE005: 横浜店（active）")
            print("    - STORE006: 大阪店（active）")
            print("    - STORE007: 名古屋店（suspended）")
            print("  👥 スタッフ情報:")
            print("    - 池袋店: 3名（店長1名、スタッフ2名）")
            print("    - 横浜店: 3名（店長1名、スタッフ2名）")
            print("    - 大阪店: 3名（店長1名、スタッフ2名）")
            print("    - 名古屋店: 2名（店長1名、スタッフ1名、全員suspended）")
            print("\n🧪 認証テストが可能になりました")
            print("🎯 次のステップ: 認証フローのテスト")
        else:
            print("\n" + "=" * 60)
            print("❌ 店舗・スタッフ情報の追加登録に失敗しました")
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
