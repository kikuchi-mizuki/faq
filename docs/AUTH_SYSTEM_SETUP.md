# 認証システムセットアップガイド

## 🎯 概要

フランチャイズ店舗のスタッフのみがLINE Botを利用できる認証システムのセットアップ手順です。

## 📋 前提条件

- ✅ LINE公式アカウントの設定完了
- ✅ Google Sheets APIの設定完了
- ✅ Railway環境の準備完了
- ✅ 基本Bot機能の動作確認完了

## 🚀 セットアップ手順

### **STEP1: 環境変数の設定**

Railwayのダッシュボードで以下の環境変数を設定してください：

```bash
# 認証機能の有効化
AUTH_ENABLED=true
AUTH_TIMEOUT=300
AUTH_MAX_ATTEMPTS=3
AUTH_SESSION_DAYS=30

# 店舗管理設定
STORE_MANAGEMENT_SHEET=store_management
STORE_CODE_PREFIX=STORE

# スタッフ管理設定
STAFF_MANAGEMENT_SHEET=staff_management

# LINEログイン設定（将来の拡張用）
LINE_LOGIN_CHANNEL_ID=your_line_login_channel_id
LINE_LOGIN_CHANNEL_SECRET=your_line_login_channel_secret
LINE_LOGIN_REDIRECT_URI=https://your-app.railway.app/auth/callback
```

### **STEP2: スプレッドシートの準備**

#### **2.1 店舗管理シートの作成**

Googleスプレッドシートに以下のシートを作成：

**シート名**: `store_management`

| 列 | 名前 | 説明 | 例 |
|----|------|------|---|
| A | store_code | 店舗コード | STORE001 |
| B | store_name | 店舗名 | 本店 |
| C | status | ステータス | active |
| D | created_at | 作成日時 | 2025-01-13T10:00:00Z |
| E | last_activity | 最終利用日時 | 2025-01-13T15:30:00Z |
| F | notes | 備考 | 本店 |
| G | admin_notes | 管理者メモ | 特記事項なし |
| H | contact_info | 連絡先情報 | 03-1234-5678 |
| I | location | 店舗所在地 | 東京都渋谷区 |
| J | manager_name | 店舗責任者名 | 田中太郎 |

#### **2.2 スタッフ管理シートの作成**

Googleスプレッドシートに以下のシートを作成：

**シート名**: `staff_management`

| 列 | 名前 | 説明 | 例 |
|----|------|------|---|
| A | store_code | 店舗コード | STORE001 |
| B | staff_id | 社員番号 | 001 |
| C | staff_name | スタッフ名 | 田中太郎 |
| D | position | 役職 | 店長 |
| E | status | ステータス | active |
| F | created_at | 作成日時 | 2025-01-13T10:00:00Z |
| G | last_activity | 最終利用日時 | 2025-01-13T15:30:00Z |
| H | line_user_id | LINEユーザーID | U1234567890abcdef |
| I | auth_time | 認証日時 | 2025-01-13T10:30:00Z |
| J | notes | 備考 | 本店店長 |

### **STEP3: テストデータの投入**

#### **3.1 店舗データの登録**

店舗管理シートに以下のデータを登録：

```
STORE001,本店,active,2025-01-13T10:00:00Z,,本店,,03-1234-5678,東京都渋谷区,田中太郎
STORE002,渋谷店,active,2025-01-13T10:00:00Z,,渋谷店,,03-2345-6789,東京都渋谷区,佐藤花子
STORE003,新宿店,suspended,2025-01-13T10:00:00Z,,新宿店（一時休業）,,03-3456-7890,東京都新宿区,鈴木一郎
```

#### **3.2 スタッフデータの登録**

スタッフ管理シートに以下のデータを登録：

```
STORE001,001,田中太郎,店長,active,2025-01-13T10:00:00Z,,,,
STORE001,002,山田花子,スタッフ,active,2025-01-13T10:00:00Z,,,,
STORE002,003,佐藤花子,店長,active,2025-01-13T10:00:00Z,,,,
STORE002,004,鈴木一郎,スタッフ,suspended,2025-01-13T10:00:00Z,,,,
```

### **STEP4: アプリケーションのデプロイ**

#### **4.1 コードのデプロイ**

```bash
# ローカルでテスト
python test_auth_system.py

# Railwayにデプロイ
git add .
git commit -m "Add authentication system"
git push origin main
```

#### **4.2 デプロイ後の確認**

1. **ヘルスチェック**
   ```bash
   curl https://your-app.railway.app/healthz
   ```

2. **統計情報の確認**
   ```bash
   curl https://your-app.railway.app/admin/stats
   ```

### **STEP5: Botの動作テスト**

#### **5.1 未認証ユーザーのテスト**

1. LINE Botにメッセージを送信
2. 「このBotは関係者専用です」メッセージが表示されることを確認
3. 「認証」と入力
4. 認証ボタンが表示されることを確認

#### **5.2 認証フローのテスト**

1. 「認証する」ボタンを押す
2. 「店舗コードを入力してください」メッセージが表示されることを確認
3. 「店舗コード:STORE001」と入力
4. 「社員番号を入力してください」メッセージが表示されることを確認
5. 「社員番号:001」と入力
6. 認証成功メッセージが表示されることを確認

#### **5.3 認証済みユーザーのテスト**

1. 認証完了後、通常のBot機能が利用できることを確認
2. Q&A検索が動作することを確認
3. 分岐会話が動作することを確認

## 🔧 トラブルシューティング

### **よくある問題**

#### **1. 認証が失敗する**
- 店舗コードと社員番号が正しいか確認
- スタッフのステータスが「active」か確認
- 店舗のステータスが「active」か確認

#### **2. スプレッドシートにアクセスできない**
- Google Sheets APIの権限設定を確認
- サービスアカウントの設定を確認

#### **3. Botが応答しない**
- 環境変数「AUTH_ENABLED」が「true」に設定されているか確認
- ログでエラーが発生していないか確認

### **ログの確認**

Railwayのダッシュボードでログを確認：

```
✅ 認証システムの初期化完了
✅ 店舗データを読み込みました: 3件
✅ スタッフデータを読み込みました: 4件
✅ 認証が完了しました
```

## 📊 運用管理

### **店舗の追加**

1. 店舗管理シートに新しい店舗を追加
2. スタッフ管理シートにスタッフを追加
3. Botの自動リロード（5分ごと）で反映

### **スタッフの管理**

1. スタッフのステータス変更（active/suspended）
2. スタッフの削除
3. 認証情報のリセット

### **統計情報の確認**

```bash
# 統計情報を取得
curl https://your-app.railway.app/admin/stats
```

## 🎯 次のステップ

認証システムのセットアップが完了したら：

1. **管理者ダッシュボードの実装**
2. **LINEログイン認証の追加**
3. **詳細な監視機能の実装**
4. **運用マニュアルの作成**

## 📞 サポート

問題が発生した場合は、以下の情報を確認してください：

1. Railwayのログ
2. 環境変数の設定
3. スプレッドシートのデータ
4. 認証フローの動作状況
