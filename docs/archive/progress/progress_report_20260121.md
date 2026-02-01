# 進捗レポート - 2026年1月21日

## 実施した作業の概要

本日は、Railway上でのLINE Q&Aシステムのクラッシュ問題の解決と、GPTsのようなファイル学習機能の実装を行いました。

---

## 1. Railway起動時のクラッシュ問題の解決

### 問題
- Railwayにデプロイ後、アプリケーションが起動後10分でクラッシュする
- ヘルスチェックで502エラーが発生

### 原因
1. 起動直後（5秒後）にGoogle Driveから文書を自動収集するバックグラウンドスレッドが実行
2. 重いMLモデル（sentence-transformers）の読み込みでメモリ不足
3. データベース接続のタイムアウト設定が短すぎた

### 実施した修正

#### 修正1: 自動文書収集の無効化
**ファイル**: `line_qa_system/app.py`
```python
# 起動時の自動文書収集を無効化（手動トリガーのみ有効）
# 理由: Railway起動時のタイムアウトとメモリ制約を考慮
print("📚 自動文書収集は無効化されています（/admin/collect-documents で手動実行可能）")
logger.info("自動文書収集は無効化されています。管理APIで手動実行してください。")
```

**コミット**: `efc73e6 - Fix: Railway起動時のクラッシュ問題を修正`

#### 修正2: RAGサービスの安定化
**ファイル**: `line_qa_system/rag_service.py`

1. DATABASE_URL未設定時の即座の代替モード切り替え
```python
if not self.database_url:
    print("⚠️ DATABASE_URLが設定されていません。代替RAGモードに切り替えます")
    return False
```

2. データベース接続タイムアウトの延長
```python
self.db_connection = psycopg2.connect(
    self.database_url,
    connect_timeout=10  # 5秒 → 10秒に延長
)
```

3. RAG軽量モードの追加
```python
rag_lightweight_mode = os.getenv('RAG_LIGHTWEIGHT_MODE', 'false').lower() == 'true'
if rag_lightweight_mode:
    # Embeddingモデルの読み込みをスキップ
```

**コミット**: `fa35c4e - Fix: RAGサービスの起動を安定化`

### 結果
- ✅ アプリが安定して起動するようになった
- ✅ ヘルスチェックが正常に応答（200 OK）
- ✅ RAGサービスが正常に動作（398件の文書を保持）

---

## 2. GPTsのようなファイル学習機能の実装

### 目的
ChatGPTsのように、ユーザーがアップロードしたファイルの内容をAIに学習させて、LINE上で質問に答えられるようにする。

### 実装した機能

#### 機能1: ファイルアップロードAPI
**ファイル**: `line_qa_system/app.py`

**エンドポイント**:
- `POST /upload-document` - 公開API（認証不要、誰でもアクセス可能）
- `POST /admin/upload-document` - 管理者用API（APIキー認証あり）

**対応ファイル形式**:
- PDF (.pdf) - pdfplumberで日本語対応
- Excel (.xlsx, .xls) - openpyxlで全シート対応
- テキスト (.txt) - UTF-8エンコーディング

**処理フロー**:
```
1. ファイル受信
   ↓
2. ファイルタイプ判定（PDF/Excel/テキスト）
   ↓
3. 内容抽出
   - PDF: pdfplumberで各ページのテキスト抽出
   - Excel: openpyxlで全シートのデータ抽出
   - テキスト: UTF-8デコード
   ↓
4. RAGサービスに追加
   - チャンク分割
   - ベクトル化（sentence-transformers）
   - PostgreSQL + pgvectorに保存
   ↓
5. 完了レスポンス
```

**コミット**: `ebd510b - Feature: ファイルアップロード機能を追加してGPTsのような学習機能を実現`

#### 機能2: 公開Webフォーム
**ファイル**: `line_qa_system/app.py`

**エンドポイント**: `GET /upload`

**特徴**:
- 認証不要で誰でもアクセス可能
- モダンで美しいUI
  - グラデーション背景（紫系）
  - リアルタイムアップロード進捗表示
  - レスポンシブデザイン
  - ローディングスピナー
  - 成功/エラーメッセージ表示

**URL**:
```
https://line-qa-system-production.up.railway.app/upload
```

**コミット**: `d3edab8 - Feature: 誰でもファイルアップロードできる公開Webフォームを追加`

#### 機能3: アップロードスクリプト
**ファイル**: `upload_file_to_rag.sh`

```bash
#!/bin/bash
# 使い方
./upload_file_to_rag.sh path/to/file.pdf
./upload_file_to_rag.sh manual.xlsx '製品マニュアル'
```

**コミット**: `ebd510b`

#### 機能4: ドキュメント
**ファイル**: `FILE_UPLOAD_README.md`

内容:
- 使い方（ブラウザ/スクリプト/curl）
- 動作の仕組み
- LINE上での利用方法
- トラブルシューティング
- 技術詳細

**コミット**: `ebd510b`

### バグ修正

#### datetime未定義エラー
**問題**: アップロード時に `name 'datetime' is not defined` エラー

**修正**:
```python
from datetime import datetime  # 追加
```

**コミット**: `048a46e - Fix: datetimeモジュールのインポート漏れを修正`

---

## 3. システムの現在の状態

### デプロイ状況
- **URL**: https://line-qa-system-production.up.railway.app
- **状態**: 正常稼働中
- **最新コミット**: `048a46e`

### データベース状況
```json
{
  "rag_service_initialized": true,
  "rag_service_enabled": true,
  "db_connected": true,
  "embedding_model_loaded": true,
  "document_count": 398,
  "embedding_count": 398,
  "gemini_api_key_set": true,
  "database_url_set": true
}
```

