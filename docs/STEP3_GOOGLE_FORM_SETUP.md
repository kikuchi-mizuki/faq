# STEP3: Googleフォーム連携セットアップガイド

## 📋 概要

非エンジニアでもQ&Aを追加できるように、GoogleフォームとGoogle Apps Scriptを使って自動化します。

---

## 🎯 目的

- 運用者がフォームから簡単にQ&Aを投稿できる
- 投稿内容は`qa_form_log`シートに自動記録
- 承認後に`qa_items`シートへ反映

---

## 📝 STEP1: Googleフォームの作成

### 1-1: 新しいGoogleフォームを作成

1. https://forms.google.com にアクセス
2. 「空白のフォーム」をクリック
3. フォームタイトル: **「Q&A追加リクエスト」**
4. 説明: **「新しいQ&Aを追加する際はこのフォームから投稿してください」**

### 1-2: 質問項目を追加

以下の質問を追加してください：

#### ① 質問（必須）
- **質問タイプ**: 記述式
- **質問文**: 質問内容を入力してください
- **必須**: ON
- **説明**: ユーザーが質問する内容を入力

#### ② 回答（必須）
- **質問タイプ**: 段落
- **質問文**: 回答内容を入力してください
- **必須**: ON
- **説明**: 質問に対する回答を入力

#### ③ カテゴリ
- **質問タイプ**: プルダウン
- **質問文**: カテゴリを選択してください
- **選択肢**:
  - 経理
  - 営業
  - 制作
  - 人事
  - IT
  - その他
- **必須**: OFF

#### ④ キーワード
- **質問タイプ**: 記述式
- **質問文**: 検索キーワードを入力（カンマ区切り）
- **必須**: OFF
- **説明**: 例: 修正,リテイク,回数

#### ⑤ 備考
- **質問タイプ**: 段落
- **質問文**: 備考（任意）
- **必須**: OFF

### 1-3: フォーム設定

1. 右上の「設定」ボタンをクリック
2. **「回答」** タブ:
   - ✅ 「回答を1回に制限する」: OFF
   - ✅ 「メールアドレスを収集する」: ON
3. 「保存」をクリック

---

## 🔗 STEP2: スプレッドシートとの連携

### 2-1: 回答先を設定

1. フォームの「回答」タブをクリック
2. 右上の「︙」（3点メニュー）→ 「回答先を選択」
3. 「既存のスプレッドシートを選択」を選択
4. Q&AシートのスプレッドシートIDを入力：
   ```
   環境変数 SHEET_ID_QA の値
   ```
5. 「選択」をクリック

### 2-2: 回答シートの確認

- 新しいシート「フォームの回答 1」が自動作成されます
- このシートにフォーム回答が記録されます

---

## ⚙️ STEP3: Google Apps Scriptの設定

### 3-1: スクリプトエディタを開く

1. スプレッドシートを開く
2. メニューバー → 「拡張機能」 → 「Apps Script」

### 3-2: スクリプトを作成

`コード.gs`ファイルに以下のコードを貼り付けてください：

```javascript
/**
 * STEP3: Googleフォーム回答を qa_form_log シートに転記するスクリプト
 */

function onFormSubmit(e) {
  try {
    // スプレッドシートとシートを取得
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var logSheet = ss.getSheetByName('qa_form_log');
    
    // qa_form_logシートが存在しない場合は作成
    if (!logSheet) {
      logSheet = ss.insertSheet('qa_form_log');
      // ヘッダー行を追加
      logSheet.appendRow([
        'timestamp',
        'question',
        'answer',
        'category',
        'keywords',
        'approved',
        'created_by',
        'notes'
      ]);
    }
    
    // フォーム回答を取得
    var itemResponses = e.response.getItemResponses();
    var timestamp = new Date();
    var email = e.response.getRespondentEmail();
    
    // 回答データを格納
    var question = '';
    var answer = '';
    var category = 'その他';
    var keywords = '';
    var notes = '';
    
    // 各質問の回答を取得
    for (var i = 0; i < itemResponses.length; i++) {
      var itemResponse = itemResponses[i];
      var title = itemResponse.getItem().getTitle();
      var response = itemResponse.getResponse();
      
      if (title.indexOf('質問内容') !== -1) {
        question = response;
      } else if (title.indexOf('回答内容') !== -1) {
        answer = response;
      } else if (title.indexOf('カテゴリ') !== -1) {
        category = response;
      } else if (title.indexOf('キーワード') !== -1) {
        keywords = response;
      } else if (title.indexOf('備考') !== -1) {
        notes = response;
      }
    }
    
    // qa_form_logシートに追加
    logSheet.appendRow([
      timestamp,
      question,
      answer,
      category,
      keywords,
      'FALSE',  // approved（デフォルトは未承認）
      email,
      notes
    ]);
    
    Logger.log('フォーム回答をqa_form_logシートに追加しました');
    
  } catch (error) {
    Logger.log('エラーが発生しました: ' + error.toString());
  }
}

/**
 * トリガーのセットアップ（初回のみ実行）
 */
function setupTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  
  // 既存のトリガーを削除
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }
  
  // 新しいトリガーを作成
  ScriptApp.newTrigger('onFormSubmit')
    .forSpreadsheet(SpreadsheetApp.getActive())
    .onFormSubmit()
    .create();
  
  Logger.log('トリガーをセットアップしました');
}
```

