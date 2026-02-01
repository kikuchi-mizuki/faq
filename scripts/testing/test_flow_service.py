"""
FlowServiceの単体テスト
"""

import sys

# パスの追加
sys.path.insert(0, '/Users/kikuchimizuki/Desktop/aicollections_2/faq')

from line_qa_system.session_service import SessionService
from line_qa_system.flow_service import FlowService

def test_flow_service():
    """FlowServiceの動作テスト"""
    
    print("=" * 60)
    print("FlowService 単体テスト")
    print("=" * 60)
    
    # 初期化
    print("\n1️⃣ FlowServiceの初期化")
    session_service = SessionService()
    flow_service = FlowService(session_service)
    print("   ✅ 初期化成功")
    print(f"   読み込みフロー数: {len(flow_service.flows)}")
    
    # 利用可能なトリガーの取得
    print("\n2️⃣ 利用可能なトリガーの取得")
    triggers = flow_service.get_available_triggers()
    print(f"   利用可能なトリガー: {triggers}")
    if triggers:
        print("   ✅ トリガー取得: 成功")
    else:
        print("   ⚠️  flowsシートにデータがありません")
        return
    
    # トリガーでフローを取得
    print("\n3️⃣ トリガーでフローを取得")
    trigger = triggers[0] if triggers else "月次締め"
    flow = flow_service.get_flow_by_trigger(trigger, step=1)
    
    if flow:
        print(f"   ✅ フロー取得: 成功")
        print(f"   trigger: {flow.trigger}")
        print(f"   step: {flow.step}")
        print(f"   question: {flow.question}")
        print(f"   options: {flow.option_list}")
    else:
        print("   ❌ フロー取得: 失敗")
        return
    
    # フローを開始
    print("\n4️⃣ フローを開始")
    user_id = "test_user_flow"
    started_flow = flow_service.start_flow(user_id, trigger)
    
    if started_flow:
        print(f"   ✅ フロー開始: 成功")
        print(f"   初回質問: {started_flow.question}")
        print(f"   選択肢: {started_flow.option_list}")
    else:
        print("   ❌ フロー開始: 失敗")
        return
    
    # フロー中かどうかの確認
    print("\n5️⃣ フロー中の確認")
    is_in_flow = flow_service.is_in_flow(user_id)
    print(f"   ✅ フロー中: {is_in_flow}")
    
    # 現在のフローを取得
    print("\n6️⃣ 現在のフローを取得")
    current_flow = flow_service.get_current_flow(user_id)
    if current_flow:
        print(f"   ✅ 現在のフロー取得: 成功")
        print(f"   step: {current_flow.step}")
        print(f"   question: {current_flow.question}")
    else:
        print("   ❌ 現在のフロー取得: 失敗")
    
    # ユーザーの選択を処理
    print("\n7️⃣ ユーザーの選択を処理（1回目）")
    if current_flow and current_flow.option_list:
        choice = current_flow.option_list[0]  # 最初の選択肢を選ぶ
        print(f"   選択: {choice}")
        
        next_flow, is_end = flow_service.process_user_choice(user_id, choice)
        
        if next_flow:
            print(f"   ✅ 次のステップ: 成功")
            print(f"   step: {next_flow.step}")
            print(f"   question: {next_flow.question}")
            print(f"   終了フラグ: {is_end}")
            
            # 終了ステップでない場合は続ける
            if not is_end and next_flow.option_list:
                print("\n8️⃣ ユーザーの選択を処理（2回目）")
                choice_2 = next_flow.option_list[0]
                print(f"   選択: {choice_2}")
                
                final_flow, is_end_2 = flow_service.process_user_choice(user_id, choice_2)
                
                if final_flow:
                    print(f"   ✅ 最終ステップ: 成功")
                    print(f"   回答: {final_flow.question}")
                    print(f"   終了フラグ: {is_end_2}")
                else:
                    print("   ❌ 最終ステップ: 失敗")
        else:
            print("   ❌ 次のステップ: 失敗")
    
    # 終了後のフロー状態確認
    print("\n9️⃣ 終了後のフロー状態確認")
    is_in_flow_after = flow_service.is_in_flow(user_id)
    if not is_in_flow_after:
        print("   ✅ フロー終了: セッションが正しくクリアされた")
    else:
        print("   ⚠️  フローがまだ継続中です")
    
    # 新しいフローを開始してキャンセル機能をテスト
    print("\n🔟 フローのキャンセルテスト")
    user_id_2 = "test_user_cancel"
    flow_service.start_flow(user_id_2, trigger)
    print(f"   フローを開始: {trigger}")
    
    # キャンセル
    cancel_result = flow_service.cancel_flow(user_id_2)
    print(f"   キャンセル: {'成功' if cancel_result else '失敗'}")
    
    # キャンセル後の確認
    is_cancelled = not flow_service.is_in_flow(user_id_2)
    if is_cancelled:
        print("   ✅ キャンセル確認: セッションがクリアされた")
    else:
        print("   ❌ キャンセル確認: セッションが残っている")
    
    # 不正な選択肢のテスト
    print("\n1️⃣1️⃣ 不正な選択肢のテスト")
    user_id_3 = "test_user_invalid"
    flow_service.start_flow(user_id_3, trigger)
    
    # 不正な選択を送信
    next_flow, is_end = flow_service.process_user_choice(user_id_3, "不正な選択肢")
    
    if next_flow:
        print(f"   ✅ フォールバック処理: 成功")
        print(f"   移動先step: {next_flow.step}")
        print(f"   メッセージ: {next_flow.question[:50]}...")
    else:
        print("   フォールバック処理が実行された")
    
    # クリーンアップ
    print("\n🧹 クリーンアップ")
    flow_service.cancel_flow(user_id)
    flow_service.cancel_flow(user_id_2)
    flow_service.cancel_flow(user_id_3)
    print("   テストセッションをクリアしました")
    
    print("\n" + "=" * 60)
    print("✅ FlowService テスト完了")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_flow_service()
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

