# STEP3: 完全自動化スクリプト

## 🎯 自動化の内容

1. ✅ **フォーム送信** → qa_form_logシートに自動追加
2. ✅ **approved列をTRUEに変更** → qa_itemsシートに自動追加
3. ✅ **重複チェック** → 同じ質問は追加しない
4. ✅ **自動ID採番** → 次のIDを自動割り当て

---

## 📝 完全自動化スクリプト

Apps Scriptエディタに以下のコードを貼り付けてください：

```javascript
/**
 * STEP3: 完全自動化スクリプト
 * - フォーム送信 → qa_form_log自動追加
 * - approved=TRUE → qa_items自動追加
 */

// ========================================
// 1. フォーム送信時の処理
// ========================================

function onFormSubmit(e) {
  try {
    Logger.log('=== フォーム送信イベント開始 ===');
    
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var logSheet = ss.getSheetByName('qa_form_log');
    
    // qa_form_logシートがなければ作成
    if (!logSheet) {
      logSheet = ss.insertSheet('qa_form_log');
      logSheet.appendRow([
        'timestamp', 'question', 'answer', 'category', 
        'keywords', 'approved', 'created_by', 'notes'
      ]);
      Logger.log('qa_form_logシートを作成しました');
    }
    
    // フォーム回答を取得
    var timestamp = new Date();
    var email = e.response.getRespondentEmail() || '匿名';
    
    // 「フォームの回答 1」シートから最新の回答を取得
    var formSheet = ss.getSheetByName('フォームの回答 1');
    if (!formSheet) {
      Logger.log('エラー: フォームの回答シートが見つかりません');
      return;
    }
    
    var lastRow = formSheet.getLastRow();
    var data = formSheet.getRange(lastRow, 1, 1, formSheet.getLastColumn()).getValues()[0];
    
    // データの割り当て（列番号は実際のフォームに合わせて調整）
    var question = data[1] || '';
    var answer = data[2] || '';
    var category = data[3] || 'その他';
    var keywords = data[4] || '';
    var notes = data[5] || '';
    
    // qa_form_logに追加
    logSheet.appendRow([
      timestamp,
      question,
      answer,
      category,
      keywords,
      'FALSE',  // デフォルトは未承認
      email,
      notes
    ]);
    
    Logger.log('✅ qa_form_logに追加しました: ' + question);
    
  } catch (error) {
    Logger.log('❌ エラー: ' + error.toString());
  }
}

// ========================================
// 2. セル編集時の処理（approved列の変更を検知）
// ========================================

function onEdit(e) {
  try {
    var sheet = e.source.getActiveSheet();
    var range = e.range;
    
    // qa_form_logシート以外は無視
    if (sheet.getName() !== 'qa_form_log') {
      return;
    }
    
    // approved列（6列目）以外は無視
    var approvedColumn = 6;
    if (range.getColumn() !== approvedColumn) {
      return;
    }
    
    // 値がTRUEでなければ無視
    var newValue = range.getValue();
    if (newValue !== true && newValue !== 'TRUE' && newValue !== 'true') {
      return;
    }
    
    Logger.log('=== approved列がTRUEに変更されました ===');
    
    // 編集された行のデータを取得
    var row = range.getRow();
    var rowData = sheet.getRange(row, 1, 1, sheet.getLastColumn()).getValues()[0];
    
    var timestamp = rowData[0];
    var question = rowData[1];
    var answer = rowData[2];
    var category = rowData[3];
    var keywords = rowData[4];
    var approved = rowData[5];
    var createdBy = rowData[6];
    var notes = rowData[7];
    
    Logger.log('承認された質問: ' + question);
    
    // qa_itemsシートに追加
    addToQAItems(question, answer, category, keywords);
    
    // 備考欄に反映済みメッセージを追加
    var currentNotes = notes || '';
    var newNotes = currentNotes + '\n[自動反映済み: ' + new Date().toLocaleString('ja-JP') + ']';
    sheet.getRange(row, 8).setValue(newNotes);
    
    Logger.log('✅ qa_itemsシートに追加しました');
    
  } catch (error) {
    Logger.log('❌ エラー: ' + error.toString());
    // エラーでも処理を止めない
  }
}

// ========================================
// 3. qa_itemsシートに追加する関数
// ========================================

function addToQAItems(question, answer, category, keywords) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var qaSheet = ss.getSheetByName('qa_items');
  
  if (!qaSheet) {
    Logger.log('エラー: qa_itemsシートが見つかりません');
    return;
  }
  
  // 重複チェック
  var lastRow = qaSheet.getLastRow();
  var existingQuestions = qaSheet.getRange(2, 2, lastRow - 1, 1).getValues();
  
  for (var i = 0; i < existingQuestions.length; i++) {
    if (existingQuestions[i][0] === question) {
      Logger.log('警告: 同じ質問が既に存在します: ' + question);
      return;  // 重複なので追加しない
    }
  }
  
  // 次のIDを取得
  var lastId = 0;
  if (lastRow > 1) {
    var ids = qaSheet.getRange(2, 1, lastRow - 1, 1).getValues();
    for (var i = 0; i < ids.length; i++) {
      if (ids[i][0] > lastId) {
        lastId = ids[i][0];
      }
    }
  }
  var nextId = lastId + 1;
  
  // 新しい行を追加
  qaSheet.appendRow([
    nextId,           // id
    question,         // question
    answer,           // answer
    keywords,         // keywords
    '',               // synonyms（空欄）
    category,         // tags（カテゴリをタグとして使用）
    1,                // priority（デフォルト1）
    'inactive',       // status（初期は非表示。確認後にactiveへ）
    new Date()        // updated_at
  ]);
  
  Logger.log('✅ qa_itemsに追加しました（ID: ' + nextId + '）');
}

// ========================================
// 4. トリガーのセットアップ
// ========================================

function setupTriggers() {
  try {
    Logger.log('=== トリガーセットアップ開始 ===');
    
    // 既存のトリガーを削除
    var triggers = ScriptApp.getProjectTriggers();
    for (var i = 0; i < triggers.length; i++) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
    Logger.log('既存トリガーを削除しました');
    
    // 1. フォーム送信トリガー
    ScriptApp.newTrigger('onFormSubmit')
      .forSpreadsheet(SpreadsheetApp.getActive())
      .onFormSubmit()
      .create();
    Logger.log('✅ フォーム送信トリガーを作成しました');
    
    // 2. セル編集トリガー
    ScriptApp.newTrigger('onEdit')
      .forSpreadsheet(SpreadsheetApp.getActive())
      .onEdit()
      .create();
    Logger.log('✅ セル編集トリガーを作成しました');
    
    Logger.log('=== トリガーセットアップ完了 ===');
    
  } catch (error) {
    Logger.log('❌ エラー: ' + error.toString());
  }
}

// ========================================
// 5. テスト用関数
// ========================================

function testAutoApproval() {
  Logger.log('=== 自動承認テスト開始 ===');
  
  // テストデータでqa_itemsへの追加をテスト
  addToQAItems(
    'テスト質問（自動追加）',
    'テスト回答です',
    'テスト',
    'テスト,自動化'
  );
  
  Logger.log('=== テスト完了 ===');
}

function testSheetAccess() {
  Logger.log('=== シートアクセステスト ===');
  
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  Logger.log('スプレッドシート名: ' + ss.getName());
  
  var sheets = ['qa_items', 'qa_form_log', 'フォームの回答 1'];
  
  for (var i = 0; i < sheets.length; i++) {
    var sheet = ss.getSheetByName(sheets[i]);
    if (sheet) {
      Logger.log('✅ ' + sheets[i] + ' が見つかりました（行数: ' + sheet.getLastRow() + '）');
    } else {
      Logger.log('❌ ' + sheets[i] + ' が見つかりません');
    }
  }
  
  Logger.log('=== テスト完了 ===');
}
```

