# Googleフォーム連携 導入完了ガイド

## 📋 導入日時
2025年12月27日

---

## 🎯 概要

Googleフォームから1問1答形式でQ&Aを追加できるシステムを導入しました。

### 主な機能

- ✅ **Googleフォームから投稿** → 自動的に`qa_items`シートに追加
- ✅ **承認プロセスなし** → フォーム送信後すぐに`active`で追加
- ✅ **即座に反映** → 5分後（または手動リロード）でLINE Botで使える
- ✅ **ログ記録** → `qa_form_log`シートに投稿履歴を保存

---

## 🔄 運用フロー

```
【運用者】
  ↓ Googleフォームから質問・回答を投稿

【自動】qa_form_logシートに記録（approved=AUTO）
  ↓

【自動】即座にqa_itemsシートに追加（status=active）
  ↓

【自動】5分後にLINE Botに自動反映
  または
  /admin/reloadで即時反映
  ↓

【完了】LINEで質問できるようになる！
```

---

## 📝 Googleフォーム構成

### フォーム項目

1. **質問内容を入力してください**（必須）
   - タイプ: 記述式
   - 説明: ユーザーが質問する内容を入力

2. **回答内容を入力してください**（必須）
   - タイプ: 段落
   - 説明: 質問に対する回答を入力

3. **カテゴリを選択してください**（任意）
   - タイプ: プルダウン
   - 選択肢: 経理、営業、制作、人事、IT、その他

4. **検索キーワードを入力（カンマ区切り）**（任意）
   - タイプ: 記述式
   - 例: 修正,リテイク,回数

5. **備考（任意）**（任意）
   - タイプ: 段落

### フォーム設定

- メールアドレスを収集: **ON**
- 回答を1回に制限する: OFF

---

## 🔧 Google Apps Script

### スクリプトファイル

最終版スクリプト:
```
/Users/kikuchimizuki/Desktop/aicollections_2/faq/google_apps_script_simple_auto.js
```

### スクリプト設置場所

- スプレッドシートID: `1ADX4AK_MYGzH4e9hfXbx61SIWt82BNmS633luZ3zPno`
- 拡張機能 → Apps Script

### トリガー設定

- **関数**: `onFormSubmit`
- **イベントのソース**: スプレッドシートから
- **イベントの種類**: フォーム送信時

---

## 📊 データフロー

### 入力: Googleフォーム

フォーム項目が「フォームの回答 3」シートに記録される。

### 中間: qa_form_logシート

| 列 | 項目 | 説明 |
|----|------|------|
| A | timestamp | 投稿日時 |
| B | question | 質問内容 |
| C | answer | 回答内容 |
| D | category | カテゴリ |
| E | keywords | キーワード |
| F | approved | AUTO（自動追加済み） |
| G | created_by | 投稿者のメールアドレス |
| H | notes | 備考 |

### 出力: qa_itemsシート

| 列 | 項目 | 値 |
|----|------|-----|
| A | row_num | 空白（自動採番） |
| B | qa_category | カテゴリ |
| C | id | 自動採番（最大ID+1） |
| D | question | 質問内容 |
| E | answer | 回答内容 |
| F | keywords | キーワード |
| G | patterns | 空白 |
| H | tags | カテゴリ |
| I | priority | 1 |
| J | status | **active** |
| K | updated_at | 投稿日時 |

---

## 🚀 導入手順まとめ

### ステップ1: Googleフォーム作成 ✅

1. https://forms.google.com で新規フォーム作成
2. 5つの質問項目を追加
3. メールアドレス収集をON

### ステップ2: スプレッドシート連携 ✅

1. フォームの「回答先を選択」
2. スプレッドシートID: `1ADX4AK_MYGzH4e9hfXbx61SIWt82BNmS633luZ3zPno`
3. 「フォームの回答 3」シートが自動作成される

### ステップ3: Google Apps Scriptセットアップ ✅

1. スプレッドシートで「拡張機能」→「Apps Script」
2. `google_apps_script_simple_auto.js`の内容を貼り付け
3. 保存

### ステップ4: トリガー設定 ✅

1. 関数選択で `setupTriggers` を選択
2. 実行ボタンをクリック
3. 権限を承認

