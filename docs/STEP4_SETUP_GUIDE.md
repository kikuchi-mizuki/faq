# STEP4: RAG機能セットアップガイド

## 🎯 概要
STEP4では、AI要約（RAG）機能を実装します。Google Sheets、Google Docs、Google Driveから文書を収集し、AIが文脈を理解して回答を生成します。

## 📋 必要な環境変数

### **Railwayでの環境変数設定**

以下の環境変数をRailwayのダッシュボードで設定してください：

```bash
# Gemini API設定（既存のGEMINI_API_KEYを使用）
# GEMINI_API_KEY=your_gemini_api_key_here  # 既に設定済み

# データベース設定（PostgreSQL + pgvector）
DATABASE_URL=postgresql://user:password@host:port/database

# 埋め込みモデル設定
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_DIMENSION=384
SIMILARITY_THRESHOLD=0.6
```

## 🗄️ データベースの準備

### **1. PostgreSQL + pgvectorの準備**

#### **RailwayでPostgreSQLを追加**
1. Railwayダッシュボードにアクセス
2. プロジェクトで「New」→「Database」→「PostgreSQL」を選択
3. データベースが作成されるまで待機
4. 接続情報をコピー

#### **pgvector拡張の有効化**
```sql
-- データベースに接続後、以下のSQLを実行
CREATE EXTENSION IF NOT EXISTS vector;
```

### **2. データベーステーブルの作成**

アプリケーション起動時に自動でテーブルが作成されますが、手動で作成する場合：

```sql
-- 文書テーブル
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(100) NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ベクトルテーブル
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector 
ON document_embeddings USING ivfflat (embedding vector_cosine_ops);
```

## 🔧 アプリケーションの設定

### **1. 依存関係のインストール**

新しい依存関係が追加されているため、Railwayで再デプロイが必要です：

```bash
# ローカルでテストする場合
pip install -r requirements.txt
```

### **2. 環境変数の確認**

以下の環境変数が設定されているか確認：

- ✅ `OPENAI_API_KEY`
- ✅ `DATABASE_URL`
- ✅ `EMBEDDING_MODEL`
- ✅ `VECTOR_DIMENSION`
- ✅ `SIMILARITY_THRESHOLD`

## 📚 文書収集の実行

### **1. 初回文書収集**

アプリケーションが起動したら、以下のエンドポイントで文書収集を実行：

```bash
# POST /admin/collect-documents
curl -X POST https://your-railway-app.railway.app/admin/collect-documents
```

### **2. 収集される文書**

- **Google Sheets**: 全シートの内容
- **Google Docs**: 文書の内容
- **Google Drive**: テキストファイル、CSV、PDF

## 🧪 RAG機能のテスト

### **1. RAG検索のテスト**

```bash
# POST /admin/rag-search
curl -X POST https://your-railway-app.railway.app/admin/rag-search \
  -H "Content-Type: application/json" \
  -d '{"query": "制作依頼について教えてください"}'
```

### **2. 期待される結果**

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

## 🔍 トラブルシューティング

### **1. よくある問題**

#### **データベース接続エラー**
```
psycopg2.OperationalError: could not connect to server
```
**解決方法**: `DATABASE_URL`が正しく設定されているか確認

#### **OpenAI APIエラー**
```
openai.error.AuthenticationError: Invalid API key
```
**解決方法**: `OPENAI_API_KEY`が正しく設定されているか確認

#### **埋め込みモデルエラー**
```
OSError: [Errno 2] No such file or directory
```
**解決方法**: 初回起動時にモデルのダウンロードが必要（時間がかかります）

### **2. ログの確認**

Railwayのログで以下のメッセージを確認：

```
✅ RAGServiceの初期化が完了しました
✅ DocumentCollectorの初期化が完了しました
✅ 文書収集が完了しました
```

## 📊 運用の確認

### **1. 統計情報の確認**

```bash
# GET /admin/stats
curl https://your-railway-app.railway.app/admin/stats
```

### **2. ヘルスチェック**

```bash
# GET /healthz
curl https://your-railway-app.railway.app/healthz
```

## 🎯 次のステップ

1. **環境変数の設定**
2. **データベースの準備**
3. **アプリケーションの再デプロイ**
4. **文書収集の実行**
5. **RAG機能のテスト**
6. **LINE Botでの動作確認**

## 📝 注意事項

- 初回の文書収集には時間がかかる場合があります
- 埋め込みモデルのダウンロードには時間がかかります
- 大量の文書がある場合、メモリ使用量に注意してください
- 定期的な文書収集の実行を推奨します

## 🆘 サポート

問題が発生した場合は、以下の情報を確認してください：

1. Railwayのログ
2. 環境変数の設定
3. データベースの接続状況
4. OpenAI APIキーの有効性
