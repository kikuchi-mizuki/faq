"""
分岐会話フローサービス
"""

import time
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog

import gspread
from google.oauth2.service_account import Credentials

from .models import FlowItem, ConversationState
from .config import Config
from .session_service import SessionService
from .ai_service import AIService
from .qa_service import QAService

logger = structlog.get_logger(__name__)


class FlowService:
    """分岐会話フローサービス"""

    def __init__(self, session_service: SessionService, qa_service: QAService = None):
        """初期化"""
        self.sheet_id = Config.SHEET_ID_QA
        self.session_service = session_service
        self.qa_service = qa_service
        self.flows: List[FlowItem] = []
        self.last_updated = datetime.now()

        # AIサービスの初期化
        self.ai_service = AIService()

        # Google Sheets APIの初期化
        self._init_google_sheets()

        # 初期データの読み込み
        self.reload_flows()

    def _init_google_sheets(self):
        """Google Sheets APIの初期化"""
        try:
            # サービスアカウントJSONのデコード
            import base64
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
            logger.info("FlowService: Google Sheets APIの初期化が完了しました")

        except Exception as e:
            logger.error("FlowService: Google Sheets APIの初期化に失敗しました", error=str(e))
            raise

    def reload_flows(self):
        """フローデータの再読み込み"""
        try:
            start_time = time.time()

            # スプレッドシートからデータを取得
            sheet = self.gc.open_by_key(self.sheet_id).worksheet("flows")
            all_values = sheet.get_all_records()

            # データの変換
            self.flows = []
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

                    # end列の処理（TRUE/FALSE文字列をboolに変換）
                    end_value = row.get("end", "FALSE")
                    if isinstance(end_value, str):
                        end_bool = end_value.upper() == "TRUE"
                    else:
                        end_bool = bool(end_value)

                    flow_item = FlowItem(
                        id=int(row.get("id", 0)),
                        trigger=str(row.get("trigger", "")),
                        step=int(row.get("step", 1)),
                        question=str(row.get("question", "")),
                        options=str(row.get("options", "")),
                        next_step=str(row.get("next_step", "")),
                        end=end_bool,
                        fallback_next=int(row.get("fallback_next", 999)),
                        updated_at=updated_at,
                    )

                    self.flows.append(flow_item)

                except Exception as e:
                    logger.warning("フロー行の解析に失敗しました", row=row, error=str(e))
                    continue

            self.last_updated = datetime.now()

            load_time = time.time() - start_time
            logger.info(
                "フローデータの再読み込みが完了しました",
                flow_count=len(self.flows),
                load_time_ms=int(load_time * 1000),
            )

        except Exception as e:
            logger.error("フローデータの再読み込みに失敗しました", error=str(e))
            # flowsシートが存在しない場合はエラーにせず空のリストとする
            self.flows = []

    def get_flow_by_trigger(self, trigger: str, step: int = 1) -> Optional[FlowItem]:
        """
        トリガーとステップでフローを取得

        Args:
            trigger: トリガー名
            step: ステップ番号

        Returns:
            フローアイテム（見つからない場合はNone）
        """
        for flow in self.flows:
            if flow.trigger.lower() == trigger.lower() and flow.step == step:
                return flow
        return None

    def get_flow_by_id(self, flow_id: int) -> Optional[FlowItem]:
        """
        IDでフローを取得

        Args:
            flow_id: フローID

        Returns:
            フローアイテム（見つからない場合はNone）
        """
        for flow in self.flows:
            if flow.id == flow_id:
                return flow
        return None

    def start_flow(self, user_id: str, trigger: str) -> Optional[FlowItem]:
        """
        フローを開始

        Args:
            user_id: ユーザーID
            trigger: トリガー名

        Returns:
            開始ステップのフローアイテム（見つからない場合はNone）
        """
        # ステップ1のフローを取得
        flow = self.get_flow_by_trigger(trigger, step=1)
        if not flow:
            logger.warning("フローが見つかりません", trigger=trigger)
            return None

        # 会話状態を作成
        state = ConversationState(
            user_id=user_id,
            flow_id=flow.id,
            current_step=1,
            trigger=trigger,
        )

        # セッションに保存
        self.session_service.set_session(user_id, state.to_dict())

        logger.info("フローを開始しました", user_id=user_id, trigger=trigger, flow_id=flow.id)
        return flow

    def get_current_flow(self, user_id: str) -> Optional[FlowItem]:
        """
        現在のフローステップを取得

        Args:
            user_id: ユーザーID

        Returns:
            現在のフローアイテム（見つからない場合はNone）
        """
        # セッションから会話状態を取得
        session_data = self.session_service.get_session(user_id)
        if not session_data:
            return None

        try:
            state = ConversationState.from_dict(session_data)
            return self.get_flow_by_trigger(state.trigger, state.current_step)
        except Exception as e:
            logger.error("フロー状態の取得に失敗しました", user_id=user_id, error=str(e))
            return None

    def process_user_choice(
        self, user_id: str, choice: str
    ) -> tuple[Optional[FlowItem], bool]:
        """
        ユーザーの選択を処理して次のステップに進む

        Args:
            user_id: ユーザーID
            choice: ユーザーの選択（選択肢のテキスト）

        Returns:
            (次のフローアイテム, 終了フラグ)のタプル
        """
        # セッションから会話状態を取得
        session_data = self.session_service.get_session(user_id)
        if not session_data:
            logger.warning("セッションが見つかりません", user_id=user_id)
            return None, True

        try:
            state = ConversationState.from_dict(session_data)
            current_flow = self.get_flow_by_trigger(state.trigger, state.current_step)

            if not current_flow:
                logger.warning("現在のフローが見つかりません", user_id=user_id, state=state.to_dict())
                return None, True

            # 選択肢のインデックスを取得
            options = current_flow.option_list
            option_index = -1
            selected_option = None
            
            for i, option in enumerate(options):
                if option.lower() in choice.lower() or choice.lower() in option.lower():
                    option_index = i
                    selected_option = option
                    break

            if option_index == -1:
                logger.warning("選択肢が見つかりません", user_id=user_id, choice=choice, options=options)
                # フォールバックステップへ
                next_step_number = current_flow.fallback_next
            else:
                # 次のステップ番号を取得
                next_step_number = current_flow.get_next_step_for_option(option_index)

            # ユーザーの選択をコンテキストに保存
            if selected_option:
                state.context[f"step_{state.current_step}_choice"] = selected_option
                state.context[f"step_{state.current_step}_choice_text"] = choice

            # 次のフローを取得
            next_flow = self.get_flow_by_trigger(state.trigger, next_step_number)

            if not next_flow:
                logger.info("フロー終了", user_id=user_id, trigger=state.trigger)
                
                # AI回答を生成
                ai_response = self._generate_ai_response(state)
                
                # セッションをクリア
                self.session_service.delete_session(user_id)
                
                # AI回答を含む仮想的なフローアイテムを返す
                ai_flow = FlowItem(
                    id=999,
                    trigger=state.trigger,
                    step=999,
                    question=ai_response,
                    options="",
                    next_step="",
                    end=True,
                    fallback_next=999,
                    updated_at=datetime.now()
                )
                
                return ai_flow, True

            # 終了ステップの場合
            if next_flow.is_end_step:
                logger.info("終了ステップに到達", user_id=user_id, trigger=state.trigger)
                # セッションをクリア
                self.session_service.delete_session(user_id)
                return next_flow, True

            # 会話状態を更新
            state.current_step = next_step_number
            state.last_updated = datetime.now()
            state.context["last_choice"] = choice

            # セッションに保存
            self.session_service.set_session(user_id, state.to_dict())

            logger.info(
                "次のステップへ進みました",
                user_id=user_id,
                trigger=state.trigger,
                step=next_step_number,
            )

            return next_flow, False

        except Exception as e:
            logger.error("選択処理中にエラーが発生しました", user_id=user_id, error=str(e))
            return None, True

    def cancel_flow(self, user_id: str) -> bool:
        """
        フローをキャンセル

        Args:
            user_id: ユーザーID

        Returns:
            成功した場合はTrue
        """
        return self.session_service.delete_session(user_id)

    def is_in_flow(self, user_id: str) -> bool:
        """
        ユーザーがフロー中かどうか

        Args:
            user_id: ユーザーID

        Returns:
            フロー中の場合はTrue
        """
        session_data = self.session_service.get_session(user_id)
        return session_data is not None

    def get_available_triggers(self) -> List[str]:
        """
        利用可能なトリガーのリストを取得

        Returns:
            トリガー名のリスト
        """
        triggers = set()
        for flow in self.flows:
            if flow.step == 1:  # ステップ1（開始ステップ）のみ
                triggers.add(flow.trigger)
        return sorted(list(triggers))

    def _generate_ai_response(self, state: ConversationState) -> str:
        """AI回答を生成（Q&Aベース）"""
        try:
            # ユーザーの選択履歴を整理
            user_choices = {}
            
            # 各ステップの選択を抽出
            for key, value in state.context.items():
                if key.startswith("step_") and key.endswith("_choice"):
                    step_num = key.split("_")[1]
                    user_choices[f"step_{step_num}"] = value
            
            # Q&Aサービスが利用可能な場合、関連するQ&Aを検索
            if self.qa_service:
                # ユーザーの選択内容から検索クエリを生成
                search_query = self._build_search_query_from_choices(user_choices, state.trigger)
                
                # qa_listシートから関連する回答を検索
                qa_results = self.qa_service.find_answer_from_qa_list(search_query)
                
                if qa_results and qa_results.get('answer'):
                    # Q&Aベースの回答を生成
                    ai_response = self._generate_qa_based_response(
                        qa_results, user_choices, state.trigger
                    )
                    logger.info("Q&AベースのAI回答を生成しました", user_id=state.user_id, trigger=state.trigger)
                    return ai_response
            
            # フォールバック: 通常のAI回答生成
            ai_response = self.ai_service.generate_flow_response(
                trigger=state.trigger,
                step=state.current_step,
                user_choices=user_choices,
                is_final=True
            )
            
            logger.info("AI回答を生成しました", user_id=state.user_id, trigger=state.trigger)
            return ai_response
            
        except Exception as e:
            logger.error("AI回答生成中にエラーが発生しました", error=str(e))
            return "申し訳ございません。回答を生成できませんでした。"

    def _build_search_query_from_choices(self, user_choices: Dict[str, str], trigger: str) -> str:
        """ユーザーの選択から検索クエリを構築"""
        query_parts = [trigger]
        
        for step, choice in user_choices.items():
            query_parts.append(choice)
        
        return " ".join(query_parts)

    def _generate_qa_based_response(self, qa_results: Dict[str, Any], user_choices: Dict[str, str], trigger: str) -> str:
        """Q&Aベースの回答を生成"""
        try:
            # 基本の回答テンプレート
            base_response = f"""
🎬 {trigger}のご相談ありがとうございます！

【ご選択内容】
"""
            
            # ユーザーの選択を整理
            for step, choice in user_choices.items():
                step_num = step.split("_")[1]
                base_response += f"・ステップ{step_num}: {choice}\n"
            
            # Q&Aからの回答を追加
            if qa_results.get('answer'):
                base_response += f"""
【詳細情報】
{qa_results['answer']}
"""
            
            # 次のステップの案内
            base_response += """
【次のステップ】
担当者から24時間以内にご連絡いたします。
詳細な見積もりとスケジュールをご提案いたします。

何かご質問がございましたら、お気軽にお声かけください！
"""
            
            return base_response.strip()
            
        except Exception as e:
            logger.error("Q&Aベース回答生成中にエラーが発生しました", error=str(e))
            return "申し訳ございません。回答を生成できませんでした。"

