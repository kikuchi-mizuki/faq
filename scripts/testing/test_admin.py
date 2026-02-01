#!/usr/bin/env python3
"""
管理者エンドポイントテスト
"""

from line_qa_system.app import app

def test_admin_endpoints():
    """管理者エンドポイントをテスト"""
    print('=== 管理者エンドポイントテスト ===')
    
    with app.test_client() as client:
        # 統計情報エンドポイント
        print('\n--- /admin/stats テスト ---')
        response = client.get('/admin/stats')
        print(f'ステータスコード: {response.status_code}')
        if response.status_code == 200:
            print('✅ 統計情報エンドポイント成功')
            print(f'レスポンス: {response.data.decode()}')
        else:
            print('❌ 統計情報エンドポイント失敗')
        
        # キャッシュリロードエンドポイント
        print('\n--- /admin/reload テスト ---')
        response = client.post('/admin/reload')
        print(f'ステータスコード: {response.status_code}')
        if response.status_code == 200:
            print('✅ キャッシュリロードエンドポイント成功')
            print(f'レスポンス: {response.data.decode()}')
        else:
            print('❌ キャッシュリロードエンドポイント失敗')

if __name__ == '__main__':
    test_admin_endpoints()
