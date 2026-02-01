#!/usr/bin/env python3
"""
Q&Aサービス統計情報テスト
"""

from line_qa_system.qa_service import QAService

def test_qa_service_stats():
    """Q&Aサービスの統計情報をテスト"""
    print('=== Q&Aサービス統計情報テスト ===')
    
    try:
        qa_service = QAService()
        print('✅ Q&Aサービス初期化成功')
        
        # 統計情報を取得
        stats = qa_service.get_stats()
        print(f'キャッシュ内Q&A数: {stats.total_qa_items}')
        print(f'最終更新時刻: {stats.last_updated}')
        print(f'キャッシュヒット率: {stats.cache_hit_rate:.2f}%')
        
        # ヘルスチェック
        health = qa_service.health_check()
        print(f'ヘルスチェック: {health}')
        
        if stats.total_qa_items > 0:
            print('✅ データ読み込み成功')
        else:
            print('⚠️ データが読み込まれていません')
            print('Google Sheetsのqa_itemsワークシートを確認してください')
            
    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')

if __name__ == '__main__':
    test_qa_service_stats()
