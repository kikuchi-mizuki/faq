#!/bin/bash

# RAGステータスチェックスクリプト
# 使い方: ./check_rag_status.sh <YOUR_ADMIN_API_KEY> <YOUR_APP_URL>

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "使い方: $0 <ADMIN_API_KEY> <APP_URL>"
    echo "例: $0 your-secret-key https://your-app.up.railway.app"
    exit 1
fi

ADMIN_API_KEY="$1"
APP_URL="$2"

echo "=== RAGステータスチェック ==="
echo ""

# RAGステータスを取得
echo "📊 RAGサービスの状態:"
curl -s -X GET "${APP_URL}/admin/rag-status" \
  -H "X-API-Key: ${ADMIN_API_KEY}" \
  -H "Content-Type: application/json" | python3 -m json.tool

echo ""
echo ""

# 登録されている文書を確認
echo "📚 登録されている文書:"
curl -s -X GET "${APP_URL}/documents" \
  -H "Content-Type: application/json" | python3 -m json.tool

echo ""
echo "=== チェック完了 ==="
