"""
資料ナビゲーションサービス（STEP3）
"""

import time
import base64
import json
from typing import List, Optional
from datetime import datetime
import structlog

import gspread
from google.oauth2.service_account import Credentials
from rapidfuzz import fuzz

from .models import LocationItem, QAFormLog
from .config import Config
from .utils import normalize_text

logger = structlog.get_logger(__name__)


class LocationService:
    """資料ナビゲーションサービス"""

    def __init__(self):
        """初期化"""
        self.sheet_id = Config.SHEET_ID_QA
        self.locations: List[LocationItem] = []
        self.form_logs: List[QAFormLog] = []
        self.last_updated = datetime.now()

        # Google Sheets APIの初期化
        self._init_google_sheets()

        # 初期データの読み込み
        self.reload_locations()
        self.reload_form_logs()

    def _init_google_sheets(self):
        """Google Sheets APIの初期化"""
        try:
            # サービスアカウントJSONのデコード
            service_account_info = json.loads(
                base64.b64decode(Config.GOOGLE_SERVICE_ACCOUNT_JSON)
            )

            # 認証情報の作成
            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )

            # クライアントの作成
            self.gc = gspread.authorize(credentials)
            logger.info("LocationService: Google Sheets APIの初期化が完了しました")

        except Exception as e:
            logger.error("LocationService: Google Sheets APIの初期化に失敗しました", error=str(e))
            raise

    def reload_locations(self):
        """locationsシートの再読み込み"""
        try:
            start_time = time.time()

            # スプレッドシートからデータを取得
            sheet = self.gc.open_by_key(self.sheet_id).worksheet("locations")
            all_values = sheet.get_all_records()

            # データの変換
            self.locations = []
            for i, row in enumerate(all_values, start=1):
                try:
                    # 日時の解析
                    updated_at_str = row.get("updated_at", "")
                    if updated_at_str:
                        try:
                            updated_at = datetime.fromisoformat(
                                updated_at_str.replace("Z", "+00:00")
                            )
                        except:
                            updated_at = datetime.now()
                    else:
                        updated_at = datetime.now()

                    location_item = LocationItem(
                        id=i,
                        category=str(row.get("category", "")),
                        title=str(row.get("title", "")),
                        url=str(row.get("url", "")),
                        description=str(row.get("description", "")),
                        tags=str(row.get("tags", "")),
                        updated_at=updated_at,
                    )

                    self.locations.append(location_item)

                except Exception as e:
                    logger.warning("location行の解析に失敗しました", row=row, error=str(e))
                    continue

            self.last_updated = datetime.now()

            load_time = time.time() - start_time
            logger.info(
                "locationsシートの再読み込みが完了しました",
                location_count=len(self.locations),
                load_time_ms=int(load_time * 1000),
            )

        except Exception as e:
            logger.error("locationsシートの再読み込みに失敗しました", error=str(e))
            # シートが存在しない場合はエラーにせず空のリストとする
            self.locations = []

    def reload_form_logs(self):
        """qa_form_logシートの再読み込み（Googleフォーム連携は無効化）"""
        # Googleフォーム連携は不要のため、空のリストを設定
        self.form_logs = []
        logger.info("Googleフォーム連携は無効化されています。スプレッドシート直接更新方式を使用してください。")

    def search_locations(self, query: str) -> List[LocationItem]:
        """
        資料を検索

        Args:
            query: 検索クエリ

        Returns:
            マッチした資料のリスト
        """
        if not query or not self.locations:
            return []

        normalized_query = normalize_text(query)
        results = []

        for location in self.locations:
            score = self._calculate_location_score(location, normalized_query)
            if score > 0.4:  # 閾値：40%以上
                results.append((location, score))

        # スコア順にソート
        results.sort(key=lambda x: x[1], reverse=True)

        return [item[0] for item in results[:5]]  # 上位5件

    def _calculate_location_score(self, location: LocationItem, query: str) -> float:
        """
        資料のマッチスコアを計算

        Args:
            location: 資料アイテム
            query: 正規化されたクエリ

        Returns:
            スコア（0.0〜1.0）
        """
        max_score = 0.0

        # 検索対象テキスト
        searchable_texts = [
            location.category,
            location.title,
            location.description,
        ] + location.tag_list

        for text in searchable_texts:
            if not text:
                continue

            normalized_text = normalize_text(text)

            # 厳密一致
            if query == normalized_text:
                score = 1.0
            # 部分一致
            elif query in normalized_text or normalized_text in query:
                score = 0.7
            # Fuzzy一致
            else:
                score = fuzz.partial_ratio(query, normalized_text) / 100.0

            max_score = max(max_score, score)

        return max_score

    def get_location_by_category(self, category: str) -> List[LocationItem]:
        """
        カテゴリで資料を取得

        Args:
            category: カテゴリ名

        Returns:
            該当する資料のリスト
        """
        results = []
        normalized_category = normalize_text(category)

        for location in self.locations:
            if normalize_text(location.category) == normalized_category:
                results.append(location)

        return results

    def get_categories(self) -> List[str]:
        """
        利用可能なカテゴリのリストを取得

        Returns:
            カテゴリ名のリスト
        """
        categories = set()
        for location in self.locations:
            if location.category:
                categories.add(location.category)
        return sorted(list(categories))

    def get_pending_form_logs(self) -> List[QAFormLog]:
        """
        承認待ちのフォーム投稿を取得（Googleフォーム連携は無効化）

        Returns:
            空のリスト（Googleフォーム連携は無効化）
        """
        logger.info("Googleフォーム連携は無効化されています。スプレッドシート直接更新方式を使用してください。")
        return []

    def get_approved_form_logs(self) -> List[QAFormLog]:
        """
        承認済みのフォーム投稿を取得（Googleフォーム連携は無効化）

        Returns:
            空のリスト（Googleフォーム連携は無効化）
        """
        logger.info("Googleフォーム連携は無効化されています。スプレッドシート直接更新方式を使用してください。")
        return []

