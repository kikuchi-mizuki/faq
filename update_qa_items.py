#!/usr/bin/env python3
"""
Q&Aアイテムのスプレッドシート直接更新スクリプト
Googleフォーム連携の代わりに、スプレッドシートを直接更新します
"""

import os
import sys
import json
import base64
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from line_qa_system.config import Config

def init_google_sheets():
    """Google Sheets APIの初期化"""
    try:
        # サービスアカウントJSONのデコード
        service_account_info = json.loads(
            base64.b64decode(Config.GOOGLE_SERVICE_ACCOUNT_JSON)
        )

        # 認証情報の作成
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )

        # クライアントの作成
        gc = gspread.authorize(credentials)
        print("✅ Google Sheets APIの初期化が完了しました")
        return gc

    except Exception as e:
        print(f"❌ Google Sheets APIの初期化に失敗しました: {e}")
        return None

def add_qa_item(gc, question: str, answer: str, category: str = "", keywords: str = "", tags: str = "", priority: int = 1):
    """Q&Aアイテムをqa_itemsシートに追加"""
    try:
        # スプレッドシートを開く
        spreadsheet = gc.open_by_key(Config.SHEET_ID_QA)
        qa_sheet = spreadsheet.worksheet("qa_items")
        
        # 既存のデータを取得してIDを決定
        existing_data = qa_sheet.get_all_records()
        next_id = max([int(row.get("id", 0)) for row in existing_data], default=0) + 1
        
        # 現在の日時
        now = datetime.now().isoformat()
        
        # 新しい行のデータ
        new_row = [
            next_id,  # id
            question,  # question
            answer,   # answer
            keywords, # keywords
            "",       # patterns
            tags,     # tags
            priority, # priority
            "active", # status
            now       # updated_at
        ]
        
        # 行を追加
        qa_sheet.append_row(new_row)
        
        print(f"✅ Q&Aアイテムを追加しました:")
        print(f"   ID: {next_id}")
        print(f"   質問: {question}")
        print(f"   回答: {answer}")
        print(f"   カテゴリ: {category}")
        print(f"   キーワード: {keywords}")
        print(f"   タグ: {tags}")
        print(f"   優先度: {priority}")
        
        return True
        
    except Exception as e:
        print(f"❌ Q&Aアイテムの追加に失敗しました: {e}")
        return False

def add_flow_item(gc, trigger: str, step: int, question: str, options: str, next_step: str, end: bool = False, fallback_next: int = 999):
    """フローアイテムをflowsシートに追加"""
    try:
        # スプレッドシートを開く
        spreadsheet = gc.open_by_key(Config.SHEET_ID_QA)
        flows_sheet = spreadsheet.worksheet("flows")
        
        # 既存のデータを取得してIDを決定
        existing_data = flows_sheet.get_all_records()
        next_id = max([int(row.get("id", 0)) for row in existing_data], default=0) + 1
        
        # 現在の日時
        now = datetime.now().isoformat()
        
        # 新しい行のデータ
        new_row = [
            next_id,      # id
            trigger,      # trigger
            step,         # step
            question,     # question
            options,      # options
            next_step,    # next_step
            "TRUE" if end else "FALSE",  # end
            fallback_next, # fallback_next
            now           # updated_at
        ]
        
        # 行を追加
        flows_sheet.append_row(new_row)
        
        print(f"✅ フローアイテムを追加しました:")
        print(f"   ID: {next_id}")
        print(f"   トリガー: {trigger}")
        print(f"   ステップ: {step}")
        print(f"   質問: {question}")
        print(f"   選択肢: {options}")
        print(f"   次のステップ: {next_step}")
        print(f"   終了: {end}")
        print(f"   フォールバック: {fallback_next}")
        
        return True
        
    except Exception as e:
        print(f"❌ フローアイテムの追加に失敗しました: {e}")
        return False

def add_location_item(gc, category: str, title: str, url: str, description: str = "", tags: str = ""):
    """ロケーションアイテムをlocationsシートに追加"""
    try:
        # スプレッドシートを開く
        spreadsheet = gc.open_by_key(Config.SHEET_ID_QA)
        locations_sheet = spreadsheet.worksheet("locations")
        
        # 現在の日時
        now = datetime.now().isoformat()
        
        # 新しい行のデータ
        new_row = [
            category,    # category
            title,       # title
            url,         # url
            description, # description
            tags,        # tags
            now          # updated_at
        ]
        
        # 行を追加
        locations_sheet.append_row(new_row)
        
        print(f"✅ ロケーションアイテムを追加しました:")
        print(f"   カテゴリ: {category}")
        print(f"   タイトル: {title}")
        print(f"   URL: {url}")
        print(f"   説明: {description}")
        print(f"   タグ: {tags}")
        
        return True
        
    except Exception as e:
        print(f"❌ ロケーションアイテムの追加に失敗しました: {e}")
        return False

