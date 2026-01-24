"""
アプリケーション設定管理
"""

import os
from typing import List
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()


class Config:
    """アプリケーション設定クラス"""

    # LINE設定
    LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
    LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

    # Google Sheets設定
    GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    SHEET_ID_QA = os.environ.get("SHEET_ID_QA", "")

    # Redis設定
    REDIS_ENABLED = os.environ.get("REDIS_ENABLED", "false").lower() == "true"
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
    REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

    # キャッシュ設定
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "300"))

    # 管理者設定
    ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")

    # ログ設定
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # マッチング設定
    MATCH_THRESHOLD = float(os.environ.get("MATCH_THRESHOLD", "0.72"))
    MAX_CANDIDATES = int(os.environ.get("MAX_CANDIDATES", "3"))

    # セキュリティ設定
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    @classmethod
    def check_production_security(cls):
        """本番環境のセキュリティ設定をチェック"""
        if cls.is_production():
            errors = []
            warnings = []

            # デフォルト値が使用されている場合はエラー（本番環境では起動を拒否）
            if cls.SECRET_KEY == "dev-secret-key-change-in-production":
                errors.append("❌ SECRET_KEYがデフォルト値です。本番環境では必ず変更してください")

            if cls.HASH_SALT == "line_qa_system_default_salt_change_in_production":
                errors.append("❌ HASH_SALTがデフォルト値です。本番環境では必ず変更してください")

            # SECRET_KEYとHASH_SALTの長さチェック
            if len(cls.SECRET_KEY) < 32:
                warnings.append("⚠️ SECRET_KEYが短すぎます（推奨: 32文字以上）")

            if len(cls.HASH_SALT) < 16:
                warnings.append("⚠️ HASH_SALTが短すぎます（推奨: 16文字以上）")

            # ADMIN_API_KEYのチェック
            if not cls.ADMIN_API_KEY or cls.ADMIN_API_KEY == "":
                warnings.append("⚠️ ADMIN_API_KEYが設定されていません")
            elif len(cls.ADMIN_API_KEY) < 32:
                warnings.append("⚠️ ADMIN_API_KEYが短すぎます（推奨: 32文字以上）")

            if errors or warnings:
                import structlog
                logger = structlog.get_logger(__name__)

                for error in errors:
                    logger.error(error)
                    print(error)

                for warning in warnings:
                    logger.warning(warning)
                    print(warning)

                # 本番環境でエラーがある場合は起動を拒否
                if errors:
                    raise ValueError(
                        f"本番環境のセキュリティ設定にエラーがあります: {', '.join(errors)}"
                    )
    
    # 認証設定
    AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "false").lower() == "true"
    AUTH_TIMEOUT = int(os.environ.get("AUTH_TIMEOUT", "300"))
    AUTH_MAX_ATTEMPTS = int(os.environ.get("AUTH_MAX_ATTEMPTS", "3"))
    AUTH_SESSION_DAYS = int(os.environ.get("AUTH_SESSION_DAYS", "30"))
    
    # 店舗管理設定
    STORE_MANAGEMENT_SHEET = os.environ.get("STORE_MANAGEMENT_SHEET", "store_management")
    STORE_CODE_PREFIX = os.environ.get("STORE_CODE_PREFIX", "STORE")
    
    # スタッフ管理設定
    STAFF_MANAGEMENT_SHEET = os.environ.get("STAFF_MANAGEMENT_SHEET", "staff_management")
    
    # LINEログイン設定
    LINE_LOGIN_CHANNEL_ID = os.environ.get("LINE_LOGIN_CHANNEL_ID", "")
    LINE_LOGIN_CHANNEL_SECRET = os.environ.get("LINE_LOGIN_CHANNEL_SECRET", "")
    LINE_LOGIN_REDIRECT_URI = os.environ.get("LINE_LOGIN_REDIRECT_URI", "")

    # クエリログ設定
    QUERY_LOG_ENABLED = os.environ.get("QUERY_LOG_ENABLED", "true").lower() == "true"
    QUERY_LOG_SHEET = os.environ.get("QUERY_LOG_SHEET", "query_log")

    # ファイルアップロード設定
    MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "10"))  # 最大ファイルサイズ（MB）
    UPLOAD_RATE_LIMIT_PER_HOUR = int(os.environ.get("UPLOAD_RATE_LIMIT_PER_HOUR", "10"))  # 1時間あたりの最大アップロード数

    # ハッシュ化設定
    HASH_SALT = os.environ.get("HASH_SALT", "line_qa_system_default_salt_change_in_production")

    @classmethod
    def validate(cls) -> List[str]:
        """設定の妥当性を検証し、問題があればエラーメッセージのリストを返す"""
        errors = []

        # 必須の環境変数
        if not cls.LINE_CHANNEL_SECRET:
            errors.append("LINE_CHANNEL_SECRETが設定されていません")

        if not cls.LINE_CHANNEL_ACCESS_TOKEN:
            errors.append("LINE_CHANNEL_ACCESS_TOKENが設定されていません")

        if not cls.GOOGLE_SERVICE_ACCOUNT_JSON:
            errors.append("GOOGLE_SERVICE_ACCOUNT_JSONが設定されていません")

        if not cls.SHEET_ID_QA:
            errors.append("SHEET_ID_QAが設定されていません")

        # 本番環境では管理者APIキーが必須
        if cls.is_production() and not cls.ADMIN_API_KEY:
            errors.append("本番環境ではADMIN_API_KEYの設定が必須です")

        # 数値の範囲チェック
        if cls.CACHE_TTL_SECONDS <= 0:
            errors.append("CACHE_TTL_SECONDSは正の整数である必要があります")

        if cls.MATCH_THRESHOLD < 0 or cls.MATCH_THRESHOLD > 1:
            errors.append("MATCH_THRESHOLDは0から1の間である必要があります")

        if cls.MAX_CANDIDATES <= 0:
            errors.append("MAX_CANDIDATESは正の整数である必要があります")

        if cls.MAX_FILE_SIZE_MB <= 0:
            errors.append("MAX_FILE_SIZE_MBは正の整数である必要があります")

        if cls.UPLOAD_RATE_LIMIT_PER_HOUR <= 0:
            errors.append("UPLOAD_RATE_LIMIT_PER_HOURは正の整数である必要があります")

        return errors

    @classmethod
    def is_production(cls) -> bool:
        """本番環境かどうかを判定"""
        return os.environ.get("FLASK_ENV") == "production"

    @classmethod
    def get_debug_mode(cls) -> bool:
        """デバッグモードの設定を取得"""
        return not cls.is_production()
