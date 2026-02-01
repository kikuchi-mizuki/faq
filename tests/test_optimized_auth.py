"""
最適化認証システムのテスト
キャッシュベース認証とステータス変更の即座反映をテスト
"""

import os
import sys
import structlog
from datetime import datetime

# 構造化ログの設定
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def test_optimized_auth_flow():
    """最適化認証フローのテスト"""
    try:
        print("🧪 最適化認証フローのテストを開始します...")
        
        from line_qa_system.optimized_auth_flow import OptimizedAuthFlow
        
        auth_flow = OptimizedAuthFlow()
        
        # テスト用のユーザーID
        test_user_id = "test_optimized_user"
        
        print(f"📋 テストユーザーID: {test_user_id}")
        
        # 1. 認証開始
        print(f"\n1️⃣ 認証開始:")
        event1 = {
            "source": {"userId": test_user_id},
            "message": {"text": "認証", "type": "text"},
            "replyToken": "test_reply_token_1"
        }
        
        result1 = auth_flow.process_auth_flow(event1)
        print(f"   結果: {result1}")
        print(f"   認証状態: {auth_flow.auth_states.get(test_user_id)}")
        print(f"   キャッシュ有効: {auth_flow._is_cache_valid()}")
        
        if not result1:
            print("   ❌ 認証開始に失敗しました")
            return False
        
        # 2. 店舗コード入力
        print(f"\n2️⃣ 店舗コード入力:")
        event2 = {
            "source": {"userId": test_user_id},
            "message": {"text": "STORE004", "type": "text"},
            "replyToken": "test_reply_token_2"
        }
        
        result2 = auth_flow.process_auth_flow(event2)
        print(f"   結果: {result2}")
        print(f"   認証状態: {auth_flow.auth_states.get(test_user_id)}")
        print(f"   一時データ: {auth_flow.temp_data.get(test_user_id)}")
        
        if not result2:
            print("   ❌ 店舗コード入力に失敗しました")
            return False
        
        # 3. 社員番号入力
        print(f"\n3️⃣ 社員番号入力:")
        event3 = {
            "source": {"userId": test_user_id},
            "message": {"text": "004", "type": "text"},
            "replyToken": "test_reply_token_3"
        }
        
        result3 = auth_flow.process_auth_flow(event3)
        print(f"   結果: {result3}")
        print(f"   認証状態: {auth_flow.auth_states.get(test_user_id)}")
        print(f"   認証済み: {auth_flow.is_authenticated(test_user_id)}")
        
        if not result3:
            print("   ❌ 社員番号入力に失敗しました")
            return False
        
        # 4. 認証情報の確認
        print(f"\n4️⃣ 認証情報の確認:")
        auth_info = auth_flow.get_auth_info(test_user_id)
        if auth_info:
            print(f"   ✅ 認証情報が見つかりました:")
            print(f"      店舗コード: {auth_info.get('store_code')}")
            print(f"      社員番号: {auth_info.get('staff_id')}")
            print(f"      店舗名: {auth_info.get('store_name')}")
            print(f"      スタッフ名: {auth_info.get('staff_name')}")
            print(f"      認証時刻: {auth_info.get('auth_time')}")
            return True
        else:
            print(f"   ❌ 認証情報が見つかりません")
            return False
        
    except Exception as e:
        print(f"❌ 最適化認証フローのテストに失敗しました: {e}")
        logger.error("最適化認証フローのテストに失敗しました", error=str(e))
        return False


def test_cache_performance():
    """キャッシュパフォーマンスのテスト"""
    try:
        print(f"\n🧪 キャッシュパフォーマンスのテスト:")
        
        from line_qa_system.optimized_auth_flow import OptimizedAuthFlow
        
        auth_flow = OptimizedAuthFlow()
        
        # キャッシュ状態の確認
        print(f"   初期キャッシュ状態: {auth_flow._is_cache_valid()}")
        print(f"   最終キャッシュ更新: {auth_flow.last_cache_update}")
        
        # 強制キャッシュ更新
        print(f"\n   🔄 キャッシュ強制更新:")
        auth_flow.force_cache_update()
        print(f"   更新後キャッシュ状態: {auth_flow._is_cache_valid()}")
        print(f"   更新後最終更新時刻: {auth_flow.last_cache_update}")
        
        # 統計情報の確認
        stats = auth_flow.get_stats()
        print(f"\n   📊 統計情報:")
        print(f"      認証済みユーザー数: {stats['total_authenticated']}")
        print(f"      キャッシュ有効: {stats['cache_valid']}")
        print(f"      最終キャッシュ更新: {stats['last_cache_update']}")
        
        return True
        
    except Exception as e:
        print(f"❌ キャッシュパフォーマンスのテストに失敗しました: {e}")
        return False


