#!/usr/bin/env python3
"""
サンプルデータをGoogle Sheetsにアップロード（修正版）
"""

import csv
import gspread
import base64
import json
from line_qa_system.config import Config
import structlog

logger = structlog.get_logger(__name__)

def upload_sample_data():
    """サンプルデータをGoogle Sheetsにアップロード"""
    print('=== サンプルデータアップロード開始（修正版） ===')
    
    try:
        # Base64デコードしてJSONを取得
        print('1. 認証情報をデコード中...')
        json_str = base64.b64decode(Config.GOOGLE_SERVICE_ACCOUNT_JSON).decode('utf-8')
        service_account_info = json.loads(json_str)
        print('✅ 認証情報のデコードが完了しました')
        
        # Google Sheetsに接続
        print('2. Google Sheetsに接続中...')
        gc = gspread.service_account_from_dict(service_account_info)
        sheet = gc.open_by_key(Config.SHEET_ID_QA)
        print(f'✅ スプレッドシート接続成功: {sheet.title}')
        
        # ワークシートの確認・作成
        print('3. ワークシートを確認中...')
        try:
            worksheet = sheet.worksheet("qa_items")
            print('✅ qa_itemsワークシートが見つかりました')
        except gspread.WorksheetNotFound:
            print('⚠️ qa_itemsワークシートが見つかりません。作成します...')
            worksheet = sheet.add_worksheet(title="qa_items", rows=100, cols=9)
            print('✅ qa_itemsワークシートを作成しました')
        
        # サンプルCSVファイルを読み込み
        print('4. サンプルデータを読み込み中...')
        sample_data = []
        with open('sample_data/qa_items_sample.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sample_data.append(row)
        
        print(f'✅ {len(sample_data)}件のサンプルデータを読み込みました')
        
        # ヘッダー行を設定
        print('5. ヘッダー行を設定中...')
        headers = ['id', 'question', 'keywords', 'synonyms', 'tags', 'answer', 'priority', 'status', 'updated_at']
        worksheet.update('A1:I1', [headers])
        print('✅ ヘッダー行を設定しました')
        
        # データ行を入力
        print('6. データ行を入力中...')
        for i, row in enumerate(sample_data, start=2):
            row_data = [
                row['id'],
                row['question'],
                row['keywords'],
                row['synonyms'],
                row['tags'],
                row['answer'],
                row['priority'],
                row['status'],
                row['updated_at']
            ]
            worksheet.update(f'A{i}:I{i}', [row_data])
        
        print(f'✅ {len(sample_data)}件のデータを入力しました')
        
        # 最終確認
        print('7. 最終確認中...')
        all_values = worksheet.get_all_values()
        print(f'✅ ワークシート内の総行数: {len(all_values)}')
        print(f'✅ データ行数: {len(all_values) - 1}')  # ヘッダー行を除く
        
        print('\n🎉 サンプルデータのアップロードが完了しました！')
        print(f'スプレッドシートURL: https://docs.google.com/spreadsheets/d/{Config.SHEET_ID_QA}')
        
    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')
        logger.error("サンプルデータアップロード中にエラーが発生しました", error=str(e))

if __name__ == '__main__':
    upload_sample_data()
