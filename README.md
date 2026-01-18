# LINE Q&A自動応答システム

LINEで受け取ったユーザーのメッセージに対し、Googleスプレッドシートに管理されたQ&Aデータから最適な回答を自動返答するシステムです。

## 特徴

- **軽量運用**: スプレッドシートを編集するだけでFAQを更新可能
- **高精度マッチング**: 厳密一致からFuzzy検索まで多段階スコアリング
- **RAG機能**: PDF/Excelなどの資料をアップロードしてAIが自動学習・回答
- **即時反映**: キャッシュ機能付きで高速応答
- **監視・ログ**: 構造化ログとヘルスチェック機能
- **セキュリティ**: LINE署名検証とサービスアカウント認証

## システム構成

```
[LINE User] → [LINE Platform] → [Flask App] → [Google Sheets (Q&A)]
                                    ↓              ↓
                                [AI + RAG] ← [Google Drive (PDF/Excel)]
                                    ↓
                              [PostgreSQL + pgvector]
```

## セットアップ手順

### 1. 前提条件

- Python 3.9以上
- Poetry
- LINE公式アカウント
- Google Cloud プロジェクト

### 2. インストール

```bash
# 依存関係のインストール
poetry install

# 開発環境の起動
poetry run dev
```

### 3. 環境変数の設定

`.env`ファイルを作成し、以下を設定：

```env
# LINE設定
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token

# Google設定
GOOGLE_SERVICE_ACCOUNT_JSON=base64_encoded_json
SHEET_ID_QA=your_google_sheet_id

# AI/RAG設定（オプション）
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql://user:password@host:port/dbname
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_DIMENSION=384
SIMILARITY_THRESHOLD=0.6

# その他
CACHE_TTL_SECONDS=300
ADMIN_API_KEY=your_admin_api_key
LOG_LEVEL=INFO
```

### 4. LINE設定

1. LINE Developers ConsoleでWebhook URLを設定
2. `/callback`エンドポイントを指定
3. 署名検証を有効化

### 5. Google Sheets設定

1. サービスアカウントにスプレッドシートの閲覧権限を付与
2. `qa_items`シートを作成（スキーマは要件定義書参照）

## 使用方法

### 基本動作

1. ユーザーがLINEでキーワードを送信
2. システムがスプレッドシートから最適な回答を検索
3. Q&Aに該当がない場合、RAGでアップロード資料から回答を生成
4. 即座に回答を返信

### RAG機能の使い方

#### 1. 資料のアップロード

Google Driveにファイルをアップロードし、サービスアカウントに共有権限を付与します：

- **対応ファイル形式**: PDF、Excel (.xlsx, .xls)、テキスト (.txt, .csv)
- **アップロード先**: Google Driveの任意のフォルダ
- **権限設定**: サービスアカウントに「閲覧者」権限を付与

#### 2. 文書の収集

管理者APIエンドポイントを使用して文書を収集：

```bash
curl -X POST https://your-domain.com/admin/collect-documents \
  -H "X-API-Key: your_admin_api_key"
```

#### 3. 動作確認

- Q&Aに該当しない質問をLINEで送信
- RAGが資料から回答を生成
- 回答末尾に「※この回答はアップロードされた資料から生成されました。」と表示

### 管理者コマンド

- `/healthz`: ヘルスチェック
- `POST /admin/reload`: Q&Aキャッシュを刷新
- `POST /admin/collect-documents`: Google Driveから文書を収集
- `GET /admin/stats`: 統計情報表示

## API エンドポイント

### パブリック
- `POST /callback`: LINE Webhook受信
- `GET /healthz`: ヘルスチェック

### 管理者専用（X-API-Keyヘッダー必須）
- `POST /admin/reload`: Q&Aキャッシュ刷新
- `POST /admin/collect-documents`: Google Driveから文書を収集してRAGに追加
- `GET /admin/stats`: 統計情報取得
- `GET /admin/authenticated-users`: 認証済みユーザー一覧

## 開発

```bash
# テスト実行
poetry run pytest

# コードフォーマット
poetry run black .

# リント
poetry run flake8
```

## ライセンス

MIT License
