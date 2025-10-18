# Railway デプロイガイド（STEP2対応）

## 🚀 デプロイ完了

**コミット**: `3e92c89` - STEP2: 分岐会話機能（フロー）実装完了

---

## ✅ 必須環境変数の確認

Railwayのダッシュボードで以下の環境変数が設定されているか確認してください：

### 既存の環境変数（STEP1から）

```bash
# LINE設定
LINE_CHANNEL_SECRET=your_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_access_token

# Google Sheets設定
GOOGLE_SERVICE_ACCOUNT_JSON=base64_encoded_json
SHEET_ID_QA=your_sheet_id

# アプリケーション設定
CACHE_TTL_SECONDS=300
MATCH_THRESHOLD=0.72
MAX_CANDIDATES=3
LOG_LEVEL=INFO
```

### 🆕 STEP2で追加された環境変数（オプション）

```bash
# Redis設定（オプション - なくてもメモリキャッシュで動作）
REDIS_HOST=redis.railway.internal  # Railwayで追加する場合
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

---

## 📝 Railway環境変数の設定手順

### 方法1: Railwayダッシュボードから設定

1. https://railway.app にアクセス
2. プロジェクトを選択
3. 「Variables」タブをクリック
4. 上記の環境変数を設定

### 方法2: Railway CLIから設定

```bash
# Redis関連（オプション）
railway variables set REDIS_HOST=localhost
railway variables set REDIS_PORT=6379
railway variables set REDIS_DB=0
```

---

## 🔧 Redis追加（オプション）

Redisを使用する場合（推奨だが必須ではない）:

### Railwayで新しいサービスを追加

1. Railwayダッシュボード → プロジェクトを開く
2. 「New Service」ボタンをクリック
3. 「Database」 → 「Redis」を選択
4. 自動的に環境変数が設定される：
   - `REDIS_HOST`
   - `REDIS_PORT`
   - `REDIS_PASSWORD`（必要な場合）

### 環境変数の接続

Redisサービスを追加すると、自動的にプライベートネットワーク経由で接続できます。

**注意**: Redisがない場合でも、アプリは**メモリキャッシュモード**で正常に動作します。

---

## 🧪 デプロイ確認手順

### 1. デプロイログの確認

Railwayダッシュボード → 「Deployments」 → 最新のデプロイを開く

確認ポイント:
- ✅ ビルドが成功している
- ✅ `Successfully installed redis-6.4.0` が表示されている
- ✅ アプリケーションが起動している
- ✅ エラーログがない

### 2. ヘルスチェック

デプロイ完了後、ヘルスチェックエンドポイントにアクセス:

```bash
curl https://your-app.railway.app/healthz
```

期待されるレスポンス:
```json
{
  "status": "healthy",
  "timestamp": 1234567890.123,
  "version": "0.1.0"
}
```

### 3. 統計情報の確認

```bash
curl https://your-app.railway.app/admin/stats
```

期待されるレスポンス:
```json
{
  "total_qa_items": 11,
  "active_qa_items": 11,
  "cache_hit_rate": 0.0,
  "average_response_time_ms": 0.0,
  "total_requests": 0,
  "successful_matches": 0,
  "last_updated": "2025-10-13T..."
}
```

### 4. flowsシートの読み込み確認

ログを確認して、flowsシートが正しく読み込まれているか確認:

```
✅ フローデータの再読み込みが完了しました flow_count=17
```

---

## 📱 LINE Webhookの確認

### LINE Developersコンソールで確認

1. https://developers.line.biz/console/ にアクセス
2. プロバイダー → チャネルを選択
3. 「Messaging API」タブを開く
4. **Webhook URL**: `https://your-app.railway.app/callback`
5. **Use webhook**: ON（有効）
6. 「Verify」ボタンをクリックして接続確認

期待される結果: ✅ Success

---

## 🧪 LINE実機テスト手順

### テスト1: 通常のQ&A（STEP1機能）

LINEで適当なメッセージを送信:
- 既存のQ&Aに該当する質問を送る
- 回答が返ってくることを確認

### テスト2: 分岐会話フロー（月次締め）

1. **「月次締め」** と送信
   - ✅ クイックリプライボタンが表示される
   - ✅ 選択肢: 「はい」「いいえ」

2. **「はい」** をタップ
   - ✅ 次の質問が表示される
   - ✅ 選択肢: 「はい」「いいえ」

