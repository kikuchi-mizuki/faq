function onFormSubmit(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var logSheet = ss.getSheetByName("qa_form_log");

    if (!logSheet) {
      logSheet = ss.insertSheet("qa_form_log");
      logSheet.appendRow(["timestamp", "question", "answer", "category", "keywords", "approved", "created_by", "notes"]);
    }

    var formSheet = ss.getSheetByName("フォームの回答 3");
    if (!formSheet) return;

    var lastRow = formSheet.getLastRow();
    var data = formSheet.getRange(lastRow, 1, 1, formSheet.getLastColumn()).getValues()[0];

    var question = data[2] || "";
    var answer = data[3] || "";
    var category = data[4] || "その他";
    var keywords = data[5] || "";
    var notes = data[6] || "";

    logSheet.appendRow([new Date(), question, answer, category, keywords, "AUTO", data[1] || "manual", notes]);

    addToQAItems(question, answer, category, keywords);

  } catch (error) {
    Logger.log("エラー: " + error);
  }
}

function addToQAItems(question, answer, category, keywords) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var qaSheet = ss.getSheetByName("qa_items");
  if (!qaSheet) return;

  var lastRow = qaSheet.getLastRow();
  var nextId = 1;

  if (lastRow > 1) {
    var ids = qaSheet.getRange(2, 3, lastRow - 1, 1).getValues();
    var maxId = 0;
    for (var i = 0; i < ids.length; i++) {
      var v = Number(ids[i][0]);
      if (!isNaN(v) && v > maxId) maxId = v;
    }
    nextId = maxId + 1;
  }

  qaSheet.appendRow(["", category, nextId, question, answer, keywords, "", category, 1, "active", new Date()]);
}

function setupTriggers() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }

  ScriptApp.newTrigger("onFormSubmit").forSpreadsheet(SpreadsheetApp.getActive()).onFormSubmit().create();

  Logger.log("トリガー設定完了");
}
