"""
認証システム用スプレッドシート作成スクリプト
店舗管理とスタッフ管理のシートを作成
"""

import os
import time
from datetime import datetime
import structlog

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


def create_auth_sheets():
    """認証システム用のスプレッドシートを作成"""
    try:
        from line_qa_system.qa_service import QAService
        
        # QAServiceを初期化
        qa_service = QAService()
        
        # 店舗管理シートの作成
        create_store_management_sheet(qa_service)
        
        # スタッフ管理シートの作成
        create_staff_management_sheet(qa_service)
        
        logger.info("認証システム用スプレッドシートの作成が完了しました")
        
    except Exception as e:
        logger.error("スプレッドシートの作成に失敗しました", error=str(e))
        raise


def create_store_management_sheet(qa_service):
    """店舗管理シートを作成"""
    try:
        sheet_name = "store_management"
        
        # ヘッダー行のデータ
        headers = [
            "store_code",      # 店舗コード
            "store_name",      # 店舗名
            "status",          # ステータス
            "created_at",      # 作成日時
            "last_activity",   # 最終利用日時
            "notes",           # 備考
            "admin_notes",     # 管理者メモ
            "contact_info",    # 連絡先情報
            "location",        # 店舗所在地
            "manager_name"     # 店舗責任者名
        ]
        
        # サンプルデータ
        sample_data = [
            ["STORE001", "本店", "active", datetime.now().isoformat(), "", "本店", "", "03-1234-5678", "東京都渋谷区", "田中太郎"],
            ["STORE002", "渋谷店", "active", datetime.now().isoformat(), "", "渋谷店", "", "03-2345-6789", "東京都渋谷区", "佐藤花子"],
            ["STORE003", "新宿店", "suspended", datetime.now().isoformat(), "", "新宿店（一時休業）", "", "03-3456-7890", "東京都新宿区", "鈴木一郎"]
        ]
        
        # シートを作成
        qa_service.create_sheet(sheet_name, headers, sample_data)
        
        logger.info("店舗管理シートを作成しました", sheet_name=sheet_name)
        
    except Exception as e:
        logger.error("店舗管理シートの作成に失敗しました", error=str(e))
        raise


def create_staff_management_sheet(qa_service):
    """スタッフ管理シートを作成"""
    try:
        sheet_name = "staff_management"
        
        # ヘッダー行のデータ
        headers = [
            "store_code",      # 店舗コード
            "staff_id",        # 社員番号
            "staff_name",      # スタッフ名
            "position",        # 役職
            "status",          # ステータス
            "created_at",      # 作成日時
            "last_activity",   # 最終利用日時
            "line_user_id",    # LINEユーザーID
            "auth_time",       # 認証日時
            "notes"            # 備考
        ]
        
        # サンプルデータ
        sample_data = [
            ["STORE001", "001", "田中太郎", "店長", "active", datetime.now().isoformat(), "", "", "", "本店店長"],
            ["STORE001", "002", "山田花子", "スタッフ", "active", datetime.now().isoformat(), "", "", "", "本店スタッフ"],
            ["STORE002", "003", "佐藤花子", "店長", "active", datetime.now().isoformat(), "", "", "", "渋谷店店長"],
            ["STORE002", "004", "鈴木一郎", "スタッフ", "suspended", datetime.now().isoformat(), "", "", "", "渋谷店スタッフ（一時停止）"]
        ]
        
        # シートを作成
        qa_service.create_sheet(sheet_name, headers, sample_data)
        
        logger.info("スタッフ管理シートを作成しました", sheet_name=sheet_name)
        
    except Exception as e:
        logger.error("スタッフ管理シートの作成に失敗しました", error=str(e))
        raise


def main():
    """メイン処理"""
    try:
        logger.info("認証システム用スプレッドシートの作成を開始します")
        create_auth_sheets()
        logger.info("認証システム用スプレッドシートの作成が完了しました")
        
    except Exception as e:
        logger.error("スプレッドシート作成処理中にエラーが発生しました", error=str(e))
        raise


if __name__ == "__main__":
    main()
