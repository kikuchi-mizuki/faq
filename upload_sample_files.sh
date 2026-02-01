#!/bin/bash

# サンプルファイルをRAGシステムにアップロードするスクリプト
BASE_URL="https://line-qa-system-production.up.railway.app"

echo "==================================="
echo "サンプルファイルアップロードスクリプト"
echo "==================================="
echo ""

# テキストファイル
echo "[1/7] 製品カタログ（テキスト）をアップロード中..."
curl -X POST "$BASE_URL/upload-document" \
  -F "file=@test_data/sample_product_catalog.txt" \
  -F "title=製品カタログ 2026年版" \
  -s | python3 -m json.tool
echo ""

echo "[2/7] 店舗情報（テキスト）をアップロード中..."
curl -X POST "$BASE_URL/upload-document" \
  -F "file=@test_data/sample_store_info.txt" \
  -F "title=店舗情報・アクセス・お問い合わせ" \
  -s | python3 -m json.tool
echo ""

echo "[3/7] 保証ポリシー（テキスト）をアップロード中..."
curl -X POST "$BASE_URL/upload-document" \
  -F "file=@test_data/sample_warranty_policy.txt" \
  -F "title=保証・アフターサービスについて" \
  -s | python3 -m json.tool
echo ""

# Excelファイル
echo "[4/7] 在庫管理・注文履歴（Excel）をアップロード中..."
curl -X POST "$BASE_URL/upload-document" \
  -F "file=@test_data/sample_inventory_orders.xlsx" \
  -F "title=在庫管理・注文履歴データ" \
  -s | python3 -m json.tool
echo ""

echo "[5/7] FAQ一覧（Excel）をアップロード中..."
curl -X POST "$BASE_URL/upload-document" \
  -F "file=@test_data/sample_faq_list.xlsx" \
  -F "title=よくある質問（FAQ）一覧" \
  -s | python3 -m json.tool
echo ""

# PDFファイル
echo "[6/7] ユーザーマニュアル（PDF）をアップロード中..."
curl -X POST "$BASE_URL/upload-document" \
  -F "file=@test_data/sample_user_manual.pdf" \
  -F "title=スマートウォッチ Pro X1 ユーザーマニュアル" \
  -s | python3 -m json.tool
echo ""

echo "==================================="
echo "アップロード完了！"
echo "==================================="
echo ""
echo "次のステップ:"
echo "1. https://line-qa-system-production.up.railway.app/upload にアクセス"
echo "2. 「ファイル一覧」タブでアップロードされたファイルを確認"
echo "3. LINEで以下のような質問をテスト:"
echo "   - 「スマートウォッチの価格は？」"
echo "   - 「渋谷店の営業時間は？」"
echo "   - 「保証期間は何年ですか？」"
echo "   - 「在庫はありますか？」"
echo "   - 「配送料はいくらですか？」（既存のサポート情報から）"
echo "   - 「ペアリングできないのですが」"
echo ""
