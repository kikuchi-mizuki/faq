#!/usr/bin/env python3
"""
フロー処理のデバッグスクリプト
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

def debug_flows():
    """フローデータのデバッグ"""
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
        
        print("🔍 flowsシートの内容:")
        print(f"総行数: {len(values)}")
        print()
        
        # ヘッダー行を表示
        if len(values) > 0:
            print("📋 ヘッダー:")
            print(values[0])
            print()
        
        # データ行を表示
        if len(values) > 1:
            print("📊 データ行:")
            for i, row in enumerate(values[1:], 1):
                print(f"行 {i+1}: {row}")
        
        # トリガーの分析
        print("\n🎯 トリガー分析:")
        triggers = set()
        for row in values[1:]:
            if len(row) > 1 and row[1]:  # trigger列
                triggers.add(row[1])
        
        print(f"利用可能なトリガー: {sorted(list(triggers))}")
        
        # 制作依頼フローの詳細
        print("\n🎬 制作依頼フローの詳細:")
        production_flows = []
        for row in values[1:]:
            if len(row) > 1 and row[1] == '制作依頼':
                production_flows.append(row)
        
        for flow in production_flows:
            print(f"ID: {flow[0] if len(flow) > 0 else 'N/A'}")
            print(f"Trigger: {flow[1] if len(flow) > 1 else 'N/A'}")
            print(f"Step: {flow[2] if len(flow) > 2 else 'N/A'}")
            print(f"Question: {flow[3] if len(flow) > 3 else 'N/A'}")
            print(f"Options: {flow[4] if len(flow) > 4 else 'N/A'}")
            print(f"Next Step: {flow[5] if len(flow) > 5 else 'N/A'}")
            print(f"End: {flow[6] if len(flow) > 6 else 'N/A'}")
            print("---")
        
    except Exception as e:
        print(f"❌ エラー: {e}")

def main():
    """メイン関数"""
    print("🚀 フローデバッグ開始...")
    
    if not SHEET_ID:
        print("❌ SHEET_ID_QA環境変数が設定されていません")
        sys.exit(1)
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ 認証ファイルが見つかりません: {CREDENTIALS_FILE}")
        sys.exit(1)
    
    debug_flows()
    print("🎉 デバッグ完了！")

if __name__ == "__main__":
    main()
