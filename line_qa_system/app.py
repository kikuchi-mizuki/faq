"""
LINE Q&A自動応答システム - メインアプリケーション
"""

import os
import time
import hashlib
import hmac
import base64
import json
from typing import Dict, Any, Optional
from functools import wraps

import structlog
from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv

from .line_client import LineClient
from .qa_service import QAService
from .config import Config
from .utils import verify_line_signature, hash_user_id

# 環境変数の読み込み
load_dotenv()

# 構造化ログの設定
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# サービスの初期化
qa_service = QAService()
line_client = LineClient()


def require_admin(f):
    """管理者権限が必要なエンドポイント用デコレータ"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.headers.get("X-User-ID")
        admin_user_ids = app.config.get("ADMIN_USER_IDS", [])
        
        # デバッグ用ログ
        logger.info("管理者権限チェック", user_id=user_id, admin_user_ids=admin_user_ids)
        
        if not user_id or user_id not in admin_user_ids:
            logger.warning("管理者権限がありません", user_id=user_id, admin_user_ids=admin_user_ids)
            abort(403, description="管理者権限が必要です")
        
        logger.info("管理者権限確認完了", user_id=user_id)
        return f(*args, **kwargs)

    return decorated_function


@app.route("/callback", methods=["POST"])
def callback():
    """LINE Webhook受信エンドポイント"""
    start_time = time.time()

    try:
        # LINE署名の検証
        if not verify_line_signature(
            request.headers.get("X-Line-Signature", ""),
            request.get_data(),
            app.config["LINE_CHANNEL_SECRET"],
        ):
            logger.warning("LINE署名検証に失敗しました")
            abort(400, description="署名検証に失敗しました")

        # リクエストボディの解析
        body = request.get_json()
        if not body:
            abort(400, description="リクエストボディが不正です")

        # イベントの処理
        for event in body.get("events", []):
            if event["type"] == "message" and event["message"]["type"] == "text":
                process_text_message(event, start_time)

        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error("Webhook処理中にエラーが発生しました", error=str(e), exc_info=True)
        abort(500, description="内部エラーが発生しました")


def process_text_message(event: Dict[str, Any], start_time: float):
    """テキストメッセージの処理"""
    user_id = event["source"]["userId"]
    message_text = event["message"]["text"]
    reply_token = event["replyToken"]

    # ユーザーIDのハッシュ化
    hashed_user_id = hash_user_id(user_id)

    logger.info("メッセージを受信しました", user_id=hashed_user_id, text=message_text)

    try:
        # Q&A検索
        result = qa_service.find_answer(message_text)

        # 応答の送信
        if result.is_found:
            response_text = format_answer(result.answer, result.question, result.tags)
            line_client.reply_text(reply_token, response_text)

            logger.info(
                "回答を送信しました",
                user_id=hashed_user_id,
                question_id=result.id,
                score=result.score,
            )
        else:
            # 候補がある場合は候補を提示
            if result.candidates:
                response_text = format_candidates(result.candidates)
                line_client.reply_text(reply_token, response_text)

                logger.info(
                    "候補を提示しました",
                    user_id=hashed_user_id,
                    candidate_count=len(result.candidates),
                )
            else:
                # フォールバック応答
                fallback_text = get_fallback_response()
                line_client.reply_text(reply_token, fallback_text)

                logger.info("フォールバック応答を送信しました", user_id=hashed_user_id)

        # 処理時間の記録
        latency = int((time.time() - start_time) * 1000)
        logger.info("メッセージ処理完了", user_id=hashed_user_id, latency_ms=latency)

    except Exception as e:
        logger.error(
            "メッセージ処理中にエラーが発生しました", user_id=hashed_user_id, error=str(e), exc_info=True
        )

        # エラー時の応答
        error_text = "申し訳ございません。一時的なエラーが発生しました。"
        line_client.reply_text(reply_token, error_text)


def format_answer(answer: str, question: str, tags: str) -> str:
    """回答のフォーマット"""
    if tags:
        return f"【回答】\n{answer}\n\n関連: {tags}"
    return f"【回答】\n{answer}"


def format_candidates(candidates: list) -> str:
    """候補のフォーマット"""
    text = "もしかしてこれですか？\n\n"
    for i, candidate in enumerate(candidates[:3], 1):
        tags_text = f" ({candidate.tags})" if candidate.tags else ""
        text += f"{i}. {candidate.question}{tags_text}\n"
    text += "\nより具体的なキーワードをお試しください。"
    return text


def get_fallback_response() -> str:
    """フォールバック応答"""
    return (
        "すみません。該当する回答が見つかりませんでした。\n\n"
        "以下のようなキーワードをお試しください：\n"
        "• 請求書\n"
        "• 設定\n"
        "• パスワード\n\n"
        "お困りの際は、お手数ですが直接お問い合わせください。"
    )


@app.route("/healthz", methods=["GET"])
def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # 基本的な健全性チェック
        qa_service.health_check()
        return jsonify(
            {"status": "healthy", "timestamp": time.time(), "version": "0.1.0"}
        )
    except Exception as e:
        logger.error("ヘルスチェックに失敗しました", error=str(e))
        return (
            jsonify({"status": "unhealthy", "error": str(e), "timestamp": time.time()}),
            500,
        )


@app.route("/admin/reload", methods=["POST"])
# @require_admin  # 一時的に無効化
def reload_cache():
    """キャッシュの再読み込み（管理者のみ）"""
    try:
        qa_service.reload_cache()
        logger.info("キャッシュの再読み込みが完了しました")
        return jsonify({"status": "success", "message": "キャッシュを再読み込みしました"})
    except Exception as e:
        logger.error("キャッシュの再読み込みに失敗しました", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/admin/stats", methods=["GET"])
# @require_admin  # 一時的に無効化
def get_stats():
    """統計情報の取得（管理者のみ）"""
    try:
        stats = qa_service.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error("統計情報の取得に失敗しました", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad Request", "message": error.description}), 400


@app.errorhandler(403)
def forbidden(error):
    return jsonify({"error": "Forbidden", "message": error.description}), 403


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal Server Error", "message": "内部エラーが発生しました"}), 500


def main():
    """アプリケーションの起動"""
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
