#!/usr/bin/env python3
"""
アプリケーション起動のデバッグスクリプト
"""

import os
import sys
import traceback
from datetime import datetime

def debug_startup():
    """起動時の問題を診断"""
    print("🔍 アプリケーション起動デバッグ開始...")
    print(f"📅 時刻: {datetime.now()}")
    print(f"🐍 Python: {sys.version}")
    print(f"📁 作業ディレクトリ: {os.getcwd()}")
    print()
    
    # 環境変数の確認
    print("🔧 環境変数の確認:")
    required_vars = [
        'LINE_CHANNEL_SECRET',
        'LINE_CHANNEL_ACCESS_TOKEN', 
        'GOOGLE_SERVICE_ACCOUNT_JSON',
        'SHEET_ID_QA'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if var == 'GOOGLE_SERVICE_ACCOUNT_JSON':
                print(f"  ✅ {var}: 設定済み (長さ: {len(value)})")
            else:
                print(f"  ✅ {var}: 設定済み")
        else:
            print(f"  ❌ {var}: 未設定")
    print()
    
    # ファイルの存在確認
    print("📁 ファイルの存在確認:")
    files_to_check = [
        'line_qa_system/__init__.py',
        'line_qa_system/app.py',
        'line_qa_system/config.py',
        'line_qa_system/qa_service.py',
        'line_qa_system/flow_service.py',
        'line_qa_system/ai_service.py',
        'faq-account.json'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
    print()
    
    # モジュールのインポートテスト
    print("📦 モジュールインポートテスト:")
    try:
        import line_qa_system
        print("  ✅ line_qa_system パッケージ")
    except Exception as e:
        print(f"  ❌ line_qa_system パッケージ: {e}")
    
    try:
        from line_qa_system.config import Config
        print("  ✅ Config クラス")
    except Exception as e:
        print(f"  ❌ Config クラス: {e}")
    
    try:
        from line_qa_system.qa_service import QAService
        print("  ✅ QAService クラス")
    except Exception as e:
        print(f"  ❌ QAService クラス: {e}")
    
    try:
        from line_qa_system.flow_service import FlowService
        print("  ✅ FlowService クラス")
    except Exception as e:
        print(f"  ❌ FlowService クラス: {e}")
    
    try:
        from line_qa_system.ai_service import AIService
        print("  ✅ AIService クラス")
    except Exception as e:
        print(f"  ❌ AIService クラス: {e}")
    
    print()
    
    # サービスの初期化テスト
    print("🚀 サービス初期化テスト:")
    try:
        from line_qa_system.config import Config
        config_errors = Config.validate()
        if config_errors:
            print(f"  ❌ 設定エラー: {config_errors}")
        else:
            print("  ✅ 設定検証OK")
    except Exception as e:
        print(f"  ❌ 設定検証エラー: {e}")
        traceback.print_exc()
    
    try:
        from line_qa_system.qa_service import QAService
        qa_service = QAService()
        print("  ✅ QAService 初期化OK")
    except Exception as e:
        print(f"  ❌ QAService 初期化エラー: {e}")
        traceback.print_exc()
    
    try:
        from line_qa_system.session_service import SessionService
        session_service = SessionService()
        print("  ✅ SessionService 初期化OK")
    except Exception as e:
        print(f"  ❌ SessionService 初期化エラー: {e}")
        traceback.print_exc()
    
    try:
        from line_qa_system.flow_service import FlowService
        from line_qa_system.session_service import SessionService
        session_service = SessionService()
        flow_service = FlowService(session_service)
        print("  ✅ FlowService 初期化OK")
    except Exception as e:
        print(f"  ❌ FlowService 初期化エラー: {e}")
        traceback.print_exc()
    
    try:
        from line_qa_system.location_service import LocationService
        location_service = LocationService()
        print("  ✅ LocationService 初期化OK")
    except Exception as e:
        print(f"  ❌ LocationService 初期化エラー: {e}")
        traceback.print_exc()
    
    print()
    print("🎯 デバッグ完了")

if __name__ == "__main__":
    debug_startup()
