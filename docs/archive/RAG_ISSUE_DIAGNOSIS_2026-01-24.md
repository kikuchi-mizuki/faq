# RAG検索問題の診断レポート - 2026年1月24日

## 📸 問題の症状

LINEで「配送にはどれくらい時間がかかる？」と質問すると、以下のような回答が返される：

```
こんにちは！お問い合わせありがとうございます！配送にかかる時間ですね。

うーん、ごめんなさい、今お持ちの情報だけでは、配送にかかる時間について
正確な情報をお伝えできないんです。商品の種類や、お届け先の地域によって
変わってくるので…。

もしよろしければ、ご注文された商品名や、おおよそのお届け先（都道府県など）
を教えていただけますでしょうか？そうすれば、もう少し詳しくお調べして、
お答えできるかと思います！

※この回答はアップロードされた資料から生成されました。
```

### 期待される回答

データベースには以下の情報が保存されているため、正しく回答されるべき：

```
Q: 配送にはどのくらい時間がかかりますか？
A: ご注文から3〜5営業日でお届けします。離島や一部地域は追加で2〜3日かかる場合があります。
```

---

## 🔍 診断プロセス

### 1. ローカル環境でのテスト

#### 結果: ✅ 正常に動作

```
初期化結果:
  is_enabled: True
  db_pool: True
  embedding_model: True
  gemini_model: True

診断結果: ✅ 完全RAG機能: 正常に動作しています
```

### 2. データベースの内容確認

#### 結果: ✅ サポート情報が正しく保存されている

```
文書数: 9件
Embedding生成済み: 9件

サポート情報:
- タイトル: サポート最新版
  内容: よくある質問（FAQ）

■ 配送について

Q: 配送にはどのくらい時間がかかりますか？
A: ご注文から3〜5営業日でお届けします。...
  Embedding: あり
```

### 3. 類似度スコアの確認

#### 結果: ⚠️ 問題発見

「配送にはどれくらい時間がかかる？」での検索結果：

| 順位 | タイトル | 類似度スコア | 閾値判定 |
|------|----------|-------------|---------|
| 1 | テスト.pdf | 0.5133 | ✅ 閾値以上 |
| 2 | テスト２.pdf | 0.4448 | ✅ 閾値以上 |
| 3 | 商品情報マニュアル | 0.3289 | ✅ 閾値以上 |
| 4 | テストアップロード_製品カタログ | 0.2427 | ✅ 閾値以上 |
| 5 | 製品カタログ | 0.2427 | ✅ 閾値以上 |
| 6 | キャンペーン情報 | 0.1629 | ✅ 閾値以上 |
| **7** | **サポート情報** | **0.1517** | **✅ 閾値以上** |
| **8** | **サポート最新版** | **0.1517** | **✅ 閾値以上** |
| 9 | 菊池さん共有_営業関連シートのコピー.xlsx | 0.0022 | ❌ 閾値未満 |

**問題点**:
- サポート情報の類似度は**0.1517**
- 閾値（0.05）以上なので検索対象だが、**7-8位**
- `limit=5`の設定により、検索結果に含まれない

---

## 🎯 問題の根本原因

### 原因1: Railway環境でEmbeddingモデルが初期化されていない（推定）

`line_qa_system/rag_service.py:447-450`:

```python
if not self.db_pool or not self.embedding_model:
    logger.warning(f"代替RAG機能チェック: DB接続プール={self.db_pool is not None}, Embeddingモデル={self.embedding_model is not None}")
    return []  # 空の結果を返す
```

**推定される原因**:
1. `RAG_LIGHTWEIGHT_MODE=true` が環境変数に設定されている
2. sentence-transformersのメモリ不足（500MB-1GB必要）
3. Embeddingモデルの初期化タイムアウト
4. 依存関係のインストール失敗

### 原因2: サポート情報のチャンク分割が不適切

現在、サポート情報全体（複数のQ&A）が1つのチャンクになっているため：
- 類似度スコアが低くなる（0.1517）
- より関連性の低い文書（「テスト.pdf」など）よりスコアが低い

**理想的なチャンク**:
- 各Q&Aを個別のチャンクにする
- 特に「配送について」セクションを独立させる

---

## 🔧 解決策

### 即座に実施可能な対策

#### 対策1: Railway環境の診断 ⏳

新しく追加した診断エンドポイントで現状を確認：

```bash
curl -H "X-API-Key: your_admin_api_key" \
  https://line-qa-system-production.up.railway.app/admin/rag-diagnostic
```

#### 対策2: 環境変数の確認と修正

