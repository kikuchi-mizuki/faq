"""
STEP3用のスプレッドシート（locations, qa_form_log）にサンプルデータを追加するスクリプト
"""

import os
import json
import base64
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

def create_step3_sheets():
    """locationsシートとqa_form_logシートを作成してサンプルデータを追加"""
    
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
    
    today = datetime.now().strftime("%Y/%m/%d")
    
    # ========================================
    # locationsシートの作成
    # ========================================
    try:
        worksheet = spreadsheet.worksheet("locations")
        print("✅ locationsシートが既に存在します")
        worksheet.clear()
        print("   既存データをクリアしました")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="locations", rows=100, cols=10)
        print("✅ locationsシートを新規作成しました")
    
    # ヘッダー行
    location_headers = [
        "category",
        "title",
        "url",
        "description",
        "tags",
        "updated_at"
    ]
    
    # サンプルデータ（資料ナビゲーション）
    location_data = [
        location_headers,
        ["経理", "月次締め手順書", "https://docs.google.com/document/d/example1", "月次締めの詳細な手順を記載", "経理,月次,締め", today],
        ["経理", "請求書発行マニュアル", "https://docs.google.com/document/d/example2", "請求書の発行方法について", "請求書,経理", today],
        ["経理", "経費精算ガイド", "https://docs.google.com/document/d/example3", "経費精算の申請方法", "経費,精算,経理", today],
        ["営業", "営業マニュアル", "https://docs.google.com/document/d/example4", "営業活動の基本手順", "営業,マニュアル", today],
        ["営業", "見積書テンプレート", "https://docs.google.com/spreadsheets/d/example5", "見積書の作成テンプレート", "見積書,営業", today],
        ["制作", "デザインガイドライン", "https://www.figma.com/file/example6", "ブランドガイドライン", "デザイン,制作", today],
        ["制作", "修正回数のルール", "https://docs.google.com/document/d/example7", "修正対応のルールについて", "修正,リテイク,制作", today],
        ["人事", "休暇申請方法", "https://docs.google.com/document/d/example8", "有給休暇の申請手順", "休暇,人事", today],
        ["人事", "シフト調整ガイド", "https://docs.google.com/document/d/example9", "シフト調整の方法", "シフト,人事", today],
        ["IT", "パスワードリセット手順", "https://docs.google.com/document/d/example10", "パスワードのリセット方法", "パスワード,IT", today],
        ["IT", "システム利用マニュアル", "https://docs.google.com/document/d/example11", "社内システムの使い方", "システム,IT", today],
    ]
    
    worksheet.update(range_name="A1", values=location_data)
    print(f"✅ locationsシートに{len(location_data) - 1}件のサンプルデータを追加しました")
    
    # ========================================
    # qa_form_logシートの作成
    # ========================================
    try:
        worksheet_log = spreadsheet.worksheet("qa_form_log")
        print("✅ qa_form_logシートが既に存在します")
        worksheet_log.clear()
        print("   既存データをクリアしました")
    except gspread.exceptions.WorksheetNotFound:
        worksheet_log = spreadsheet.add_worksheet(title="qa_form_log", rows=100, cols=10)
        print("✅ qa_form_logシートを新規作成しました")
    
    # ヘッダー行
    form_log_headers = [
        "timestamp",
        "question",
        "answer",
        "category",
        "keywords",
        "approved",
        "created_by",
        "notes"
    ]
    
    # サンプルデータ（フォーム投稿ログ）
    form_log_data = [
        form_log_headers,
        [today, "新しいプランの料金はいくらですか？", "新プランは月額5,000円からご利用いただけます。", "営業", "料金,プラン", "FALSE", "yamada@example.com", "営業チームから投稿"],
        [today, "リモートワークは可能ですか？", "週2日までリモートワークが可能です。事前に申請が必要です。", "人事", "リモート,働き方", "FALSE", "tanaka@example.com", "人事部門から投稿"],
        [today, "データのバックアップ方法は？", "毎日自動バックアップが実行されます。手動バックアップも可能です。", "IT", "バックアップ,データ", "TRUE", "suzuki@example.com", "承認済み・IT部門"],
    ]
    
    worksheet_log.update(range_name="A1", values=form_log_data)
    print(f"✅ qa_form_logシートに{len(form_log_data) - 1}件のサンプルデータを追加しました")
    
    print("\n" + "=" * 60)
    print("🎉 STEP3のシート作成が完了しました！")
    print("=" * 60)
    print("\n📊 追加されたシート:")
    print("  1. locationsシート（資料ナビゲーション）")
    print(f"     - {len(location_data) - 1}件の資料リンク")
    print("  2. qa_form_logシート（フォーム投稿ログ）")
    print(f"     - {len(form_log_data) - 1}件の投稿ログ")
    print("\n🎯 次のステップ:")
    print("  1. アプリをリロード: curl -X POST http://localhost:5000/admin/reload")
    print("  2. LINEで「経理の資料」と送信してテスト")
    print("  3. Googleフォームを作成して連携")


if __name__ == "__main__":
    try:
        create_step3_sheets()
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

