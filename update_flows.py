#!/usr/bin/env python3
"""
Flowsシート自動更新スクリプト
Google Sheets APIを使ってflowsシートを更新
"""

import os
import sys
import json
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

def update_flows():
    """Flowsシートを更新"""
    try:
        service = get_sheets_service()
        
        # 新しいフローアイテムのデータ
        new_flows = [
            # 制作依頼フロー
            {
                'id': 201,
                'trigger': '制作依頼',
                'step': 1,
                'question': 'どのような媒体で制作をご希望ですか？',
                'options': 'YouTube/Instagram/TikTok/その他',
                'next_step': 2,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 202,
                'trigger': '制作依頼',
                'step': 2,
                'question': '制作本数は何本ご希望ですか？',
                'options': '1-3本/4-10本/10本以上',
                'next_step': 3,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 203,
                'trigger': '制作依頼',
                'step': 3,
                'question': '納期はいかがでしょうか？',
                'options': '1週間以内/2-3週間/1ヶ月以上',
                'next_step': 4,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 204,
                'trigger': '制作依頼',
                'step': 4,
                'question': '広告運用もご希望ですか？',
                'options': 'はい（Twenty BUZZプラン）/いいえ（制作のみ）',
                'next_step': 999,
                'end': True,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            
            # 料金・契約フロー
            {
                'id': 205,
                'trigger': '料金相談',
                'step': 1,
                'question': 'どのような料金についてお聞きになりたいですか？',
                'options': '制作費用/広告運用費/初期費用・解約費用',
                'next_step': 2,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 206,
                'trigger': '料金相談',
                'step': 2,
                'question': '制作本数はどのくらいを想定されていますか？',
                'options': '1-3本/4-10本/10本以上',
                'next_step': 999,
                'end': True,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            
            # 修正・キャンセルフロー
            {
                'id': 207,
                'trigger': '修正相談',
                'step': 1,
                'question': '修正についてお聞きになりたいですか？',
                'options': '修正回数/修正料金/修正手順',
                'next_step': 2,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 208,
                'trigger': '修正相談',
                'step': 2,
                'question': '修正回数に制限はありません。何度でも無料で対応いたします。',
                'options': '了解/詳細を聞く',
                'next_step': 999,
                'end': True,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            
            # プラン相談フロー
            {
                'id': 209,
                'trigger': 'プラン相談',
                'step': 1,
                'question': 'どのプランについてお聞きになりたいですか？',
                'options': 'Twenty BUZZプラン/モーグラ動画/その他',
                'next_step': 2,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 210,
                'trigger': 'プラン相談',
                'step': 2,
                'question': 'Twenty BUZZプランは広告費込みのプランです。詳細な料金をお知らせします。',
                'options': '料金を聞く/申し込む/他のプランを見る',
                'next_step': 999,
                'end': True,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            
            # サポートフロー
            {
                'id': 211,
                'trigger': 'サポート',
                'step': 1,
                'question': 'どのようなサポートが必要ですか？',
                'options': '技術的問題/料金問題/その他',
                'next_step': 2,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 212,
                'trigger': 'サポート',
                'step': 2,
                'question': '問題の詳細をお聞かせください。担当者が直接サポートいたします。',
                'options': '問題を説明/担当者に連絡/FAQを見る',
                'next_step': 999,
                'end': True,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            }
        ]
        
        # ヘッダー行を準備
        headers = ['id', 'trigger', 'step', 'question', 'options', 'next_step', 'end', 'fallback_next', 'updated_at']
        
        # データ行を準備
        data_rows = [headers]
        for flow in new_flows:
            data_rows.append([
                flow['id'],
                flow['trigger'],
                flow['step'],
                flow['question'],
                flow['options'],
                flow['next_step'],
                flow['end'],
                flow['fallback_next'],
                flow['updated_at']
            ])
        
        # 既存のデータをクリア
        clear_range = 'flows!A2:I1000'  # データ行のみクリア
        service.spreadsheets().values().clear(
            spreadsheetId=SHEET_ID,
            range=clear_range
        ).execute()
        
        # 新しいデータを追加
        update_range = f'flows!A1:I{len(data_rows)}'
        body = {
            'values': data_rows
        }
        
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=update_range,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"✅ Flows更新完了: {len(new_flows)}件")
        print(f"📅 更新日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # フロー統計を表示
        triggers = {}
        for flow in new_flows:
            trigger = flow['trigger']
            if trigger not in triggers:
                triggers[trigger] = 0
            triggers[trigger] += 1
        
        print("\n📊 フロー統計:")
        for trigger, count in triggers.items():
            print(f"  - {trigger}: {count}ステップ")
        
    except HttpError as e:
        print(f"❌ Google Sheets API エラー: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)

def main():
    """メイン関数"""
    print("🚀 Flows自動更新開始...")
    
    if not SHEET_ID:
        print("❌ SHEET_ID_QA環境変数が設定されていません")
        sys.exit(1)
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ 認証ファイルが見つかりません: {CREDENTIALS_FILE}")
        sys.exit(1)
    
    update_flows()
    print("🎉 Flows更新完了！")

if __name__ == "__main__":
    main()
