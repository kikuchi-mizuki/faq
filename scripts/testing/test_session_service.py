"""
SessionServiceの単体テスト
"""

import sys
import time
from datetime import datetime

# パスの追加
sys.path.insert(0, '/Users/kikuchimizuki/Desktop/aicollections_2/faq')

from line_qa_system.session_service import SessionService

def test_session_service():
    """SessionServiceの動作テスト"""
    
    print("=" * 60)
    print("SessionService 単体テスト")
    print("=" * 60)
    
    # 初期化
    print("\n1️⃣ SessionServiceの初期化")
    session_service = SessionService()
    print("   ✅ 初期化成功")
    
    # ヘルスチェック
    print("\n2️⃣ ヘルスチェック")
    is_healthy = session_service.health_check()
    print(f"   ✅ ヘルスチェック: {'成功' if is_healthy else '失敗'}")
    
    # セッションの保存
    print("\n3️⃣ セッションの保存")
    user_id = "test_user_001"
    session_data = {
        "flow_id": 201,
        "current_step": 1,
        "trigger": "月次締め",
        "context": {"last_choice": "はい"},
        "started_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
    }
    
    result = session_service.set_session(user_id, session_data, ttl=60)
    print(f"   ✅ セッション保存: {'成功' if result else '失敗'}")
    print(f"   データ: {session_data}")
    
    # セッションの取得
    print("\n4️⃣ セッションの取得")
    retrieved_data = session_service.get_session(user_id)
    print(f"   ✅ セッション取得: {'成功' if retrieved_data else '失敗'}")
    if retrieved_data:
        print(f"   flow_id: {retrieved_data.get('flow_id')}")
        print(f"   current_step: {retrieved_data.get('current_step')}")
        print(f"   trigger: {retrieved_data.get('trigger')}")
    
    # データの一致確認
    if retrieved_data:
        if retrieved_data["flow_id"] == session_data["flow_id"]:
            print("   ✅ データ一致確認: 成功")
        else:
            print("   ❌ データ一致確認: 失敗")
    
    # セッションの更新
    print("\n5️⃣ セッションの更新")
    updates = {
        "current_step": 2,
        "context": {"last_choice": "いいえ"},
    }
    result = session_service.update_session(user_id, updates, ttl=60)
    print(f"   ✅ セッション更新: {'成功' if result else '失敗'}")
    
    # 更新後のデータ確認
    updated_data = session_service.get_session(user_id)
    if updated_data:
        print(f"   current_step: {updated_data.get('current_step')}")
        print(f"   last_choice: {updated_data.get('context', {}).get('last_choice')}")
    
    # 別のユーザーのセッション
    print("\n6️⃣ 複数ユーザーのセッション管理")
    user_id_2 = "test_user_002"
    session_data_2 = {
        "flow_id": 301,
        "current_step": 1,
        "trigger": "サポート",
    }
    session_service.set_session(user_id_2, session_data_2, ttl=60)
    
    # 両方のセッションが独立していることを確認
    data_1 = session_service.get_session(user_id)
    data_2 = session_service.get_session(user_id_2)
    
    print(f"   User 1 trigger: {data_1.get('trigger') if data_1 else 'None'}")
    print(f"   User 2 trigger: {data_2.get('trigger') if data_2 else 'None'}")
    
    if data_1 and data_2 and data_1['trigger'] != data_2['trigger']:
        print("   ✅ セッション分離: 成功")
    else:
        print("   ❌ セッション分離: 失敗")
    
    # 存在しないセッションの取得
    print("\n7️⃣ 存在しないセッションの取得")
    non_existent = session_service.get_session("non_existent_user")
    if non_existent is None:
        print("   ✅ 存在しないセッション: 正しくNoneを返す")
    else:
        print("   ❌ 存在しないセッション: 予期しないデータが返された")
    
    # セッションの削除
    print("\n8️⃣ セッションの削除")
    result = session_service.delete_session(user_id)
    print(f"   ✅ セッション削除: {'成功' if result else '失敗'}")
    
    # 削除後の確認
    deleted_data = session_service.get_session(user_id)
    if deleted_data is None:
        print("   ✅ 削除確認: セッションが正しく削除された")
    else:
        print("   ❌ 削除確認: セッションが残っている")
    
    # TTLテスト（短いTTLで確認）
    print("\n9️⃣ TTL（有効期限）テスト")
    user_id_ttl = "test_user_ttl"
    session_service.set_session(user_id_ttl, {"test": "data"}, ttl=2)
    print("   セッション保存（TTL=2秒）")
    
    # 即座に取得
    immediate_data = session_service.get_session(user_id_ttl)
    if immediate_data:
        print("   ✅ 即座に取得: 成功")
    
    # 3秒待機
    print("   3秒待機中...")
    time.sleep(3)
    
    # 期限切れ確認
    expired_data = session_service.get_session(user_id_ttl)
    if expired_data is None:
        print("   ✅ TTL期限切れ: 正しく削除された")
    else:
        print("   ❌ TTL期限切れ: セッションが残っている")
    
    # クリーンアップ
    print("\n🧹 クリーンアップ")
    session_service.delete_session(user_id_2)
    print("   テストセッションを削除しました")
    
    print("\n" + "=" * 60)
    print("✅ SessionService テスト完了")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_session_service()
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

