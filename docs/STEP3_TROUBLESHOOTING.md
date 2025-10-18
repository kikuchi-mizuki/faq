# STEP3 トラブルシューティング

## 🚨 問題: Googleフォームの送信内容がスプレッドシートに反映されない

---

## ステップ1: 基本設定の確認

### 1-1: フォームの回答先を確認

1. Googleフォームを開く
2. 上部の「回答」タブをクリック
3. 右上の「スプレッドシートで表示」アイコン（緑色）をクリック
4. スプレッドシートが開くか確認

**問題がある場合:**
- 「回答先を選択」でスプレッドシートを再設定

### 1-2: 回答が記録されているか確認

1. スプレッドシートを開く
2. 「フォームの回答 1」というシートを探す
3. テストで送信したデータが記録されているか確認

**✅ ここまで確認できれば、フォーム→スプレッドシートの基本連携はOKです**

---

## ステップ2: Google Apps Scriptの設定

### 2-1: スクリプトエディタを開く

1. Q&Aスプレッドシートを開く
2. メニューバー → 「拡張機能」 → 「Apps Script」

### 2-2: スクリプトが存在するか確認

左側のファイル一覧に `コード.gs` があることを確認

**ない場合:**
- 新規作成して、下記のコードを貼り付け

### 2-3: 簡易版スクリプト（推奨）

**問題:** 複雑なスクリプトは動作しない場合があります。

**解決策:** よりシンプルなスクリプトを使用します：

```javascript
/**
 * フォーム送信時に実行される関数（簡易版）
 */
function onFormSubmit(e) {
  try {
    Logger.log('=== フォーム送信イベント開始 ===');
    
    // スプレッドシートを取得
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    Logger.log('スプレッドシート取得完了: ' + ss.getName());
    
    // qa_form_logシートを取得（なければ作成）
    var logSheet = ss.getSheetByName('qa_form_log');
    if (!logSheet) {
      Logger.log('qa_form_logシートが見つからないため、新規作成します');
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
      Logger.log('ヘッダー行を追加しました');
    }
    
    // フォーム回答を取得
    var timestamp = new Date();
    var email = e.response.getRespondentEmail() || '匿名';
    Logger.log('メールアドレス: ' + email);
    
    // 「フォームの回答 1」シートから最新の回答を取得
    var formSheet = ss.getSheetByName('フォームの回答 1');
    if (!formSheet) {
      Logger.log('エラー: フォームの回答シートが見つかりません');
      return;
    }
    
    // 最後の行を取得（最新の回答）
    var lastRow = formSheet.getLastRow();
    var data = formSheet.getRange(lastRow, 1, 1, formSheet.getLastColumn()).getValues()[0];
    
    Logger.log('取得したデータ: ' + data);
    
    // データの割り当て（フォームの列順に合わせて調整してください）
    var question = data[1] || '';  // 2列目: 質問内容
    var answer = data[2] || '';    // 3列目: 回答内容
    var category = data[3] || 'その他';  // 4列目: カテゴリ
    var keywords = data[4] || '';  // 5列目: キーワード
    var notes = data[5] || '';     // 6列目: 備考
    
    // qa_form_logシートに追加
    logSheet.appendRow([
      timestamp,
      question,
      answer,
      category,
      keywords,
      'FALSE',  // approved
      email,
      notes
    ]);
    
    Logger.log('✅ qa_form_logシートに追加完了');
    
  } catch (error) {
    Logger.log('❌ エラー: ' + error.toString());
    Logger.log('スタックトレース: ' + error.stack);
  }
}

/**
 * トリガーのセットアップ（初回のみ実行）
 */
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
    
    // 新しいトリガーを作成
    ScriptApp.newTrigger('onFormSubmit')
      .forSpreadsheet(SpreadsheetApp.getActive())
      .onFormSubmit()
      .create();
    
    Logger.log('✅ トリガーをセットアップしました');
    
  } catch (error) {
    Logger.log('❌ エラー: ' + error.toString());
  }
}

/**
 * テスト用関数（手動実行して動作確認）
 */
function testScript() {
  Logger.log('=== テスト実行開始 ===');
  
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  Logger.log('スプレッドシート名: ' + ss.getName());
  
  var logSheet = ss.getSheetByName('qa_form_log');
  if (logSheet) {
    Logger.log('✅ qa_form_logシートが見つかりました');
  } else {
    Logger.log('❌ qa_form_logシートが見つかりません');
  }
  
  var formSheet = ss.getSheetByName('フォームの回答 1');
  if (formSheet) {
    Logger.log('✅ フォームの回答シートが見つかりました');
    Logger.log('最終行: ' + formSheet.getLastRow());
  } else {
    Logger.log('❌ フォームの回答シートが見つかりません');
  }
  
  Logger.log('=== テスト実行完了 ===');
}
```

---

## ステップ3: スクリプトの実行と設定

### 3-1: テスト実行

