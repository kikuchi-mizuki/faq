# AIマニュアルBot システム構成詳細書

## 📋 概要

AIマニュアルBotのシステム構成、アーキテクチャ、コンポーネント間の関係性を詳細に説明します。

---

## 🏗️ 全体アーキテクチャ

### システム全体図
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LINE User     │    │  LINE Platform  │    │   Flask App    │
│                 │◄──►│                 │◄──►│                 │
│ 質問・回答受信  │    │  Webhook処理    │    │  Q&A検索・返信  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Google Sheets  │◄──►│   Cache Layer   │◄──►│   Log System    │
│                 │    │                 │    │                 │
│ Q&A・Flows管理  │    │ Redis/Memory    │    │ structlog JSON  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### データフロー
```
1. ユーザー質問 → LINE Platform → Flask App
2. Flask App → Cache Layer → Google Sheets
3. Google Sheets → Q&A検索 → 回答生成
4. 回答 → LINE Platform → ユーザー
5. 全プロセス → ログ記録
```

---

## 🔧 コンポーネント詳細

### 1. LINE Platform連携
**ファイル**: `line_qa_system/line_client.py`

#### 機能
- LINE Messaging API v3との通信
- 署名検証によるセキュリティ確保
- メッセージタイプ別の処理分岐
- エラーハンドリングとリトライ機能

#### 主要メソッド
```python
class LineClient:
    def verify_signature(self, body: str, signature: str) -> bool
    def send_reply_message(self, reply_token: str, messages: List[dict])
    def send_push_message(self, user_id: str, messages: List[dict])
    def handle_message(self, event: dict) -> dict
```

### 2. Q&A検索エンジン
**ファイル**: `line_qa_system/qa_service.py`

#### 機能
- Google Sheetsからのデータ取得
- キーワード検索と類似度計算
- スコアリングアルゴリズム
- キャッシュ管理

#### 検索アルゴリズム
```python
class QAService:
    def search_qa(self, query: str) -> List[SearchResult]
    def calculate_score(self, query: str, qa_item: QAItem) -> float
    def get_best_match(self, results: List[SearchResult]) -> Optional[SearchResult]
```

### 3. セッション管理
**ファイル**: `line_qa_system/session_service.py`

#### 機能
- ユーザーセッションの永続化
- 会話状態の管理
- TTL（有効期限）管理
- セッションクリーンアップ

#### セッション構造
```python
@dataclass
class UserSession:
    user_id: str
    current_flow: Optional[str]
    flow_step: int
    flow_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

### 4. 分岐会話エンジン
**ファイル**: `line_qa_system/flow_service.py`

#### 機能
- flowsシートからのフロー定義読み込み
- ステップ管理と遷移制御
- ユーザー選択の処理
- フォールバック処理

#### フロー処理
```python
class FlowService:
    def start_flow(self, user_id: str, trigger: str) -> FlowStep
    def process_user_input(self, user_id: str, input_text: str) -> FlowStep
    def get_current_step(self, user_id: str) -> Optional[FlowStep]
    def cancel_flow(self, user_id: str) -> bool
```

### 5. キャッシュ層
**ファイル**: `line_qa_system/cache_service.py`

#### 機能
- Redis接続管理
- メモリキャッシュフォールバック
- TTL管理
- キャッシュ無効化

#### キャッシュ戦略
```python
class CacheService:
    def get(self, key: str) -> Optional[Any]
    def set(self, key: str, value: Any, ttl: int = 300)
    def delete(self, key: str) -> bool
    def clear_pattern(self, pattern: str) -> int
```

---

## 📊 データベース設計

### Google Sheets構造

#### qa_itemsシート
| 列 | 名前 | 型 | 説明 |
|----|------|----|----|
| A | id | 整数 | ユニークID |
| B | question | 文字列 | 質問文 |
| C | keywords | 文字列 | 検索キーワード |
| D | synonyms | 文字列 | 同義語 |
| E | tags | 文字列 | カテゴリタグ |
| F | answer | 文字列 | 回答文 |
| G | priority | 整数 | 優先度 |
| H | status | 文字列 | 状態 |
| I | updated_at | 日時 | 更新日時 |

#### flowsシート
| 列 | 名前 | 型 | 説明 |
|----|------|----|----|
| A | id | 整数 | フローID |
| B | trigger | 文字列 | トリガーキーワード |
| C | step | 整数 | ステップ番号 |
| D | question | 文字列 | 質問文 |
| E | options | 文字列 | 選択肢 |
| F | next_step | 文字列 | 次ステップ |
| G | end | 真偽値 | 終了フラグ |
| H | fallback_next | 整数 | フォールバック |
| I | updated_at | 日時 | 更新日時 |

### キャッシュ構造

#### Redis Key設計
```
qa:items:{timestamp}     # Q&Aデータキャッシュ
flows:{timestamp}        # フロー定義キャッシュ
session:{user_id}        # ユーザーセッション
stats:daily:{date}       # 日次統計
```

#### メモリキャッシュ構造
```python
{
    "qa_items": List[QAItem],
    "flows": List[FlowItem],
    "last_updated": datetime,
    "cache_ttl": int
}
```

---

## 🔄 処理フロー

### 1. 通常のQ&A検索フロー
```
1. ユーザー質問受信
2. 署名検証
3. セッション確認
4. Q&A検索実行
5. スコア計算
6. 最適回答選択
7. 回答送信
8. ログ記録
```

### 2. 分岐会話フロー
```
1. トリガーキーワード検出
2. フロー開始
3. セッション状態保存
4. 質問表示
5. ユーザー回答待ち
6. 回答処理
7. 次ステップ判定
8. 継続/終了判定
```

### 3. エラーハンドリングフロー
```
1. エラー検出
2. エラータイプ判定
3. ログ記録
4. ユーザー通知
5. 管理者通知（必要時）
6. システム復旧
```

---

## 🛡️ セキュリティアーキテクチャ

### 認証・認可フロー
```
1. LINE署名検証
   ├─ リクエストボディ取得
   ├─ 署名計算
   ├─ 比較検証
   └─ 検証結果返却

