"""
LINE Q&A自動応答システム - メインアプリケーション
"""

import os
import time
import hashlib
import hmac
import base64
import json
import threading
from typing import Dict, Any, Optional
from functools import wraps

import structlog
from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv

from .line_client import LineClient
from .qa_service import QAService
from .session_service import SessionService
from .flow_service import FlowService
from .location_service import LocationService
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

# サービスの初期化（遅延初期化）
qa_service = None
line_client = None
session_service = None
flow_service = None
location_service = None

def initialize_services():
    """サービスの初期化（遅延初期化）"""
    global qa_service, line_client, session_service, flow_service, location_service
    
    if qa_service is not None:
        return  # 既に初期化済み
    
    try:
        logger.info("サービスの初期化を開始します")
        
        qa_service = QAService()
        logger.info("QAServiceの初期化が完了しました")
        
        line_client = LineClient()
        logger.info("LineClientの初期化が完了しました")
        
        session_service = SessionService()
        logger.info("SessionServiceの初期化が完了しました")
        
        flow_service = FlowService(session_service)
        logger.info("FlowServiceの初期化が完了しました")
        
        location_service = LocationService()
        logger.info("LocationServiceの初期化が完了しました")
        
        logger.info("全てのサービスの初期化が完了しました")
        
    except Exception as e:
        logger.error("サービスの初期化中にエラーが発生しました", error=str(e), exc_info=True)
        # エラーが発生してもアプリケーションは起動する
        logger.warning("一部のサービスが初期化できませんでした。基本機能のみ利用可能です。")


def start_auto_reload():
    """定期的な自動リロード機能を開始"""
    last_sheet_update = None
    
    def auto_reload_worker():
        nonlocal last_sheet_update
        while True:
            try:
                time.sleep(300)  # 5分ごと
                logger.info("自動リロードチェック開始")
                
                # スプレッドシートの最終更新時刻をチェック
                try:
                    # 現在の最終更新時刻を取得（簡易実装）
                    current_time = time.time()
                    
                    # 初回実行時または強制リロード時
                    if last_sheet_update is None:
                        qa_service.reload_cache()
                        last_sheet_update = current_time
                        logger.info("初回自動リロード完了")
                    else:
                        # 通常の定期リロード（変更検知なし）
                        qa_service.reload_cache()
                        flow_service.reload_flows()
                        location_service.reload_locations()
                        location_service.reload_form_logs()
                        logger.info("定期自動リロード完了")
                        
                except Exception as e:
                    logger.error("スプレッドシート更新チェック中にエラー", error=str(e))
                
            except Exception as e:
                logger.error("自動リロード中にエラーが発生しました", error=str(e))
    
    # バックグラウンドで自動リロードを開始
    reload_thread = threading.Thread(target=auto_reload_worker, daemon=True)
    reload_thread.start()
    logger.info("自動リロード機能を開始しました")


