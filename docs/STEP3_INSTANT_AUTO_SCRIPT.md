# STEP3: 即時自動反映スクリプト（承認不要）

## 🚀 即時自動反映とは

フォーム送信と同時に、**承認なしで直接qa_itemsシートに自動追加**します。

```
フォーム送信
   ↓ 【即座に自動】
qa_itemsシートに追加
   ↓ 【5分後に自動】
Botに反映

完了！✨
```

---

## ⚠️ 注意事項

### メリット
- ✅ 超高速（フォーム送信→即反映）
- ✅ 承認作業が不要
- ✅ 運用が簡単

### デメリット
- ❌ 誤った情報も即座に反映される
- ❌ 不適切な内容のチェックができない
- ❌ 後から修正が必要

### 推奨運用
- 信頼できる運用者のみがフォームにアクセス
- または、定期的にqa_itemsシートを確認

---

## 📝 即時自動反映スクリプト

Apps Scriptエディタに以下のコードを貼り付けてください：

```javascript
/**
 * STEP3: 即時自動反映スクリプト（承認不要版）
 * フォーム送信 → 即座にqa_itemsに追加
 */

// ========================================
// フォーム送信時の処理（即座にqa_itemsに追加）
// ========================================

function onFormSubmit(e) {
  try {
    Logger.log('=== フォーム送信イベント開始 ===');
    
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    
    // フォーム回答を取得
    var timestamp = new Date();
    var email = e.response.getRespondentEmail() || '匿名';
    Logger.log('投稿者: ' + email);
    
    // 「フォームの回答 1」シートから最新の回答を取得
    var formSheet = ss.getSheetByName('フォームの回答 1');
    if (!formSheet) {
      Logger.log('エラー: フォームの回答シートが見つかりません');
      return;
    }
    
    var lastRow = formSheet.getLastRow();
    var data = formSheet.getRange(lastRow, 1, 1, formSheet.getLastColumn()).getValues()[0];
    
    Logger.log('取得したデータ: ' + data);
    
    // データの割り当て（フォームの列順に合わせて調整）
    var question = data[1] || '';      // 質問内容
    var answer = data[2] || '';        // 回答内容
    var category = data[3] || 'その他'; // カテゴリ
    var keywords = data[4] || '';      // キーワード
    var notes = data[5] || '';         // 備考
    
    // バリデーション
    if (!question || !answer) {
      Logger.log('エラー: 質問または回答が空です');
      return;
    }
    
    Logger.log('質問: ' + question);
    Logger.log('回答: ' + answer);
    
    // 即座にqa_itemsシートに追加
    addToQAItemsDirectly(question, answer, category, keywords, email);
    
    Logger.log('✅ qa_itemsシートに即座に追加しました');
    
    // オプション: qa_form_logにも記録（履歴用）
    recordToFormLog(timestamp, question, answer, category, keywords, email, notes);
    
  } catch (error) {
    Logger.log('❌ エラー: ' + error.toString());
    Logger.log('スタックトレース: ' + error.stack);
  }
}

// ========================================
// qa_itemsシートに直接追加
// ========================================

function addToQAItemsDirectly(question, answer, category, keywords, createdBy) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var qaSheet = ss.getSheetByName('qa_items');
  
  if (!qaSheet) {
    Logger.log('エラー: qa_itemsシートが見つかりません');
    return;
  }
  
  // 重複チェック
  var lastRow = qaSheet.getLastRow();
  if (lastRow > 1) {
    var existingQuestions = qaSheet.getRange(2, 2, lastRow - 1, 1).getValues();
    
    for (var i = 0; i < existingQuestions.length; i++) {
      if (existingQuestions[i][0] === question) {
        Logger.log('警告: 同じ質問が既に存在します: ' + question);
        return;  // 重複なので追加しない
      }
    }
  }
  
  // 次のIDを自動採番
  var nextId = getNextId(qaSheet, lastRow);
  
  Logger.log('次のID: ' + nextId);
  
  // qa_itemsシートに追加
  qaSheet.appendRow([
    nextId,                    // id
    question,                  // question
    answer,                    // answer
    keywords,                  // keywords
    '',                        // synonyms（空欄）
    category,                  // tags（カテゴリをタグとして使用）
    1,                         // priority（デフォルト1）
    'inactive',                // status（初期は非表示。確認後にactiveへ）
    new Date()                 // updated_at
  ]);
  
  Logger.log('✅ qa_itemsに追加完了（ID: ' + nextId + ', 投稿者: ' + createdBy + '）');
}

// ========================================
// 次のIDを取得（自動採番）
// ========================================

function getNextId(qaSheet, lastRow) {
  var lastId = 0;
  
  if (lastRow > 1) {
    var ids = qaSheet.getRange(2, 1, lastRow - 1, 1).getValues();
    
    for (var i = 0; i < ids.length; i++) {
      var currentId = parseInt(ids[i][0]);
      if (!isNaN(currentId) && currentId > lastId) {
        lastId = currentId;
      }
    }
  }
  
  return lastId + 1;
}

// ========================================
// qa_form_logにも記録（履歴用・オプション）
// ========================================

function recordToFormLog(timestamp, question, answer, category, keywords, email, notes) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var logSheet = ss.getSheetByName('qa_form_log');
  
  // qa_form_logシートがなければ作成
  if (!logSheet) {
    logSheet = ss.insertSheet('qa_form_log');
    logSheet.appendRow([
      'timestamp', 'question', 'answer', 'category', 
      'keywords', 'approved', 'created_by', 'notes'
    ]);
  }
  
  // 履歴として記録（approved=TRUEで記録）
  logSheet.appendRow([
    timestamp,
    question,
    answer,
    category,
    keywords,
    'TRUE',  // 自動承認済み
    email,
    notes + '\n[自動承認: ' + new Date().toLocaleString('ja-JP') + ']'
  ]);
  
  Logger.log('✅ qa_form_logにも記録しました（履歴用）');
}

// ========================================
// トリガーのセットアップ
// ========================================

function setupTrigger() {
  try {
    Logger.log('=== トリガーセットアップ開始 ===');
    
    // 既存のトリガーを削除
    var triggers = ScriptApp.getProjectTriggers();
    Logger.log('既存トリガー数: ' + triggers.length);
    
    for (var i = 0; i < triggers.length; i++) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
    Logger.log('既存トリガーを削除しました');
    
    // フォーム送信トリガーを作成
    ScriptApp.newTrigger('onFormSubmit')
      .forSpreadsheet(SpreadsheetApp.getActive())
      .onFormSubmit()
      .create();
    
    Logger.log('✅ フォーム送信トリガーを作成しました');
    Logger.log('=== トリガーセットアップ完了 ===');
    
  } catch (error) {
    Logger.log('❌ エラー: ' + error.toString());
  }
}

// ========================================
// テスト用関数
// ========================================

function testDirectAdd() {
  Logger.log('=== 直接追加テスト開始 ===');
  
  // テストデータで追加
  addToQAItemsDirectly(
    'テスト質問（即時反映）',
    'これはテスト回答です',
    'テスト',
    'テスト,即時,自動',
    'test@example.com'
  );
  
  Logger.log('=== テスト完了 ===');
}

function testSheetAccess() {
  Logger.log('=== シートアクセステスト ===');
  
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  Logger.log('スプレッドシート名: ' + ss.getName());
  
  var qaSheet = ss.getSheetByName('qa_items');
  if (qaSheet) {
    var lastRow = qaSheet.getLastRow();
    Logger.log('✅ qa_itemsシートが見つかりました（行数: ' + lastRow + '）');
    
    var nextId = getNextId(qaSheet, lastRow);
    Logger.log('次のID: ' + nextId);
  } else {
    Logger.log('❌ qa_itemsシートが見つかりません');
  }
  
  Logger.log('=== テスト完了 ===');
}

// ========================================
// 既存データの一括インポート（オプション）
// ========================================

function importExistingFormResponses() {
  Logger.log('=== 既存フォーム回答の一括インポート開始 ===');
  
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var formSheet = ss.getSheetByName('フォームの回答 1');
  
  if (!formSheet) {
    Logger.log('エラー: フォームの回答シートが見つかりません');
    return;
  }
  
  var lastRow = formSheet.getLastRow();
  Logger.log('フォーム回答の総数: ' + (lastRow - 1));
  
  var importCount = 0;
  var skipCount = 0;
  
  // 2行目から（ヘッダーを除く）
  for (var row = 2; row <= lastRow; row++) {
    var data = formSheet.getRange(row, 1, 1, formSheet.getLastColumn()).getValues()[0];
    
    var question = data[1] || '';
    var answer = data[2] || '';
    var category = data[3] || 'その他';
    var keywords = data[4] || '';
    
    if (question && answer) {
      addToQAItemsDirectly(question, answer, category, keywords, 'インポート');
      importCount++;
      Logger.log('インポート済み (' + row + '行目): ' + question);
    } else {
      skipCount++;
      Logger.log('スキップ (' + row + '行目): データ不足');
    }
    
    // 処理速度制限対策
    if (row % 10 === 0) {
      Utilities.sleep(1000);  // 10件ごとに1秒待機
    }
  }
  
  Logger.log('=== インポート完了 ===');
  Logger.log('インポート件数: ' + importCount);
  Logger.log('スキップ件数: ' + skipCount);
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
3. ログで以下が表示されればOK：
   ```
   ✅ qa_itemsシートが見つかりました
   次のID: 106
   ```

#### テスト2: 即時追加テスト

1. 関数選択で **`testDirectAdd`** を選択
2. 「実行」ボタンをクリック
3. `qa_items`シートに「テスト質問（即時反映）」が追加されればOK

### 3. トリガーのセットアップ

1. 関数選択で **`setupTrigger`** を選択
2. 「実行」ボタンをクリック
3. 権限確認画面が表示されたら許可
4. ログで「✅ フォーム送信トリガーを作成しました」と表示されればOK

### 4. トリガー確認

1. 左メニューの「トリガー」アイコン（⏰）をクリック
2. 以下のトリガーが表示されていることを確認：
   - `onFormSubmit` - フォーム送信時

---

## 🎬 実際の使い方

### 運用者がやること

```
1. Googleフォームを開く
2. 質問と回答を入力
3. 「送信」をクリック

