#!/bin/bash
# RAGアプリケーション起動スクリプト

# 古い環境変数をクリア
unset DATABASE_URL
unset GEMINI_API_KEY

# .envファイルから環境変数を読み込んでアプリを起動
cd "$(dirname "$0")"
python3 start.py
