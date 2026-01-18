#!/usr/bin/env python3
"""
Railway用起動スクリプト
"""

import os
import sys
import traceback

def validate_environment():
    """環境変数の検証"""
    required_vars = [
        'LINE_CHANNEL_SECRET',
        'LINE_CHANNEL_ACCESS_TOKEN',
        'GOOGLE_SERVICE_ACCOUNT_JSON',
        'SHEET_ID_QA',
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f'❌ 必須環境変数が設定されていません: {", ".join(missing_vars)}')
        return False
    
    print('✅ 全ての必須環境変数が設定されています')
    return True

if __name__ == '__main__':
    try:
        # 環境変数の確認
        port = int(os.getenv('PORT', 8000))
        print(f'=== Railway起動スクリプト ===')
        print(f'PORT: {port}')
        print(f'FLASK_APP: {os.getenv("FLASK_APP", "未設定")}')
        print(f'FLASK_ENV: {os.getenv("FLASK_ENV", "未設定")}')
        
        # 環境変数の検証
        if not validate_environment():
            print('❌ 環境変数が不足しています。Railwayで設定してください。')
            sys.exit(1)
        
        # 環境変数を設定
        os.environ['FLASK_APP'] = 'line_qa_system.app'
        os.environ['FLASK_ENV'] = 'production'
        
        print('=== Flaskアプリケーションのインポート ===')
        from line_qa_system.app import app, initialize_services

        print(f'✅ アプリ名: {app.name}')
        print(f'✅ デバッグモード: {app.debug}')

        # サービスの初期化
        print('🚀 サービスを初期化しています...')
        initialize_services()
        print('✅ サービス初期化完了')

        print(f'=== Flask起動開始 (ポート: {port}) ===')

        # Flaskアプリケーションを直接起動
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
        
    except Exception as e:
        print(f'❌ アプリケーション起動中にエラーが発生しました: {e}')
        print('=== トレースバック ===')
        traceback.print_exc()
        sys.exit(1)
