#!/usr/bin/env python3
"""
最小限のアプリケーション（Railway用）
"""

import os
import sys
import time
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/healthz", methods=["GET"])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        "status": "healthy", 
        "message": "Minimal app is running",
        "python_version": sys.version,
        "port": os.environ.get("PORT", "5000"),
        "timestamp": time.time()
    }), 200

@app.route("/", methods=["GET"])
def root():
    """ルートエンドポイント"""
    return jsonify({
        "message": "LINE Q&A System - Minimal Version",
        "status": "running",
        "timestamp": time.time()
    }), 200

@app.route("/test", methods=["GET"])
def test():
    """テストエンドポイント"""
    return jsonify({
        "message": "Test endpoint is working",
        "timestamp": time.time(),
        "environment": os.environ.get("RAILWAY_ENVIRONMENT", "local")
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting minimal app on port {port}")
    print(f"🌍 Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python version: {sys.version}")
    
    try:
        app.run(host="0.0.0.0", port=port, debug=False)
    except Exception as e:
        print(f"❌ Error starting app: {e}")
        sys.exit(1)
