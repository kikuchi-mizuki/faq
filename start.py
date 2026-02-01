#!/usr/bin/env python3
"""
アプリケーション起動スクリプト（Railway/本番環境用）
"""

import os
import sys

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from line_qa_system.app import app

if __name__ == "__main__":
    # 環境変数からポート番号を取得（デフォルト: 8000）
    port = int(os.environ.get("PORT", 8000))

    # 本番環境ではdebug=False
    debug = os.environ.get("DEBUG", "false").lower() == "true"

    print(f"🚀 Starting Flask app on port {port} (debug={debug})")

    # Flaskアプリを起動
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug
    )