3. **「はい」** をタップ
   - ✅ 完了メッセージが表示される
   - 「処理が完了しました。✅ 経理システムをご確認ください。」

### テスト3: 分岐会話フロー（サポート）

1. **「サポート」** と送信
   - ✅ クイックリプライボタンが表示される
   - ✅ 選択肢: 「ログインできない」「エラーが出る」「その他」

2. **「ログインできない」** をタップ
   - ✅ 次の質問が表示される
   - ✅ 選択肢: 「はい」「いいえ」

3. **「はい」** をタップ
   - ✅ 完了メッセージが表示される
   - 「パスワードリセットリンクを送信しました。📧...」

### テスト4: キャンセル機能

1. **「月次締め」** と送信
   - ✅ フローが開始される

2. **「キャンセル」** と送信
   - ✅ 「会話をキャンセルしました。」と表示される
   - ✅ フローが終了する

### テスト5: 不正な選択肢

1. **「月次締め」** と送信
2. **「あいうえお」** と送信（不正な選択肢）
   - ✅ フォールバックメッセージが表示される
   - 「入力が正しくありません。❌...」

---

## 🐛 トラブルシューティング

### ❌ デプロイが失敗する

**原因**: 依存関係のエラー

**解決策**:
```bash
# ローカルでテスト
pip3 install -r requirements.txt  # requirements.txtがある場合
# または
pip3 install redis structlog cachetools
```

### ❌ flowsシートが読み込まれない

**原因**: スプレッドシートに`flows`シートが存在しない

**解決策**:
1. `create_flows_sheet.py`を実行してflowsシートを作成
2. または、手動で`docs/STEP2_FLOWS_SHEET_SETUP.md`の手順に従って作成

### ❌ クイックリプライが表示されない

**原因**: LINE側の問題 or フローが開始されていない

**確認事項**:
1. ログで「フローを開始しました」が表示されているか
2. トリガーワード（「月次締め」「サポート」）が正しく送信されているか
3. flowsシートが正しく読み込まれているか

### ❌ セッションが保持されない

**原因**: Redisが設定されておらず、アプリが再起動している

**解決策**:
- メモリキャッシュモードでは、アプリ再起動時にセッションが消える（これは正常）
- 永続的なセッション管理が必要な場合はRedisを追加

---

## 📊 期待される動作

### ログ出力例（正常）

```
2025-10-13 16:42:08 [info] FlowService: Google Sheets APIの初期化が完了しました
2025-10-13 16:42:09 [info] フローデータの再読み込みが完了しました flow_count=17
2025-10-13 16:42:10 [info] メッセージを受信しました user_id=hashed_xxx text=月次締め
2025-10-13 16:42:10 [info] フローを開始しました flow_id=201 trigger=月次締め
2025-10-13 16:42:10 [info] 次のステップへ進みました step=2 trigger=月次締め
2025-10-13 16:42:11 [info] 終了ステップに到達 trigger=月次締め
```

### エラーログ例

**Redis未接続（正常）**:
```
[error] Redisの初期化に失敗しました error='Error 61...'
[warning] メモリキャッシュモードで動作します
```
→ これは正常です。メモリキャッシュで動作します。

**flowsシート未作成（要対応）**:
```
[error] フローデータの再読み込みに失敗しました
```
→ flowsシートを作成してください。

---

## ✅ チェックリスト

デプロイ前:
- [x] Gitコミット・プッシュ完了
- [x] 環境変数の確認

デプロイ中:
- [ ] Railwayでビルドが成功
- [ ] アプリケーションが起動
- [ ] ヘルスチェックが成功

デプロイ後:
- [ ] LINE Webhook接続確認
- [ ] flowsシートの読み込み確認
- [ ] LINEで通常Q&Aテスト
- [ ] LINEで分岐会話テスト（月次締め）
- [ ] LINEで分岐会話テスト（サポート）
- [ ] キャンセル機能テスト

---

## 🎉 完了！

全てのチェックリストが完了したら、STEP2のデプロイは成功です！

次のステップ:
- STEP3: Googleフォーム連携
- STEP4: AI要約（RAG）機能

---

## 📞 サポート

問題が発生した場合:
1. Railwayのログを確認
2. `/admin/stats`エンドポイントで状態確認
3. LINE Developers ConsoleでWebhookログを確認

