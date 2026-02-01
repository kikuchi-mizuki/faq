#!/usr/bin/env python3
"""
ヘルスチェックエンドポイントテスト
"""

from line_qa_system.app import app

def test_health_endpoint():
    """ヘルスチェックエンドポイントをテスト"""
    print('=== ヘルスチェックエンドポイントテスト ===')
    
    with app.test_client() as client:
        response = client.get('/healthz')
        print(f'ステータスコード: {response.status_code}')
        print(f'レスポンス: {response.data.decode()}')
        
        if response.status_code == 200:
            print('✅ ヘルスチェック成功')
        else:
            print('❌ ヘルスチェック失敗')

if __name__ == '__main__':
    test_health_endpoint()
