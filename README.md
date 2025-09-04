# LINE Q&A自動応答システム

LINEで受け取ったユーザーのメッセージに対し、Googleスプレッドシートに管理されたQ&Aデータから最適な回答を自動返答するシステムです。

## 特徴

- **軽量運用**: スプレッドシートを編集するだけでFAQを更新可能
- **高精度マッチング**: 厳密一致からFuzzy検索まで多段階スコアリング
- **即時反映**: キャッシュ機能付きで高速応答
- **監視・ログ**: 構造化ログとヘルスチェック機能
- **セキュリティ**: LINE署名検証とサービスアカウント認証

## システム構成

```
[LINE User] → [LINE Platform] → [Flask App] → [Google Sheets]
                                    ↓
                              [Cache + Logs]
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
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
GOOGLE_SERVICE_ACCOUNT_JSON=base64_encoded_json
SHEET_ID_QA=your_google_sheet_id
CACHE_TTL_SECONDS=300
ADMIN_USER_IDS=user_id1,user_id2
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
3. 即座に回答を返信

### 管理者コマンド

- `/reload`: キャッシュを刷新
- `/healthz`: ヘルスチェック
- `/admin/stats`: 統計情報表示

## API エンドポイント

- `POST /callback`: LINE Webhook受信
- `GET /healthz`: ヘルスチェック
- `POST /admin/reload`: キャッシュ刷新
- `GET /admin/stats`: 統計情報

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
