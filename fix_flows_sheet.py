#!/usr/bin/env python3
"""
flowsシートの修正スクリプト
204制作依頼の分岐を修正
"""

import os
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

def get_credentials():
    """Google認証情報を取得"""
    service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not service_account_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON環境変数が設定されていません")
    
    return json.loads(service_account_json)

def fix_flows_sheet():
    """flowsシートを修正"""
    try:
        # 認証情報を取得
        credentials_info = get_credentials()
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # スプレッドシートを開く
        sheet_id = os.getenv('SHEET_ID_QA')
        if not sheet_id:
            raise ValueError("SHEET_ID_QA環境変数が設定されていません")
        
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open_by_key(sheet_id)
        
        # flowsシートを取得
        flows_sheet = spreadsheet.worksheet('flows')
        print("✅ flowsシートにアクセスしました")
        
        # 現在のデータを取得
        all_data = flows_sheet.get_all_records()
        print(f"📊 現在のデータ件数: {len(all_data)}件")
        
        # ID 5の行を修正（204制作依頼のStep 4）
        # EndをFALSEに、Next Stepを5に変更
        flows_sheet.update_cell(6, 7, 'FALSE')  # End列（G列）をFALSEに
        flows_sheet.update_cell(6, 6, '5')      # Next Step列（F列）を5に
        
        print("✅ ID 5の行を修正しました（End=FALSE, Next Step=5）")
        
        # 新しい分岐を追加
        new_rows = [
            # ID 6: 媒体の選択
            [6, '204 制作依頼', 5, 'ご希望の媒体はどちらですか？', '動画 / 静止画 / 両方', '6', 'FALSE', ''],
            # ID 7: 制作本数
            [7, '204 制作依頼', 6, '制作本数は何本ですか？', '1本 / 2-3本 / 4本以上', '7', 'FALSE', ''],
            # ID 8: 納期
            [8, '204 制作依頼', 7, '納期はいつ頃ですか？', '1週間以内 / 2週間以内 / 1ヶ月以内', '8', 'FALSE', ''],
            # ID 9: 広告運用
            [9, '204 制作依頼', 8, '広告運用もご希望ですか？', 'はい / いいえ', '9', 'FALSE', ''],
            # ID 10: 最終確認
            [10, '204 制作依頼', 9, '制作依頼の詳細を承りました。担当者から24時間以内にご連絡いたします。', '', '', 'TRUE', '']
        ]
        
        # 新しい行を追加
        for row_data in new_rows:
            flows_sheet.append_row(row_data)
            print(f"✅ 新しい分岐を追加しました: ID {row_data[0]}")
        
        print("🎉 flowsシートの修正が完了しました！")
        print("\n📋 修正内容:")
        print("- ID 5: End=FALSE, Next Step=5に変更")
        print("- ID 6-10: 新しい分岐を追加")
        print("- 制作依頼の分岐が5ステップに拡張")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_flows_sheet()