def main():
    """メイン関数"""
    print("🚀 Q&Aアイテムのスプレッドシート直接更新スクリプト")
    print("=" * 50)
    
    # Google Sheets APIの初期化
    gc = init_google_sheets()
    if not gc:
        return
    
    print("\n📝 利用可能な操作:")
    print("1. Q&Aアイテムの追加")
    print("2. フローアイテムの追加")
    print("3. ロケーションアイテムの追加")
    print("4. 一括サンプルデータの追加")
    
    choice = input("\n操作を選択してください (1-4): ").strip()
    
    if choice == "1":
        # Q&Aアイテムの追加
        print("\n📝 Q&Aアイテムの追加")
        question = input("質問を入力してください: ").strip()
        answer = input("回答を入力してください: ").strip()
        category = input("カテゴリを入力してください (任意): ").strip()
        keywords = input("キーワードを入力してください (任意): ").strip()
        tags = input("タグを入力してください (任意): ").strip()
        priority = int(input("優先度を入力してください (1-5, デフォルト: 1): ").strip() or "1")
        
        if question and answer:
            add_qa_item(gc, question, answer, category, keywords, tags, priority)
        else:
            print("❌ 質問と回答は必須です")
    
    elif choice == "2":
        # フローアイテムの追加
        print("\n🔄 フローアイテムの追加")
        trigger = input("トリガーを入力してください: ").strip()
        step = int(input("ステップ番号を入力してください: ").strip())
        question = input("質問を入力してください: ").strip()
        options = input("選択肢を入力してください (「/」で区切り): ").strip()
        next_step = input("次のステップを入力してください: ").strip()
        end = input("終了ステップですか？ (y/n): ").strip().lower() == "y"
        fallback_next = int(input("フォールバック次のステップを入力してください (デフォルト: 999): ").strip() or "999")
        
        if trigger and question:
            add_flow_item(gc, trigger, step, question, options, next_step, end, fallback_next)
        else:
            print("❌ トリガーと質問は必須です")
    
    elif choice == "3":
        # ロケーションアイテムの追加
        print("\n📍 ロケーションアイテムの追加")
        category = input("カテゴリを入力してください: ").strip()
        title = input("タイトルを入力してください: ").strip()
        url = input("URLを入力してください: ").strip()
        description = input("説明を入力してください (任意): ").strip()
        tags = input("タグを入力してください (任意): ").strip()
        
        if category and title and url:
            add_location_item(gc, category, title, url, description, tags)
        else:
            print("❌ カテゴリ、タイトル、URLは必須です")
    
    elif choice == "4":
        # 一括サンプルデータの追加
        print("\n📊 一括サンプルデータの追加")
        
        # Q&Aサンプルデータ
        qa_samples = [
            {
                "question": "修正は何回まで可能ですか？",
                "answer": "修正回数は無制限です。納品後1ヶ月以内であれば、何度でも無料で修正いたします。",
                "category": "制作",
                "keywords": "修正,リテイク,回数",
                "tags": "制作",
                "priority": 1
            },
            {
                "question": "動画の納期はどのくらいですか？",
                "answer": "動画の納期は2-3週間程度です。本数や内容によって変動する場合があります。",
                "category": "制作",
                "keywords": "納期,期間,スケジュール",
                "tags": "制作",
                "priority": 1
            }
        ]
        
        # フローサンプルデータ
        flow_samples = [
            {
                "trigger": "制作依頼",
                "step": 1,
                "question": "どのような媒体で動画を制作されますか？",
                "options": "YouTube/Instagram/TikTok/その他",
                "next_step": "2",
                "end": False,
                "fallback_next": 999
            }
        ]
        
        # ロケーションサンプルデータ
        location_samples = [
            {
                "category": "制作",
                "title": "動画制作ガイド",
                "url": "https://example.com/video-guide",
                "description": "動画制作の基本的な流れを説明したガイドです",
                "tags": "制作,ガイド,初心者"
            }
        ]
        
        # データを追加
        print("Q&Aアイテムを追加中...")
        for qa in qa_samples:
            add_qa_item(gc, **qa)
        
        print("\nフローアイテムを追加中...")
        for flow in flow_samples:
            add_flow_item(gc, **flow)
        
        print("\nロケーションアイテムを追加中...")
        for location in location_samples:
            add_location_item(gc, **location)
        
        print("\n✅ サンプルデータの追加が完了しました")
    
    else:
        print("❌ 無効な選択です")
    
    print("\n🎉 操作が完了しました")

if __name__ == "__main__":
    main()