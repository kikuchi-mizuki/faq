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

    def __init__(self, ai_service=None):
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
        
        # AIサービスの初期化
        self.ai_service = ai_service

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
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets.readonly",
                    "https://www.googleapis.com/auth/spreadsheets"
                ],
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

            # AIが有効な場合は、AIによる文脈理解で最適な回答を選択
            ai_boost_used = False
            search_results = []

            if self.ai_service and self.ai_service.is_enabled:
                # AIによる文脈判断を最優先
                ai_results = self._search_with_ai_context(query)
                if ai_results:
                    search_results = ai_results
                    ai_boost_used = True
                    logger.info("AI文脈判断で回答を選択しました", query=query)
                else:
                    # AIで見つからない場合のみキーワードマッチング
                    logger.info("AIで回答が見つからず、キーワードマッチングを試行", query=query)
                    search_results = self._search_qa_items(query)
            else:
                # AIが無効な場合はキーワードマッチング
                logger.info("AIが無効のため、キーワードマッチングを使用", query=query)
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
                elif ai_boost_used:
                    # AIが選んだ候補がある場合はしきい値未満でも採用（柔軟に回答）
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

    def _search_with_ai_context(self, query: str) -> List[SearchResult]:
        """AI文脈判断によるQ&A検索"""
        try:
            if not self.ai_service or not self.ai_service.is_enabled:
                return []

            # 既存のQ&A内容を取得（ID付き）
            qa_contents = self._get_qa_contents_for_ai()

            # AIに文脈判断を依頼
            context_prompt = f"""
あなたは動画制作会社のカスタマーサポートAIです。
ユーザーの質問の意図を深く理解し、最も適切なQ&Aを選択してください。

【既存のQ&A一覧】
{qa_contents}

【ユーザーの質問】
{query}

【重要な判断基準】
1. 質問の**本質的な意図**を理解する
   - 「ヒアリング項目は？」→ ユーザーは必要な情報を知りたい
   - 「制作フローは？」→ ユーザーは制作の流れを知りたい
2. キーワードではなく**文脈と意味**で判断
3. 最も関連性が高いQ&AのIDを選択
4. 該当するQ&Aがない場合は「NONE」と回答

【例】
- 「顧客からヒアリングする項目は？」→ ヒアリング項目に関するQ&AのID
- 「制作の流れを教えて」→ 制作フローに関するQ&AのID
- 「全く関係ない質問」→ NONE

回答は該当するQ&AのID番号のみ（例: 6）、または「NONE」。説明不要。
"""

            # AI回答を生成
            response = self.ai_service.model.generate_content(context_prompt)
            if response and response.text:
                ai_response = response.text.strip()
                logger.info(f"AI文脈判断結果: '{query}' -> '{ai_response}'")

                # NONEの場合は該当なし
                if ai_response.upper() == "NONE":
                    logger.info("AI判断: 該当するQ&Aなし")
                    return []

                # ID番号をパース（柔軟に対応）
                try:
                    # 「ID: 6」「Q&A ID: 6」などの形式に対応
                    import re
                    id_match = re.search(r'\d+', ai_response)
                    if id_match:
                        qa_id = int(id_match.group())
                    else:
                        raise ValueError(f"ID番号が見つかりません: {ai_response}")

                    # IDでQ&Aを取得
                    for qa_item in self.qa_items:
                        if qa_item.id == qa_id:
                            # 高スコアで返す（AI判断なので信頼度高い）
                            result = SearchResult(
                                qa_item=qa_item,
                                score=0.95,  # AI判断なので高スコア
                                match_type="ai_context",
                                matched_text=query,
                            )
                            logger.info(f"AI判断でQ&A ID:{qa_id}を選択", question=qa_item.question)
                            return [result]

                    logger.warning(f"AI判断されたID {qa_id} が見つかりません")
                except ValueError:
                    logger.warning(f"AI判断結果がID番号ではありません: '{ai_response}'")
            else:
                logger.warning("AI文脈判断の回答が空です")

        except Exception as e:
            logger.error("AI文脈判断中にエラーが発生しました", error=str(e))

        return []

    def _get_qa_contents_for_ai(self) -> str:
        """AI判断用のQ&A内容を取得（ID付き）"""
        try:
            qa_contents = []
            for qa in self.qa_items:
                # ID、質問、回答の一部を含める
                answer_preview = qa.answer[:150] + "..." if len(qa.answer) > 150 else qa.answer
                qa_contents.append(f"ID: {qa.id}\nQ: {qa.question}\nA: {answer_preview}\n")

            return "\n".join(qa_contents) if qa_contents else "Q&A内容がありません"
        except Exception as e:
            logger.error("Q&A内容の取得に失敗しました", error=str(e))
            return "Q&A内容の取得に失敗しました"

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

    def log_query(
        self,
        user_id_hash: str,
        query: str,
        result: SearchResponse,
        store_code: str = "",
        staff_id: str = ""
    ):
        """
        質問をGoogle Sheetsに記録

        Args:
            user_id_hash: ハッシュ化されたユーザーID
            query: ユーザーの質問
            result: 検索結果
            store_code: 店舗コード（認証時）
            staff_id: スタッフID（認証時）
        """
        if not Config.QUERY_LOG_ENABLED:
            return

        try:
            # ログデータの作成
            timestamp = datetime.now().isoformat()
            result_type = "found" if result.is_found else "not_found"
            matched_qa_id = result.top_result.id if result.top_result else ""
            response_time_ms = result.search_time_ms

            log_row = [
                timestamp,
                user_id_hash,
                query,
                result_type,
                matched_qa_id,
                response_time_ms,
                store_code,
                staff_id
            ]

            # Google Sheetsに追記
            try:
                sheet = self.gc.open_by_key(self.sheet_id).worksheet(Config.QUERY_LOG_SHEET)
                sheet.append_row(log_row)
                logger.info("質問をログに記録しました", query=query, result_type=result_type)
            except gspread.WorksheetNotFound:
                logger.warning(f"{Config.QUERY_LOG_SHEET}シートが見つかりません。ログ機能を無効にするか、シートを作成してください。")
            except Exception as e:
                logger.error("質問ログの記録に失敗しました", error=str(e))

        except Exception as e:
            logger.error("質問ログ処理中にエラーが発生しました", error=str(e))

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

    def find_answer_from_qa_list(self, query: str) -> Optional[SearchResponse]:
        """qa_listシートから回答を検索"""
        if not query or not query.strip():
            return None

        # キャッシュをチェック
        cache_key = f"qa_list_search:{query}"
        if cache_key in self.cache:
            logger.info("キャッシュからqa_list回答を取得しました", query=query)
            return self.cache[cache_key]

        try:
            # qa_listシートのデータを取得
            qa_list_data = self._load_qa_list_data()
            
            if not qa_list_data:
                logger.warning("qa_listシートのデータが取得できませんでした")
                return None

            # 検索実行
            results = self._search_qa_list_items(query, qa_list_data)
            
            if not results:
                logger.info("qa_listから該当する回答が見つかりませんでした", query=query)
                return None

            # 最適な回答を選択
            best_result = results[0]
            response = SearchResponse(
                answer=best_result.answer,
                score=best_result.score,
                keywords=best_result.keywords,
                source="qa_list"
            )

            # キャッシュに保存
            self.cache[cache_key] = response
            logger.info("qa_listから回答を検索しました", query=query, score=best_result.score)
            return response

        except Exception as e:
            logger.error("qa_list検索中にエラーが発生しました", error=str(e), query=query)
            return None

    def _load_qa_list_data(self) -> List[Dict[str, Any]]:
        """qa_listシートのデータを読み込み"""
        try:
            # スプレッドシートを開く
            credentials = Credentials.from_service_account_info(
                json.loads(Config.GOOGLE_SERVICE_ACCOUNT_JSON),
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            gc = gspread.authorize(credentials)
            spreadsheet = gc.open_by_key(self.sheet_id)
            
            # qa_listシートの存在確認
            try:
                qa_list_sheet = spreadsheet.worksheet('qa_list')
                data = qa_list_sheet.get_all_records()
                
                if not data:
                    logger.warning("qa_listシートは存在しますが、データが空です")
                    return []
                
                logger.info(f"qa_listシートから{len(data)}件のデータを読み込みました")
                return data
                
            except gspread.WorksheetNotFound:
                logger.warning("qa_listシートが見つかりません。シートを作成するか、既存のシート名を確認してください")
                return []
            
        except Exception as e:
            logger.error("qa_listシートの読み込み中にエラーが発生しました", error=str(e))
            return []

    def _search_qa_list_items(self, query: str, qa_list_data: List[Dict[str, Any]]) -> List[SearchResult]:
        """qa_listシートのアイテムを検索"""
        if not query or not qa_list_data:
            return []

        normalized_query = normalize_text(query)
        query_keywords = extract_keywords(normalized_query)
        results = []

        for item in qa_list_data:
            # 質問と回答のテキストを取得
            question = item.get('question', '')
            answer = item.get('answer', '')
            
            if not question and not answer:
                continue

            # スコア計算
            score = self._calculate_qa_list_score(item, normalized_query, query_keywords)
            
            if score > 0:
                result = SearchResult(
                    id=item.get('id', 0),
                    question=question,
                    answer=answer,
                    score=score,
                    keywords=query_keywords,
                    source="qa_list"
                )
                results.append(result)

        # スコア順でソート
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:5]  # 上位5件を返す

    def _calculate_qa_list_score(self, item: Dict[str, Any], query: str, query_keywords: List[str]) -> float:
        """qa_listアイテムのスコアを計算"""
        question = item.get('question', '')
        answer = item.get('answer', '')
        keywords = item.get('keywords', '')
        
        # 質問との類似度
        question_score = 0
        if question:
            question_score = fuzz.ratio(query, question) / 100.0
        
        # 回答との類似度
        answer_score = 0
        if answer:
            answer_score = fuzz.ratio(query, answer) / 100.0
        
        # キーワードとの一致
        keyword_score = 0
        if keywords:
            keyword_list = [k.strip() for k in keywords.split(',')]
            for keyword in keyword_list:
                if keyword.lower() in query.lower():
                    keyword_score += 0.3
        
        # 重み付きスコア計算
        total_score = (question_score * 0.5 + answer_score * 0.3 + keyword_score * 0.2)
        
        return min(total_score, 1.0)  # 最大1.0に制限
