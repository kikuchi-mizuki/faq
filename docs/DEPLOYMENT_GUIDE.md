# AIマニュアルBot デプロイメントガイド

## 📋 概要

AIマニュアルBotのデプロイメント手順、環境設定、監視・運用方法を詳細に説明します。

---

## 🚀 デプロイメント概要

### 現在のデプロイ状況
- **プラットフォーム**: Railway
- **ステータス**: 本番稼働中
- **バージョン**: STEP3実装中
- **URL**: `https://your-app.railway.app`

### デプロイメント履歴
| 日付 | バージョン | 内容 | ステータス |
|------|-----------|------|-----------|
| 2025/10/13 | STEP1 | 基本Q&A機能 | ✅完了 |
| 2025/10/13 | STEP2 | 分岐会話機能 | ✅完了 |
| 2025/10/13 | STEP3 | フォーム連携 | 🔄実装中 |

---

## 🔧 環境設定

### 1. 必須環境変数

#### LINE設定
```bash
# LINE Developers Consoleで取得
LINE_CHANNEL_SECRET=your_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_access_token
```

#### Google設定
```bash
# Google Cloud Consoleで取得
GOOGLE_SERVICE_ACCOUNT_JSON=base64_encoded_json
SHEET_ID_QA=your_google_sheet_id
```

#### アプリケーション設定
```bash
# キャッシュ設定
CACHE_TTL_SECONDS=300
MATCH_THRESHOLD=0.72
MAX_CANDIDATES=3

# ログ設定
LOG_LEVEL=INFO
LOG_FORMAT=json

# 管理者設定
ADMIN_USER_IDS=user_id1,user_id2
```

#### Redis設定（オプション）
```bash
# Redis接続設定（なくてもメモリキャッシュで動作）
REDIS_HOST=redis.railway.internal
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

### 2. Railway環境変数設定

#### Railwayダッシュボードから設定
1. https://railway.app にアクセス
2. プロジェクトを選択
3. 「Variables」タブをクリック
4. 上記の環境変数を設定
5. 「Deploy」をクリック

#### Railway CLIから設定
```bash
# Railway CLIのインストール
npm install -g @railway/cli

# ログイン
railway login

# プロジェクトに接続
railway link

# 環境変数の設定
railway variables set LINE_CHANNEL_SECRET=your_secret
railway variables set LINE_CHANNEL_ACCESS_TOKEN=your_token
railway variables set GOOGLE_SERVICE_ACCOUNT_JSON=your_json
railway variables set SHEET_ID_QA=your_sheet_id
```

---

## 🏗️ デプロイメント手順

### 1. 初回デプロイ

#### 前提条件
- Python 3.11以上
- Poetry
- Git
- Railwayアカウント

#### 手順
```bash
# 1. リポジトリのクローン
git clone https://github.com/your-org/ai-manual-bot.git
cd ai-manual-bot

# 2. 依存関係のインストール
poetry install

# 3. 環境変数の設定
cp env.example .env
# .envファイルを編集

# 4. ローカルテスト
poetry run python -m line_qa_system.app

# 5. Railwayにデプロイ
railway login
railway link
railway up
```

### 2. 継続デプロイ

#### 自動デプロイ設定
```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install Poetry
        run: pip install poetry
      - name: Install dependencies
        run: poetry install
      - name: Run tests
        run: poetry run pytest
      - name: Deploy to Railway
        run: railway up
```

#### 手動デプロイ
```bash
# 最新コードの取得
git pull origin main

# 依存関係の更新
poetry install

# テストの実行
poetry run pytest

# Railwayにデプロイ
railway up
```

---

## 📊 監視・運用

### 1. ヘルスチェック

#### エンドポイント
```bash
# ヘルスチェック
curl -X GET https://your-app.railway.app/healthz

# 統計情報
curl -X GET https://your-app.railway.app/admin/stats \
  -H "X-User-ID: admin_user_id"

# 自動リロード状態
curl -X GET https://your-app.railway.app/admin/auto-reload/status \
  -H "X-User-ID: admin_user_id"
```

#### 期待されるレスポンス
```json
{
  "status": "healthy",
  "timestamp": 1697123456.789,
  "version": "0.1.0"
}
```

### 2. ログ監視

#### ログの確認方法
```bash
# Railway CLIでログ確認
railway logs

# リアルタイムログ
railway logs --follow

# 特定の時間範囲
railway logs --since 1h
```

#### ログ形式
```json
{
  "timestamp": "2025-10-13T10:30:00Z",
  "level": "INFO",
  "service": "line_qa_bot",
  "user_id": "hash_user_id",
  "event_type": "qa_search",
  "query": "修正回数",
  "response_time_ms": 150,
  "cache_hit": true,
  "result_count": 3,
  "best_score": 0.95
}
```

### 3. パフォーマンス監視

#### メトリクス
- **レスポンス時間**: 平均・95%tile
- **エラー率**: 4xx/5xxエラー率
- **キャッシュヒット率**: キャッシュ利用率
- **メモリ使用量**: ヒープ使用量
- **CPU使用率**: プロセス使用率

#### アラート設定
```bash
# エラー率が5%を超えた場合
if error_rate > 0.05; then
  send_alert "エラー率が異常に高いです: ${error_rate}"
fi

