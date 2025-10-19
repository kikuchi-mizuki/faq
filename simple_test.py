#!/usr/bin/env python3
"""
シンプルなテストアプリケーション
"""

import os
import sys
from flask import Flask, jsonify

# 環境変数の設定
os.environ['LINE_CHANNEL_SECRET'] = '64da56e9a8a938a97f7603d41d6db9a4'
os.environ['LINE_CHANNEL_ACCESS_TOKEN'] = 'QoggJTuqTEKwMF2+wMoqxfX1ijpFo5tiCawckdsy09n/jnQrlFJm2oSXdtrMl2sYnxzVf4P6CmrMtcuCwTx06dnysDizOQhuAcrmQAWyF7S8Yz8SJ+fRDHSd8rZJTNMkFWxtfY+xy7LpJi5colfijwdB04t89/1O/w1cDnyilFU='
os.environ['SHEET_ID_QA'] = '1ADX4AK_MYGzH4e9hfXbx61SIWt82BNmS633luZ3zPno'

app = Flask(__name__)

@app.route("/healthz", methods=["GET"])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        "status": "healthy", 
        "message": "Simple test app is running",
        "python_version": sys.version
    })

@app.route("/", methods=["GET"])
def root():
    """ルートエンドポイント"""
    return jsonify({
        "message": "LINE Q&A System",
        "status": "running"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting simple test app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