### 3-3: トリガーのセットアップ

1. スクリプトエディタで上記コードを貼り付け
2. 「保存」アイコンをクリック
3. 関数選択ドロップダウンから **`setupTrigger`** を選択
4. 「実行」ボタン（▶️）をクリック
5. 権限を確認画面が表示されたら：
   - 「権限を確認」をクリック
   - Googleアカウントを選択
   - 「詳細」→ 「<プロジェクト名>に移動」をクリック
   - 「許可」をクリック
6. 実行ログに「トリガーをセットアップしました」と表示されればOK

---

## 🧪 STEP4: 動作テスト

### 4-1: フォームから投稿

1. 作成したGoogleフォームを開く
2. テストデータを入力：
   - 質問: 「テスト質問です」
   - 回答: 「テスト回答です」
   - カテゴリ: 「IT」
   - キーワード: 「テスト」
3. 「送信」をクリック

### 4-2: 確認

1. スプレッドシートの`qa_form_log`シートを開く
2. 新しい行が追加されていることを確認
3. 以下の項目が正しく記録されているか確認：
   - timestamp: 投稿日時
   - question: 質問内容
   - answer: 回答内容
   - category: カテゴリ
   - keywords: キーワード
   - approved: FALSE（未承認）
   - created_by: 投稿者のメールアドレス
   - notes: 備考

---

## ✅ STEP5: 承認フロー

### 5-1: 承認方法

1. `qa_form_log`シートを開く
2. 承認する行の**approved列**を **`TRUE`** に変更
3. 承認済みの内容を`qa_items`シートにコピー：

#### 手動コピーの手順

1. 承認した行の内容をコピー
2. `qa_items`シートを開く
3. 新しい行に以下のように貼り付け：
   - **id**: 次の番号（最後のid + 1）
   - **question**: qa_form_logのquestion
   - **answer**: qa_form_logのanswer
   - **keywords**: qa_form_logのkeywords
   - **synonyms**: 空欄（任意）
   - **tags**: qa_form_logのcategory
   - **priority**: 1（デフォルト）
   - **status**: active
   - **updated_at**: 今日の日付

### 5-2: 自動反映（オプション）

将来的には、approved=TRUEになったら自動的にqa_itemsに追加するスクリプトも作成可能です。

---

## 📊 STEP6: 運用フロー

### 通常の運用フロー

```
1. 運用者がGoogleフォームから投稿
   ↓
2. 自動的にqa_form_logシートに記録
   ↓
3. 管理者がqa_form_logを確認
   ↓
4. 内容をチェックし、approved列をTRUEに変更
   ↓
5. 承認済みの内容をqa_itemsシートにコピー
   ↓
6. 5分後（または/admin/reloadで即時）にBotに反映
```

### 承認待ち確認方法

LINEBotの管理APIで確認可能：

```bash
curl https://your-app.railway.app/admin/stats
```

レスポンス例：
```json
{
  "locations": {
    "pending_form_logs": 2,   ← 承認待ち件数
    "approved_form_logs": 5   ← 承認済み件数
  }
}
```

---

## 🎉 完了！

これでSTEP3のGoogleフォーム連携が完成しました。

### 運用者への共有内容

1. **フォームURL**: フォームの「送信」→「リンク」からURLを取得して共有
2. **使い方**:
   - フォームから質問と回答を投稿
   - 管理者が承認後、Botに反映される
3. **問い合わせ先**: IT担当者のメールアドレス

---

## 🔧 トラブルシューティング

### フォーム送信後にqa_form_logに追加されない

- Google Apps Scriptのトリガーが正しく設定されているか確認
- スクリプトの実行ログを確認（Apps Script → 「実行数」）

### approved列がTRUEにしても反映されない

- qa_itemsシートに手動でコピーする必要があります
- コピー後、/admin/reloadでキャッシュを更新

### 権限エラーが表示される

- Google Apps Scriptの権限承認が必要
- setupTrigger関数を再実行して権限を許可

---

## 📚 参考リンク

- [Google Forms公式ドキュメント](https://support.google.com/docs/answer/6281888)
- [Google Apps Script公式ドキュメント](https://developers.google.com/apps-script)