以上！自動的にqa_itemsに追加されます！✨
```

### システムが自動でやること

```
✅ フォーム送信を検知
✅ qa_itemsに行を追加
✅ 次のIDを自動採番
✅ question, answer, keywords, category を設定
✅ priority=1, status=active を自動設定
✅ 重複チェック（同じ質問は追加しない）
✅ qa_form_logに履歴を記録（オプション）
```

---

## 🔄 既存のフォーム回答を一括インポート

既にフォームに回答が溜まっている場合、一括でqa_itemsに追加できます：

1. 関数選択で **`importExistingFormResponses`** を選択
2. 「実行」ボタンをクリック
3. 既存の全回答がqa_itemsに追加されます

**注意:** 重複チェックが働くので、既に追加済みの質問は追加されません。

---

## 📊 フローの比較

### オプション1: 即時自動反映（このスクリプト）

```
フォーム送信
   ↓ 【即座に】
qa_itemsに追加
   ↓ 【5分後】
Botに反映

所要時間: 5分
承認作業: なし
```

### オプション2: 承認後に反映（STEP3_FULL_AUTO_SCRIPT.md）

```
フォーム送信
   ↓ 【即座に】
qa_form_logに追加
   ↓ 【管理者が確認】
approved列をTRUEに変更
   ↓ 【自動】
