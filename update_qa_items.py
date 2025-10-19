#!/usr/bin/env python3
"""
Q&Aアイテム自動更新スクリプト
Google Sheets APIを使ってqa_itemsシートを更新
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

def update_qa_items():
    """Q&Aアイテムを更新"""
    try:
        service = get_sheets_service()
        
        # 新しいQ&Aアイテムのデータ
        new_qa_items = [
            {
                'id': 101,
                'question': 'どのような媒体で制作可能ですか？',
                'answer': '様々な媒体に対応可能です。',
                'keywords': '媒体,制作,対応',
                'patterns': '媒体,制作,対応',
                'tags': '制作',
                'priority': 1,
                'status': 'active',
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 102,
                'question': 'どのような制作フローですか？',
                'answer': 'A.通常以下のフローでお作りしております。',
                'keywords': '制作フロー,フロー,手順',
                'patterns': '制作フロー,フロー,手順',
                'tags': '制作',
                'priority': 1,
                'status': 'active',
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 103,
                'question': '広告運用はご依頼可能ですか？',
                'answer': 'Twenty BUZZ!!プランという広告費込みのプランをご用意しております。',
                'keywords': '広告運用,広告費,プラン',
                'patterns': '広告運用,広告費,プラン',
                'tags': '広告',
                'priority': 1,
                'status': 'active',
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 104,
                'question': '修正は何回までできますか？',
                'answer': '修正回数に制限はありません。',
                'keywords': '修正,回数,制限',
                'patterns': '修正,回数,制限',
                'tags': '制作',
                'priority': 1,
                'status': 'active',
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 105,
                'question': '発注後のキャンセルは可能ですか？',
                'answer': '発注後のキャンセルは可能です。',
                'keywords': 'キャンセル,発注後,可能',
                'patterns': 'キャンセル,発注後,可能',
                'tags': '契約',
                'priority': 1,
                'status': 'active',
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 106,
                'question': '初期費用・解約費用・分割手数料はありますか？',
                'answer': 'ありません。0円です。',
                'keywords': '初期費用,解約費用,分割手数料',
                'patterns': '初期費用,解約費用,分割手数料',
                'tags': '料金',
                'priority': 1,
                'status': 'active',
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 107,
                'question': '何本からご依頼可能ですか？',
                'answer': '編集セット・撮影セットは3本〜ご依頼可能、出張セットは4本~ご依頼可能です。',
                'keywords': '本数,依頼,可能',
                'patterns': '本数,依頼,可能',
                'tags': '制作',
                'priority': 1,
                'status': 'active',
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 108,
                'question': '納期は何日程度ですか？',
                'answer': '1分以上動画(編集セット) ¥10,000 ・1分追加ごとに10,000円追加',
                'keywords': '納期,日数,期間',
                'patterns': '納期,日数,期間',
                'tags': '制作',
                'priority': 1,
                'status': 'active',
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 109,
                'question': 'Twenty BUZZプランについて教えてください',
                'answer': 'Twenty BUZZ!!プランという広告費込みのプランをご用意しております。',
                'keywords': 'Twenty BUZZプラン,広告費,プラン',
                'patterns': 'Twenty BUZZプラン,広告費,プラン',
                'tags': 'プラン',
                'priority': 1,
                'status': 'active',
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 110,
                'question': 'モーグラ(窪田さんの様な動画)について教えてください',
                'answer': 'モーグラ(窪田さんの様な動画)の制作も承っております。',
                'keywords': 'モーグラ,窪田,動画',
                'patterns': 'モーグラ,窪田,動画',
                'tags': '制作',
                'priority': 1,
                'status': 'active',
                'updated_at': datetime.now().isoformat()
            }
        ]
        
        # ヘッダー行を準備
        headers = ['id', 'question', 'answer', 'keywords', 'patterns', 'tags', 'priority', 'status', 'updated_at']
        
        # データ行を準備
        data_rows = [headers]
        for item in new_qa_items:
            data_rows.append([
                item['id'],
                item['question'],
                item['answer'],
                item['keywords'],
                item['patterns'],
                item['tags'],
                item['priority'],
                item['status'],
                item['updated_at']
            ])
        
        # 既存のデータをクリア
        clear_range = 'qa_items!A2:I1000'  # データ行のみクリア
        service.spreadsheets().values().clear(
            spreadsheetId=SHEET_ID,
            range=clear_range
        ).execute()
        
        # 新しいデータを追加
        update_range = f'qa_items!A1:I{len(data_rows)}'
        body = {
            'values': data_rows
        }
        
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=update_range,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"✅ Q&Aアイテム更新完了: {len(new_qa_items)}件")
        print(f"📅 更新日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except HttpError as e:
        print(f"❌ Google Sheets API エラー: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)

def main():
    """メイン関数"""
    print("🚀 Q&Aアイテム自動更新開始...")
    
    if not SHEET_ID:
        print("❌ SHEET_ID_QA環境変数が設定されていません")
        sys.exit(1)
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ 認証ファイルが見つかりません: {CREDENTIALS_FILE}")
        sys.exit(1)
    
    update_qa_items()
    print("🎉 更新完了！")

if __name__ == "__main__":
    main()
