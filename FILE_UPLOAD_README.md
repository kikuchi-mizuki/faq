# ファイルアップロードでAI学習させる方法

## 概要

ChatGPTsのように、アップロードしたファイルの内容をAIに学習させて、LINE上で質問に答えられるようにできます。

## 対応ファイル形式

- **PDF** (.pdf) - pdfplumberで日本語対応
- **Excel** (.xlsx, .xls) - 全シート対応
- **テキスト** (.txt) - UTF-8エンコーディング

## 使い方

### 方法1: シェルスクリプトを使う（簡単）

```bash
# 1. スクリプトに実行権限を付与（初回のみ）
chmod +x upload_file_to_rag.sh

# 2. ファイルをアップロード
./upload_file_to_rag.sh path/to/your/file.pdf

# 3. タイトルを指定してアップロード
./upload_file_to_rag.sh path/to/manual.xlsx '製品マニュアル'
```

### 方法2: curlコマンドで直接アップロード

```bash
curl -X POST "https://line-qa-system-production.up.railway.app/admin/upload-document" \
  -H "X-API-Key: admin-faq-2025-xK9mP2qL" \
  -F "file=@/path/to/your/file.pdf" \
  -F "title=マニュアル"
```

## 動作の仕組み

1. **ファイルアップロード** → `/admin/upload-document` APIにPOST
2. **内容を抽出** → PDF/Excel/テキストから文字列を抽出
3. **チャンク分割** → 長い文章を適切なサイズに分割
4. **ベクトル化** → sentence-transformersでembeddingを生成
5. **DBに保存** → PostgreSQL + pgvectorに保存

## LINE上での利用

ファイルをアップロードすると、LINE上で以下のように動作します：

1. **ユーザーが質問** → Q&Aに該当するか確認
2. **Q&Aに該当なし** → RAG（アップロードした資料）を検索
3. **類似文書を発見** → Gemini AIが資料の内容を元に回答生成
4. **回答を返信** → 「※この回答はアップロードされた資料から生成されました」と表示

## 現在登録されているファイル

```bash
# 登録済みファイルの確認
curl "https://line-qa-system-production.up.railway.app/admin/documents" \
  -H "X-API-Key: admin-faq-2025-xK9mP2qL"
```

## RAGサービスの状態確認

```bash
# RAG機能の状態確認
curl "https://line-qa-system-production.up.railway.app/admin/rag-status" \
  -H "X-API-Key: admin-faq-2025-xK9mP2qL"
```

## トラブルシューティング

### アップロードが失敗する

- ファイルサイズが大きすぎる可能性があります（目安: 10MB以下推奨）
- ファイル形式が対応していない可能性があります

### AIが正しく回答しない

- アップロードしたファイルの内容が不明瞭な場合があります
- より具体的な質問をすると精度が上がります

### 文書が見つからない

以下のコマンドで登録状況を確認してください：

```bash
curl "https://line-qa-system-production.up.railway.app/admin/documents" \
  -H "X-API-Key: admin-faq-2025-xK9mP2qL" | jq .
```

## セキュリティ

- すべてのアップロードはADMIN_API_KEYで保護されています
- 認証なしではアップロードできません
- アップロードされたファイルはPostgreSQLに暗号化して保存されます

## 技術詳細

- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2 (384次元)
- **Vector DB**: PostgreSQL + pgvector
- **AI Model**: Google Gemini 2.0 Flash
- **PDF解析**: pdfplumber（日本語対応）
- **Excel解析**: openpyxl
