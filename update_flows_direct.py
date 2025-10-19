#!/usr/bin/env python3
"""
flowsシートを直接修正するスクリプト
既存のupdate_flows.pyを拡張
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
    # 環境変数から直接読み込み
    service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not service_account_json:
        # ファイルから読み込みを試行
        try:
            with open('faq-account.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise ValueError("認証情報が見つかりません")
    
    return json.loads(service_account_json)

def update_flows_sheet():
    """flowsシートを更新"""
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
        # 行番号を特定（ID 5の行）
        for i, row in enumerate(all_data, start=2):  # ヘッダー行を考慮
            if row.get('id') == 5:
                # End列（G列）をFALSEに変更
                flows_sheet.update_cell(i, 7, 'FALSE')
                # Next Step列（F列）を5に変更
                flows_sheet.update_cell(i, 6, '5')
                print(f"✅ ID 5の行（行{i}）を修正しました")
                break
        
        # 新しい分岐を追加
        new_flows = [
            # ID 6: 媒体の選択
            {
                'id': 6,
                'trigger': '204 制作依頼',
                'step': 5,
                'question': 'ご希望の媒体はどちらですか？',
                'options': '動画 / 静止画 / 両方',
                'next_step': '6',
                'end': 'FALSE',
                'fa': ''
            },
            # ID 7: 制作本数
            {
                'id': 7,
                'trigger': '204 制作依頼',
                'step': 6,
                'question': '制作本数は何本ですか？',
                'options': '1本 / 2-3本 / 4本以上',
                'next_step': '7',
                'end': 'FALSE',
                'fa': ''
            },
            # ID 8: 納期
            {
                'id': 8,
                'trigger': '204 制作依頼',
                'step': 7,
                'question': '納期はいつ頃ですか？',
                'options': '1週間以内 / 2週間以内 / 1ヶ月以内',
                'next_step': '8',
                'end': 'FALSE',
                'fa': ''
            },
            # ID 9: 広告運用
            {
                'id': 9,
                'trigger': '204 制作依頼',
                'step': 8,
                'question': '広告運用もご希望ですか？',
                'options': 'はい / いいえ',
                'next_step': '9',
                'end': 'FALSE',
                'fa': ''
            },
            # ID 10: 最終確認
            {
                'id': 10,
                'trigger': '204 制作依頼',
                'step': 9,
                'question': '制作依頼の詳細を承りました。担当者から24時間以内にご連絡いたします。',
                'options': '',
                'next_step': '',
                'end': 'TRUE',
                'fa': ''
            }
        ]
        
        # 新しい行を追加
        for flow in new_flows:
            row_data = [
                flow['id'],
                flow['trigger'],
                flow['step'],
                flow['question'],
                flow['options'],
                flow['next_step'],
                flow['end'],
                flow['fa']
            ]
            flows_sheet.append_row(row_data)
            print(f"✅ 新しい分岐を追加しました: ID {flow['id']}")
        
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
    update_flows_sheet()
