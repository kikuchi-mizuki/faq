#!/bin/bash
# Google Driveから文書を手動収集するスクリプト

# 使い方:
# 1. RAILWAY_DOMAINをあなたのRailwayドメインに置き換えてください
#    例: https://faq-production.up.railway.app
# 2. このスクリプトを実行: bash collect_documents.sh

# RailwayドメインとAPIキーを設定
RAILWAY_DOMAIN="https://line-qa-system-production.up.railway.app"
ADMIN_API_KEY="admin-faq-2025-xK9mP2qL"

# 色付き出力用
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================"
echo "📚 Google Drive 文書収集"
echo "========================================"
echo ""
echo "📍 ドメイン: $RAILWAY_DOMAIN"
echo "🔑 APIキー: ${ADMIN_API_KEY:0:20}..."
echo ""
echo "🚀 文書収集を開始します..."
echo ""

# 文書収集APIを呼び出し
response=$(curl -X POST "$RAILWAY_DOMAIN/admin/collect-documents" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -w "\n%{http_code}" \
  -s)

# HTTPステータスコードを取得
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

echo "HTTP Status: $http_code"
echo "Response:"
echo "$body" | jq '.' 2>/dev/null || echo "$body"
echo ""

# 結果を判定
if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ 文書収集が完了しました！${NC}"
    echo ""
    echo "次のステップ:"
    echo "1. Railwayのログで収集結果を確認"
    echo "2. LINEで質問を送信して動作確認"
elif [ "$http_code" = "401" ]; then
    echo -e "${RED}❌ 認証エラー: APIキーが正しくありません${NC}"
    echo "ADMIN_API_KEYを確認してください"
elif [ "$http_code" = "404" ]; then
    echo -e "${RED}❌ エンドポイントが見つかりません${NC}"
    echo "RAILWAY_DOMAINを確認してください"
else
    echo -e "${YELLOW}⚠️ エラーが発生しました (HTTP $http_code)${NC}"
fi

echo ""
echo "========================================"