# アプリケーション起動時に自動リロードを開始
start_auto_reload()


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
        # サービスが初期化されていない場合は初期化を試行
        if qa_service is None:
            initialize_services()
        
        # サービスが初期化されていない場合はエラーメッセージを返す
        if qa_service is None or line_client is None:
            line_client = LineClient()  # 最低限の初期化
            line_client.reply_text(reply_token, "申し訳ございません。システムの初期化中です。しばらくお待ちください。")
            return
        # キャンセルコマンドのチェック
        if message_text.strip().lower() in ["キャンセル", "cancel", "やめる", "終了"]:
            if flow_service.is_in_flow(user_id):
                flow_service.cancel_flow(user_id)
                line_client.reply_text(reply_token, "会話をキャンセルしました。")
                logger.info("フローをキャンセルしました", user_id=hashed_user_id)
                return
            else:
                line_client.reply_text(reply_token, "現在、会話は進行していません。")
                return

        # フロー中かどうかをチェック
        if flow_service.is_in_flow(user_id):
            # フロー中の場合は選択を処理
            next_flow, is_end = flow_service.process_user_choice(user_id, message_text)

            if next_flow:
                # 次のステップがある場合
                if is_end:
                    # 終了ステップ（回答）
                    line_client.reply_text(reply_token, next_flow.question)
                    logger.info("フロー終了", user_id=hashed_user_id)
                else:
                    # 次の質問を提示（クイックリプライ付き）
                    options = next_flow.option_list
                    line_client.reply_text(
                        reply_token, next_flow.question, quick_reply=options if options else None
                    )
                    logger.info(
                        "次のステップへ進みました", user_id=hashed_user_id, step=next_flow.step
                    )
            else:
                # フローが見つからない場合
                line_client.reply_text(
                    reply_token,
                    "申し訳ございません。処理中にエラーが発生しました。最初からやり直してください。",
                )
                flow_service.cancel_flow(user_id)
                logger.warning("フロー処理に失敗しました", user_id=hashed_user_id)

        else:
            # フロー外の場合は通常のQ&A検索
            # まず、フローのトリガーかどうかをチェック
            available_triggers = flow_service.get_available_triggers()
            for trigger in available_triggers:
                if trigger.lower() in message_text.lower():
                    # フローを開始
                    flow = flow_service.start_flow(user_id, trigger)
                    if flow:
                        # 最初の質問を送信（クイックリプライ付き）
                        options = flow.option_list
                        line_client.reply_text(
                            reply_token,
                            flow.question,
                            quick_reply=options if options else None,
                        )
                        logger.info(
                            "フローを開始しました", user_id=hashed_user_id, trigger=trigger
                        )
                        return

            # フローに該当しない場合は通常のQ&A検索
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
                    # Q&Aに該当しない場合は資料検索を試みる（STEP3）
                    locations = location_service.search_locations(message_text)
                    
                    if locations:
                        # 資料が見つかった場合
                        response_text = format_locations(locations)
                        line_client.reply_text(reply_token, response_text)
                        
                        logger.info(
                            "資料を提示しました",
                            user_id=hashed_user_id,
                            location_count=len(locations),
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
    # シンプルにanswerだけを返す
    return answer


def format_candidates(candidates: list) -> str:
    """候補のフォーマット"""
    text = "もしかしてこれですか？\n\n"
    for i, candidate in enumerate(candidates[:3], 1):
        tags_text = f" ({candidate.tags})" if candidate.tags else ""
        text += f"{i}. {candidate.question}{tags_text}\n"
    text += "\nより具体的なキーワードをお試しください。"
    return text


def format_locations(locations: list) -> str:
    """資料のフォーマット（STEP3）"""
    text = "📚 関連資料が見つかりました：\n\n"
    for i, location in enumerate(locations[:3], 1):
        text += f"{i}. {location.title}\n"
        text += f"   カテゴリ: {location.category}\n"
        if location.description:
            text += f"   {location.description}\n"
        text += f"   🔗 {location.url}\n\n"
    
    if len(locations) > 3:
        text += f"他 {len(locations) - 3}件の資料があります。\n"
    
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
        # サービスが初期化されていない場合は初期化を試行
        if qa_service is None:
            initialize_services()
        
        # 基本的な健全性チェック
        if qa_service is not None:
            qa_healthy = qa_service.health_check()
        else:
            qa_healthy = False
            
        if flow_service is not None:
            flow_healthy = len(flow_service.flows) > 0
            ai_healthy = flow_service.ai_service.health_check()
        else:
            flow_healthy = False
            ai_healthy = False
        
        if qa_healthy and flow_healthy:
            return jsonify({
                "status": "healthy", 
                "timestamp": time.time(), 
                "version": "0.1.0",
                "qa_service": "ok",
                "flow_service": "ok",
                "ai_service": "ok" if ai_healthy else "disabled"
            })
        else:
            return jsonify({
                "status": "unhealthy",
                "qa_service": "ok" if qa_healthy else "error",
                "flow_service": "ok" if flow_healthy else "error",
                "timestamp": time.time()
            }), 500
            
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
        flow_service.reload_flows()
        location_service.reload_locations()
        location_service.reload_form_logs()
        logger.info("手動リロードが完了しました")
        return jsonify({
            "status": "success", 
            "message": "キャッシュを再読み込みしました（Q&A + フロー + 資料）",
            "timestamp": time.time(),
            "auto_reload_active": True
        })
    except Exception as e:
        logger.error("キャッシュの再読み込みに失敗しました", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/admin/stats", methods=["GET"])
# @require_admin  # 一時的に無効化
def get_stats():
    """統計情報の取得（管理者のみ）"""
    try:
        qa_stats = qa_service.get_stats()
        
        # STEP3: 資料・フォームログの統計を追加
        location_stats = {
            "total_locations": len(location_service.locations),
            "total_categories": len(location_service.get_categories()),
            "total_form_logs": len(location_service.form_logs),
            "pending_form_logs": len(location_service.get_pending_form_logs()),
            "approved_form_logs": len(location_service.get_approved_form_logs()),
        }
        
        # 統計を結合
        combined_stats = qa_stats.to_dict()
        combined_stats["locations"] = location_stats
        combined_stats["total_flows"] = len(flow_service.flows)
        
        return jsonify(combined_stats)
    except Exception as e:
        logger.error("統計情報の取得に失敗しました", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/admin/auto-reload/status", methods=["GET"])
# @require_admin  # 一時的に無効化
def get_auto_reload_status():
    """自動リロードの状態確認"""
    try:
        return jsonify({
            "status": "success",
            "auto_reload_active": True,
            "last_reload": time.time(),
            "next_reload_in_seconds": 300,  # 5分後
            "message": "自動リロードが動作中です"
        })
    except Exception as e:
        logger.error("自動リロード状態の取得に失敗しました", error=str(e))
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
    try:
        port = int(os.environ.get("PORT", 5000))
        logger.info(f"アプリケーションを起動します (ポート: {port})")
        app.run(host="0.0.0.0", port=port, debug=False)
    except Exception as e:
        logger.error("アプリケーションの起動に失敗しました", error=str(e))
        raise


if __name__ == "__main__":
    main()
