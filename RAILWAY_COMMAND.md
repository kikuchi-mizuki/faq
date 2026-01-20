# Railway 文書収集コマンド

## 1. Railwayのドメインを確認

Railwayにログインして、以下のいずれかの方法でドメインを確認してください：

### 方法A: Railway Dashboard
1. [Railway Dashboard](https://railway.app/dashboard)にアクセス
2. プロジェクト「faq」を選択
3. 「Settings」→「Domains」でドメインを確認
   - 例: `faq-production.up.railway.app`

### 方法B: Railway CLI（インストール済みの場合）
```bash
railway status
```

---

## 2. 文書収集を実行

### オプションA: スクリプトを使用（推奨）

1. `collect_documents.sh`を編集:
```bash
nano collect_documents.sh
```

2. `RAILWAY_DOMAIN`を実際のドメインに置き換え:
```bash
RAILWAY_DOMAIN="https://faq-production.up.railway.app"  # ← あなたのドメイン
```

3. スクリプトを実行:
```bash
bash collect_documents.sh
```

### オプションB: curlコマンドを直接実行

**Railwayのドメインを以下に置き換えて実行してください：**

```bash
curl -X POST https://YOUR-DOMAIN.up.railway.app/admin/collect-documents \
  -H "X-API-Key: your_secure_admin_key_here_change_me" \
  -v
```

**置き換え例：**
```bash
curl -X POST https://faq-production.up.railway.app/admin/collect-documents \
  -H "X-API-Key: your_secure_admin_key_here_change_me" \
  -v
```

---

## 3. 実行結果の確認

### 成功した場合
```json
{
  "status": "success",
  "message": "文書収集が完了しました",
  "collected": 5
}
```

### 失敗した場合

**401 Unauthorized**
- APIキーが間違っています
- `.env`ファイルの`ADMIN_API_KEY`を確認

**404 Not Found**
- ドメインが間違っています
- Railwayのドメインを再確認

**503 Service Unavailable**
- Google Sheets/Drive APIの一時的なエラー
- 数分後に再試行

---

## 4. Railwayログで確認

文書収集が実行されると、Railwayのログに以下のように表示されます：

```
文書収集を開始します
Google Drive APIサービスを初期化しています...
Google Driveファイルを X 件発見しました
pdfplumberを使用してPDFを解析します: テスト.pdf
Google Driveファイル 'テスト.pdf' を収集しました
Google Driveファイル '菊池さん共有_営業関連シート.xlsx' を収集しました
✅ 起動時の文書収集が完了しました
```

---

## 5. 動作確認

文書収集が完了したら、LINEで質問を送信して確認してください：

**質問例：**
- 「面談の準備は何をすればいい？」
- 「営業の進め方を教えて」
- 「提案資料について教えて」

**期待される動作：**
- 「💭 考え中です...」が表示される
- Excelファイルの内容から回答が生成される
- 「※この回答はアップロードされた資料から生成されました。」が表示される

---

## トラブルシューティング

### 文書が収集されない

1. **Excelファイルがゴミ箱にある**
   - Google Driveのゴミ箱から復元してください

2. **サービスアカウントの権限**
   - ファイルが`faq-625@numeric-scope-456509-t3.iam.gserviceaccount.com`と共有されているか確認

3. **手動で確認**
```bash
python3 check_google_drive.py
```

### APIキーが分からない

`.env`ファイルを確認:
```bash
grep ADMIN_API_KEY .env
```

Railwayの環境変数を確認:
- Railway Dashboard → Settings → Variables → `ADMIN_API_KEY`

---

## まとめ

1. ✅ Excelファイルをゴミ箱から復元
2. ✅ Railwayのドメインを確認
3. ✅ `collect_documents.sh`を編集して実行
4. ✅ Railwayログで収集結果を確認
5. ✅ LINEで動作確認
