# Supabase認証テーブルのセットアップガイド

このガイドでは、認証データをSupabaseに永続化するためのテーブル作成手順を説明します。

## 📋 概要

認証機能が強化され、以下の問題が解決されました：

- ✅ **アプリ再起動後も認証が維持される**（データベースに永続化）
- ✅ **認証フローのバグを修正**（シンプルな1ステップ認証）
- ✅ **認証ループ問題を解決**（データベースとセッションの両方で管理）

## 🚀 セットアップ手順

### 1. Supabaseにログイン

1. [Supabase](https://supabase.com)にアクセス
2. プロジェクト `line-qa-rag` を開く

### 2. SQLエディタでテーブルを作成

1. 左サイドバーの **SQL Editor** をクリック
2. **New query** をクリック
3. `setup_supabase_auth.sql` ファイルの内容を全てコピー&ペースト
4. **Run** ボタンをクリック

### 3. テーブルの確認

1. 左サイドバーの **Table Editor** をクリック
2. 以下のテーブルが作成されているか確認：
   - `authenticated_users` - 認証済みユーザー情報
   - `auth_logs` - 認証ログ（監査用）

### 4. 環境変数の確認

Railwayで `DATABASE_URL` が正しく設定されているか確認：

```bash
# RailwayのVariablesセクションで確認
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.zztchlwbfbzkvygazhmk.supabase.co:5432/postgres
```

## 📊 作成されるテーブル

### `authenticated_users` テーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | SERIAL | 主キー |
| line_user_id | VARCHAR(255) | LINEユーザーID（ユニーク） |
| store_code | VARCHAR(50) | 店舗コード |
| staff_id | VARCHAR(50) | スタッフID |
| staff_name | VARCHAR(255) | スタッフ名 |
| store_name | VARCHAR(255) | 店舗名 |
| auth_time | TIMESTAMP | 認証日時 |
| expires_at | TIMESTAMP | 有効期限 |
| last_activity | TIMESTAMP | 最終アクティビティ |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

### `auth_logs` テーブル（監査用）

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | SERIAL | 主キー |
| line_user_id | VARCHAR(255) | LINEユーザーID |
| action | VARCHAR(50) | アクション（login/logout/refresh/revoke） |
| store_code | VARCHAR(50) | 店舗コード |
| staff_id | VARCHAR(50) | スタッフID |
| success | BOOLEAN | 成功/失敗 |
| error_message | TEXT | エラーメッセージ |
| ip_address | VARCHAR(50) | IPアドレス |
| created_at | TIMESTAMP | 作成日時 |

## 🔄 認証フローの変更点

### 旧フロー（問題あり）

1. 「認証」と入力
2. 店舗コード入力画面
3. 「店舗コード:STORE004」と入力
4. 社員番号入力画面
5. 「社員番号:004」と入力
6. **→ ここでループが発生していた**

### 新フロー（改善版）

1. **「STORE004」と入力するだけ**
   - または「004」のみでもOK
2. ✅ 認証完了！

## 🧪 動作テスト手順

### 1. ローカルテスト

```bash
# 開発サーバーを起動
poetry run python start.py

# 別ターミナルでテスト
curl http://localhost:5000/healthz
```

### 2. LINE認証テスト

1. LINEで「こんにちは」と送信
2. 認証案内が表示される
3. 「STORE004」と入力
4. 認証成功メッセージが表示される
5. 質問を送信してBotが応答するか確認

### 3. 永続性テスト

1. 認証完了後、アプリを再起動
2. LINEで質問を送信
3. ✅ 認証が維持されていることを確認

## 🔍 トラブルシューティング

### 認証テーブルが作成されない

```sql
-- テーブルの存在確認
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('authenticated_users', 'auth_logs');
```

### データベース接続エラー

```bash
# Railwayログで確認
# "認証データベースサービスを初期化しました" のログを確認
```

### 認証が保存されない

```sql
-- 認証データの確認
SELECT * FROM authenticated_users;

-- ログの確認
SELECT * FROM auth_logs ORDER BY created_at DESC LIMIT 10;
```

## 📝 管理API

### 認証済みユーザー一覧

```bash
curl -X GET https://line-qa-system-production.up.railway.app/admin/authenticated-users \
  -H "X-API-Key: admin-faq-2025-xK9mP2qL"
```

### ユーザーの認証を取り消し

```bash
curl -X POST https://line-qa-system-production.up.railway.app/admin/revoke-auth \
  -H "X-API-Key: admin-faq-2025-xK9mP2qL" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "LINE_USER_ID"}'
```

## 🎯 次のステップ

1. ✅ Supabaseにテーブルを作成
2. ✅ Railwayに変更をデプロイ
3. ✅ LINE認証テスト
4. ✅ 本番運用開始

---

**更新日時**: 2026-01-20
**対応バージョン**: v2.0.0以降
