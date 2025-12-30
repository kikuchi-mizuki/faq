/**
 * STEP3 完全自動版（フォーム投稿→即座にqa_itemsに追加）
 * 承認プロセスなし、フォーム送信後すぐにactiveで追加
 */

/* フォーム送信時: qa_form_log に追記 & 自動的にqa_itemsに追加 */
function onFormSubmit(e) {
  try {
    Logger.log('=== フォーム送信イベント開始 ===');

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var logSheet = ss.getSheetByName('qa_form_log');

    if (!logSheet) {
      logSheet = ss.insertSheet('qa_form_log');
      logSheet.appendRow([
        'timestamp','question','answer','category','keywords','approved','created_by','notes'
      ]);
      Logger.log('qa_form_logシートを作成しました');
    }

    var timestamp = new Date();
    var email = e.response ? e.response.getRespondentEmail() || 'anonymous' : 'manual-run';

    var formSheet = ss.getSheetByName('フォームの回答 3');
    if (!formSheet) {
      Logger.log('エラー: フォームの回答シートが見つかりません');
      return;
    }

    var lastRow = formSheet.getLastRow();
    var lastCol = formSheet.getLastColumn();

    var header = formSheet.getRange(1, 1, 1, lastCol).getValues()[0];
    var row = formSheet.getRange(lastRow, 1, 1, lastCol).getValues()[0];

    function colIdxContains(keyword) {
      for (var i = 0; i < header.length; i++) {
        if (header[i] && header[i].toString().indexOf(keyword) !== -1) return i;
      }
      return -1;
    }

    var idxQuestion  = colIdxContains('質問');
    var idxAnswer    = colIdxContains('回答');
    var idxCategory  = colIdxContains('カテゴリ');
    var idxKeywords  = colIdxContains('キーワード');
    var idxNotes     = colIdxContains('備考');

    var question = idxQuestion >= 0 ? (row[idxQuestion] || '') : '';
    var answer   = idxAnswer   >= 0 ? (row[idxAnswer]   || '') : '';
    var category = idxCategory >= 0 ? (row[idxCategory] || 'その他') : 'その他';
    var keywords = idxKeywords >= 0 ? (row[idxKeywords] || '') : '';
    var notes    = idxNotes    >= 0 ? (row[idxNotes]    || '') : '';

    Logger.log('取得データ: 質問=' + question + ', 回答=' + answer);

    // qa_form_logに追加
    logSheet.appendRow([
      timestamp,
      question,
      answer,
      category,
      keywords,
      'AUTO',  // 自動追加済みのマーク
      email,
      notes + '\n[自動追加済み: ' + new Date().toLocaleString('ja-JP') + ']'
    ]);

    Logger.log('qa_form_logに追加しました: ' + question);

    // 即座にqa_itemsに追加（active状態で）
    addToQAItems(question, answer, category, keywords, true);
    Logger.log('qa_itemsに自動追加しました');

  } catch (error) {
    Logger.log('エラー: ' + error.toString());
  }
}

/* セル編集時: approved=TRUE になった行を qa_items に追加（手動承認用、残しておく） */
function onEdit(e) {
  try {
    var sheet = e.source.getActiveSheet();
    var range = e.range;

    if (sheet.getName() !== 'qa_form_log') {
      return;
    }

    var approvedColumn = 6;
    if (range.getColumn() !== approvedColumn) {
      return;
    }

    var newValue = range.getValue();
    if (newValue !== true && newValue !== 'TRUE' && newValue !== 'true') {
      return;
    }

    Logger.log('=== approved列がTRUEに変更されました ===');

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

    // すでに自動追加されている場合はスキップ
    if (approved === 'AUTO') {
      Logger.log('すでに自動追加済みです');
      return;
    }

    Logger.log('承認された質問: ' + question);

    addToQAItems(question, answer, category, keywords, false);

    var currentNotes = notes || '';
    var newNotes = currentNotes + '\n[手動承認済み: ' + new Date().toLocaleString('ja-JP') + ']';
    sheet.getRange(row, 8).setValue(newNotes);

    Logger.log('qa_itemsシートに追加しました');

  } catch (error) {
    Logger.log('エラー: ' + error.toString());
  }
}

