#!/bin/bash
# ファイルをRAGにアップロードするスクリプト

# 使い方
if [ $# -lt 1 ]; then
  echo "使い方: $0 <ファイルパス> [タイトル]"
  echo ""
  echo "例:"
  echo "  $0 manual.pdf"
  echo "  $0 document.xlsx '製品マニュアル'"
  echo "  $0 notes.txt"
  echo ""
  echo "対応ファイル形式: PDF, Excel (.xlsx, .xls), テキスト (.txt)"
  exit 1
fi

FILE_PATH="$1"
TITLE="${2:-$(basename "$FILE_PATH")}"

# ファイルの存在確認
if [ ! -f "$FILE_PATH" ]; then
  echo "エラー: ファイルが見つかりません: $FILE_PATH"
  exit 1
fi

# Railway設定
RAILWAY_APP_URL="${RAILWAY_APP_URL:-https://line-qa-system-production.up.railway.app}"
ADMIN_API_KEY="${ADMIN_API_KEY:-admin-faq-2025-xK9mP2qL}"

echo "📤 ファイルをアップロードしています..."
echo "ファイル: $FILE_PATH"
echo "タイトル: $TITLE"
echo "URL: $RAILWAY_APP_URL/admin/upload-document"
echo ""

# アップロード実行
RESPONSE=$(curl -X POST "$RAILWAY_APP_URL/admin/upload-document" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -F "file=@$FILE_PATH" \
  -F "title=$TITLE" \
  -w "\n%{http_code}" \
  -s)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ アップロード成功!"
  echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
  echo "❌ アップロード失敗"
  echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
  exit 1
fi
