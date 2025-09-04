#!/usr/bin/env python3
"""
Railway用起動スクリプト
"""

import os
from line_qa_system.app import app

if __name__ == '__main__':
    # 環境変数の確認
    port = int(os.getenv('PORT', 8000))
    print(f'=== Railway起動スクリプト ===')
    print(f'PORT: {port}')
    print(f'FLASK_APP: {os.getenv("FLASK_APP", "未設定")}')
    print(f'FLASK_ENV: {os.getenv("FLASK_ENV", "未設定")}')
    print(f'アプリ名: {app.name}')
    print(f'デバッグモード: {app.debug}')
    print(f'=== Flask起動開始 (ポート: {port}) ===')
    
    # 環境変数を設定
    os.environ['FLASK_APP'] = 'line_qa_system.app'
    os.environ['FLASK_ENV'] = 'production'
    
    # Flaskアプリケーションを直接起動
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