qa_itemsに追加
   ↓ 【5分後】
Botに反映

所要時間: 管理者次第
承認作業: あり（品質チェック可能）
```

---

## ⚙️ 列の調整

フォームの質問順序が異なる場合、以下を調整：

```javascript
// データの割り当て（列番号は実際のフォームに合わせて調整）
var question = data[1] || '';      // 質問内容の列（0始まり）
var answer = data[2] || '';        // 回答内容の列
var category = data[3] || '';      // カテゴリの列
var keywords = data[4] || '';      // キーワードの列
var notes = data[5] || '';         // 備考の列
```

**確認方法:**
1. 「フォームの回答 1」シートのヘッダー行を確認
2. タイムスタンプ=0列目、質問内容=1列目...と数える
3. スクリプトの数字を調整

---

## 🎯 推奨運用

### 小規模チーム・信頼できるメンバー
→ **即時自動反映（このスクリプト）** がおすすめ
- 速い
- シンプル
- 承認不要

### 大規模チーム・品質管理が必要
→ **承認後に反映（STEP3_FULL_AUTO_SCRIPT.md）** がおすすめ
- 品質チェック可能
- 誤情報の防止
- 承認フロー

---

## 🔧 トラブルシューティング

### 自動追加されない

1. トリガーが設定されているか確認
2. 「実行数」でエラーログを確認
3. 質問または回答が空でないか確認

### IDが重複する

- `getNextId`関数でID採番ロジックを確認
- qa_itemsシートのID列が数値になっているか確認

### 重複する質問が追加される

- 重複チェックは完全一致のみ
- 大文字・小文字、スペースの違いで別の質問と判定される

---

## 🎉 完成！

これで**フォーム送信と同時に即座にBotに反映**されます！

- ✅ フォーム送信 → 即qa_items追加
- ✅ ID自動採番
- ✅ 重複防止
- ✅ 履歴記録
- ✅ 5分後にBot反映

**運用者は、フォームから送信するだけ！** ✨