### ステップ5: 動作確認 ✅

1. Googleフォームからテスト投稿
2. `qa_form_log`シートにデータが追加されることを確認
3. `qa_items`シートに自動追加されることを確認
4. `status`が`active`になっていることを確認

---

## 📖 運用マニュアル

### 運用者向け

1. **GoogleフォームのURLにアクセス**
2. **質問と回答を入力**
3. **カテゴリとキーワードを入力**（推奨）
4. **送信**
5. **5分後に自動でLINE Botに反映される**

### 管理者向け

#### 即時反映する場合

```bash
curl -X POST https://your-app.railway.app/admin/reload \
  -H "X-API-Key: YOUR_ADMIN_API_KEY"
```

#### 投稿履歴を確認

`qa_form_log`シートを確認:
- 誰が、いつ、何を投稿したかを確認できる
- `approved`列が`AUTO`になっている = 自動追加済み

#### Q&Aを無効化する場合

`qa_items`シートで該当行の`status`列を`inactive`に変更:
- LINE Botで使えなくなる
- データは残る（後で再度`active`に変更可能）

---

## ⚠️ トラブルシューティング

### フォーム送信してもqa_form_logに追加されない

**原因**: トリガーが設定されていない

**解決策**:
1. Apps Scriptエディタを開く
2. `setupTriggers`関数を実行
3. トリガー画面で`onFormSubmit`が表示されることを確認

---

### qa_itemsに追加されているが、列がずれている

**原因**: スクリプトのシート構成が実際のシートと一致していない

**解決策**:
1. 最新版のスクリプト（`google_apps_script_simple_auto.js`）を使用
2. スクリプトを全て差し替える
3. `setupTriggers`を再実行

---

### LINE Botで質問できない

**原因1**: `status`が`inactive`になっている

**解決策**: `qa_items`シートで`status`列を`active`に変更

**原因2**: キャッシュが更新されていない

**解決策**: 5分待つ、または`/admin/reload`で手動更新

---

## 🔑 重要な設定情報

### スプレッドシート

- **ID**: `1ADX4AK_MYGzH4e9hfXbx61SIWt82BNmS633luZ3zPno`
- **フォーム回答シート**: `フォームの回答 3`
- **ログシート**: `qa_form_log`
- **Q&Aシート**: `qa_items`

### 環境変数（.env）

```env
SHEET_ID_QA=1ADX4AK_MYGzH4e9hfXbx61SIWt82BNmS633luZ3zPno
CACHE_TTL_SECONDS=300
```

---

## 📈 今後の拡張案

### オプション1: 承認フローの追加

必要に応じて、以下の機能を追加可能:
- `approved`列を手動で`TRUE`に変更するフロー
- 承認前は`inactive`、承認後に`active`に変更

### オプション2: 通知機能

フォーム投稿時に管理者にメール通知:
```javascript
MailApp.sendEmail(
  "admin@example.com",
  "新しいQ&Aが投稿されました",
  "質問: " + question
);
```

### オプション3: 重複チェック強化

現在は質問文の完全一致のみチェック。
類似質問の検出機能を追加可能。

---

## 📞 サポート

### ドキュメント

- `docs/STEP3_GOOGLE_FORM_SETUP.md` - 詳細セットアップガイド
- `docs/STEP3_FINAL_APPS_SCRIPT.md` - スクリプト詳細

### スクリプトファイル

- `google_apps_script_simple_auto.js` - 最終版（シンプル）
- `google_apps_script_auto.js` - 完全版
- `google_apps_script_fixed.js` - 修正版（承認フロー付き）

---

## ✅ 導入完了チェックリスト

- [x] Googleフォーム作成
- [x] フォームとスプレッドシート連携
- [x] Google Apps Scriptセットアップ
- [x] トリガー設定
- [x] 動作テスト（フォーム → qa_form_log）
- [x] 動作テスト（qa_form_log → qa_items）
- [x] 列構成の修正
- [x] 完全自動化（承認プロセス省略）
- [x] シンプル版スクリプト作成

---

**導入完了日**: 2025年12月27日
**最終更新**: 2025年12月27日
