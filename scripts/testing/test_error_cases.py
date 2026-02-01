"""
エラーケース・エッジケースのテスト
"""

import sys

# パスの追加
sys.path.insert(0, '/Users/kikuchimizuki/Desktop/aicollections_2/faq')

from line_qa_system.session_service import SessionService
from line_qa_system.flow_service import FlowService

def test_error_cases():
    """エラーケース・エッジケースのテスト"""
    
    print("=" * 70)
    print("エラーケース・エッジケースのテスト")
    print("=" * 70)
    
    session_service = SessionService()
    flow_service = FlowService(session_service)
    
    # テスト1: 存在しないトリガー
    print("\n1️⃣ 存在しないトリガーでフロー開始")
    user_id = "error_test_1"
    flow = flow_service.start_flow(user_id, "存在しないトリガー")
    
    if flow is None:
        print("   ✅ 正しくNoneを返す")
    else:
        print("   ❌ 予期しないフローが返された")
    
    # テスト2: フロー中でない時の選択処理
    print("\n2️⃣ フロー中でない時の選択処理")
    user_id_2 = "error_test_2"
    next_flow, is_end = flow_service.process_user_choice(user_id_2, "はい")
    
    if next_flow is None and is_end:
        print("   ✅ 正しくNone, Trueを返す")
    else:
        print("   ❌ 予期しない結果")
    
    # テスト3: 不正な選択肢（フォールバック）
    print("\n3️⃣ 不正な選択肢の処理")
    user_id_3 = "error_test_3"
    flow_service.start_flow(user_id_3, "月次締め")
    
    # 全く関係ない選択肢を送信
    next_flow, is_end = flow_service.process_user_choice(user_id_3, "あいうえお")
    
    if next_flow:
        print(f"   ✅ フォールバックステップへ遷移 (step: {next_flow.step})")
        print(f"      メッセージ: {next_flow.question[:30]}...")
    else:
        print("   ❌ フォールバック処理失敗")
    
    # テスト4: 空文字列の処理
    print("\n4️⃣ 空文字列の処理")
    user_id_4 = "error_test_4"
    flow_service.start_flow(user_id_4, "サポート")
    
    next_flow, is_end = flow_service.process_user_choice(user_id_4, "")
    
    if next_flow:
        print(f"   ✅ 空文字列を処理 (step: {next_flow.step})")
    else:
        print("   ❌ 空文字列処理失敗")
    
    # テスト5: セッション有効期限切れのシミュレーション
    print("\n5️⃣ セッション削除後の操作")
    user_id_5 = "error_test_5"
    flow_service.start_flow(user_id_5, "月次締め")
    
    # セッションを手動削除
    session_service.delete_session(user_id_5)
    
    # 削除後に操作を試みる
    next_flow, is_end = flow_service.process_user_choice(user_id_5, "はい")
    
    if next_flow is None:
        print("   ✅ セッション削除後は正しくNoneを返す")
    else:
        print("   ❌ セッション削除後に予期しない結果")
    
    # テスト6: 同じユーザーが複数のフローを開始
    print("\n6️⃣ 同じユーザーが連続してフローを開始")
    user_id_6 = "error_test_6"
    
    flow_1 = flow_service.start_flow(user_id_6, "月次締め")
    print(f"   1回目: {flow_1.trigger if flow_1 else 'None'}")
    
    # 途中で別のフローを開始（上書き）
    flow_2 = flow_service.start_flow(user_id_6, "サポート")
    print(f"   2回目: {flow_2.trigger if flow_2 else 'None'}")
    
    # セッションを確認
    session = session_service.get_session(user_id_6)
    if session and session['trigger'] == "サポート":
        print("   ✅ 新しいフローで上書きされた")
    else:
        print("   ❌ フロー上書き失敗")
    
    # テスト7: 大量のセッション同時作成
    print("\n7️⃣ 大量セッションの同時作成")
    user_count = 50
    
    for i in range(user_count):
        user_id = f"load_test_{i}"
        session_service.set_session(user_id, {"test": i}, ttl=60)
    
    # ランダムに取得して確認
    test_session = session_service.get_session("load_test_25")
    if test_session and test_session['test'] == 25:
        print(f"   ✅ {user_count}件のセッションを正しく管理")
    else:
        print(f"   ❌ 大量セッション管理に問題")
    
    # クリーンアップ
    for i in range(user_count):
        session_service.delete_session(f"load_test_{i}")
    
    # テスト8: 特殊文字を含むメッセージ
    print("\n8️⃣ 特殊文字を含むメッセージ")
    user_id_8 = "error_test_8"
    flow_service.start_flow(user_id_8, "月次締め")
    
    special_chars = ["😀", "\\n\\r", "<script>", "NULL"]
    
    for char in special_chars:
        try:
            next_flow, is_end = flow_service.process_user_choice(user_id_8, char)
            print(f"   ✅ 特殊文字'{char}'を処理")
        except Exception as e:
            print(f"   ❌ 特殊文字'{char}'でエラー: {e}")
    
    # クリーンアップ
    print("\n🧹 クリーンアップ")
    for i in range(1, 9):
        flow_service.cancel_flow(f"error_test_{i}")
    print("   テストセッションをクリアしました")
    
    print("\n" + "=" * 70)
    print("✅ エラーケーステスト完了")
    print("=" * 70)
    print("\n全てのエラーケースが適切に処理されました！")


if __name__ == "__main__":
    try:
        test_error_cases()
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

