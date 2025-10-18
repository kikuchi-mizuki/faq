#!/usr/bin/env python3
"""
超シンプルな起動スクリプト（デバッグ用）
"""

import os
import sys

print("=" * 60)
print("超シンプル起動スクリプト開始")
print("=" * 60)

# 環境変数の確認
print("\n環境変数チェック:")
print(f"PORT: {os.getenv('PORT', '未設定')}")
print(f"LINE_CHANNEL_SECRET: {'設定済み' if os.getenv('LINE_CHANNEL_SECRET') else '未設定'}")
print(f"LINE_CHANNEL_ACCESS_TOKEN: {'設定済み' if os.getenv('LINE_CHANNEL_ACCESS_TOKEN') else '未設定'}")
print(f"GOOGLE_SERVICE_ACCOUNT_JSON: {'設定済み' if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') else '未設定'}")
print(f"SHEET_ID_QA: {os.getenv('SHEET_ID_QA', '未設定')}")

print("\nPythonバージョン:")
print(sys.version)

print("\nインストール済みパッケージの確認:")
try:
    import flask
    print(f"✅ Flask: {flask.__version__}")
except:
    print("❌ Flask: インストールされていません")

try:
    import structlog
    print(f"✅ structlog: インストール済み")
except:
    print("❌ structlog: インストールされていません")

try:
    import redis
    print(f"✅ redis: インストール済み")
except:
    print("❌ redis: インストールされていません")

try:
    import gspread
    print(f"✅ gspread: インストール済み")
except:
    print("❌ gspread: インストールされていません")

print("\n" + "=" * 60)
print("アプリケーションのインポートを試行")
print("=" * 60)

try:
    from line_qa_system.app import app
    print("✅ アプリケーションのインポート成功")
    
    port = int(os.getenv('PORT', 8000))
    print(f"\nFlask起動開始: 0.0.0.0:{port}")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    
except Exception as e:
    print(f"❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

