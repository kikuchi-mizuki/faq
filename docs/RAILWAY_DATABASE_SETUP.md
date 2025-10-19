# Railway PostgreSQL + pgvector セットアップガイド

## 🎯 概要
RailwayでPostgreSQLデータベースを追加し、pgvector拡張を有効化してRAG機能を動作させます。

## 📋 手順

### **1. RailwayでPostgreSQLを追加**

1. **Railwayダッシュボードにアクセス**
   - https://railway.app にログイン
   - 対象のプロジェクトを選択

2. **データベースを追加**
   - 「New」ボタンをクリック
   - 「Database」を選択
   - 「PostgreSQL」を選択
   - データベース名を入力（例：`faq-rag-db`）

3. **接続情報を取得**
   - データベースが作成されるまで待機（2-3分）
   - 「Variables」タブで接続情報を確認
   - `DATABASE_URL`をコピー

### **2. 環境変数の設定**

Railwayのプロジェクト設定で以下の環境変数を追加：

```bash
# データベース設定
DATABASE_URL=postgresql://postgres:password@host:port/railway

# OpenAI API設定
OPENAI_API_KEY=your_openai_api_key_here

# 埋め込みモデル設定
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_DIMENSION=384
SIMILARITY_THRESHOLD=0.6
```

### **3. pgvector拡張の有効化**

#### **方法1: Railway CLIを使用**
```bash
# Railway CLIをインストール
npm install -g @railway/cli

# ログイン
railway login

# プロジェクトを選択
railway link

# データベースに接続
railway connect postgres
```

#### **方法2: 外部ツールを使用**
- pgAdmin、DBeaver、またはpsqlを使用
- Railwayの接続情報でデータベースに接続
- 以下のSQLを実行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### **4. テーブルの作成**

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

## 🔧 トラブルシューティング

### **よくある問題**

#### **1. データベース接続エラー**
```
psycopg2.OperationalError: could not connect to server
```

**解決方法**:
- `DATABASE_URL`の形式を確認
- 接続情報が正しいか確認
- データベースが起動しているか確認

#### **2. pgvector拡張エラー**
```
ERROR: extension "vector" does not exist
```

**解決方法**:
- pgvector拡張を手動でインストール
- RailwayのPostgreSQLバージョンを確認

#### **3. 権限エラー**
```
ERROR: permission denied for schema public
```

**解決方法**:
- データベースユーザーの権限を確認
- 管理者権限で接続

## 📊 確認方法

### **1. 接続テスト**
```bash
# アプリケーションのヘルスチェック
curl https://your-app.railway.app/healthz
```

### **2. 統計情報の確認**
```bash
# 統計情報を取得
curl https://your-app.railway.app/admin/stats
```

### **3. ログの確認**
Railwayのダッシュボードでログを確認：
- 「Deployments」→「View Logs」
- エラーメッセージを確認

## 🎯 次のステップ

1. ✅ PostgreSQLデータベースの追加
2. ✅ 環境変数の設定
3. ✅ pgvector拡張の有効化
4. 🔄 アプリケーションの再デプロイ
5. 🔄 文書収集の実行
6. 🔄 RAG機能のテスト

## 📝 注意事項

- データベースの作成には2-3分かかります
- 初回起動時にモデルのダウンロードが必要です
- 大量の文書がある場合、メモリ使用量に注意してください