### 保存されている文書
1. **Google Sheets: flows** - 198チャンク
2. **Google Sheets: qa_form_log** - 99チャンク
3. **Google Sheets: フォームの回答 3** - 99チャンク
4. **Google Drive: テスト.pdf** - 2チャンク

合計: **398チャンク**

---

## 4. 技術スタック

### バックエンド
- **Flask** - Webアプリケーションフレームワーク
- **PostgreSQL + pgvector** - ベクトルデータベース
- **sentence-transformers** - Embeddingモデル（all-MiniLM-L6-v2, 384次元）
- **Google Gemini 2.0 Flash** - AI回答生成

### ファイル解析
- **pdfplumber** - PDF解析（日本語対応）
- **openpyxl** - Excel解析
- **Python標準ライブラリ** - テキストファイル

### インフラ
- **Railway** - デプロイプラットフォーム
- **GitHub** - ソースコード管理
- **LINE Messaging API** - チャットボット

---

## 5. 今後の改善案

### セキュリティ
- ファイルサイズ制限の追加（現在: 無制限）
- ファイルアップロード時の認証オプション追加
- レート制限の実装

### パフォーマンス
- 非同期バックグラウンドジョブ化（Celery等）
- ファイル解析のタイムアウト設定
- キャッシュ機構の追加

### 機能拡張
- ドラッグ&ドロップ対応
- 複数ファイル同時アップロード
- アップロード履歴の表示
- 文書の削除機能
- 文書の検索・フィルタリング機能

---

## 6. コミット履歴（本日分）

```
048a46e - Fix: datetimeモジュールのインポート漏れを修正
d3edab8 - Feature: 誰でもファイルアップロードできる公開Webフォームを追加
ebd510b - Feature: ファイルアップロード機能を追加してGPTsのような学習機能を実現
fa35c4e - Fix: RAGサービスの起動を安定化
efc73e6 - Fix: Railway起動時のクラッシュ問題を修正
f77bebc - Fix: 文書収集ログにprint文を追加してRailwayログに表示されるように改善
```

---

## 7. 成果物

### 新規ファイル
1. `upload_file_to_rag.sh` - ファイルアップロードスクリプト
2. `FILE_UPLOAD_README.md` - 使い方ドキュメント
3. `progress_report_20260121.md` - 本レポート

### 変更ファイル
1. `line_qa_system/app.py` - メインアプリケーション
   - 自動文書収集の無効化
   - ファイルアップロードAPI追加
   - 公開Webフォーム追加
   - datetimeインポート追加

2. `line_qa_system/rag_service.py` - RAGサービス
   - データベース接続の安定化
   - タイムアウト延長
   - 軽量モード追加
   - エラーハンドリング強化

---

## 8. 使い方

### ファイルアップロード（ブラウザ）
1. https://line-qa-system-production.up.railway.app/upload にアクセス
2. ファイルを選択
3. タイトルを入力（オプション）
4. アップロードボタンをクリック

### ファイルアップロード（コマンドライン）
```bash
# スクリプトを使用
./upload_file_to_rag.sh path/to/file.pdf

# curlを使用
curl -X POST "https://line-qa-system-production.up.railway.app/upload-document" \
  -F "file=@path/to/file.pdf" \
  -F "title=マニュアル"
```

### LINE上で質問
1. アップロード完了後、LINEボットに質問を送信
2. Q&Aに該当しない場合、RAGで検索
3. アップロードした資料から回答が生成される
4. 「※この回答はアップロードされた資料から生成されました」と表示

---

## 9. 問題点と解決状況

| 問題 | 状態 | 解決方法 |
|------|------|----------|
| Railway起動時のクラッシュ | ✅ 解決 | 自動文書収集の無効化、RAG安定化 |
| Google Driveファイルが収集されない | ⚠️ 部分的 | 手動アップロード機能で代替 |
| 文書収集処理のタイムアウト | ⚠️ 既知の問題 | 重い処理のため手動実行を推奨 |
| datetime未定義エラー | ✅ 解決 | インポート追加 |

---

## 10. 今日の成果まとめ

### 達成したこと
✅ Railwayのクラッシュ問題を完全に解決
✅ GPTsのようなファイル学習機能を実装
✅ 誰でも使える美しいWebアップロードフォームを作成
✅ PDF、Excel、テキストファイルの自動解析に対応
✅ 認証不要で誰でもアップロード可能に
✅ ドキュメントとスクリプトを整備

### 技術的な学び
- Railwayのメモリ制約とタイムアウトへの対処
- RAGシステムの安定化手法
- Flask + PostgreSQL + pgvectorの統合
- pdfplumber、openpyxlでの日本語ファイル解析

---

## 付録: 環境変数

現在設定されている環境変数（Railway）:
- `GEMINI_API_KEY` - Google Gemini API認証
- `DATABASE_URL` - PostgreSQLデータベース接続
- `LINE_CHANNEL_SECRET` - LINE認証
- `LINE_CHANNEL_ACCESS_TOKEN` - LINE API
- `ADMIN_API_KEY` - 管理者API認証
- `GOOGLE_SERVICE_ACCOUNT_JSON` - Google API認証（Base64エンコード）
- `SHEET_ID_QA` - Q&Aスプレッドシート
- `AUTH_ENABLED` - 認証機能の有効化
- その他、アプリ固有の設定

---

**作成日**: 2026年1月21日
**最終更新**: 2026年1月21日
**作成者**: Claude Code (Anthropic Claude Sonnet 4.5)
