"""
AI回答生成サービス
分岐フローの内容を踏まえて適切な回答を生成
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

import google.generativeai as genai
from google.oauth2.service_account import Credentials

from .config import Config
from .models import FlowItem, ConversationState

logger = structlog.get_logger(__name__)


class AIService:
    """AI回答生成サービス"""

    def __init__(self):
        """初期化"""
        self.model = None
        self._init_gemini()
        
        # 回答テンプレート
        self.response_templates = {
            "制作依頼": {
                "final_response": """
🎬 制作依頼の詳細をありがとうございます！

【ご依頼内容】
・媒体: {media}
・本数: {quantity}
・納期: {deadline}
・広告運用: {advertising}

【次のステップ】
1. 詳細な企画書の作成
2. 見積もりの提出
3. 制作スケジュールの調整

担当者から24時間以内にご連絡いたします。
何かご質問がございましたら、お気軽にお声かけください！
""",
                "partial_response": """
📋 情報をありがとうございます！

現在のご要望:
{current_info}

次の質問にお答えください。
"""
            },
            "料金相談": {
                "final_response": """
💰 料金についてご説明いたします！

【{category}について】
{detailed_info}

【お見積もり】
{estimate_info}

詳細な見積もりをご希望の場合は、制作依頼フローからお進みください。
""",
                "partial_response": """
💵 料金相談をありがとうございます！

{current_info}

詳細をお答えしますので、次の質問にお答えください。
"""
            },
            "修正相談": {
                "final_response": """
✅ 修正についてご説明いたします！

【修正ポリシー】
・修正回数: 無制限
・修正料金: 無料
・修正期間: 納品後1ヶ月以内
・修正方法: {correction_method}

【修正の流れ】
1. 修正内容の確認
2. 修正作業の実施
3. 修正版の納品

安心してご依頼ください！
""",
                "partial_response": """
✏️ 修正についてご相談ですね！

{current_info}

詳細な修正ポリシーをお答えします。
"""
            },
            "プラン相談": {
                "final_response": """
📦 プランについてご説明いたします！

【{plan_name}の詳細】
{plan_details}

【料金】
{plan_pricing}

【お申し込み】
{plan_application}

ご不明な点がございましたら、お気軽にお声かけください！
""",
                "partial_response": """
🎯 プランについてご相談ですね！

{current_info}

詳細なプラン内容をお答えします。
"""
            },
            "サポート": {
                "final_response": """
🆘 サポート対応いたします！

【問題の分類】
{issue_category}

【対応方法】
{support_method}

【担当者連絡】
担当者から24時間以内にご連絡いたします。

緊急の場合は、直接お電話ください。
""",
                "partial_response": """
👨‍💼 サポート対応いたします！

{current_info}

担当者にご案内いたします。
"""
            },
            "よくある質問": {
                "final_response": """
📚 よくある質問にお答えします！

【{category}について】
{faq_answer}

【関連情報】
{related_info}

他にご質問がございましたら、お気軽にお声かけください！
""",
                "partial_response": """
❓ よくある質問ですね！

{current_info}

詳細な回答をご案内いたします。
"""
            }
        }

    def _init_gemini(self):
        """Gemini APIの初期化"""
        try:
            # 環境変数からAPIキーを取得
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                logger.warning("GEMINI_API_KEYが設定されていません。AI機能は無効です。")
                return
            
            # Gemini APIの設定
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini APIの初期化が完了しました")
            
        except Exception as e:
            logger.error("Gemini APIの初期化に失敗しました", error=str(e))
            self.model = None

    def generate_flow_response(
        self, 
        trigger: str, 
        step: int, 
        user_choices: Dict[str, Any],
        is_final: bool = False
    ) -> str:
        """
        フローに基づいてAI回答を生成
        
        Args:
            trigger: トリガー名
            step: ステップ番号
            user_choices: ユーザーの選択履歴
            is_final: 最終ステップかどうか
            
        Returns:
            生成された回答
        """
        try:
            if not self.model:
                return self._get_fallback_response(trigger, step, user_choices, is_final)
            
            # プロンプトを生成
            prompt = self._build_prompt(trigger, step, user_choices, is_final)
            
            # AI回答を生成
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                logger.info("AI回答を生成しました", trigger=trigger, step=step)
                return response.text.strip()
            else:
                logger.warning("AI回答の生成に失敗しました")
                return self._get_fallback_response(trigger, step, user_choices, is_final)
                
        except Exception as e:
            logger.error("AI回答生成中にエラーが発生しました", error=str(e))
            return self._get_fallback_response(trigger, step, user_choices, is_final)

    def _build_prompt(
        self, 
        trigger: str, 
        step: int, 
        user_choices: Dict[str, Any],
        is_final: bool
    ) -> str:
        """プロンプトを構築"""
        
        # 基本情報
        base_prompt = f"""
