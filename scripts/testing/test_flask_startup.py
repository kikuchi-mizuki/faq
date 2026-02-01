#!/usr/bin/env python3
"""
Flaskアプリケーション起動テスト
"""

import os
from line_qa_system.app import app

def test_flask_startup():
    """Flaskアプリケーションの起動をテスト"""
    print('=== Flaskアプリケーション起動テスト ===')
    
    try:
        # 環境変数の確認
        print(f'FLASK_APP: {os.getenv("FLASK_APP", "未設定")}')
        print(f'FLASK_ENV: {os.getenv("FLASK_ENV", "未設定")}')
        print(f'PORT: {os.getenv("PORT", "未設定")}')
        
        # アプリケーションの確認
        print(f'アプリ名: {app.name}')
        print(f'デバッグモード: {app.debug}')
        
        # ルートの確認
        print(f'ルート数: {len(app.url_map._rules)}')
        print('\n=== 利用可能なエンドポイント ===')
        for rule in app.url_map._rules:
            print(f'  {rule.rule} [{", ".join(rule.methods)}]')
        
        # ヘルスチェックエンドポイントの確認
        with app.test_client() as client:
            response = client.get('/healthz')
            print('\n=== ヘルスチェックテスト ===')
            print(f'ステータスコード: {response.status_code}')
            print(f'レスポンス: {response.data.decode()}')
            
            if response.status_code == 200:
                print('✅ ヘルスチェック成功')
            else:
                print('❌ ヘルスチェック失敗')
        
        print('\n✅ Flaskアプリケーション起動テスト完了')
        
    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')

if __name__ == '__main__':
    test_flask_startup()
