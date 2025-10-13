"""
データモデル定義
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class QAItem:
    """Q&Aアイテムのデータ構造"""

    id: int
    question: str
    keywords: str
    synonyms: str
    tags: str
    answer: str
    priority: int
    status: str
    updated_at: datetime

    def __post_init__(self):
        """初期化後の処理"""
        # 文字列フィールドの正規化
        if self.keywords:
            self.keywords = self.keywords.strip()
        if self.synonyms:
            self.synonyms = self.synonyms.strip()
        if self.tags:
            self.tags = self.tags.strip()
        if self.answer:
            self.answer = self.answer.strip()

    @property
    def is_active(self) -> bool:
        """アクティブなアイテムかどうか"""
        return self.status.lower() == "active"

    @property
    def keyword_list(self) -> List[str]:
        """キーワードのリスト"""
        from .utils import split_comma_separated

        return split_comma_separated(self.keywords)

    @property
    def synonym_list(self) -> List[str]:
        """同義語のリスト"""
        from .utils import split_comma_separated

        return split_comma_separated(self.synonyms)

    @property
    def tag_list(self) -> List[str]:
        """タグのリスト"""
        from .utils import extract_tags

        return list(extract_tags(self.tags))

    def get_all_searchable_texts(self) -> List[str]:
        """検索対象となるすべてのテキストを取得"""
        texts = []

        # 質問文
        if self.question:
            texts.append(self.question)

        # キーワード
        texts.extend(self.keyword_list)

        # 同義語
        texts.extend(self.synonym_list)

        # タグ（#を除去）
        for tag in self.tag_list:
            texts.append(tag)

        return texts


@dataclass
class SearchResult:
    """検索結果のデータ構造"""

    qa_item: QAItem
    score: float
    match_type: str
    matched_text: str

    @property
    def id(self) -> int:
        return self.qa_item.id

    @property
    def question(self) -> str:
        return self.qa_item.question

    @property
    def answer(self) -> str:
        return self.qa_item.answer

    @property
    def tags(self) -> str:
        return self.qa_item.tags

    @property
    def priority(self) -> int:
        return self.qa_item.priority


@dataclass
class SearchResponse:
    """検索応答のデータ構造"""

    is_found: bool
    top_result: Optional[SearchResult]
    candidates: List[SearchResult]
    total_candidates: int
    search_time_ms: float

    @property
    def answer(self) -> Optional[str]:
        """最適な回答を取得"""
        if self.top_result:
            return self.top_result.answer
        return None

    @property
    def question(self) -> Optional[str]:
        """最適な質問を取得"""
        if self.top_result:
            return self.top_result.question
        return None

    @property
    def tags(self) -> Optional[str]:
        """最適なタグを取得"""
        if self.top_result:
            return self.top_result.tags
        return None

    @property
    def score(self) -> Optional[float]:
        """最適なスコアを取得"""
        if self.top_result:
            return self.top_result.score
        return None


@dataclass
class SystemStats:
    """システム統計情報"""

    total_qa_items: int
    active_qa_items: int
    cache_hit_rate: float
    average_response_time_ms: float
    total_requests: int
    successful_matches: int
    last_updated: datetime

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "total_qa_items": self.total_qa_items,
            "active_qa_items": self.active_qa_items,
            "cache_hit_rate": round(self.cache_hit_rate, 3),
            "average_response_time_ms": round(self.average_response_time_ms, 1),
            "total_requests": self.total_requests,
            "successful_matches": self.successful_matches,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class FlowItem:
    """分岐会話フローのデータ構造"""

    id: int
    trigger: str
    step: int
    question: str
    options: str
    next_step: str
    end: bool
    fallback_next: int
    updated_at: datetime

    def __post_init__(self):
        """初期化後の処理"""
        # 文字列フィールドの正規化
        if self.trigger:
            self.trigger = self.trigger.strip()
        if self.question:
            self.question = self.question.strip()
        if self.options:
            self.options = self.options.strip()
        if self.next_step:
            self.next_step = self.next_step.strip()

    @property
    def is_end_step(self) -> bool:
        """終了ステップかどうか"""
        return self.end

    @property
    def option_list(self) -> List[str]:
        """選択肢のリスト"""
        if not self.options:
            return []
        return [opt.strip() for opt in self.options.split("／") if opt.strip()]

    @property
    def next_step_list(self) -> List[int]:
        """次ステップのリスト"""
        if not self.next_step:
            return []
        try:
            return [int(step.strip()) for step in self.next_step.split("／") if step.strip()]
        except ValueError:
            return []

    def get_next_step_for_option(self, option_index: int) -> Optional[int]:
        """
        選択肢のインデックスに対応する次のステップを取得

        Args:
            option_index: 選択肢のインデックス（0始まり）

        Returns:
            次のステップ番号（見つからない場合はfallback_next）
        """
        next_steps = self.next_step_list
        if 0 <= option_index < len(next_steps):
            return next_steps[option_index]
        return self.fallback_next


@dataclass
class ConversationState:
    """会話状態のデータ構造"""

    user_id: str
    flow_id: int
    current_step: int
    trigger: str
    context: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "user_id": self.user_id,
            "flow_id": self.flow_id,
            "current_step": self.current_step,
            "trigger": self.trigger,
            "context": self.context,
            "started_at": self.started_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        """辞書から復元"""
        return cls(
            user_id=data["user_id"],
            flow_id=data["flow_id"],
            current_step=data["current_step"],
            trigger=data["trigger"],
            context=data.get("context", {}),
            started_at=datetime.fromisoformat(data["started_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
        )
