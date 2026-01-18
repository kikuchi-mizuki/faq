# Railway本番環境 - 環境変数設定ガイド

## RAG機能に必要な環境変数

Railway の環境変数設定画面で以下を設定してください。

### 1. データベース設定

```bash
DATABASE_URL=postgresql://postgres.zztchlwbfbzkvygazhmk:mizuki8441844@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres
```

### 2. RAG機能の設定

```bash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_DIMENSION=384
SIMILARITY_THRESHOLD=0.6
```

### 3. Gemini API設定

```bash
GEMINI_API_KEY=admin-faq-2025-xK9mP2qL
```

## 既存の環境変数（確認用）

以下の環境変数が既に設定されているはずです：

```bash
# LINE設定
LINE_CHANNEL_SECRET=64da56e9a8a938a97f7603d41d6db9a4
LINE_CHANNEL_ACCESS_TOKEN=QoggJTuqTEKwMF2+wMoqxfX1ijpFo5tiCawckdsy09n/jnQrlFJm2oSXdtrMl2sYnxzVf4P6CmrMtcuCwTx06dnysDizOQhuAcrmQAWyF7S8Yz8SJ+fRDHSd8rZJTNMkFWxtfY+xy7LpJi5colfijwdB04t89/1O/w1cDnyilFU=

# Google Sheets設定
GOOGLE_SERVICE_ACCOUNT_JSON=faq-account.json
SHEET_ID_QA=1ADX4AK_MYGzH4e9hfXbx61SIWt82BNmS633luZ3zPno

# Redis設定
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# アプリケーション設定
CACHE_TTL_SECONDS=300
MATCH_THRESHOLD=0.72
MAX_CANDIDATES=3

# 管理者設定
ADMIN_API_KEY=your_secure_admin_key_here_change_me

# ログ設定
LOG_LEVEL=INFO

# セキュリティ設定
SECRET_KEY=your_secret_key_here_change_in_production

# 環境設定
FLASK_ENV=production
DEBUG=False
```

## Railway での設定手順

1. Railwayダッシュボードにログイン
2. プロジェクトを選択
3. "Variables" タブをクリック
4. 上記のRAG機能用環境変数（DATABASE_URL、EMBEDDING_MODEL、VECTOR_DIMENSION、SIMILARITY_THRESHOLD、GEMINI_API_KEY）を追加
5. "Deploy" をクリックして再デプロイ

## 確認方法

デプロイ後、以下のエンドポイントでRAG機能の状態を確認できます：

```bash
curl https://your-app.railway.app/api/rag/status
```

期待される応答：
```json
{
  "enabled": true,
  "db_connected": true,
  "embedding_model_loaded": true,
  "gemini_configured": true,
  "document_count": 0
}
```

## トラブルシューティング

### ログの確認
Railwayのログで以下のメッセージを確認：
- "RAGService初期化完了: is_enabled=True" → 成功
- "データベース接続に失敗しました" → DATABASE_URLを確認
- "sentence-transformersまたはnumpyが利用できません" → requirements.txtを確認

### よくある問題

1. **DATABASE_URLの形式エラー**
   - 正しい形式: `postgresql://user:password@host:port/database`
   - Supabase Shared Poolerの接続文字列を使用

2. **メモリ不足**
   - sentence-transformersのモデル読み込みには約1GB必要
   - Railwayのプランを確認

3. **タイムアウト**
   - 初回起動時は埋め込みモデルのダウンロードに時間がかかります
   - healthcheckTimeout を 300秒に設定済み
