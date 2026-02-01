#!/usr/bin/env python3
"""
Q&A検索機能テスト
"""

from line_qa_system.qa_service import QAService

def test_qa_search():
    """Q&A検索機能をテスト"""
    print('=== Q&A検索機能テスト ===')
    
    try:
        qa_service = QAService()
        print('✅ Q&Aサービス初期化成功')
        
        # テストケース
        test_cases = [
            "請求書",
            "インボイス",  # 同義語テスト
            "パスワード",
            "口座",
            "見積書",
            "ログイン",
            "アップロード",
            "不明なキーワード"  # フォールバックテスト
        ]
        
        for query in test_cases:
            print(f'\n--- 検索クエリ: "{query}" ---')
            result = qa_service.find_answer(query)
            
            if result.is_found:
                print(f'✅ 検索成功')
                print(f'  質問: {result.question}')
                print(f'  回答: {result.answer[:50]}...')
                print(f'  スコア: {result.score:.3f}')
                print(f'  タグ: {result.tags}')
                print(f'  候補数: {result.total_candidates}')
            else:
                print(f'❌ 検索失敗 - 該当なし')
                print(f'  候補数: {result.total_candidates}')
            
            print(f'  検索時間: {result.search_time_ms:.1f}ms')
        
        print('\n🎉 Q&A検索機能テストが完了しました！')
        
    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')

if __name__ == '__main__':
    test_qa_search()