**確認項目**:
- `RAG_LIGHTWEIGHT_MODE` が設定されているか
- `SIMILARITY_THRESHOLD` の値（推奨: 0.10〜0.15）

**修正方法**（もし`RAG_LIGHTWEIGHT_MODE=true`なら）:
```bash
# Railway CLIで削除
railway variables delete RAG_LIGHTWEIGHT_MODE

# または、Railway Webコンソールから削除
```

#### 対策3: 検索パラメータの調整

`line_qa_system/rag_service.py:447-450`または呼び出し側で：

**オプション1: 検索件数を増やす**
```python
# Before
results = rag_service.search_similar_documents(query, limit=5)

# After
results = rag_service.search_similar_documents(query, limit=10)
```

**オプション2: 類似度閾値を下げる**
```python
# 環境変数
SIMILARITY_THRESHOLD=0.10  # 現在: 0.15（Railway）/ 0.05（ローカル）
```

### 中期的な改善策

#### 改善1: サポート情報のチャンク分割改善 🎯 推奨

現在のサポート情報をセクションごとに分割：

**Before（1チャンク）**:
```
よくある質問（FAQ）

■ 配送について
Q: 配送にはどのくらい時間がかかりますか？
A: ご注文から3〜5営業日でお届けします。

■ 返品について
Q: 返品は可能ですか？
A: 商品到着後7日以内であれば可能です。
...
```

**After（複数チャンク）**:
```
チャンク1:
配送について
Q: 配送にはどのくらい時間がかかりますか？
A: ご注文から3〜5営業日でお届けします。離島や一部地域は追加で2〜3日かかる場合があります。

チャンク2:
返品について
Q: 返品は可能ですか？
A: 商品到着後7日以内であれば可能です。
...
```

**期待される効果**:
- 類似度スコア: **0.15 → 0.60以上**（推定）
- 検索順位: **7位 → 1-2位**

**実装方法**:
1. サポート情報ファイルを再アップロード（セクションごとに分割）
2. または、RAGServiceのチャンク分割ロジックを改善

#### 改善2: Embeddingモデルの軽量化

メモリ不足が原因の場合：

```python
# より軽量なモデルに変更
EMBEDDING_MODEL=sentence-transformers/paraphrase-MiniLM-L3-v2  # 約60MB
# 現在: all-MiniLM-L6-v2 (約80MB)
```

または、OpenAI Embeddingsなどの外部APIを使用。

---

## 📊 推奨される対応順序

### 優先度: 高（今すぐ）

1. **Railway診断エンドポイントを実行** ⏳
   ```bash
   curl -H "X-API-Key: xxx" \
     https://line-qa-system-production.up.railway.app/admin/rag-diagnostic
   ```

2. **結果に基づいて対応**:
   - `RAG_LIGHTWEIGHT_MODE=true` → 削除
   - Embeddingモデル未ロード → メモリ確認
   - 依存関係エラー → 再デプロイ

### 優先度: 中（今日中）

3. **サポート情報のチャンク分割改善**
   - セクションごとに分割したファイルを再アップロード
   - 類似度スコアの改善を確認

### 優先度: 低（今週中）

4. **検索パラメータの最適化**
   - 類似度閾値の調整
   - 検索件数の調整

---

## 🧪 テストスクリプト

### ローカルテスト

```bash
# 1. RAG初期化診断
python3 check_rag_initialization.py

# 2. RAG検索テスト
python3 test_rag_search.py

# 3. サポート情報の類似度確認
python3 test_support_similarity.py

# 4. Embedding状況確認
python3 check_embedding_status.py
```

### Railway診断

```bash
# 管理者APIキーを使用
export ADMIN_API_KEY="your_admin_api_key"

# RAG診断
curl -H "X-API-Key: $ADMIN_API_KEY" \
  https://line-qa-system-production.up.railway.app/admin/rag-diagnostic
```

---

## 📝 まとめ

### 問題の全体像

1. **Railway環境**: Embeddingモデルが初期化されていない（推定）
   - → ベクトル検索ができない
   - → AIが「情報がない」と判断

2. **チャンク分割**: サポート情報の類似度スコアが低い（0.1517）
   - → `limit=5`で検索結果に含まれない

### 次のステップ

1. ✅ 診断エンドポイントを作成してデプロイ済み
2. ⏳ Railway環境での診断実行（デプロイ完了後）
3. ⏳ 問題に応じて修正を実施
4. ⏳ サポート情報のチャンク分割改善

---

**作成日**: 2026年1月24日 21:30
**作成者**: Claude Code (Anthropic Claude Sonnet 4.5)
**関連コミット**: ba144d8
