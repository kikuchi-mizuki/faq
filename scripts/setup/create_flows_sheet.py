"""
flowsシートにサンプルデータを追加するスクリプト
"""

import os
import json
import base64
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

def create_flows_sheet():
    """flowsシートを作成してサンプルデータを追加"""
    
    # Google Sheets APIの初期化
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    
    # Base64デコード or ファイルパス
    if service_account_json.endswith('.json'):
        # ファイルパスの場合
        credentials = Credentials.from_service_account_file(
            service_account_json,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
    else:
        # Base64エンコードされたJSONの場合
        service_account_info = json.loads(base64.b64decode(service_account_json))
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
    
    gc = gspread.authorize(credentials)
    
    # スプレッドシートを開く
    sheet_id = os.environ.get("SHEET_ID_QA", "")
    spreadsheet = gc.open_by_key(sheet_id)
    
    # flowsシートが存在するか確認
    try:
        worksheet = spreadsheet.worksheet("flows")
        print("✅ flowsシートが既に存在します")
        
        # データをクリア
        worksheet.clear()
        print("   既存データをクリアしました")
        
    except gspread.exceptions.WorksheetNotFound:
        # シートを新規作成
        worksheet = spreadsheet.add_worksheet(title="flows", rows=100, cols=10)
        print("✅ flowsシートを新規作成しました")
    
    # ヘッダー行を作成
    headers = [
        "id",
        "trigger",
        "step",
        "question",
        "options",
        "next_step",
        "end",
        "fallback_next",
        "updated_at"
    ]
    
    # サンプルデータ（月次締めフロー）
    today = datetime.now().strftime("%Y/%m/%d")
    
    sample_data = [
        headers,  # ヘッダー行
        # 月次締めフロー
        [201, "月次締め", 1, "申請は完了していますか？", "はい／いいえ", "2／3", "FALSE", 999, today],
        [202, "月次締め", 2, "承認されましたか？", "はい／いいえ", "10／11", "FALSE", 999, today],
        [203, "月次締め", 3, "申請フォームを開きますか？", "はい／いいえ", "20／999", "FALSE", 999, today],
        [210, "月次締め", 10, "処理が完了しました。✅\n\n経理システムをご確認ください。", "", "", "TRUE", 999, today],
        [211, "月次締め", 11, "承認待ちです。⏳\n\n上長に確認してください。", "", "", "TRUE", 999, today],
        [220, "月次締め", 20, "申請フォームはこちらです。\n📝 https://example.com/form\n\n記入後、改めて申請してください。", "", "", "TRUE", 999, today],
        [299, "月次締め", 999, "入力が正しくありません。❌\n\n最初からやり直す場合は「月次締め」と入力してください。", "", "", "TRUE", 999, today],
        
        # サポートフロー（追加例）
        [301, "サポート", 1, "どのような問題ですか？", "ログインできない／エラーが出る／その他", "2／3／4", "FALSE", 999, today],
        [302, "サポート", 2, "パスワードをリセットしますか？", "はい／いいえ", "10／11", "FALSE", 999, today],
        [303, "サポート", 3, "エラーコードを教えてください", "E001／E002／その他", "20／21／22", "FALSE", 999, today],
        [304, "サポート", 4, "お問い合わせフォームからご連絡ください。\n📧 support@example.com", "", "", "TRUE", 999, today],
        [310, "サポート", 10, "パスワードリセットリンクを送信しました。📧\n\nメールをご確認ください。", "", "", "TRUE", 999, today],
        [311, "サポート", 11, "パスワードは管理者にお問い合わせください。", "", "", "TRUE", 999, today],
        [320, "サポート", 20, "E001エラーは再ログインで解決することがあります。\n\n一度ログアウトして再試行してください。", "", "", "TRUE", 999, today],
        [321, "サポート", 21, "E002エラーはシステムメンテナンス中の可能性があります。\n\n30分後に再度お試しください。", "", "", "TRUE", 999, today],
        [322, "サポート", 22, "サポートチームにお問い合わせください。\n📧 support@example.com", "", "", "TRUE", 999, today],
        [399, "サポート", 999, "入力が正しくありません。❌\n\n最初からやり直す場合は「サポート」と入力してください。", "", "", "TRUE", 999, today],
    ]
    
    # データを一括で書き込み
    worksheet.update(range_name="A1", values=sample_data)
    
    print(f"✅ {len(sample_data) - 1}件のサンプルデータを追加しました")
    print("\n📊 追加されたフロー:")
    print("  1. 月次締めフロー（トリガー: 月次締め）")
    print("  2. サポートフロー（トリガー: サポート）")
    print("\n🎯 次のステップ:")
    print("  1. アプリをリロード: curl -X POST http://localhost:5000/admin/reload")
    print("  2. LINEで「月次締め」または「サポート」と送信してテスト")


if __name__ == "__main__":
    try:
        create_flows_sheet()
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