2. 管理者認証
   ├─ X-User-IDヘッダ確認
   ├─ 許可リスト照合
   └─ 権限レベル判定
```

### データ保護
```
1. 個人情報保護
   ├─ user_idハッシュ化
   ├─ PII非保存
   └─ ログ匿名化

2. 通信保護
   ├─ HTTPS必須
   ├─ 証明書検証
   └─ 暗号化通信
```

---

## 📈 パフォーマンス設計

### レスポンス時間目標
- **Q&A検索**: 500ms以内
- **分岐会話**: 200ms以内
- **キャッシュ取得**: 50ms以内
- **全体応答**: 2秒以内

### スケーラビリティ
- **同時接続**: 100ユーザー
- **スループット**: 1000リクエスト/分
- **メモリ使用量**: 512MB以内
- **CPU使用率**: 80%以内

### キャッシュ戦略
```
1. データキャッシュ
   ├─ Q&Aデータ: 5分TTL
   ├─ フロー定義: 10分TTL
   └─ セッション: 30分TTL

2. キャッシュ無効化
   ├─ 手動リロード
   ├─ TTL期限切れ
   └─ データ更新検知
```

---

## 🔧 設定管理

### 環境変数
```bash
# LINE設定
LINE_CHANNEL_SECRET=your_secret
LINE_CHANNEL_ACCESS_TOKEN=your_token

# Google設定
GOOGLE_SERVICE_ACCOUNT_JSON=base64_json
SHEET_ID_QA=your_sheet_id

# キャッシュ設定
REDIS_URL=redis://localhost:6379
CACHE_TTL_SECONDS=300

# 管理者設定
ADMIN_USER_IDS=user1,user2

# ログ設定
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 設定クラス
```python
@dataclass
class Config:
    # LINE設定
    line_channel_secret: str
    line_channel_access_token: str
    
    # Google設定
    google_service_account_json: str
    sheet_id_qa: str
    
    # キャッシュ設定
    redis_url: Optional[str]
    cache_ttl_seconds: int = 300
    
    # 管理者設定
    admin_user_ids: List[str]
    
    # ログ設定
    log_level: str = "INFO"
    log_format: str = "json"
```

---

## 📊 監視・ログ設計

### ログ構造
```json
{
    "timestamp": "2025-10-13T10:30:00Z",
    "level": "INFO",
    "service": "line_qa_bot",
    "user_id": "hash_user_id",
    "event_type": "qa_search",
    "query": "修正回数",
    "response_time_ms": 150,
    "cache_hit": true,
    "result_count": 3,
    "best_score": 0.95
}
```

### メトリクス
- **リクエスト数**: 総リクエスト数/分
- **レスポンス時間**: 平均・95%tile
- **エラー率**: 4xx/5xxエラー率
- **キャッシュヒット率**: キャッシュ利用率
- **アクティブユーザー**: 同時接続ユーザー数

### アラート設定
- **エラー率**: 5%超過でアラート
- **レスポンス時間**: 5秒超過でアラート
- **メモリ使用量**: 80%超過でアラート
- **CPU使用率**: 90%超過でアラート

---

## 🚀 デプロイメント設計

### Railway構成
```yaml
# railway.toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn line_qa_system.app:app"
healthcheckPath = "/admin/healthz"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
```

### 環境分離
- **開発環境**: ローカル開発
- **ステージング環境**: テスト用
- **本番環境**: Railway本番

### スケーリング
- **水平スケーリング**: 複数インスタンス
- **垂直スケーリング**: リソース増強
- **自動スケーリング**: 負荷に応じた調整

---

## 🔄 継続的改善

### パフォーマンス監視
- **APM**: アプリケーションパフォーマンス監視
- **ログ分析**: 構造化ログの分析
- **メトリクス収集**: システムメトリクスの収集
- **アラート**: 異常検知と通知

### 機能改善
- **A/Bテスト**: 機能の効果測定
- **ユーザーフィードバック**: 利用者からの意見収集
- **データ分析**: 利用パターンの分析
- **最適化**: アルゴリズムの改善

---

## 📝 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|----------|--------|
| 2025/10/13 | 1.0 | 初版作成 | AI Assistant |
| - | - | STEP1完了 | - |
| - | - | STEP2完了 | - |
| - | - | STEP3実装中 | - |

---

## 📞 関連ドキュメント

- **要件定義書**: `docs/REQUIREMENTS.md`
- **API仕様書**: `docs/API_SPECIFICATION.md`
- **デプロイメントガイド**: `docs/DEPLOYMENT_GUIDE.md`
- **各ステップ別ガイド**: `docs/STEP*_*.md`
