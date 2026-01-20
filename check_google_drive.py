"""
Google Drive診断スクリプト
サービスアカウントがアクセスできるファイルを一覧表示
"""

import os
import json
import base64
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# 環境変数を読み込み
load_dotenv()

def get_credentials():
    """Google認証情報を取得"""
    service_account_json_raw = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')

    if not service_account_json_raw:
        print("❌ GOOGLE_SERVICE_ACCOUNT_JSON環境変数が設定されていません")
        return None

    # ファイルパスの場合は直接読み込み
    if service_account_json_raw.endswith('.json'):
        print(f"📄 JSONファイルから読み込み: {service_account_json_raw}")
        with open(service_account_json_raw, 'r') as f:
            credentials_info = json.load(f)
    else:
        # Base64デコードを試行
        try:
            service_account_json = base64.b64decode(service_account_json_raw).decode('utf-8')
        except:
            service_account_json = service_account_json_raw

        credentials_info = json.loads(service_account_json)

    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/documents'
        ]
    )

    return credentials

def list_all_files():
    """サービスアカウントがアクセスできる全てのファイルを一覧表示"""
    print("=" * 60)
    print("Google Drive ファイル診断")
    print("=" * 60)

    credentials = get_credentials()
    if not credentials:
        return

    print("✅ 認証情報を取得しました")
    print(f"サービスアカウント: {credentials.service_account_email}")
    print()

    # Drive APIサービスを初期化
    drive_service = build('drive', 'v3', credentials=credentials)
    print("✅ Google Drive APIサービスを初期化しました")
    print()

    # 全てのファイルを取得
    print("📂 サービスアカウントがアクセスできるファイル:")
    print("-" * 60)

    try:
        results = drive_service.files().list(
            fields="files(id, name, mimeType, modifiedTime, owners)",
            pageSize=100
        ).execute()

        files = results.get('files', [])

        if not files:
            print("⚠️ アクセスできるファイルが見つかりません")
            print()
            print("確認事項:")
            print("1. Google Driveにファイルがアップロードされているか")
            print("2. サービスアカウントにファイルが共有されているか")
            print(f"   サービスアカウント: {credentials.service_account_email}")
            print("3. 権限: 閲覧者 以上")
        else:
            print(f"✅ {len(files)}件のファイルが見つかりました")
            print()

            for i, file in enumerate(files, 1):
                print(f"{i}. 名前: {file['name']}")
                print(f"   ID: {file['id']}")
                print(f"   MimeType: {file['mimeType']}")
                print(f"   更新日時: {file.get('modifiedTime', 'N/A')}")
                print()

        # PDF/Excelファイルのみを検索
        print()
        print("📄 PDF/Excel/テキストファイル:")
        print("-" * 60)

        query = (
            "mimeType='text/plain' or "
            "mimeType='text/csv' or "
            "mimeType='application/pdf' or "
            "mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or "
            "mimeType='application/vnd.ms-excel'"
        )

        results = drive_service.files().list(
            q=query,
            fields="files(id, name, mimeType, modifiedTime)"
        ).execute()

        target_files = results.get('files', [])

        if not target_files:
            print("⚠️ PDF/Excel/テキストファイルが見つかりません")
            print()
            print("対応形式:")
            print("- PDF (.pdf)")
            print("- Excel (.xlsx, .xls)")
            print("- テキスト (.txt, .csv)")
        else:
            print(f"✅ {len(target_files)}件のファイルが見つかりました")
            print()

            for i, file in enumerate(target_files, 1):
                print(f"{i}. 名前: {file['name']}")
                print(f"   ID: {file['id']}")
                print(f"   MimeType: {file['mimeType']}")
                print(f"   更新日時: {file.get('modifiedTime', 'N/A')}")
                print()

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        print(traceback.format_exc())

    print("=" * 60)

if __name__ == '__main__':
    list_all_files()