# レスポンス時間が5秒を超えた場合
if response_time > 5000; then
  send_alert "レスポンス時間が異常に長いです: ${response_time}ms"
fi

# メモリ使用量が80%を超えた場合
if memory_usage > 0.8; then
  send_alert "メモリ使用量が高いです: ${memory_usage}"
fi
```

---

## 🔄 運用フロー

### 1. 日常運用

#### 毎日の確認事項
- [ ] ヘルスチェックの実行
- [ ] エラーログの確認
- [ ] パフォーマンスメトリクスの確認
- [ ] キャッシュの状態確認

#### 週次の確認事項
- [ ] 統計情報の確認
- [ ] ユーザー利用状況の分析
- [ ] システムリソースの確認
- [ ] セキュリティログの確認

### 2. 障害対応

#### 障害発生時の対応手順
1. **障害の確認**
   ```bash
   # ヘルスチェック
   curl -X GET https://your-app.railway.app/healthz
   
   # ログ確認
   railway logs --since 10m
   ```

2. **原因の特定**
   - エラーログの分析
   - システムリソースの確認
   - 外部サービス（Google Sheets）の状態確認

3. **応急対応**
   ```bash
   # キャッシュの再読み込み
   curl -X POST https://your-app.railway.app/admin/reload \
     -H "X-User-ID: admin_user_id"
   
   # サービス再起動
   railway restart
   ```

4. **根本原因の解決**
   - コードの修正
   - 設定の調整
   - インフラの改善

### 3. アップデート

#### マイナーアップデート
```bash
# コードの取得
git pull origin main

# テストの実行
poetry run pytest

# デプロイ
railway up
```

#### メジャーアップデート
```bash
# バックアップの作成
railway backup

# ステージング環境でのテスト
railway up --environment staging

# 本番環境へのデプロイ
railway up --environment production
```

---

## 🛡️ セキュリティ

### 1. 認証・認可

#### LINE署名検証
- 全Webhookリクエストで署名検証を実施
- HMAC-SHA256による署名計算
- 不正なリクエストの拒否

#### 管理者認証
- X-User-IDヘッダによる認証
- 許可リストによるアクセス制御
- 管理者権限の最小化

### 2. データ保護

#### 個人情報保護
- user_idのハッシュ化
- PII（個人識別情報）の非保存
- ログの匿名化

#### 通信の暗号化
- HTTPS必須
- TLS 1.2以上
- 証明書の定期更新

### 3. 監査ログ

#### ログ記録項目
- 全APIリクエスト
- 管理者操作
- エラー・例外
- セキュリティイベント

#### ログ保持期間
- アクセスログ: 30日
- エラーログ: 90日
- セキュリティログ: 1年

---

## 📈 スケーリング

### 1. 水平スケーリング

#### 複数インスタンス
```yaml
# railway.toml
[deploy]
replicas = 3
```

#### ロードバランシング
- Railwayの自動ロードバランシング
- ヘルスチェックによる自動切り替え
- セッション管理の分散

### 2. 垂直スケーリング

#### リソース増強
```bash
# Railway CLIでリソース増強
railway scale --memory 1GB --cpu 1
```

#### パフォーマンスチューニング
- キャッシュサイズの調整
- データベース接続プールの最適化
- 非同期処理の導入

---

## 🔧 トラブルシューティング

### 1. よくある問題

#### 問題: LINE Webhookが応答しない
**原因**: 署名検証の失敗
**解決方法**:
```bash
# 環境変数の確認
railway variables

# 署名検証のテスト
curl -X POST https://your-app.railway.app/callback \
  -H "X-Line-Signature: test_signature" \
  -d '{"events":[]}'
```

#### 問題: Google Sheetsに接続できない
**原因**: サービスアカウントの権限不足
**解決方法**:
1. Google Cloud Consoleでサービスアカウントの権限確認
2. スプレッドシートの共有設定確認
3. 環境変数の再設定

#### 問題: キャッシュが更新されない
**原因**: 自動リロードの停止
**解決方法**:
```bash
# 手動リロード
curl -X POST https://your-app.railway.app/admin/reload \
  -H "X-User-ID: admin_user_id"

# 自動リロードの状態確認
curl -X GET https://your-app.railway.app/admin/auto-reload/status \
  -H "X-User-ID: admin_user_id"
```

### 2. デバッグ方法

#### ログレベルの変更
```bash
# デバッグログの有効化
railway variables set LOG_LEVEL=DEBUG

# アプリケーションの再起動
railway restart
```

#### 詳細ログの確認
```bash
# 特定の時間範囲のログ
railway logs --since 1h --follow

# エラーログのみ
railway logs --since 1h | grep ERROR
```

---

## 📝 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|----------|--------|
| 2025/10/13 | 1.0 | 初版作成 | AI Assistant |
| - | - | STEP1完了 | - |
| - | - | STEP2完了 | - |
| - | - | STEP3実装中 | - |

---

## 📞 関連ドキュメント

- **要件定義書**: `docs/REQUIREMENTS.md`
- **システム構成書**: `docs/SYSTEM_ARCHITECTURE.md`
- **API仕様書**: `docs/API_SPECIFICATION.md`
- **Railwayデプロイガイド**: `docs/RAILWAY_DEPLOYMENT_GUIDE.md`
- **各ステップ別ガイド**: `docs/STEP*_*.md`
