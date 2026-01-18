# Railway本番環境デプロイメントガイド - RAG機能対応版

## 📋 目次
1. [環境変数の設定](#環境変数の設定)
2. [デプロイ手順](#デプロイ手順)
3. [動作確認](#動作確認)
4. [トラブルシューティング](#トラブルシューティング)

---

## 🔧 環境変数の設定

### Railway ダッシュボードでの設定手順

1. **Railwayにログイン**
   - https://railway.app/ にアクセス
   - プロジェクトを選択

2. **Variables タブを開く**
   - プロジェクトページで "Variables" タブをクリック

3. **以下の環境変数を追加**

#### ✅ RAG機能用（新規追加）

```bash
DATABASE_URL=postgresql://postgres.zztchlwbfbzkvygazhmk:mizuki8441844@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

VECTOR_DIMENSION=384

SIMILARITY_THRESHOLD=0.6

GEMINI_API_KEY=admin-faq-2025-xK9mP2qL
```

#### 📝 既存の環境変数（確認のみ）

以下が既に設定されていることを確認してください：

```bash
LINE_CHANNEL_SECRET=(既存の値)
LINE_CHANNEL_ACCESS_TOKEN=(既存の値)
GOOGLE_SERVICE_ACCOUNT_JSON=(既存の値)
SHEET_ID_QA=(既存の値)
FLASK_ENV=production
DEBUG=False
```

---

## 🚀 デプロイ手順

### 1. 環境変数設定後の再デプロイ

```bash
# ローカルでコミット（必要に応じて）
git add .
git commit -m "feat: Add RAG functionality with Supabase integration"
git push origin main
```

Railwayは自動的にデプロイを開始します。

### 2. デプロイログの確認

Railwayの "Deployments" タブで以下のログメッセージを確認：

**成功時のログ:**
```
✅ RAGServiceの初期化を開始します
✅ データベース接続を確立しました
✅ pgvector拡張機能を有効化しました
✅ Embeddingモデルを読み込んでいます: sentence-transformers/all-MiniLM-L6-v2
✅ Embeddingモデルの読み込みが完了しました
✅ Gemini APIを初期化しました
✅ RAGService初期化完了: is_enabled=True
```

**初回デプロイ時の注意:**
- 埋め込みモデルのダウンロードに2-3分かかります
- `healthcheckTimeout=300`秒に設定済みなので問題ありません

---

## ✅ 動作確認

### 1. ヘルスチェック

```bash
curl https://your-app-name.railway.app/healthz
```

**期待される応答:**
```json
{
  "status": "ok",
  "timestamp": 1234567890.123
}
```

### 2. RAG機能の状態確認

```bash
curl -X GET https://your-app-name.railway.app/admin/rag-status \
  -H "X-Admin-API-Key: your_secure_admin_key_here_change_me"
```

**期待される応答:**
```json
{
  "status": "success",
  "rag_service_initialized": true,
  "rag_service_enabled": true,
  "document_collector_initialized": true,
  "gemini_api_key_set": true,
  "database_url_set": true,
  "timestamp": 1234567890.123
}
```

### 3. ドキュメント収集のテスト

```bash
curl -X POST https://your-app-name.railway.app/admin/collect-documents \
  -H "X-Admin-API-Key: your_secure_admin_key_here_change_me" \
  -H "Content-Type: application/json"
```

**期待される応答:**
```json
{
  "status": "success",
  "message": "ドキュメント収集を開始しました（バックグラウンド実行）",
  "task_id": "..."
}
```

---

## 🔍 トラブルシューティング

### 問題1: データベース接続エラー

**症状:**
```
データベース接続に失敗しました
```

**解決策:**
1. `DATABASE_URL` が正しく設定されているか確認
2. Supabaseのデータベースが起動しているか確認
3. 接続文字列の形式を確認: `postgresql://user:pass@host:port/db`

### 問題2: 埋め込みモデルの読み込み失敗

**症状:**
```
sentence-transformersまたはnumpyが利用できません
```

**解決策:**
1. `requirements.txt` に以下が含まれているか確認:
   ```
   sentence-transformers>=2.2.0
   numpy>=1.24.0
   ```
2. Railwayで再デプロイ

### 問題3: メモリ不足

**症状:**
```
Killed (OOM - Out of Memory)
```

**解決策:**
1. Railwayのプランをアップグレード
2. 埋め込みモデルは約1GBのメモリが必要
3. より軽量なモデルに変更を検討:
   ```
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # 現在(384次元)
   ```

### 問題4: タイムアウト

**症状:**
```
Health check timeout
```

**解決策:**
1. `railway.toml` で設定済み: `healthcheckTimeout = 300`
2. 初回起動は時間がかかるため、ログで進行状況を確認
3. 数分待ってから再度アクセス

### 問題5: Gemini API エラー

**症状:**
```
API key not valid
```

**解決策:**
1. `GEMINI_API_KEY` が正しく設定されているか確認
2. APIキーが有効か確認（Google AI Studioで確認）
3. フォールバックモデルが動作すれば一部機能は利用可能

---

## 📊 監視とメンテナンス

### ログの確認

Railwayの "Logs" タブで以下を監視：

```bash
# 正常な初期化
RAGService初期化完了: is_enabled=True

# データベース接続
データベース接続を確立しました

# モデル読み込み
Embeddingモデルの読み込みが完了しました
```

### パフォーマンス監視

- 初回起動時間: 2-3分（モデルダウンロード含む）
- 通常起動時間: 30-60秒
- メモリ使用量: 約1-1.5GB

---

## 🎯 次のステップ

1. **LINEボットでテスト**
   - Google Driveに資料をアップロード
   - `/admin/collect-documents` でドキュメント収集
   - LINEで質問して回答を確認

2. **本番データの準備**
   - FAQ資料をGoogle Driveに配置
   - PDF/Excelファイルをアップロード

3. **定期的なドキュメント更新**
   - 新しい資料追加時に `/admin/collect-documents` を実行

---

## 📞 サポート

問題が解決しない場合：
1. Railwayのログを確認
2. Supabaseのダッシュボードでデータベース状態を確認
3. ローカル環境で同じ設定をテスト
