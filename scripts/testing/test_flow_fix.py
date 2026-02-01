#!/usr/bin/env python3
"""
フロー修正のテストスクリプト
"""

import os
import sys
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# 設定
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = os.getenv('SHEET_ID_QA')
CREDENTIALS_FILE = 'faq-account.json'

def get_sheets_service():
    """Google Sheets APIサービスを取得"""
    try:
        creds = Credentials.from_service_account_file(
            CREDENTIALS_FILE, 
            scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        print(f"❌ Google Sheets API認証エラー: {e}")
        sys.exit(1)

def test_flow_parsing():
    """フロー解析のテスト"""
    try:
        service = get_sheets_service()
        
        # flowsシートからデータを取得
        range_name = 'flows!A1:I1000'
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            print("❌ flowsシートにデータがありません")
            return
        
        print("🔍 フロー解析テスト:")
        print()
        
        # データ行を処理
        for i, row in enumerate(values[1:], 1):
            if len(row) > 4 and row[1] == '制作依頼' and row[2] == '1':  # 制作依頼のステップ1
                print(f"📋 行 {i+1}: {row}")
                print(f"   Options: '{row[4]}'")
                
                # 修正前の解析
                old_options = [opt.strip() for opt in row[4].split("／") if opt.strip()]
                print(f"   修正前: {old_options}")
                
                # 修正後の解析
                options_text = row[4].replace("／", "/")
                new_options = [opt.strip() for opt in options_text.split("/") if opt.strip()]
                print(f"   修正後: {new_options}")
                
                print(f"   選択肢数: {len(new_options)}")
                print()
        
    except Exception as e:
        print(f"❌ エラー: {e}")

def main():
    """メイン関数"""
    print("🚀 フロー解析テスト開始...")
    
    if not SHEET_ID:
        print("❌ SHEET_ID_QA環境変数が設定されていません")
        sys.exit(1)
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ 認証ファイルが見つかりません: {CREDENTIALS_FILE}")
        sys.exit(1)
    
    test_flow_parsing()
    print("🎉 テスト完了！")

if __name__ == "__main__":
    main()