---

## 🔧 セットアップ手順

### 1. スクリプトを貼り付け

1. スプレッドシートを開く
2. 「拡張機能」→「Apps Script」
3. 既存のコードを削除
4. 上記のスクリプトを貼り付け
5. 「保存」をクリック

### 2. テスト実行

#### テスト1: シートアクセス確認

1. 関数選択で **`testSheetAccess`** を選択
2. 「実行」ボタンをクリック
3. ログで以下が表示されることを確認：
   ```
   ✅ qa_items が見つかりました
   ✅ qa_form_log が見つかりました
   ✅ フォームの回答 1 が見つかりました
   ```

#### テスト2: 自動追加テスト

1. 関数選択で **`testAutoApproval`** を選択
2. 「実行」ボタンをクリック
3. `qa_items`シートに「テスト質問（自動追加）」が追加されたことを確認

### 3. トリガーのセットアップ

1. 関数選択で **`setupTriggers`** を選択
2. 「実行」ボタンをクリック
3. 権限確認画面が表示されたら許可
4. ログで以下が表示されることを確認：
   ```
   ✅ フォーム送信トリガーを作成しました
   ✅ セル編集トリガーを作成しました
   ```

### 4. トリガー確認

1. 左メニューの「トリガー」アイコン（⏰）をクリック
2. 以下の2つのトリガーが表示されていることを確認：
   - `onFormSubmit` - フォーム送信時
   - `onEdit` - 編集時

