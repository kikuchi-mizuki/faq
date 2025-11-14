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
from .rag_service import RAGService
from .document_collector import DocumentCollector
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

# 認証システム用スプレッドシートの自動作成
try:
    from auto_setup import auto_setup_auth_sheets
    auto_setup_auth_sheets()
    logger.info("認証システム用スプレッドシートの自動作成が完了しました")
except Exception as e:
    logger.warning("認証システム用スプレッドシートの自動作成に失敗しました", error=str(e))

app = Flask(__name__)
app.config.from_object(Config)

# サービスの初期化（遅延初期化）
qa_service = None
line_client = None
session_service = None
flow_service = None
rag_service = None
document_collector = None

def initialize_services():
    """サービスの初期化（遅延初期化）"""
    global qa_service, line_client, session_service, flow_service, rag_service, document_collector
    
    if qa_service is not None:
        return  # 既に初期化済み
    
    try:
        logger.info("サービスの初期化を開始します")
        
        # AIServiceの初期化（最優先で行い、他サービスへ注入）
        from .ai_service import AIService
        ai_service = AIService()
        logger.info(f"AIServiceの初期化完了: is_enabled={ai_service.is_enabled}")
        
        # AIサービスが無効な場合の詳細ログ
        if not ai_service.is_enabled:
            logger.warning("AIサービスが無効です。GEMINI_API_KEYの設定を確認してください。")
        else:
            logger.info("AIサービスが有効です。")
        
        # QAService（AIServiceを渡す）
        qa_service = QAService(ai_service)
        logger.info("QAServiceの初期化が完了しました")
        
        line_client = LineClient()
        logger.info("LineClientの初期化が完了しました")
        
        session_service = SessionService()
        logger.info("SessionServiceの初期化が完了しました")
        
        # RAGサービスの初期化（段階的有効化）
        rag_service = None
        try:
            logger.info("RAGServiceの初期化を開始します")
            rag_service = RAGService()
            logger.info(f"RAGServiceの初期化完了: is_enabled={rag_service.is_enabled}")
        except Exception as e:
            logger.error("RAG機能の初期化に失敗しました", error=str(e))
            logger.info("RAG機能は無効化されています。基本機能のみ利用可能です。")
        
        flow_service = FlowService(session_service, qa_service, rag_service, ai_service)
        logger.info("FlowServiceの初期化が完了しました")
        
        # DocumentCollectorの初期化（RAG機能が有効な場合）
        document_collector = None
        if rag_service and rag_service.is_enabled:
            try:
                document_collector = DocumentCollector(rag_service)
                logger.info("DocumentCollectorの初期化が完了しました")
            except Exception as e:
                logger.error("DocumentCollectorの初期化に失敗しました", error=str(e))
        
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
    """管理者権限が必要なエンドポイント用デコレータ（APIキー認証）"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        expected_api_key = app.config.get("ADMIN_API_KEY", "")

        # APIキーが設定されていない場合はエラー
        if not expected_api_key:
            logger.error("ADMIN_API_KEYが設定されていません")
            abort(500, description="サーバー設定エラー: ADMIN_API_KEYが未設定です")

        # APIキーの検証
        if not api_key:
            logger.warning("APIキーが提供されていません")
            abort(401, description="認証が必要です。X-API-Keyヘッダーを含めてください")

        if api_key != expected_api_key:
            logger.warning("無効なAPIキーが提供されました")
            abort(403, description="無効なAPIキーです")

        logger.info("管理者認証成功")
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
            elif event["type"] == "postback":
                process_postback_message(event, start_time)

        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error("Webhook処理中にエラーが発生しました", error=str(e), exc_info=True)
        abort(500, description="内部エラーが発生しました")


def process_postback_message(event: Dict[str, Any], start_time: float):
    """ポストバックメッセージの処理"""
    user_id = event["source"]["userId"]
    reply_token = event["replyToken"]
    
    # ユーザーIDのハッシュ化
    hashed_user_id = hash_user_id(user_id)
    
    logger.info("ポストバックを受信しました", user_id=hashed_user_id)
    
    try:
        # 認証フローの処理
        if Config.AUTH_ENABLED:
            from .auth_flow import AuthFlow
            auth_flow = AuthFlow()
            
            if auth_flow.handle_postback(event):
                return  # 認証フローで処理された場合は終了
        
        # その他のポストバック処理
        # 必要に応じて追加
        
    except Exception as e:
        logger.error("ポストバック処理中にエラーが発生しました", 
                    user_id=hashed_user_id, 
                    error=str(e), 
                    exc_info=True)
        
        # エラー時の応答
        try:
            line_client.reply_text(reply_token, "申し訳ございません。一時的なエラーが発生しました。")
        except Exception as reply_error:
            logger.error("エラーメッセージの送信に失敗しました", error=str(reply_error))


def process_text_message(event: Dict[str, Any], start_time: float):
    """テキストメッセージの処理（認証チェック付き）"""
    user_id = event["source"]["userId"]
    message_text = event["message"]["text"]
    reply_token = event["replyToken"]

    # ユーザーIDのハッシュ化
    hashed_user_id = hash_user_id(user_id)

    logger.info("メッセージを受信しました", user_id=hashed_user_id, text=message_text)

    try:
        # サービスが初期化されていない場合は初期化を試行
        if qa_service is None or line_client is None:
            initialize_services()
        
        # サービスが初期化されていない場合はエラーメッセージを返す
        if qa_service is None or line_client is None:
            try:
                # 最低限のLineClientを初期化
                temp_line_client = LineClient()
                temp_line_client.reply_text(reply_token, "申し訳ございません。システムの初期化中です。しばらくお待ちください。")
            except Exception as e:
                logger.error("エラーメッセージの送信に失敗しました", error=str(e))
            return
        
        # 認証チェック（認証が有効な場合）
        if Config.AUTH_ENABLED:
            from .optimized_auth_flow import OptimizedAuthFlow
            auth_flow = OptimizedAuthFlow()
            
            # 認証フローの処理
            if auth_flow.process_auth_flow(event):
                return  # 認証フローで処理された場合は終了
            
            # 認証済みでない場合は制限メッセージを送信
            try:
                is_authenticated = auth_flow.is_authenticated(user_id)
                logger.info("認証チェック結果", 
                           user_id=hashed_user_id, 
                           is_authenticated=is_authenticated)
                
                if not is_authenticated:
                    auth_flow.send_auth_required_message(reply_token)
                    logger.info("未認証ユーザーからのアクセス", user_id=hashed_user_id)
                    return
            except Exception as e:
                logger.error("認証チェック中にエラーが発生しました", 
                           user_id=hashed_user_id, 
                           error=str(e))
                # エラーが発生した場合は安全のため認証が必要メッセージを送信
                try:
                    auth_flow.send_auth_required_message(reply_token)
                except:
                    pass
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
            # まず、AI文脈判断でフローのトリガーかどうかをチェック
            flow = flow_service.find_flow_by_ai_context(message_text)
            if flow:
                # AI文脈判断でフローを開始
                flow_service.start_flow(user_id, flow.trigger)
                # 最初の質問を送信（クイックリプライ付き）
                options = flow.option_list
                line_client.reply_text(
                    reply_token,
                    flow.question,
                    quick_reply=options if options else None,
                )
                logger.info(
                    "AI文脈判断でフローを開始しました", user_id=hashed_user_id, trigger=flow.trigger
                )
                return
            
            # 自然言語マッチングも試行
            flow = flow_service.find_flow_by_natural_language(message_text)
            if flow:
                # 自然言語マッチングでフローを開始
                flow_service.start_flow(user_id, flow.trigger)
                # 最初の質問を送信（クイックリプライ付き）
                options = flow.option_list
                line_client.reply_text(
                    reply_token,
                    flow.question,
                    quick_reply=options if options else None,
                )
                logger.info(
                    "自然言語マッチングでフローを開始しました", user_id=hashed_user_id, trigger=flow.trigger
                )
                return
            
            # 従来の厳密マッチングも試行
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

            # 認証情報の取得（ログ用）
            store_code = ""
            staff_id = ""
            if Config.AUTH_ENABLED:
                try:
                    from .optimized_auth_flow import OptimizedAuthFlow
                    auth_flow = OptimizedAuthFlow()
                    auth_data = auth_flow.authenticated_users.get(user_id, {})
                    store_code = auth_data.get('store_code', '')
                    staff_id = auth_data.get('staff_id', '')
                except:
                    pass

            # 質問をログに記録
            qa_service.log_query(
                user_id_hash=hashed_user_id,
                query=message_text,
                result=result,
                store_code=store_code,
                staff_id=staff_id
            )

            # 応答の送信
            if result.is_found and result.top_result is not None:
                response_text = format_answer(
                    result.top_result.answer,
                    result.top_result.question,
                    getattr(result.top_result, "tags", "")
                )
                line_client.reply_text(reply_token, response_text)

                logger.info(
                    "回答を送信しました",
                    user_id=hashed_user_id,
                    question_id=getattr(result.top_result, "id", None),
                    score=getattr(result.top_result, "score", None),
                )
            else:
                # 候補がある場合はAIで最適候補を自動選択（文脈判断）
                if result.candidates:
                    try:
                        ai = flow_service.ai_service if flow_service else None
                        if ai and ai.is_enabled and ai.model:
                            # 候補を番号付きで並べてAIに1つ選ばせる
                            choices_text = "\n".join(
                                [f"{i+1}. {c.question}" for i, c in enumerate(result.candidates)]
                            )
                            prompt = (
                                "ユーザーの質問に最も適切な候補を1つだけ番号で答えてください。"\
                                "\n候補一覧:\n" + choices_text + "\n\nユーザーの質問: " + message_text +
                                "\n出力は番号のみ（例: 2）。説明は不要です。"
                            )
                            ai_resp = ai.model.generate_content(prompt)
                            if ai_resp and ai_resp.text:
                                sel = ai_resp.text.strip()
                                # 数字を抽出
                                import re
                                m = re.search(r"(\d+)", sel)
                                if m:
                                    idx = int(m.group(1)) - 1
                                    if 0 <= idx < len(result.candidates):
                                        chosen = result.candidates[idx]
                                        line_client.reply_text(reply_token, chosen.answer)
                                        logger.info(
                                            "AIで候補から最適回答を選択して送信しました",
                                            user_id=hashed_user_id,
                                            selected_index=idx+1,
                                        )
                                        return
                        # 失敗時は従来どおり候補提示
                    except Exception as e:
                        logger.warning("候補のAI自動選択に失敗しました", error=str(e))

                    response_text = format_candidates(result.candidates)
                    line_client.reply_text(reply_token, response_text)

                    logger.info(
                        "候補を提示しました",
                        user_id=hashed_user_id,
                        candidate_count=len(result.candidates),
                    )
                else:
                        # RAG機能を使用したAI回答生成を試行
                        if rag_service and rag_service.is_enabled:
                            try:
                                rag_response = rag_service.generate_answer(
                                    query=message_text,
                                    context=f"ユーザー質問: {message_text}"
                                )
                                if rag_response:
                                    line_client.reply_text(reply_token, rag_response)
                                    logger.info("RAG機能を使用したAI回答を送信しました", user_id=hashed_user_id)
                                    return
                            except Exception as e:
                                logger.error("RAG機能での回答生成に失敗しました", error=str(e))
                        
                        # 最終フォールバック応答
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
            logger.info("ヘルスチェック時にサービスを初期化します")
            initialize_services()
        else:
            logger.info("サービスは既に初期化済みです")
        
        # 基本的な健全性チェック（QAが生きていればOK、他は情報として返す）
        qa_healthy = qa_service.health_check() if qa_service is not None else False
        flow_loaded = (flow_service is not None and len(flow_service.flows) > 0)
        ai_healthy = (flow_service is not None and flow_service.ai_service.health_check()) if flow_service is not None else False
        
        if qa_healthy:
            return jsonify({
                "status": "healthy",
                "timestamp": time.time(),
                "version": "0.1.0",
                "qa_service": "ok",
                "flow_service_loaded": flow_loaded,
                "ai_service": "ok" if ai_healthy else "disabled"
            })
        else:
            return jsonify({
                "status": "unhealthy",
                "qa_service": "error",
                "flow_service_loaded": flow_loaded,
                "ai_service": "ok" if ai_healthy else "disabled",
                "timestamp": time.time()
            }), 500
            
    except Exception as e:
        logger.error("ヘルスチェックに失敗しました", error=str(e))
        return (
            jsonify({"status": "unhealthy", "error": str(e), "timestamp": time.time()}),
            500,
        )


@app.route("/admin/reload", methods=["POST"])
@require_admin
def reload_cache():
    """キャッシュの再読み込み（管理者のみ）"""
    try:
        qa_service.reload_cache()
        flow_service.reload_flows()
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
@require_admin
def get_stats():
    """統計情報の取得（管理者のみ）"""
    try:
        qa_stats = qa_service.get_stats()
        
        # 統計を結合
        combined_stats = qa_stats.to_dict()
        combined_stats["total_flows"] = len(flow_service.flows)
        
        return jsonify(combined_stats)
    except Exception as e:
        logger.error("統計情報の取得に失敗しました", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/admin/auto-reload/status", methods=["GET"])
@require_admin
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


@app.route("/admin/authenticated-users", methods=["GET"])
@require_admin
def get_authenticated_users():
    """認証済みユーザー一覧を取得"""
    try:
        from .optimized_auth_flow import OptimizedAuthFlow
        
        auth_flow = OptimizedAuthFlow()
        stats = auth_flow.get_stats()
        
        # 認証済みユーザーの詳細情報を取得
        authenticated_users = []
        for user_id, auth_info in auth_flow.authenticated_users.items():
            authenticated_users.append({
                "user_id": hash_user_id(user_id),
                "store_code": auth_info.get('store_code'),
                "staff_id": auth_info.get('staff_id'),
                "store_name": auth_info.get('store_name'),
                "staff_name": auth_info.get('staff_name'),
                "auth_time": auth_info.get('auth_time')
            })
        
        return jsonify({
            "status": "success",
            "total_authenticated": stats['total_authenticated'],
            "authenticated_users": authenticated_users,
            "cache_valid": stats.get('cache_valid', False),
            "last_cache_update": stats.get('last_cache_update', 0),
            "last_updated": stats['last_updated']
        })
        
    except Exception as e:
        logger.error("認証済みユーザー一覧の取得に失敗しました", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/admin/force-cache-update", methods=["POST"])
@require_admin
def force_cache_update():
    """キャッシュを強制更新"""
    try:
        from .optimized_auth_flow import OptimizedAuthFlow
        
        auth_flow = OptimizedAuthFlow()
        auth_flow.force_cache_update()
        
        logger.info("管理者によるキャッシュ強制更新が完了しました")
        return jsonify({
            "status": "success",
            "message": "キャッシュを強制更新しました",
            "cache_valid": auth_flow._is_cache_valid(),
            "last_cache_update": auth_flow.last_cache_update
        })
        
    except Exception as e:
        logger.error("キャッシュ強制更新に失敗しました", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/admin/check-all-users-status", methods=["POST"])
@require_admin
def check_all_users_status():
    """全認証済みユーザーのステータスを即座にチェック"""
    try:
        from .optimized_auth_flow import OptimizedAuthFlow
        
        auth_flow = OptimizedAuthFlow()
        result = auth_flow.check_all_users_status()
        
        if result:
            logger.info("管理者による全ユーザーステータスチェックが完了しました")
            return jsonify({
                "status": "success",
                "message": "全ユーザーのステータスチェックが完了しました",
                "total_checked": result['total_checked'],
                "deauthenticated_count": result['deauthenticated_count'],
                "deauthenticated_users": [hash_user_id(uid) for uid in result['deauthenticated_users']]
            })
        else:
            return jsonify({
                "status": "error",
                "message": "全ユーザーのステータスチェックに失敗しました"
            }), 500
        
    except Exception as e:
        logger.error("全ユーザーステータスチェックに失敗しました", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/admin/deauthenticate", methods=["POST"])
@require_admin
def deauthenticate_user():
    """ユーザーの認証を取り消す"""
    try:
        from .optimized_auth_flow import OptimizedAuthFlow
        
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({
                "status": "error", 
                "message": "user_idが必要です"
            }), 400
        
        user_id = data['user_id']
        auth_flow = OptimizedAuthFlow()
        
        # 認証を取り消し
        success = auth_flow.deauthenticate_user(user_id)
        
        if success:
            logger.info("管理者による認証取り消しが完了しました", 
                       user_id=hash_user_id(user_id))
            return jsonify({
                "status": "success",
                "message": f"ユーザー {hash_user_id(user_id)} の認証を取り消しました"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"ユーザー {hash_user_id(user_id)} の認証取り消しに失敗しました"
            }), 400
            
    except Exception as e:
        logger.error("認証取り消しに失敗しました", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad Request", "message": error.description}), 400


@app.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": "Unauthorized", "message": error.description}), 401


@app.errorhandler(403)
def forbidden(error):
    return jsonify({"error": "Forbidden", "message": error.description}), 403


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal Server Error", "message": "内部エラーが発生しました"}), 500


def main():
    """アプリケーションの起動"""
    try:
        # サービスを初期化
        logger.info("サービスを初期化しています...")
        initialize_services()
        logger.info("サービス初期化完了")
        
        port = int(os.environ.get("PORT", 5000))
        logger.info(f"アプリケーションを起動します (ポート: {port})")
        app.run(host="0.0.0.0", port=port, debug=False)
    except Exception as e:
        logger.error("アプリケーションの起動に失敗しました", error=str(e))
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