あなたは動画制作会社のカスタマーサポートAIです。
以下の情報を基に、ユーザーに適切な回答を生成してください。

【会社情報】
- 動画制作会社
- YouTube、Instagram、TikTok対応
- Twenty BUZZプラン（広告運用込み）
- 修正無制限・無料
- 初期費用・解約費用なし

【ユーザーの状況】
- トリガー: {trigger}
- ステップ: {step}
- 選択履歴: {json.dumps(user_choices, ensure_ascii=False, indent=2)}
- 最終ステップ: {is_final}
"""

        # トリガー別の詳細プロンプト
        if trigger == "制作依頼":
            base_prompt += """
【制作依頼について】
- 媒体選択、本数、納期、広告運用の順で情報収集
- 最終ステップでは見積もり依頼の流れを案内
- 担当者からの連絡を約束
"""
        
        elif trigger == "料金相談":
            base_prompt += """
【料金相談について】
- 制作費用、広告運用費、初期費用について説明
- 本数による料金体系を説明
- 見積もり依頼を案内
"""
        
        elif trigger == "修正相談":
            base_prompt += """
【修正相談について】
- 修正回数無制限、料金無料を強調
- 修正期間と手順を説明
- 安心感を与える回答
"""
        
        elif trigger == "プラン相談":
            base_prompt += """
【プラン相談について】
- Twenty BUZZプランの詳細説明
- 各プランの料金と特徴
- お申し込み方法の案内
"""
        
        elif trigger == "サポート":
            base_prompt += """
【サポートについて】
- 問題の分類と対応方法
- 担当者からの連絡約束
- 緊急時の連絡方法
"""
        
        elif trigger == "よくある質問":
            base_prompt += """
【よくある質問について】
- カテゴリ別の詳細回答
- 関連情報の提供
- 追加質問の案内
"""

        # 回答の指示
        base_prompt += """
【回答の指示】
- 親しみやすく丁寧な敬語を使用
- 絵文字を適度に使用（🎬、💰、✅など）
- 具体的で実用的な情報を提供
- 次のアクションを明確に案内
- 200文字以内で簡潔に回答

【回答例の形式】
🎬 ご依頼ありがとうございます！

【内容】
・媒体: YouTube
・本数: 3本
・納期: 2-3週間

【次のステップ】
担当者から24時間以内にご連絡いたします。

何かご質問がございましたら、お気軽にお声かけください！
"""

        return base_prompt

    def _get_fallback_response(
        self, 
        trigger: str, 
        step: int, 
        user_choices: Dict[str, Any],
        is_final: bool
    ) -> str:
        """フォールバック回答を取得"""
        
        if trigger not in self.response_templates:
            return "申し訳ございません。回答を生成できませんでした。"
        
        template = self.response_templates[trigger]
        
        if is_final:
            # 最終回答のテンプレート
            response_template = template.get("final_response", "")
        else:
            # 中間回答のテンプレート
            response_template = template.get("partial_response", "")
        
        # プレースホルダーを置換
        try:
            # 基本的な置換
            response = response_template.format(
                current_info=self._format_current_info(user_choices),
                **user_choices
            )
            return response
        except KeyError:
            # プレースホルダーが見つからない場合はそのまま返す
            return response_template

    def _format_current_info(self, user_choices: Dict[str, Any]) -> str:
        """現在の情報をフォーマット"""
        if not user_choices:
            return "情報収集中です。"
        
        info_parts = []
        for key, value in user_choices.items():
            if value:
                info_parts.append(f"・{key}: {value}")
        
        return "\n".join(info_parts) if info_parts else "情報収集中です。"

    def health_check(self) -> bool:
        """ヘルスチェック"""
        return self.model is not None
