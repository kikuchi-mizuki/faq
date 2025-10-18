# STEP3: 最終版Google Apps Script

## 📋 完全動作版スクリプト

以下のスクリプトをGoogle Apps Scriptに**丸ごと置き換え**してください：

```javascript
/**
 * STEP3 完全動作版（フォーム→ログ→承認でqa_items自動追加）
 * シート前提:
 * - qa_form_log: [timestamp, question, answer, category, keywords, approved, created_by, notes]
 * - qa_items    : [id, question, keywords, synonyms, tags, answer, priority, status, updated_at]
 */

/* ========== 1) フォーム送信時: qa_form_log に追記 ========== */
function onFormSubmit(e) {
  try {
    Logger.log('=== フォーム送信イベント開始 ===');
    
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var logSheet = ss.getSheetByName('qa_form_log');
    
    // qa_form_logシートがなければ作成
    if (!logSheet) {
      logSheet = ss.insertSheet('qa_form_log');
      logSheet.appendRow([
        'timestamp','question','answer','category','keywords','approved','created_by','notes'
      ]);
      Logger.log('qa_form_logシートを作成しました');
    }
    
    // フォーム回答を取得
    var timestamp = new Date();
    var email = e.response ? e.response.getRespondentEmail() || '匿名' : 'manual-run';
    
    // 「フォームの回答 1」シートから最新の回答を取得
    var formSheet = ss.getSheetByName('フォームの回答 1');
    if (!formSheet) {
      Logger.log('エラー: フォームの回答シートが見つかりません');
      return;
    }
    
    var lastRow = formSheet.getLastRow();
    var lastCol = formSheet.getLastColumn();
    
    // 見出し行を取得
    var header = formSheet.getRange(1, 1, 1, lastCol).getValues()[0];
    var row = formSheet.getRange(lastRow, 1, 1, lastCol).getValues()[0];
    
    // 見出し名に部分一致する列を探すヘルパー
    function colIdxContains(keyword) {
      for (var i = 0; i < header.length; i++) {
        if (header[i] && header[i].toString().indexOf(keyword) !== -1) return i;
      }
      return -1;
    }
    
    // 必要列のインデックス（存在しなくても動くように）
    var idxQuestion  = colIdxContains('質問');      // 例: 「質問内容」
    var idxAnswer    = colIdxContains('回答');      // 例: 「回答内容」
    var idxCategory  = colIdxContains('カテゴリ');
    var idxKeywords  = colIdxContains('キーワード');
    var idxNotes     = colIdxContains('備考');
    
    // 値の取り出し（なければ既定値）
    var question = idxQuestion >= 0 ? (row[idxQuestion] || '') : '';
    var answer   = idxAnswer   >= 0 ? (row[idxAnswer]   || '') : '';
    var category = idxCategory >= 0 ? (row[idxCategory] || 'その他') : 'その他';
    var keywords = idxKeywords >= 0 ? (row[idxKeywords] || '') : '';
    var notes    = idxNotes    >= 0 ? (row[idxNotes]    || '') : '';
    
    Logger.log('取得データ: 質問=' + question + ', 回答=' + answer + ', カテゴリ=' + category);
    
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
    Logger.log('スタック: ' + error.stack);
  }
}

/* ========== 2) セル編集時: approved=TRUE になった行を qa_items に追加 ========== */
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
    Logger.log('スタック: ' + error.stack);
  }
}

/* ========== 3) qa_items へ追記（列順: id, question, keywords, synonyms, tags, answer, priority, status, updated_at） ========== */
function addToQAItems(question, answer, category, keywords) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var qaSheet = ss.getSheetByName('qa_items');

  if (!qaSheet) {
    Logger.log('エラー: qa_itemsシートが見つかりません');
    return;
  }

  // 重複チェック（B列: question）
  var lastRow = qaSheet.getLastRow();
  if (lastRow > 1) {
    var existingQuestions = qaSheet.getRange(2, 2, lastRow - 1, 1).getValues();
    for (var i = 0; i < existingQuestions.length; i++) {
      if ((existingQuestions[i][0] || '').toString().trim() === (question || '').toString().trim()) {
        Logger.log('⚠️ 重複につきスキップ: ' + question);
        return;
      }
    }
  }

  // 次のIDを採番（A列: id の最大+1）
  var nextId = 1;
  if (lastRow > 1) {
    var ids = qaSheet.getRange(2, 1, lastRow - 1, 1).getValues();
    var maxId = 0;
    for (var j = 0; j < ids.length; j++) {
      var v = Number(ids[j][0]);
      if (!isNaN(v) && v > maxId) maxId = v;
    }
    nextId = maxId + 1;
  }

  // 追記（synonymsは空、priority=1、status=inactive）
  qaSheet.appendRow([
    nextId,           // A: id
    question,         // B: question
    keywords,         // C: keywords
    '',               // D: synonyms
    category,         // E: tags（カテゴリをタグとして使用）
    answer,           // F: answer
    1,                // G: priority
    'inactive',       // H: status
    new Date()        // I: updated_at
  ]);

  Logger.log('✅ qa_itemsに追加しました（ID: ' + nextId + '）');
}

/* ========== 4) トリガー一括設定 ========== */
function setupTriggers() {
  try {
    Logger.log('=== トリガーセットアップ開始 ===');
    var triggers = ScriptApp.getProjectTriggers();
    for (var i = 0; i < triggers.length; i++) ScriptApp.deleteTrigger(triggers[i]);

    ScriptApp.newTrigger('onFormSubmit')
      .forSpreadsheet(SpreadsheetApp.getActive())
      .onFormSubmit()
      .create();

    ScriptApp.newTrigger('onEdit')
      .forSpreadsheet(SpreadsheetApp.getActive())
      .onEdit()
      .create();

    Logger.log('✅ トリガー作成: onFormSubmit, onEdit');
  } catch (error) {
    Logger.log('❌ setupTriggers エラー: ' + error);
  }
}

/* ========== 5) 手動テスト用（任意） ========== */
function testDirectAdd() {
  addToQAItems('テスト質問（直接追加）', 'テスト回答です', 'テスト', 'テスト,直接追加');
  Logger.log('🧪 testDirectAdd 完了');
}

function testFormSubmit() {
  Logger.log('=== 手動実行テスト開始 ===');
  
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    Logger.log('スプレッドシート取得完了: ' + ss.getName());
    
    var logSheet = ss.getSheetByName('qa_form_log');
    if (!logSheet) {
      logSheet = ss.insertSheet('qa_form_log');
      logSheet.appendRow([
        'timestamp', 'question', 'answer', 'category', 
        'keywords', 'approved', 'created_by', 'notes'
      ]);
      Logger.log('qa_form_logシートを作成しました');
    }
    Logger.log('qa_form_logシート取得完了');
    
    var formSheet = ss.getSheetByName('フォームの回答 1');
    if (!formSheet) {
      Logger.log('❌ フォームの回答 1シートが見つかりません');
      return;
    }
    Logger.log('フォーム回答シート取得完了');
    
    var lastRow = formSheet.getLastRow();
    var lastCol = formSheet.getLastColumn();
    Logger.log('最終行: ' + lastRow + ', 最終列: ' + lastCol);
    
    if (lastRow < 2) {
      Logger.log('❌ フォーム回答データがありません（見出し行のみ）');
      return;
    }
    
    // 見出し行を取得
    var header = formSheet.getRange(1, 1, 1, lastCol).getValues()[0];
    Logger.log('見出し: ' + JSON.stringify(header));
    
    var row = formSheet.getRange(lastRow, 1, 1, lastCol).getValues()[0];
    Logger.log('最新行データ: ' + JSON.stringify(row));
    
    // 見出し名に部分一致する列を探すヘルパ
    function colIdxContains(keyword) {
      for (var i = 0; i < header.length; i++) {
        if (header[i] && header[i].toString().indexOf(keyword) !== -1) return i;
      }
      return -1;
    }

    // 必要列のインデックス（存在しなくても動くように）
    var idxQuestion  = colIdxContains('質問');      // 例: 「質問内容」
    var idxAnswer    = colIdxContains('回答');      // 例: 「回答内容」
    var idxCategory  = colIdxContains('カテゴリ');
    var idxKeywords  = colIdxContains('キーワード');
    var idxNotes     = colIdxContains('備考');
    var idxEmail     = colIdxContains('メール');     // 収集メールがある場合

    Logger.log('列インデックス: 質問=' + idxQuestion + ', 回答=' + idxAnswer + ', カテゴリ=' + idxCategory);

    // 値の取り出し（なければ既定値）
    var question = idxQuestion >= 0 ? (row[idxQuestion] || '') : '';
    var answer   = idxAnswer   >= 0 ? (row[idxAnswer]   || '') : '';
    var category = idxCategory >= 0 ? (row[idxCategory] || 'その他') : 'その他';
    var keywords = idxKeywords >= 0 ? (row[idxKeywords] || '') : '';
    var notes    = idxNotes    >= 0 ? (row[idxNotes]    || '') : '';
    var email    = idxEmail    >= 0 ? (row[idxEmail]    || 'manual-run') : 'manual-run';
    
    Logger.log('取得データ:');
    Logger.log('質問: ' + question);
    Logger.log('回答: ' + answer);
    Logger.log('カテゴリ: ' + category);
    Logger.log('キーワード: ' + keywords);
    Logger.log('備考: ' + notes);
    Logger.log('メール: ' + email);
    
    // データが空でないかチェック
    if (!question && !answer) {
      Logger.log('❌ 質問と回答の両方が空です');
      return;
    }
    
    // qa_form_logに追加
    logSheet.appendRow([
      new Date(),  // timestamp
      question,    // question
      answer,      // answer
      category,    // category
      keywords,    // keywords
      'FALSE',     // approved（デフォルトは未承認）
      email,       // created_by
      notes        // notes
    ]);
    
    Logger.log('✅ qa_form_logに追加しました');
    Logger.log('=== 手動実行テスト完了 ===');
    
  } catch (error) {
    Logger.log('❌ エラー: ' + error.toString());
    Logger.log('スタック: ' + error.stack);
  }
}
```

## 🔧 セットアップ手順

### 1. スクリプトを貼り付け
1. スプレッドシートを開く
2. 「拡張機能」→「Apps Script」
3. 既存のコードを削除
4. 上記のスクリプトを貼り付け
5. 「保存」をクリック

### 2. テスト実行
1. 関数選択で **`testFormSubmit`** を選択
2. 「実行」ボタンをクリック
3. ログで以下が表示されることを確認：
   ```
   ✅ qa_form_logに追加しました
   ```

### 3. トリガーのセットアップ
1. 関数選択で **`setupTriggers`** を選択
2. 「実行」ボタンをクリック
3. 権限確認画面が表示されたら許可
4. ログで以下が表示されることを確認：
   ```
   ✅ トリガー作成: onFormSubmit, onEdit
   ```

### 4. トリガー確認
1. 左メニューの「トリガー」アイコン（⏰）をクリック
2. 以下の2つのトリガーが表示されていることを確認：
   - `onFormSubmit` - フォーム送信時
   - `onEdit` - 編集時

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
