"""
Q&A検索サービス
"""

import time
import base64
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from cachetools import TTLCache
import structlog

import gspread
from google.oauth2.service_account import Credentials
from rapidfuzz import fuzz, process

from .models import QAItem, SearchResult, SearchResponse, SystemStats
from .config import Config
from .utils import normalize_text, extract_keywords, split_comma_separated

logger = structlog.get_logger(__name__)


class QAService:
    """Q&A検索サービス"""

    def __init__(self):
        """初期化"""
        self.sheet_id = Config.SHEET_ID_QA
        self.cache = TTLCache(maxsize=1000, ttl=Config.CACHE_TTL_SECONDS)
        self.qa_items: List[QAItem] = []
        self.last_updated = datetime.now()
        self.stats = {
            "total_requests": 0,
            "successful_matches": 0,
            "cache_hits": 0,
            "response_times": [],
        }

        # Google Sheets APIの初期化
        self._init_google_sheets()

        # 初期データの読み込み
        self.reload_cache()

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
            logger.info("Google Sheets APIの初期化が完了しました")

        except Exception as e:
            logger.error("Google Sheets APIの初期化に失敗しました", error=str(e))
            raise

    def reload_cache(self):
        """キャッシュの再読み込み"""
        try:
            start_time = time.time()

            # スプレッドシートからデータを取得
            sheet = self.gc.open_by_key(self.sheet_id).worksheet("qa_items")
            all_values = sheet.get_all_records()

            # データの変換
            self.qa_items = []
            for row in all_values:
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

                    qa_item = QAItem(
                        id=int(row.get("id", 0)),
                        question=str(row.get("question", "")),
                        keywords=str(row.get("keywords", "")),
                        synonyms=str(row.get("synonyms", "")),
                        tags=str(row.get("tags", "")),
                        answer=str(row.get("answer", "")),
                        priority=int(row.get("priority", 1)),
                        status=str(row.get("status", "active")),
                        updated_at=updated_at,
                    )

                    # アクティブなアイテムのみ追加
                    if qa_item.is_active:
                        self.qa_items.append(qa_item)

                except Exception as e:
                    logger.warning("行の解析に失敗しました", row=row, error=str(e))
                    continue

            self.last_updated = datetime.now()
            self.cache.clear()

            load_time = time.time() - start_time
            logger.info(
                "キャッシュの再読み込みが完了しました",
                item_count=len(self.qa_items),
                load_time_ms=int(load_time * 1000),
            )

        except Exception as e:
            logger.error("キャッシュの再読み込みに失敗しました", error=str(e))
            raise

    def find_answer(self, query: str) -> SearchResponse:
        """
        クエリに対する回答を検索

        Args:
            query: 検索クエリ

        Returns:
            検索結果
        """
        start_time = time.time()
        self.stats["total_requests"] += 1

        try:
            # キャッシュチェック
            cache_key = f"search:{normalize_text(query)}"
            if cache_key in self.cache:
                self.stats["cache_hits"] += 1
                cached_result = self.cache[cache_key]
                cached_result.search_time_ms = int((time.time() - start_time) * 1000)
                return cached_result

            # 検索実行
            search_results = self._search_qa_items(query)

            # 結果の構築
            is_found = False
            top_result = None
            candidates = []

            if search_results:
                # スコアでソート
                search_results.sort(key=lambda x: x.score, reverse=True)

                # 閾値チェック
                if search_results[0].score >= Config.MATCH_THRESHOLD:
                    is_found = True
                    top_result = search_results[0]

                # 候補の取得
                candidates = search_results[: Config.MAX_CANDIDATES]

            # 応答の作成
            response = SearchResponse(
                is_found=is_found,
                top_result=top_result,
                candidates=candidates,
                total_candidates=len(candidates),
                search_time_ms=int((time.time() - start_time) * 1000),
            )

            # 成功したマッチの記録
            if is_found:
                self.stats["successful_matches"] += 1

            # 応答時間の記録
            self.stats["response_times"].append(response.search_time_ms)
            if len(self.stats["response_times"]) > 100:
                self.stats["response_times"] = self.stats["response_times"][-100:]

            # キャッシュに保存
            self.cache[cache_key] = response

            return response

        except Exception as e:
            logger.error("検索中にエラーが発生しました", query=query, error=str(e))
            # エラー時は空の応答を返す
            return SearchResponse(
                is_found=False,
                top_result=None,
                candidates=[],
                total_candidates=0,
                search_time_ms=int((time.time() - start_time) * 1000),
            )

    def _search_qa_items(self, query: str) -> List[SearchResult]:
        """
        Q&Aアイテムの検索

        Args:
            query: 検索クエリ

        Returns:
            検索結果のリスト
        """
        if not query or not self.qa_items:
            return []

        normalized_query = normalize_text(query)
        query_keywords = extract_keywords(normalized_query)

        results = []

        for qa_item in self.qa_items:
            score = self._calculate_score(qa_item, normalized_query, query_keywords)

            if score > 0:
                # マッチタイプの判定
                match_type = self._determine_match_type(
                    qa_item, normalized_query, score
                )
                matched_text = self._get_matched_text(qa_item, normalized_query)

                result = SearchResult(
                    qa_item=qa_item,
                    score=score,
                    match_type=match_type,
                    matched_text=matched_text,
                )

                results.append(result)

        return results

    def _calculate_score(
        self, qa_item: QAItem, query: str, query_keywords: List[str]
    ) -> float:
        """
        スコアの計算

        Args:
            qa_item: Q&Aアイテム
            query: 正規化されたクエリ
            query_keywords: クエリのキーワード

        Returns:
            スコア（0.0〜1.0）
        """
        max_score = 0.0

        # 検索対象テキストの取得
        searchable_texts = qa_item.get_all_searchable_texts()

        for text in searchable_texts:
            if not text:
                continue

            normalized_text = normalize_text(text)

            # 1. 厳密一致
            if query == normalized_text:
                score = 1.0
            # 2. フレーズ部分一致
            elif query in normalized_text or normalized_text in query:
                score = 0.6
            # 3. キーワード部分一致
            elif any(keyword in normalized_text for keyword in query_keywords):
                score = 0.4
            # 4. Fuzzy一致
            else:
                # rapidfuzzを使用した類似度計算
                ratio = fuzz.partial_ratio(query, normalized_text) / 100.0
                token_sort_ratio = fuzz.token_sort_ratio(query, normalized_text) / 100.0
                score = (ratio + token_sort_ratio) / 2.0

            # 優先度の重み付け
            if score > 0:
                score *= 1 + qa_item.priority * 0.05
                max_score = max(max_score, score)

        return min(max_score, 1.0)

    def _determine_match_type(self, qa_item: QAItem, query: str, score: float) -> str:
        """
        マッチタイプの判定

        Args:
            qa_item: Q&Aアイテム
            query: 正規化されたクエリ
            score: スコア

        Returns:
            マッチタイプ
        """
        if score >= 0.9:
            return "exact_match"
        elif score >= 0.7:
            return "phrase_match"
        elif score >= 0.5:
            return "keyword_match"
        else:
            return "fuzzy_match"

    def _get_matched_text(self, qa_item: QAItem, query: str) -> str:
        """
        マッチしたテキストを取得

        Args:
            qa_item: Q&Aアイテム
            query: 正規化されたクエリ

        Returns:
            マッチしたテキスト
        """
        searchable_texts = qa_item.get_all_searchable_texts()

        for text in searchable_texts:
            normalized_text = normalize_text(text)
            if query in normalized_text or normalized_text in query:
                return text

        return qa_item.question

    def health_check(self) -> bool:
        """
        ヘルスチェック

        Returns:
            健全な場合はTrue
        """
        try:
            # 基本的なチェック
            if not self.qa_items:
                return False

            # スプレッドシートへの接続テスト
            sheet = self.gc.open_by_key(self.sheet_id).worksheet("qa_items")
            sheet.get_all_records()

            return True

        except Exception as e:
            logger.error("ヘルスチェックに失敗しました", error=str(e))
            return False

    def get_stats(self) -> SystemStats:
        """
        システム統計情報を取得

        Returns:
            統計情報
        """
        # 平均応答時間の計算
        avg_response_time = 0.0
        if self.stats["response_times"]:
            avg_response_time = sum(self.stats["response_times"]) / len(
                self.stats["response_times"]
            )

        # キャッシュヒット率の計算
        cache_hit_rate = 0.0
        if self.stats["total_requests"] > 0:
            cache_hit_rate = self.stats["cache_hits"] / self.stats["total_requests"]

        return SystemStats(
            total_qa_items=len(self.qa_items),
            active_qa_items=len([item for item in self.qa_items if item.is_active]),
            cache_hit_rate=cache_hit_rate,
            average_response_time_ms=avg_response_time,
            total_requests=self.stats["total_requests"],
            successful_matches=self.stats["successful_matches"],
            last_updated=self.last_updated,
        )

    def get_qa_item_by_id(self, item_id: int) -> Optional[QAItem]:
        """
        IDでQ&Aアイテムを取得

        Args:
            item_id: アイテムID

        Returns:
            Q&Aアイテム（見つからない場合はNone）
        """
        for item in self.qa_items:
            if item.id == item_id:
                return item
        return None

    def search_by_tags(self, tags: List[str]) -> List[QAItem]:
        """
        タグでQ&Aアイテムを検索

        Args:
            tags: タグのリスト

        Returns:
            マッチしたQ&Aアイテムのリスト
        """
        if not tags:
            return []

        results = []
        for item in self.qa_items:
            item_tags = set(item.tag_list)
            if any(tag in item_tags for tag in tags):
                results.append(item)

        return results