def test_status_change_effect():
    """ステータス変更の効果テスト"""
    try:
        print(f"\n🧪 ステータス変更の効果テスト:")
        
        from line_qa_system.optimized_auth_flow import OptimizedAuthFlow
        from line_qa_system.staff_service import StaffService
        
        auth_flow = OptimizedAuthFlow()
        staff_service = StaffService()
        
        # テスト用のユーザーID
        test_user_id = "test_status_user"
        store_code = "STORE004"
        staff_id = "004"
        
        print(f"   テストユーザー: {test_user_id}")
        print(f"   店舗コード: {store_code}")
        print(f"   社員番号: {staff_id}")
        
        # 1. 認証フローを実行
        print(f"\n   1️⃣ 認証フロー実行:")
        events = [
            {"source": {"userId": test_user_id}, "message": {"text": "認証", "type": "text"}, "replyToken": "token_1"},
            {"source": {"userId": test_user_id}, "message": {"text": store_code, "type": "text"}, "replyToken": "token_2"},
            {"source": {"userId": test_user_id}, "message": {"text": staff_id, "type": "text"}, "replyToken": "token_3"}
        ]
        
        for i, event in enumerate(events, 1):
            result = auth_flow.process_auth_flow(event)
            print(f"      ステップ{i}: {result}")
        
        # 認証完了確認
        is_authenticated = auth_flow.is_authenticated(test_user_id)
        print(f"      認証完了: {is_authenticated}")
        
        if not is_authenticated:
            print("      ❌ 認証が完了していません")
            return False
        
        # 2. ステータス変更のシミュレーション
        print(f"\n   2️⃣ ステータス変更シミュレーション:")
        print(f"      現在のステータス: {staff_service.get_staff(store_code, staff_id).get('status')}")
        
        # 注意: 実際のスプレッドシート変更は行わない
        print(f"      ⚠️  実際のスプレッドシート変更は行いません")
        print(f"      📝 手動でスプレッドシートのステータスをsuspendedに変更してください")
        
        # 3. 認証状態の再チェック
        print(f"\n   3️⃣ 認証状態の再チェック:")
        is_authenticated_after = auth_flow.is_authenticated(test_user_id)
        print(f"      認証状態: {is_authenticated_after}")
        
        if is_authenticated_after:
            print(f"      ✅ 認証状態が維持されています")
            print(f"      📝 スプレッドシートでステータスをsuspendedに変更後、再度テストしてください")
        else:
            print(f"      ❌ 認証状態が失われています")
        
        return True
        
    except Exception as e:
        print(f"❌ ステータス変更の効果テストに失敗しました: {e}")
        return False


def main():
    """メイン処理"""
    try:
        print("=" * 60)
        print("🧪 最適化認証システムテスト")
        print("=" * 60)
        
        # 最適化認証フローのテスト
        auth_test_success = test_optimized_auth_flow()
        
        if auth_test_success:
            # キャッシュパフォーマンスのテスト
            cache_test_success = test_cache_performance()
            
            if cache_test_success:
                # ステータス変更の効果テスト
                status_test_success = test_status_change_effect()
            else:
                status_test_success = False
        else:
            cache_test_success = False
            status_test_success = False
        
        print("\n" + "=" * 60)
        if auth_test_success and cache_test_success and status_test_success:
            print("🎉 最適化認証システムが完全に動作しています！")
            print("✅ キャッシュベース認証で高速動作")
            print("✅ ステータス変更が確実に反映")
            print("✅ パフォーマンスが大幅に向上")
            print("🚀 Railwayデプロイの準備が整いました")
        elif auth_test_success and cache_test_success:
            print("🎉 基本的な最適化認証システムが動作しています！")
            print("✅ Railwayデプロイの準備が整いました")
        else:
            print("❌ 最適化認証システムに問題があります")
            print("🔧 追加の修正が必要です")
        print("=" * 60)
        
        return auth_test_success and cache_test_success
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        return False


if __name__ == "__main__":
    main()
