#!/bin/bash

# サポート情報をセクションごとにアップロードするスクリプト

BASE_URL="https://line-qa-system-production.up.railway.app"

echo "🚀 サポート情報のセクション別アップロードを開始します..."
echo ""

# 配送情報
echo "📦 配送情報をアップロード中..."
curl -X POST "$BASE_URL/upload-document" \
  -F "file=@support_delivery.txt" \
  -F "title=配送について（FAQ）" \
  2>&1 | grep -E "status|message" || echo "  ✅ アップロード完了"
echo ""

sleep 2

# 支払い情報
echo "💳 支払い情報をアップロード中..."
curl -X POST "$BASE_URL/upload-document" \
  -F "file=@support_payment.txt" \
  -F "title=支払い方法について（FAQ）" \
  2>&1 | grep -E "status|message" || echo "  ✅ アップロード完了"
echo ""

sleep 2

# 返品・交換情報
echo "🔄 返品・交換情報をアップロード中..."
curl -X POST "$BASE_URL/upload-document" \
  -F "file=@support_return.txt" \
  -F "title=返品・交換について（FAQ）" \
  2>&1 | grep -E "status|message" || echo "  ✅ アップロード完了"
echo ""

echo "✅ すべてのセクションのアップロードが完了しました！"
echo ""
echo "📊 次のステップ:"
echo "  1. https://$BASE_URL/upload でファイル一覧を確認"
echo "  2. 古い「サポート最新版」ファイルを削除"
echo "  3. LINEで「送料はいくらですか？」とテスト"
