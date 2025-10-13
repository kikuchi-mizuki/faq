"""
LINE Messaging API クライアント
"""

import json
import requests
from typing import Dict, Any, List, Optional
import structlog

from .config import Config

logger = structlog.get_logger(__name__)


class LineClient:
    """LINE Messaging API クライアント"""

    def __init__(self):
        """初期化"""
        self.channel_access_token = Config.LINE_CHANNEL_ACCESS_TOKEN
        self.base_url = "https://api.line.me/v2"
        self.headers = {
            "Authorization": f"Bearer {self.channel_access_token}",
            "Content-Type": "application/json",
        }

    def reply_text(
        self, reply_token: str, text: str, quick_reply: Optional[List[str]] = None
    ) -> bool:
        """
        テキストメッセージを返信

        Args:
            reply_token: 返信トークン
            text: 返信テキスト
            quick_reply: クイックリプライの選択肢リスト（オプション）

        Returns:
            成功時はTrue
        """
        try:
            message = {"type": "text", "text": text}

            # クイックリプライがある場合は追加
            if quick_reply:
                message["quickReply"] = self._create_quick_reply_items(quick_reply)

            payload = {
                "replyToken": reply_token,
                "messages": [message],
            }

            response = requests.post(
                f"{self.base_url}/bot/message/reply",
                headers=self.headers,
                json=payload,
                timeout=10,
            )

            if response.status_code == 200:
                logger.info("LINE返信が成功しました", reply_token=reply_token[:10])
                return True
            else:
                logger.error(
                    "LINE返信が失敗しました",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return False

        except Exception as e:
            logger.error(
                "LINE返信中にエラーが発生しました", error=str(e), reply_token=reply_token[:10]
            )
            return False

    def reply_flex_message(
        self, reply_token: str, flex_content: Dict[str, Any]
    ) -> bool:
        """
        Flexメッセージを返信

        Args:
            reply_token: 返信トークン
            flex_content: Flexメッセージの内容

        Returns:
            成功時はTrue
        """
        try:
            payload = {
                "replyToken": reply_token,
                "messages": [
                    {
                        "type": "flex",
                        "altText": flex_content.get("altText", "回答"),
                        "contents": flex_content["contents"],
                    }
                ],
            }

            response = requests.post(
                f"{self.base_url}/bot/message/reply",
                headers=self.headers,
                json=payload,
                timeout=10,
            )

            if response.status_code == 200:
                logger.info("LINE Flex返信が成功しました", reply_token=reply_token[:10])
                return True
            else:
                logger.error(
                    "LINE Flex返信が失敗しました",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return False

        except Exception as e:
            logger.error(
                "LINE Flex返信中にエラーが発生しました", error=str(e), reply_token=reply_token[:10]
            )
            return False

    def create_flex_message(
        self,
        title: str,
        body: str,
        url: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Flexメッセージの内容を作成

        Args:
            title: タイトル
            body: 本文
            url: 関連URL（オプション）
            tags: タグ（オプション）

        Returns:
            Flexメッセージの内容
        """
        contents = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1DB446",
                    },
                    {"type": "text", "text": body, "wrap": True, "margin": "md"},
                ],
            },
        }

        # タグがある場合は追加
        if tags:
            contents["body"]["contents"].append(
                {
                    "type": "text",
                    "text": f"関連: {tags}",
                    "size": "sm",
                    "color": "#666666",
                    "margin": "md",
                }
            )

        # URLがある場合はボタンを追加
        if url:
            contents["footer"] = {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {"type": "uri", "label": "詳細を見る", "uri": url},
                        "style": "primary",
                        "color": "#1DB446",
                    }
                ],
            }

        return {"altText": title, "contents": contents}

    def push_message(self, user_id: str, text: str) -> bool:
        """
        プッシュメッセージを送信

        Args:
            user_id: ユーザーID
            text: メッセージテキスト

        Returns:
            成功時はTrue
        """
        try:
            payload = {"to": user_id, "messages": [{"type": "text", "text": text}]}

            response = requests.post(
                f"{self.base_url}/bot/message/push",
                headers=self.headers,
                json=payload,
                timeout=10,
            )

            if response.status_code == 200:
                logger.info("LINEプッシュメッセージが成功しました", user_id=user_id[:10])
                return True
            else:
                logger.error(
                    "LINEプッシュメッセージが失敗しました",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return False

        except Exception as e:
            logger.error(
                "LINEプッシュメッセージ中にエラーが発生しました", error=str(e), user_id=user_id[:10]
            )
            return False

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        ユーザープロフィールを取得

        Args:
            user_id: ユーザーID

        Returns:
            プロフィール情報（失敗時はNone）
        """
        try:
            response = requests.get(
                f"{self.base_url}/bot/profile/{user_id}",
                headers=self.headers,
                timeout=10,
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "プロフィール取得が失敗しました",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return None

        except Exception as e:
            logger.error("プロフィール取得中にエラーが発生しました", error=str(e), user_id=user_id[:10])
            return None

    def validate_token(self) -> bool:
        """
        アクセストークンの妥当性を検証

        Returns:
            有効な場合はTrue
        """
        try:
            response = requests.get(
                f"{self.base_url}/bot/profile/U1234567890abcdef1234567890abcdef",
                headers=self.headers,
                timeout=10,
            )

            # 401エラーはトークンが無効、404エラーはユーザーが存在しない（トークンは有効）
            return response.status_code in [200, 404]

        except Exception as e:
            logger.error("トークン検証中にエラーが発生しました", error=str(e))
            return False

    def _create_quick_reply_items(self, options: List[str]) -> Dict[str, Any]:
        """
        クイックリプライアイテムを作成

        Args:
            options: 選択肢のリスト

        Returns:
            クイックリプライオブジェクト
        """
        items = []
        for option in options[:13]:  # LINEの制限：最大13個
            items.append(
                {
                    "type": "action",
                    "action": {"type": "message", "label": option, "text": option},
                }
            )
        return {"items": items}
