#!/usr/bin/env python3
"""
Flowsシート改善版更新スクリプト
より実用的で分かりやすい分岐フローを作成
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

def update_flows_improved():
    """Flowsシートを改善版に更新"""
    try:
        service = get_sheets_service()
        
        # 改善されたフローアイテムのデータ
        new_flows = [
            # 制作依頼フロー（改善版）
            {
                'id': 201,
                'trigger': '制作依頼',
                'step': 1,
                'question': '🎬 動画制作のご依頼ありがとうございます！\n\nまず、どの媒体での制作をご希望でしょうか？',
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
                'question': '📊 制作本数はいかがでしょうか？\n\n本数によって料金プランが変わります。',
                'options': '1-3本/4-10本/10本以上/相談したい',
                'next_step': 3,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 203,
                'trigger': '制作依頼',
                'step': 3,
                'question': '⏰ 納期について教えてください。\n\n急ぎの場合は特急料金が発生する場合があります。',
                'options': '1週間以内（特急）/2-3週間（通常）/1ヶ月以上/相談したい',
                'next_step': 4,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 204,
                'trigger': '制作依頼',
                'step': 4,
                'question': '💰 広告運用もご希望ですか？\n\nTwenty BUZZプランなら動画制作＋広告運用がセットでお得です！',
                'options': 'はい（Twenty BUZZプラン）/いいえ（制作のみ）/詳細を聞く',
                'next_step': 999,
                'end': True,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            
            # 料金相談フロー（改善版）
            {
                'id': 205,
                'trigger': '料金相談',
                'step': 1,
                'question': '💵 料金についてご相談ですね！\n\nどのような料金についてお聞きになりたいですか？',
                'options': '制作費用/広告運用費/初期費用・解約費用/全体の料金体系',
                'next_step': 2,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 206,
                'trigger': '料金相談',
                'step': 2,
                'question': '📋 制作本数はどのくらいを想定されていますか？\n\n本数によって単価が変わります。',
                'options': '1-3本/4-10本/10本以上/まだ決めていない',
                'next_step': 999,
                'end': True,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            
            # 修正相談フロー（改善版）
            {
                'id': 207,
                'trigger': '修正相談',
                'step': 1,
                'question': '✏️ 修正についてご相談ですね！\n\nどのような修正についてお聞きになりたいですか？',
                'options': '修正回数/修正料金/修正の手順/修正期間',
                'next_step': 2,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 208,
                'trigger': '修正相談',
                'step': 2,
                'question': '✅ 修正についてお答えします！\n\n・修正回数：無制限\n・修正料金：無料\n・修正期間：納品後1ヶ月以内\n\n何かご不明な点はございますか？',
                'options': '了解しました/詳細を聞く/他の質問がある',
                'next_step': 999,
                'end': True,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            
            # プラン相談フロー（改善版）
            {
                'id': 209,
                'trigger': 'プラン相談',
                'step': 1,
                'question': '📦 プランについてご相談ですね！\n\nどのプランについて詳しくお聞きになりたいですか？',
                'options': 'Twenty BUZZプラン/モーグラ動画/編集セット/出張セット/その他',
                'next_step': 2,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 210,
                'trigger': 'プラン相談',
                'step': 2,
                'question': '🎯 プランの詳細をお答えします！\n\nTwenty BUZZプラン：\n・動画制作＋広告運用\n・月2本まで\n・広告費込み\n\n詳細な料金をお知らせしますか？',
                'options': '料金を聞く/申し込みたい/他のプランを見る/相談したい',
                'next_step': 999,
                'end': True,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            
            # サポートフロー（改善版）
            {
                'id': 211,
                'trigger': 'サポート',
                'step': 1,
                'question': '🆘 サポートが必要ですね！\n\nどのようなサポートが必要でしょうか？',
                'options': '技術的問題/料金問題/制作進行/その他',
                'next_step': 2,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 212,
                'trigger': 'サポート',
                'step': 2,
                'question': '👨‍💼 サポート担当者にご案内いたします！\n\n問題の詳細をお聞かせください。\n担当者が直接サポートいたします。',
                'options': '問題を説明する/担当者に連絡/FAQを見る/緊急対応',
                'next_step': 999,
                'end': True,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            
            # 新規追加：よくある質問フロー
            {
                'id': 213,
                'trigger': 'よくある質問',
                'step': 1,
                'question': '❓ よくある質問ですね！\n\nどのカテゴリについてお聞きになりたいですか？',
                'options': '制作について/料金について/納期について/修正について/その他',
                'next_step': 2,
                'end': False,
                'fallback_next': 999,
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 214,
                'trigger': 'よくある質問',
                'step': 2,
                'question': '📚 よくある質問をお答えします！\n\n詳細な回答をご案内いたします。',
                'options': '詳細を見る/他の質問/担当者に相談/終了',
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
        
        print(f"✅ Flows改善版更新完了: {len(new_flows)}件")
        print(f"📅 更新日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # フロー統計を表示
        triggers = {}
        for flow in new_flows:
            trigger = flow['trigger']
            if trigger not in triggers:
                triggers[trigger] = 0
            triggers[trigger] += 1
        
        print("\n📊 改善版フロー統計:")
        for trigger, count in triggers.items():
            print(f"  - {trigger}: {count}ステップ")
        
        print("\n🎯 改善ポイント:")
        print("  - 絵文字と改行で視認性向上")
        print("  - より具体的で分かりやすい質問文")
        print("  - 実用的な選択肢")
        print("  - ユーザーフレンドリーな表現")
        
    except HttpError as e:
        print(f"❌ Google Sheets API エラー: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)

def main():
    """メイン関数"""
    print("🚀 Flows改善版更新開始...")
    
    if not SHEET_ID:
        print("❌ SHEET_ID_QA環境変数が設定されていません")
        sys.exit(1)
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ 認証ファイルが見つかりません: {CREDENTIALS_FILE}")
        sys.exit(1)
    
    update_flows_improved()
    print("🎉 Flows改善版更新完了！")

if __name__ == "__main__":
    main()