---

## 🎬 使い方

### ステップ1: フォームから投稿

1. Googleフォームから質問を投稿
2. → **自動的に** `qa_form_log`シートに追加される
3. → `approved`列は`FALSE`（未承認）

### ステップ2: 承認する

1. `qa_form_log`シートを開く
2. 承認したい行の`approved`列（F列）をクリック
3. `TRUE` と入力（またはチェックボックスにチェック）
4. → **自動的に** `qa_items`シートに追加される！✨

### ステップ3: Botに反映

- 5分待つ（自動リロード）
- または即座に反映：
  ```bash
  curl -X POST https://your-app.railway.app/admin/reload
  ```

---

## 🎉 完全自動化フロー

```
【運用者】
   ↓ Googleフォームから投稿
   
【自動】qa_form_logに記録（approved=FALSE）
   ↓
   
【管理者】approved列をTRUEに変更
   ↓
   
【自動】qa_itemsに追加（ID自動採番・重複チェック）
   ↓
   
【自動】5分後にBotに反映（または/admin/reloadで即時）
   ↓
   
【完了】LINEで質問できるようになる！
```

---

## 🔍 動作確認方法

### 確認1: フォーム送信テスト

1. Googleフォームから投稿
2. `qa_form_log`シートを確認
3. 新しい行が追加されていればOK

### 確認2: 自動承認テスト

1. `qa_form_log`の任意の行の`approved`列を`TRUE`に変更
2. `qa_items`シートを確認
3. 新しい行が自動追加されていればOK
4. IDが自動採番されているか確認

### 確認3: 重複チェックテスト

1. 同じ行の`approved`列を`FALSE`→`TRUE`に再度変更
2. `qa_items`シートに重複して追加されないことを確認
3. 実行ログに「同じ質問が既に存在します」と表示されればOK

---

## 📊 列の調整

フォームの質問順序が異なる場合、以下の部分を調整してください：

```javascript
// データの割り当て（列番号は実際のフォームに合わせて調整）
var question = data[1] || '';    // 質問内容の列（0始まり）
var answer = data[2] || '';      // 回答内容の列
var category = data[3] || '';    // カテゴリの列
var keywords = data[4] || '';    // キーワードの列
var notes = data[5] || '';       // 備考の列
```

**確認方法:**
1. 「フォームの回答 1」シートのヘッダー行を確認
2. 各項目が何列目にあるか数える（1列目=タイムスタンプ=0, 2列目=1...）
3. スクリプトの数字を調整

---

## ⚠️ 注意事項

### approved列の形式

以下のいずれかで動作します：
- `TRUE`（大文字）
- `true`（小文字）
- チェックボックス（TRUE値）

### IDの採番

- 既存のqa_itemsシートの最大ID + 1
- 例: 最大IDが105 → 次は106

### 重複チェック

- 同じ質問文が既にqa_itemsに存在する場合は追加しない
- 大文字・小文字は区別される

---

## 🔧 トラブルシューティング

### 自動追加されない

1. トリガーが設定されているか確認
2. 実行ログでエラーを確認
3. `approved`列が正確に`TRUE`になっているか確認

### IDが重複する

- スクリプトの`addToQAItems`関数でID採番ロジックを確認
- 手動で追加したIDと競合していないか確認

### 権限エラー

- `setupTriggers`関数を再実行
- Googleアカウントで権限を許可

---

## 🎉 完成！

これで完全自動化が完了しました！

- ✅ フォーム送信 → 自動記録
- ✅ 承認（TRUE） → 自動追加
- ✅ ID自動採番
- ✅ 重複防止
- ✅ Bot自動反映

**運用者は、承認したい行の`approved`列を`TRUE`にするだけ！**

