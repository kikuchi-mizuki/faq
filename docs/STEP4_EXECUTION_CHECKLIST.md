# STEP4実行チェックリスト

## ✅ 実行手順

### **Phase 1: 環境準備**

#### **1. RailwayでPostgreSQLを追加**
- [ ] Railwayダッシュボードにアクセス
- [ ] 「New」→「Database」→「PostgreSQL」を選択
- [ ] データベース名を入力（例：`faq-rag-db`）
- [ ] 作成完了まで待機（2-3分）
- [ ] `DATABASE_URL`をコピー

#### **2. 環境変数を設定**
- [ ] `OPENAI_API_KEY`を設定
- [ ] `DATABASE_URL`を設定
- [ ] `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`を設定
- [ ] `VECTOR_DIMENSION=384`を設定
- [ ] `SIMILARITY_THRESHOLD=0.6`を設定

#### **3. pgvector拡張を有効化**
- [ ] データベースに接続
- [ ] `CREATE EXTENSION IF NOT EXISTS vector;`を実行
- [ ] 拡張が有効化されたことを確認

### **Phase 2: アプリケーションの再デプロイ**

#### **4. 依存関係の更新**
- [ ] 新しい依存関係が追加されていることを確認
- [ ] Railwayで自動デプロイが開始されることを確認
- [ ] ビルドが成功することを確認

#### **5. アプリケーションの起動確認**
- [ ] ヘルスチェックが成功することを確認
- [ ] ログでRAGServiceの初期化を確認
- [ ] ログでDocumentCollectorの初期化を確認

### **Phase 3: 文書収集の実行**

#### **6. 初回文書収集**
```bash
# 文書収集を実行
curl -X POST https://your-app.railway.app/admin/collect-documents
```
- [ ] 文書収集が成功することを確認
- [ ] ログで収集された文書数を確認
- [ ] データベースに文書が保存されることを確認

#### **7. 収集される文書の確認**
- [ ] Google Sheetsの内容が収集される
- [ ] Google Docsの内容が収集される
- [ ] Google Driveのファイルが収集される

### **Phase 4: RAG機能のテスト**

#### **8. RAG検索のテスト**
```bash
# RAG検索をテスト
curl -X POST https://your-app.railway.app/admin/rag-search \
  -H "Content-Type: application/json" \
  -d '{"query": "制作依頼について教えてください"}'
```
- [ ] 検索結果が返されることを確認
- [ ] 類似文書が取得されることを確認
- [ ] AI回答が生成されることを確認

#### **9. 統計情報の確認**
```bash
# 統計情報を取得
curl https://your-app.railway.app/admin/stats
```
- [ ] RAG統計が表示されることを確認
- [ ] データベース接続状況を確認
- [ ] 埋め込みモデルの状況を確認

### **Phase 5: LINE Botでの動作確認**

#### **10. LINE Botのテスト**
- [ ] LINE Botで「制作依頼」と送信
- [ ] 分岐フローが正常に動作することを確認
- [ ] フロー完了時にAI回答が生成されることを確認
- [ ] qa_listシートの内容が活用されることを確認

## 🔍 トラブルシューティング

### **よくある問題と解決方法**

#### **1. データベース接続エラー**
```
psycopg2.OperationalError: could not connect to server
```
**解決方法**:
- `DATABASE_URL`の形式を確認
- 接続情報が正しいか確認
- データベースが起動しているか確認

#### **2. OpenAI APIエラー**
```
openai.error.AuthenticationError: Invalid API key
```
**解決方法**:
- `OPENAI_API_KEY`が正しく設定されているか確認
- APIキーが有効か確認

#### **3. 埋め込みモデルエラー**
```
OSError: [Errno 2] No such file or directory
```
**解決方法**:
- 初回起動時にモデルのダウンロードが必要
- 時間がかかる場合があります（5-10分）

#### **4. 文書収集エラー**
```
googleapiclient.errors.HttpError: 403 Forbidden
```
**解決方法**:
- Google認証情報を確認
- 必要な権限が設定されているか確認

## 📊 成功の確認

### **完了した場合の表示**

#### **ログでの確認**
```
✅ RAGServiceの初期化が完了しました
✅ DocumentCollectorの初期化が完了しました
✅ 文書収集が完了しました
✅ 類似文書を検索しました: 3件
✅ AI回答を生成しました
```

#### **統計情報での確認**
```json
{
  "rag_stats": {
    "enabled": true,
    "database_connected": true,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
  }
}
```

#### **RAG検索での確認**
```json
{
  "query": "制作依頼について教えてください",
  "answer": "制作依頼について以下の情報をお答えします...",
  "documents": [
    {
      "id": 1,
      "source_type": "google_sheets",
      "title": "制作依頼フロー",
      "content": "制作依頼の詳細...",
      "similarity": 0.85
    }
  ]
}
```

## 🎯 次のステップ

STEP4が完了したら：

1. **STEP5: 運用・分析改善**
   - 定常運用の開始
   - 精度向上のための分析
   - ユーザーフィードバックの収集

2. **継続的な改善**
   - 文書の定期収集
   - モデルの更新
   - 機能の拡張

## 📝 注意事項

- 初回の文書収集には時間がかかります
- 埋め込みモデルのダウンロードには時間がかかります
- 大量の文書がある場合、メモリ使用量に注意してください
- 定期的な文書収集の実行を推奨します
