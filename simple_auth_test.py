"""
認証システムの簡易テスト
依存関係の問題を回避してテスト
"""

import os
import sys
from datetime import datetime

# 環境変数を設定
os.environ['AUTH_ENABLED'] = 'true'
os.environ['STORE_MANAGEMENT_SHEET'] = 'store_management'
os.environ['STAFF_MANAGEMENT_SHEET'] = 'staff_management'

def test_auth_components():
    """認証コンポーネントの簡易テスト"""
    try:
        print("🔍 認証システムの簡易テストを開始します...")
        
        # 認証サービスのテスト
        test_auth_service()
        
        # 店舗管理サービスのテスト
        test_store_service()
        
        # スタッフ管理サービスのテスト
        test_staff_service()
        
        print("✅ 認証システムの簡易テストが完了しました")
        
    except Exception as e:
        print(f"❌ テスト中にエラーが発生しました: {e}")
        return False
    
    return True

def test_auth_service():
    """認証サービスのテスト"""
    try:
        print("📋 認証サービスのテスト...")
        
        # 認証サービスのインポート
        from line_qa_system.auth_service import AuthService
        
        # 認証サービスの初期化
        auth_service = AuthService()
        
        # 基本機能のテスト
        test_user_id = "test_user_123"
        
        # 認証状態のテスト
        is_authenticated = auth_service.is_authenticated(test_user_id)
        print(f"  - 認証状態チェック: {is_authenticated}")
        
        # 認証プロセスのテスト
        auth_message = auth_service.start_auth_process(test_user_id)
        print(f"  - 認証プロセス開始: {len(auth_message)}文字")
        
        # 認証統計のテスト
        stats = auth_service.get_auth_stats()
        print(f"  - 認証統計: {stats}")
        
        print("  ✅ 認証サービスのテスト完了")
        
    except Exception as e:
        print(f"  ❌ 認証サービスのテストに失敗: {e}")
        raise

def test_store_service():
    """店舗管理サービスのテスト"""
    try:
        print("🏪 店舗管理サービスのテスト...")
        
        # 店舗管理サービスのインポート
        from line_qa_system.store_service import StoreService
        
        # 店舗管理サービスの初期化
        store_service = StoreService()
        
        # 基本機能のテスト
        all_stores = store_service.get_all_stores()
        print(f"  - 店舗一覧: {len(all_stores)}件")
        
        active_stores = store_service.get_active_stores()
        print(f"  - アクティブ店舗: {len(active_stores)}件")
        
        stats = store_service.get_stats()
        print(f"  - 店舗統計: {stats}")
        
        print("  ✅ 店舗管理サービスのテスト完了")
        
    except Exception as e:
        print(f"  ❌ 店舗管理サービスのテストに失敗: {e}")
        raise

def test_staff_service():
    """スタッフ管理サービスのテスト"""
    try:
        print("👥 スタッフ管理サービスのテスト...")
        
        # スタッフ管理サービスのインポート
        from line_qa_system.staff_service import StaffService
        
        # スタッフ管理サービスの初期化
        staff_service = StaffService()
        
        # 基本機能のテスト
        all_staff = staff_service.get_staff_list()
        print(f"  - スタッフ一覧: {len(all_staff)}件")
        
        active_staff = staff_service.get_active_staff()
        print(f"  - アクティブスタッフ: {len(active_staff)}件")
        
        stats = staff_service.get_stats()
        print(f"  - スタッフ統計: {stats}")
        
        print("  ✅ スタッフ管理サービスのテスト完了")
        
    except Exception as e:
        print(f"  ❌ スタッフ管理サービスのテストに失敗: {e}")
        raise

def test_auth_flow():
    """認証フローのテスト"""
    try:
        print("🔄 認証フローのテスト...")
        
        # 認証フローのインポート
        from line_qa_system.auth_flow import AuthFlow
        
        # 認証フローの初期化
        auth_flow = AuthFlow()
        
        # サービス初期化のテスト
        auth_flow.initialize_services()
        print("  - 認証フロー初期化完了")
        
        print("  ✅ 認証フローのテスト完了")
        
    except Exception as e:
        print(f"  ❌ 認証フローのテストに失敗: {e}")
        raise

def main():
    """メイン処理"""
    print("🚀 認証システムの簡易テストを開始します")
    print("=" * 50)
    
    try:
        # 認証コンポーネントのテスト
        if test_auth_components():
            print("\n🎉 全てのテストが完了しました！")
            print("\n📋 次のステップ:")
            print("1. スプレッドシートの準備")
            print("2. 環境変数の設定")
            print("3. 本番環境へのデプロイ")
            print("4. Botの動作確認")
        else:
            print("\n❌ テストに失敗しました")
            
    except Exception as e:
        print(f"\n❌ テスト処理中にエラーが発生しました: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