1. スクリプトエディタで上記コードをコピー＆ペースト
2. 「保存」ボタンをクリック（💾）
3. 関数選択ドロップダウンから **`testScript`** を選択
4. 「実行」ボタン（▶️）をクリック
5. 実行ログを確認：
   ```
   ✅ qa_form_logシートが見つかりました
   ✅ フォームの回答シートが見つかりました
   ```

### 3-2: トリガーのセットアップ

1. 関数選択ドロップダウンから **`setupTrigger`** を選択
2. 「実行」ボタン（▶️）をクリック
3. 権限確認が表示されたら：
   - 「権限を確認」をクリック
   - アカウントを選択
   - 「詳細」をクリック
   - 「（プロジェクト名）に移動」をクリック
   - 「許可」をクリック
4. 実行ログに「✅ トリガーをセットアップしました」と表示されればOK

### 3-3: トリガーが設定されているか確認

1. スクリプトエディタの左メニュー → 「トリガー」アイコン（⏰）をクリック
2. 以下のトリガーが表示されていることを確認：
   - **関数**: `onFormSubmit`
   - **イベント**: `フォーム送信時`
   - **障害通知**: あなたのメールアドレス

**トリガーがない場合:**
- `setupTrigger`関数を再実行

---

## ステップ4: 動作テスト

### 4-1: フォームから送信

1. Googleフォームを開く
2. テストデータを入力：
   ```
   質問: テスト質問123
   回答: テスト回答ABC
   カテゴリ: IT
   キーワード: テスト
   備考: 動作確認
   ```
3. 「送信」をクリック

### 4-2: スプレッドシートを確認

1. Q&Aスプレッドシートを開く
2. **「フォームの回答 1」シート**を確認
   - → 回答が記録されているか確認（タイムスタンプ、質問、回答など）
3. **「qa_form_log」シート**を確認
   - → 同じ内容が転記されているか確認

### 4-3: 実行ログを確認

フォーム送信後、スクリプトが実行されたか確認：

1. スクリプトエディタを開く
2. 左メニュー → 「実行数」をクリック
3. 最新の実行ログを確認：
   - **ステータス**: 完了（✅）
   - **関数**: `onFormSubmit`

**エラーがある場合:**
- 実行ログをクリックして詳細を確認
- エラーメッセージをもとに修正

---

## よくある問題と解決策

### 問題1: 「フォームの回答 1」シートに記録されない

**原因:** フォームとスプレッドシートが連携されていない

**解決策:**
1. Googleフォームを開く
2. 「回答」タブ → 「︙」（3点メニュー）→ 「回答先を選択」
3. 「既存のスプレッドシート」を選択
4. Q&Aスプレッドシートを選択

### 問題2: qa_form_logシートに転記されない

**原因:** トリガーが設定されていない、またはスクリプトにエラー

**解決策:**
1. `setupTrigger`関数を実行
2. トリガー一覧で設定を確認
3. テスト送信後、「実行数」でエラーログを確認

### 問題3: 列の位置がずれる

**原因:** フォームの質問順序とスクリプトの列番号が一致していない

**解決策:**
スクリプトの以下の部分を修正：

```javascript
// データの割り当て（フォームの列順に合わせて調整）
var question = data[1] || '';  // 質問内容の列番号
var answer = data[2] || '';    // 回答内容の列番号
var category = data[3] || '';  // カテゴリの列番号
```

**確認方法:**
1. 「フォームの回答 1」シートを開く
2. ヘッダー行を確認して、各項目が何列目にあるか確認
3. スクリプトの列番号を調整（0始まり）

### 問題4: 権限エラー

**原因:** スクリプトがスプレッドシートにアクセスする権限がない

**解決策:**
1. `setupTrigger`関数を再実行
2. 権限確認画面で「許可」をクリック
3. 必要に応じてGoogleアカウントの設定を確認

---

## 手動での転記方法（暫定対応）

スクリプトがどうしても動作しない場合、手動で転記も可能です：

1. 「フォームの回答 1」シートから回答をコピー
2. 「qa_form_log」シートの新しい行に貼り付け
3. 以下の項目を調整：
   - timestamp: 現在の日時
   - approved: FALSE
   - created_by: 投稿者のメールアドレス

---

## デバッグ用のログ確認方法

### スクリプトのログを確認

1. Apps Scriptエディタを開く
2. 関数選択で `onFormSubmit` を選択
3. 左メニュー → 「実行数」をクリック
4. 最新の実行をクリック
5. ログメッセージを確認：
   ```
   === フォーム送信イベント開始 ===
   スプレッドシート取得完了: Q&Aシート
   メールアドレス: user@example.com
   取得したデータ: ...
   ✅ qa_form_logシートに追加完了
   ```

### エラーログの例

```
❌ エラー: Cannot read property 'getRespondentEmail' of undefined
```

→ イベントオブジェクトが取得できていない（トリガー設定の問題）

---

## サポートが必要な場合

以下の情報を確認してください：

1. **トリガー一覧のスクリーンショット**
2. **実行ログのエラーメッセージ**
3. **「フォームの回答 1」シートのヘッダー行**
4. **qa_form_logシートの状態**

これらの情報があれば、より具体的なサポートが可能です。