/* qa_items へ追記（実際のシート構成に対応） */
function addToQAItems(question, answer, category, keywords, isActive) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var qaSheet = ss.getSheetByName('qa_items');

  if (!qaSheet) {
    Logger.log('エラー: qa_itemsシートが見つかりません');
    return;
  }

  var lastRow = qaSheet.getLastRow();

  // 重複チェック（D列: question）
  if (lastRow > 1) {
    var existingQuestions = qaSheet.getRange(2, 4, lastRow - 1, 1).getValues();
    for (var i = 0; i < existingQuestions.length; i++) {
      if ((existingQuestions[i][0] || '').toString().trim() === (question || '').toString().trim()) {
        Logger.log('重複につきスキップ: ' + question);
        return;
      }
    }
  }

  // 次のIDを採番（C列: id の最大+1）
  var nextId = 1;
  if (lastRow > 1) {
    var ids = qaSheet.getRange(2, 3, lastRow - 1, 1).getValues();
    var maxId = 0;
    for (var j = 0; j < ids.length; j++) {
      var v = Number(ids[j][0]);
      if (!isNaN(v) && v > maxId) maxId = v;
    }
    nextId = maxId + 1;
  }

  // statusを決定（自動追加の場合はactive、手動承認の場合はinactive）
  var status = isActive ? 'active' : 'inactive';

  // 実際のシート構成に合わせて追加
  // A: row_num, B: qa_category, C: id, D: question, E: answer,
  // F: keywords, G: patterns, H: tags, I: priority, J: status, K: updated_at
  qaSheet.appendRow([
    '',              // A: row_num（空白、自動採番される場合）
    category,        // B: qa_category
    nextId,          // C: id
    question,        // D: question
    answer,          // E: answer
    keywords,        // F: keywords
    '',              // G: patterns
    category,        // H: tags
    1,               // I: priority
    status,          // J: status（activeまたはinactive）
    new Date()       // K: updated_at
  ]);

  Logger.log('qa_itemsに追加しました（ID: ' + nextId + ', status: ' + status + '）');
}

/* トリガー一括設定 */
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

    Logger.log('トリガー作成: onFormSubmit, onEdit');
  } catch (error) {
    Logger.log('setupTriggers エラー: ' + error);
  }
}

/* 手動テスト用 */
function testDirectAdd() {
  addToQAItems('テスト質問（直接追加）', 'テスト回答です', 'テスト', 'テスト,直接追加', true);
  Logger.log('testDirectAdd 完了');
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

    var formSheet = ss.getSheetByName('フォームの回答 3');
    if (!formSheet) {
      Logger.log('フォームの回答 3シートが見つかりません');
      return;
    }
    Logger.log('フォーム回答シート取得完了');

    var lastRow = formSheet.getLastRow();
    var lastCol = formSheet.getLastColumn();
    Logger.log('最終行: ' + lastRow + ', 最終列: ' + lastCol);

    if (lastRow < 2) {
      Logger.log('フォーム回答データがありません（見出し行のみ）');
      return;
    }

    var header = formSheet.getRange(1, 1, 1, lastCol).getValues()[0];
    Logger.log('見出し: ' + JSON.stringify(header));

    var row = formSheet.getRange(lastRow, 1, 1, lastCol).getValues()[0];
    Logger.log('最新行データ: ' + JSON.stringify(row));

    function colIdxContains(keyword) {
      for (var i = 0; i < header.length; i++) {
        if (header[i] && header[i].toString().indexOf(keyword) !== -1) return i;
      }
      return -1;
    }

    var idxQuestion  = colIdxContains('質問');
    var idxAnswer    = colIdxContains('回答');
    var idxCategory  = colIdxContains('カテゴリ');
    var idxKeywords  = colIdxContains('キーワード');
    var idxNotes     = colIdxContains('備考');
    var idxEmail     = colIdxContains('メール');

    Logger.log('列インデックス: 質問=' + idxQuestion + ', 回答=' + idxAnswer);

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

    if (!question && !answer) {
      Logger.log('質問と回答の両方が空です');
      return;
    }

    logSheet.appendRow([
      new Date(),
      question,
      answer,
      category,
      keywords,
      'AUTO',
      email,
      notes + '\n[テスト自動追加: ' + new Date().toLocaleString('ja-JP') + ']'
    ]);

    // 自動的にqa_itemsに追加
    addToQAItems(question, answer, category, keywords, true);

    Logger.log('qa_form_logとqa_itemsに追加しました');
    Logger.log('=== 手動実行テスト完了 ===');

  } catch (error) {
    Logger.log('エラー: ' + error.toString());
  }
}
