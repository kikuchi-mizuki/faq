#!/usr/bin/env python3
"""
最小限のアプリケーション（Railway用）
"""

import os
import sys
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/healthz", methods=["GET"])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        "status": "healthy", 
        "message": "Minimal app is running",
        "python_version": sys.version,
        "port": os.environ.get("PORT", "5000")
    })

@app.route("/", methods=["GET"])
def root():
    """ルートエンドポイント"""
    return jsonify({
        "message": "LINE Q&A System - Minimal Version",
        "status": "running"
    })

@app.route("/test", methods=["GET"])
def test():
    """テストエンドポイント"""
    return jsonify({
        "message": "Test endpoint is working",
        "timestamp": os.environ.get("RAILWAY_STATIC_URL", "local")
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting minimal app on port {port}")
    print(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
    app.run(host="0.0.0.0", port=port, debug=False)
