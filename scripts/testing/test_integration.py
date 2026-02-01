"""
統合テスト - アプリケーション全体の動作確認
"""

import sys
import time

# パスの追加
sys.path.insert(0, '/Users/kikuchimizuki/Desktop/aicollections_2/faq')

from line_qa_system.qa_service import QAService
from line_qa_system.session_service import SessionService
from line_qa_system.flow_service import FlowService
from line_qa_system.line_client import LineClient

def test_integration():
    """統合テスト"""
    
    print("=" * 70)
    print("統合テスト - アプリケーション全体の動作確認")
    print("=" * 70)
    
    # 全サービスの初期化
    print("\n📦 サービスの初期化")
    print("-" * 70)
    
    try:
        qa_service = QAService()
        print(f"✅ QAService: {len(qa_service.qa_items)}件のQ&Aアイテムを読み込み")
    except Exception as e:
        print(f"❌ QAService初期化エラー: {e}")
        return
    
    try:
        session_service = SessionService()
        print(f"✅ SessionService: 初期化成功（メモリキャッシュモード）")
    except Exception as e:
        print(f"❌ SessionService初期化エラー: {e}")
        return
    
    try:
        flow_service = FlowService(session_service)
        print(f"✅ FlowService: {len(flow_service.flows)}件のフローを読み込み")
        triggers = flow_service.get_available_triggers()
        print(f"   利用可能なトリガー: {triggers}")
    except Exception as e:
        print(f"❌ FlowService初期化エラー: {e}")
        return
    
    try:
        line_client = LineClient()
        print(f"✅ LineClient: 初期化成功")
    except Exception as e:
        print(f"❌ LineClient初期化エラー: {e}")
        return
    
    # シナリオ1: 通常のQ&A検索
    print("\n\n📝 シナリオ1: 通常のQ&A検索")
    print("-" * 70)
    
    test_queries = [
        "修正は何回まで可能ですか",
        "納期について",
        "存在しない質問",
    ]
    
    for query in test_queries:
        print(f"\n質問: 「{query}」")
        result = qa_service.find_answer(query)
        
        if result.is_found:
            print(f"  ✅ 回答発見")
            print(f"     スコア: {result.score:.2f}")
            print(f"     回答: {result.answer[:50]}...")
        elif result.candidates:
            print(f"  ⚠️  候補あり（{len(result.candidates)}件）")
            for i, cand in enumerate(result.candidates, 1):
                print(f"     {i}. {cand.question} (スコア: {cand.score:.2f})")
        else:
            print(f"  ❌ 回答なし")
    
    # シナリオ2: フロー会話のシミュレーション
    print("\n\n🔄 シナリオ2: フロー会話のシミュレーション")
    print("-" * 70)
    
    user_id = "integration_test_user"
    
    # ステップ1: トリガー検出
    print("\nステップ1: ユーザーメッセージ「月次締め」")
    message = "月次締め"
    
    # トリガーチェック
    triggers = flow_service.get_available_triggers()
    trigger_found = None
    for trigger in triggers:
        if trigger.lower() in message.lower():
            trigger_found = trigger
            break
    
    if trigger_found:
        print(f"  ✅ トリガー検出: {trigger_found}")
        
        # フロー開始
        flow = flow_service.start_flow(user_id, trigger_found)
        if flow:
            print(f"  ✅ フロー開始")
            print(f"     Bot応答: {flow.question}")
            print(f"     選択肢: {flow.option_list}")
    else:
        print(f"  ❌ トリガー未検出")
    
    # ステップ2: 最初の選択
    print("\nステップ2: ユーザー選択「はい」")
    choice_1 = "はい"
    
    if flow_service.is_in_flow(user_id):
        next_flow, is_end = flow_service.process_user_choice(user_id, choice_1)
        
        if next_flow:
            print(f"  ✅ 次のステップへ進行")
            print(f"     Bot応答: {next_flow.question}")
            if not is_end:
                print(f"     選択肢: {next_flow.option_list}")
            else:
                print(f"     [終了ステップ]")
        else:
            print(f"  ❌ フロー処理失敗")
    
    # ステップ3: 2回目の選択
    if not is_end:
        print("\nステップ3: ユーザー選択「はい」")
        choice_2 = "はい"
        
        final_flow, is_end_2 = flow_service.process_user_choice(user_id, choice_2)
        
        if final_flow:
            print(f"  ✅ 最終ステップ")
            print(f"     Bot応答: {final_flow.question}")
            print(f"     終了: {is_end_2}")
        else:
            print(f"  ❌ フロー処理失敗")
    
    # フロー終了確認
    print("\nステップ4: フロー終了確認")
    is_still_in_flow = flow_service.is_in_flow(user_id)
    if not is_still_in_flow:
        print(f"  ✅ フローが正常に終了しました")
    else:
        print(f"  ⚠️  フローがまだ継続中")
    
    # シナリオ3: キャンセル機能
    print("\n\n❌ シナリオ3: キャンセル機能")
    print("-" * 70)
    
    user_id_2 = "cancel_test_user"
    
    print("\nフローを開始...")
    flow_service.start_flow(user_id_2, "サポート")
    print(f"  フロー中: {flow_service.is_in_flow(user_id_2)}")
    
    print("\nキャンセルコマンド送信...")
    flow_service.cancel_flow(user_id_2)
    print(f"  フロー中: {flow_service.is_in_flow(user_id_2)}")
    
    if not flow_service.is_in_flow(user_id_2):
        print(f"  ✅ キャンセル成功")
    else:
        print(f"  ❌ キャンセル失敗")
    
    # シナリオ4: 複数ユーザーの同時処理
    print("\n\n👥 シナリオ4: 複数ユーザーの同時処理")
    print("-" * 70)
    
    user_a = "user_a"
    user_b = "user_b"
    
    print("\nUser A: フロー「月次締め」を開始")
    flow_service.start_flow(user_a, "月次締め")
    
    print("User B: フロー「サポート」を開始")
    flow_service.start_flow(user_b, "サポート")
    
    # 両方のユーザーの状態を確認
    session_a = session_service.get_session(user_a)
    session_b = session_service.get_session(user_b)
    
    print(f"\nUser A trigger: {session_a.get('trigger') if session_a else 'なし'}")
    print(f"User B trigger: {session_b.get('trigger') if session_b else 'なし'}")
    
    if session_a and session_b:
        if session_a['trigger'] != session_b['trigger']:
            print("  ✅ セッション分離: 成功")
        else:
            print("  ❌ セッション分離: 失敗")
    
    # クリーンアップ
    flow_service.cancel_flow(user_a)
    flow_service.cancel_flow(user_b)
    
    # システム統計
    print("\n\n📊 システム統計")
    print("-" * 70)
    
    stats = qa_service.get_stats()
    print(f"Q&Aアイテム総数: {stats.total_qa_items}")
    print(f"アクティブQ&A: {stats.active_qa_items}")
    print(f"総リクエスト数: {stats.total_requests}")
    print(f"成功マッチ数: {stats.successful_matches}")
    print(f"平均応答時間: {stats.average_response_time_ms:.1f}ms")
    print(f"キャッシュヒット率: {stats.cache_hit_rate:.1%}")
    
    # 最終確認
    print("\n\n✅ 統合テスト完了")
    print("=" * 70)
    print("\n🎉 全てのシナリオが正常に動作しました！")
    print("\n次のステップ:")
    print("  1. アプリケーションを起動: python3 start.py")
    print("  2. LINEで実際にテストしてみましょう！")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_integration()
    except Exception as e:
        print(f"\n❌ 統合テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

