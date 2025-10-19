#!/usr/bin/env python3
"""
qa_listシート対応の追加メソッド
"""

def add_qa_list_support():
    """qa_listシート対応のメソッドを追加"""
    
    qa_list_methods = '''
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
            
            # qa_listシートを取得
            qa_list_sheet = spreadsheet.worksheet('qa_list')
            data = qa_list_sheet.get_all_records()
            
            logger.info(f"qa_listシートから{len(data)}件のデータを読み込みました")
            return data
            
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
'''
    
    return qa_list_methods

if __name__ == "__main__":
    print("qa_listシート対応のメソッドを生成しました")
