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

    # キャッシュ設定
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "300"))

    # 管理者設定
    ADMIN_USER_IDS = (
        os.environ.get("ADMIN_USER_IDS", "").split(",")
        if os.environ.get("ADMIN_USER_IDS")
        else []
    )

    # ログ設定
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # マッチング設定
    MATCH_THRESHOLD = float(os.environ.get("MATCH_THRESHOLD", "0.72"))
    MAX_CANDIDATES = int(os.environ.get("MAX_CANDIDATES", "3"))

    # セキュリティ設定
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    @classmethod
    def validate(cls) -> List[str]:
        """設定の妥当性を検証し、問題があればエラーメッセージのリストを返す"""
        errors = []

        if not cls.LINE_CHANNEL_SECRET:
            errors.append("LINE_CHANNEL_SECRETが設定されていません")

        if not cls.LINE_CHANNEL_ACCESS_TOKEN:
            errors.append("LINE_CHANNEL_ACCESS_TOKENが設定されていません")

        if not cls.GOOGLE_SERVICE_ACCOUNT_JSON:
            errors.append("GOOGLE_SERVICE_ACCOUNT_JSONが設定されていません")

        if not cls.SHEET_ID_QA:
            errors.append("SHEET_ID_QAが設定されていません")

        if cls.CACHE_TTL_SECONDS <= 0:
            errors.append("CACHE_TTL_SECONDSは正の整数である必要があります")

        if cls.MATCH_THRESHOLD < 0 or cls.MATCH_THRESHOLD > 1:
            errors.append("MATCH_THRESHOLDは0から1の間である必要があります")

        if cls.MAX_CANDIDATES <= 0:
            errors.append("MAX_CANDIDATESは正の整数である必要があります")

        return errors

    @classmethod
    def is_production(cls) -> bool:
        """本番環境かどうかを判定"""
        return os.environ.get("FLASK_ENV") == "production"

    @classmethod
    def get_debug_mode(cls) -> bool:
        """デバッグモードの設定を取得"""
        return not cls.is_production()
