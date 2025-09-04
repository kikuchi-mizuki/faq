"""
共通ユーティリティ関数
"""

import hashlib
import hmac
import base64
import unicodedata
import re
from typing import List, Set, Dict, Any


def verify_line_signature(signature: str, body: bytes, channel_secret: str) -> bool:
    """
    LINE署名の検証

    Args:
        signature: X-Line-Signatureヘッダーの値
        body: リクエストボディ
        channel_secret: LINEチャンネルシークレット

    Returns:
        署名が有効な場合はTrue
    """
    if not signature or not channel_secret:
        return False

    try:
        # 署名の計算
        hash_value = hmac.new(
            channel_secret.encode("utf-8"), body, hashlib.sha256
        ).digest()

        calculated_signature = base64.b64encode(hash_value).decode("utf-8")

        return hmac.compare_digest(signature, calculated_signature)

    except Exception:
        return False


def hash_user_id(user_id: str, salt: str = "line_qa_system_salt") -> str:
    """
    ユーザーIDをハッシュ化（PII最小化）

    Args:
        user_id: 元のユーザーID
        salt: ハッシュ化用のソルト

    Returns:
        ハッシュ化されたユーザーID
    """
    try:
        # ソルト付きでハッシュ化
        hash_obj = hashlib.sha256()
        hash_obj.update((user_id + salt).encode("utf-8"))
        return hash_obj.hexdigest()[:16]  # 16文字に短縮
    except Exception:
        # エラー時は元のIDをそのまま返す（ログ記録のため）
        return user_id


def normalize_text(text: str) -> str:
    """
    テキストの正規化（前処理）

    Args:
        text: 元のテキスト

    Returns:
        正規化されたテキスト
    """
    if not text:
        return ""

    # NFKC正規化（全角/半角、ひらがな/カタカナの統一）
    normalized = unicodedata.normalize("NFKC", text)

    # カタカナをひらがなに変換
    normalized = katakana_to_hiragana(normalized)

    # 英数字を半角に統一
    normalized = fullwidth_to_halfwidth(normalized)

    # 記号と余分な空白を除去
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    # 前後の空白を除去
    normalized = normalized.strip()

    return normalized.lower()


def katakana_to_hiragana(text: str) -> str:
    """
    カタカナをひらがなに変換
    
    Args:
        text: 変換対象のテキスト
    
    Returns:
        ひらがなに変換されたテキスト
    """
    # カタカナ→ひらがな変換マップ
    katakana_map = {
        'ァ': 'ぁ', 'ア': 'あ', 'ィ': 'ぃ', 'イ': 'い', 'ゥ': 'ぅ', 'ウ': 'う', 'ェ': 'ぇ', 'エ': 'え', 'ォ': 'ぉ', 'オ': 'お',
        'カ': 'か', 'ガ': 'が', 'キ': 'き', 'ギ': 'ぎ', 'ク': 'く', 'グ': 'ぐ', 'ケ': 'け', 'ゲ': 'げ', 'コ': 'こ', 'ゴ': 'ご',
        'サ': 'さ', 'ザ': 'ざ', 'シ': 'し', 'ジ': 'じ', 'ス': 'す', 'ズ': 'ず', 'セ': 'せ', 'ゼ': 'ぜ', 'ソ': 'そ', 'ゾ': 'ぞ',
        'タ': 'た', 'ダ': 'だ', 'チ': 'ち', 'ヂ': 'ぢ', 'ッ': 'っ', 'ツ': 'つ', 'ヅ': 'づ', 'テ': 'て', 'デ': 'で', 'ト': 'と', 'ド': 'ど',
        'ナ': 'な', 'ニ': 'に', 'ヌ': 'ぬ', 'ネ': 'ね', 'ノ': 'の',
        'ハ': 'は', 'バ': 'ば', 'パ': 'ぱ', 'ヒ': 'ひ', 'ビ': 'び', 'ピ': 'ぴ', 'フ': 'ふ', 'ブ': 'ぶ', 'プ': 'ぷ', 'ヘ': 'へ', 'ベ': 'べ', 'ペ': 'ぺ', 'ホ': 'ほ', 'ボ': 'ぼ', 'ポ': 'ぽ',
        'マ': 'ま', 'ミ': 'み', 'ム': 'む', 'メ': 'め', 'モ': 'も',
        'ャ': 'ゃ', 'ヤ': 'や', 'ュ': 'ゅ', 'ユ': 'ゆ', 'ョ': 'ょ', 'ヨ': 'よ',
        'ラ': 'ら', 'リ': 'り', 'ル': 'る', 'レ': 'れ', 'ロ': 'ろ',
        'ワ': 'わ', 'ヲ': 'を', 'ン': 'ん'
    }
    
    result = ""
    for char in text:
        if char in katakana_map:
            result += katakana_map[char]
        else:
            result += char
    
    return result


def fullwidth_to_halfwidth(text: str) -> str:
    """
    全角英数字を半角に変換

    Args:
        text: 変換対象のテキスト

    Returns:
        半角に変換されたテキスト
    """
    result = ""
    for char in text:
        code = ord(char)
        if 0xFF01 <= code <= 0xFF5E:  # 全角英数字・記号の範囲
            # 全角を半角に変換（-0xFEE0）
            result += chr(code - 0xFEE0)
        else:
            result += char
    return result


def extract_keywords(text: str, min_length: int = 2) -> List[str]:
    """
    テキストからキーワードを抽出（AIベースの形態素解析）
    
    Args:
        text: 対象テキスト
        min_length: 最小文字数
    
    Returns:
        キーワードのリスト
    """
    if not text:
        return []
    
    try:
        # SudachiPyを使用した形態素解析
        from sudachipy import tokenizer
        from sudachipy import dictionary
        
        # トークナイザーの初期化
        tokenizer_obj = dictionary.Dictionary().create()
        
        # 形態素解析の実行
        tokens = tokenizer_obj.tokenize(text)
        
        # 名詞、動詞、形容詞のみを抽出
        keywords = []
        for token in tokens:
            # 品詞情報を取得
            pos = token.part_of_speech()
            
            # 名詞、動詞、形容詞のみを対象とする
            if (pos[0] in ['名詞', '動詞', '形容詞'] and 
                len(token.surface()) >= min_length):
                keywords.append(token.surface())
        
        return keywords
        
    except ImportError:
        # SudachiPyが利用できない場合は簡易版を使用
        return _extract_keywords_simple(text, min_length)
    except Exception:
        # エラーが発生した場合は簡易版を使用
        return _extract_keywords_simple(text, min_length)


def _extract_keywords_simple(text: str, min_length: int = 2) -> List[str]:
    """
    簡易版キーワード抽出（フォールバック用）
    
    Args:
        text: 対象テキスト
        min_length: 最小文字数
    
    Returns:
        キーワードのリスト
    """
    if not text:
        return []
    
    # 正規化（記号除去なし）
    normalized = text
    
    # カタカナをひらがなに変換
    normalized = katakana_to_hiragana(normalized)
    
    # 英数字を半角に統一
    normalized = fullwidth_to_halfwidth(normalized)
    
    # 助詞・助動詞などの除去（簡易版）
    particles = ['の', 'を', 'に', 'は', 'が', 'で', 'と', 'から', 'まで', 'より', 'へ', 'や', 'か', 'も', 'でも', 'でも', 'ば', 'たら', 'なら', 'て', 'で', 'た', 'だ', 'です', 'ます', 'れる', 'られる', 'せる', 'させる']
    
    # 助詞で分割してから空白で分割
    for particle in particles:
        normalized = normalized.replace(particle, ' ')
    
    # 連続する空白を単一の空白に置換
    normalized = ' '.join(normalized.split())
    
    # 空白で分割
    words = normalized.split()
    
    # 最小文字数以上の単語のみ抽出
    keywords = [word for word in words if len(word) >= min_length]
    
    return keywords


def calculate_similarity(text1: str, text2: str) -> float:
    """
    2つのテキスト間の類似度を計算（AIベース）
    
    Args:
        text1: テキスト1
        text2: テキスト2
    
    Returns:
        類似度（0.0〜1.0）
    """
    if not text1 or not text2:
        return 0.0
    
    # 正規化
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    # 完全一致
    if norm1 == norm2:
        return 1.0
    
    # 部分一致
    if norm1 in norm2 or norm2 in norm1:
        return 0.8
    
    # AIベースのキーワード抽出
    keywords1 = set(extract_keywords(norm1))
    keywords2 = set(extract_keywords(norm2))
    
    if not keywords1 or not keywords2:
        return 0.0
    
    # キーワードの類似度計算
    similarity_score = _calculate_keyword_similarity(keywords1, keywords2)
    
    # Jaccard類似度との組み合わせ
    jaccard = len(keywords1 & keywords2) / len(keywords1 | keywords2)
    
    # 重み付き平均
    return 0.7 * similarity_score + 0.3 * jaccard


def _calculate_keyword_similarity(keywords1: set, keywords2: set) -> float:
    """
    キーワード間の類似度を計算
    
    Args:
        keywords1: キーワードセット1
        keywords2: キーワードセット2
    
    Returns:
        類似度（0.0〜1.0）
    """
    if not keywords1 or not keywords2:
        return 0.0
    
    # 同義語辞書（簡易版）
    synonym_dict = {
        '請求書': ['インボイス', '領収書', 'レシート'],
        'インボイス': ['請求書', '領収書'],
        'パスワード': ['パス', '暗証番号'],
        'パス': ['パスワード', '暗証番号'],
        '設定': ['セッティング', '構成'],
        'ログイン': ['サインイン', 'ログオン'],
        'サインイン': ['ログイン', 'ログオン'],
        'エクスポート': ['出力', 'ダウンロード'],
        '出力': ['エクスポート', 'ダウンロード'],
        'アップロード': ['アップロード', 'ファイル登録'],
        'ファイル': ['ファイル', '文書'],
        '通知': ['アラート', 'お知らせ'],
        'アラート': ['通知', 'お知らせ']
    }
    
    # 同義語を考慮した類似度計算
    total_similarity = 0.0
    count = 0
    
    for kw1 in keywords1:
        for kw2 in keywords2:
            # 完全一致
            if kw1 == kw2:
                total_similarity += 1.0
            # 同義語
            elif (kw1 in synonym_dict and kw2 in synonym_dict[kw1]) or \
                 (kw2 in synonym_dict and kw1 in synonym_dict[kw2]):
                total_similarity += 0.8
            # 部分一致
            elif kw1 in kw2 or kw2 in kw1:
                total_similarity += 0.6
            # 文字レベルの類似度
            else:
                # rapidfuzzを使用した文字レベルの類似度
                try:
                    from rapidfuzz import fuzz
                    ratio = fuzz.ratio(kw1, kw2) / 100.0
                    if ratio > 0.7:  # 70%以上の類似度
                        total_similarity += ratio * 0.5
                except ImportError:
                    pass
            
            count += 1
    
    if count == 0:
        return 0.0
    
    return total_similarity / count


def split_comma_separated(text: str) -> List[str]:
    """
    カンマ区切りのテキストを分割

    Args:
        text: カンマ区切りのテキスト

    Returns:
        分割されたテキストのリスト
    """
    if not text:
        return []

    # カンマで分割し、空白を除去
    items = [item.strip() for item in text.split(",")]

    # 空の項目を除外
    return [item for item in items if item]


def extract_tags(text: str) -> Set[str]:
    """
    テキストからタグを抽出（AIベース）

    Args:
        text: タグが含まれるテキスト

    Returns:
        タグのセット
    """
    if not text:
        return set()

    # #タグを抽出
    explicit_tags = re.findall(r"#(\w+)", text)

    # AIベースの自動タグ生成
    auto_tags = _generate_auto_tags(text)

    # 明示的タグと自動生成タグを結合
    all_tags = set(explicit_tags) | set(auto_tags)

    return all_tags


def analyze_text_intelligence(text: str) -> Dict[str, Any]:
    """
    テキストの知能的分析（AIベース）
    
    Args:
        text: 分析対象テキスト
    
    Returns:
        分析結果の辞書
    """
    if not text:
        return {}
    
    # キーワード抽出
    keywords = extract_keywords(text)
    
    # 感情分析（簡易版）
    sentiment = _analyze_sentiment(text)
    
    # 重要度分析
    importance = _analyze_importance(text)
    
    # カテゴリ分類
    category = _classify_category(keywords)
    
    # 意図推定
    intent = _estimate_intent(text, keywords)
    
    return {
        'keywords': keywords,
        'sentiment': sentiment,
        'importance': importance,
        'category': category,
        'intent': intent,
        'confidence': _calculate_confidence(text, keywords)
    }


def _analyze_sentiment(text: str) -> str:
    """
    感情分析（簡易版）
    
    Args:
        text: 対象テキスト
    
    Returns:
        感情の種類
    """
    positive_words = ['ありがとう', '感謝', '助かる', '良い', '素晴らしい', '便利', '簡単']
    negative_words = ['困る', '問題', 'エラー', '失敗', 'できない', '難しい', '面倒']
    
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    
    if positive_count > negative_count:
        return 'positive'
    elif negative_count > positive_count:
        return 'negative'
    else:
        return 'neutral'


def _analyze_importance(text: str) -> str:
    """
    重要度分析
    
    Args:
        text: 対象テキスト
    
    Returns:
        重要度レベル
    """
    high_importance = ['重要', '緊急', '必須', '必要', '推奨', '警告', '注意']
    medium_importance = ['確認', 'チェック', '検討', '検証']
    
    if any(word in text for word in high_importance):
        return 'high'
    elif any(word in text for word in medium_importance):
        return 'medium'
    else:
        return 'low'


def _classify_category(keywords: List[str]) -> str:
    """
    カテゴリ分類
    
    Args:
        keywords: キーワードリスト
    
    Returns:
        カテゴリ名
    """
    category_scores = {
        '経理': 0,
        '設定': 0,
        'データ': 0,
        '通知': 0,
        'トラブル': 0,
        'セキュリティ': 0,
        '手続き': 0
    }
    
    # カテゴリ辞書
    category_words = {
        '経理': ['請求書', 'インボイス', '領収書', 'レシート', '見積書', '会計', '経費', '精算'],
        '設定': ['パスワード', 'パス', 'ログイン', 'サインイン', 'アカウント', 'プロフィール', '設定'],
        'データ': ['エクスポート', '出力', 'ダウンロード', 'アップロード', 'ファイル', 'バックアップ'],
        '通知': ['通知', 'アラート', 'お知らせ', 'メール', 'プッシュ'],
        'トラブル': ['エラー', '問題', '不具合', 'ログインできない', '動作しない'],
        'セキュリティ': ['セキュリティ', '認証', '暗号化', 'アクセス制御'],
        '手続き': ['手続き', '申請', '承認', 'ワークフロー', 'プロセス']
    }
    
    # スコア計算
    for keyword in keywords:
        for category, words in category_words.items():
            if keyword in words:
                category_scores[category] += 1
    
    # 最高スコアのカテゴリを返す
    if max(category_scores.values()) == 0:
        return 'その他'
    
    return max(category_scores, key=category_scores.get)


def _estimate_intent(text: str, keywords: List[str]) -> str:
    """
    ユーザーの意図を推定
    
    Args:
        text: 対象テキスト
        keywords: キーワードリスト
    
    Returns:
        推定される意図
    """
    intent_patterns = {
        '質問': ['方法', 'やり方', '手順', 'どうやって', '何を', 'どこで'],
        '問題報告': ['できない', 'エラー', '問題', '困る', '失敗'],
        '設定変更': ['変更', '設定', '修正', '更新', '調整'],
        '情報取得': ['確認', '調べる', '知りたい', '教えて'],
        '操作実行': ['実行', '開始', '起動', '作成', '削除']
    }
    
    for intent, patterns in intent_patterns.items():
        if any(pattern in text for pattern in patterns):
            return intent
    
    return 'その他'


def _calculate_confidence(text: str, keywords: List[str]) -> float:
    """
    分析結果の信頼度を計算
    
    Args:
        text: 対象テキスト
        keywords: キーワードリスト
    
    Returns:
        信頼度（0.0〜1.0）
    """
    if not text or not keywords:
        return 0.0
    
    # テキスト長による信頼度
    length_confidence = min(len(text) / 100.0, 1.0)
    
    # キーワード数による信頼度
    keyword_confidence = min(len(keywords) / 5.0, 1.0)
    
    # 平均信頼度
    return (length_confidence + keyword_confidence) / 2.0


def _generate_auto_tags(text: str) -> List[str]:
    """
    テキストから自動的にタグを生成

    Args:
        text: 対象テキスト

    Returns:
        生成されたタグのリスト
    """
    if not text:
        return []

    # キーワード抽出
    keywords = extract_keywords(text)

    # カテゴリ分類辞書
    category_dict = {
        '経理': ['請求書', 'インボイス', '領収書', 'レシート', '見積書', '会計', '経費', '精算'],
        '設定': ['パスワード', 'パス', 'ログイン', 'サインイン', 'アカウント', 'プロフィール', '設定'],
        'データ': ['エクスポート', '出力', 'ダウンロード', 'アップロード', 'ファイル', 'バックアップ'],
        '通知': ['通知', 'アラート', 'お知らせ', 'メール', 'プッシュ'],
        'トラブル': ['エラー', '問題', '不具合', 'ログインできない', '動作しない'],
        'セキュリティ': ['セキュリティ', '認証', '暗号化', 'アクセス制御'],
        '手続き': ['手続き', '申請', '承認', 'ワークフロー', 'プロセス']
    }

    # カテゴリタグの生成
    tags = []
    for category, words in category_dict.items():
        if any(word in keywords for word in words):
            tags.append(category)

    # 重要度タグの生成
    importance_words = ['重要', '緊急', '必須', '必要', '推奨']
    if any(word in text for word in importance_words):
        tags.append('重要')

    # 技術タグの生成
    tech_words = ['API', 'SDK', 'データベース', 'サーバー', 'クラウド']
    if any(word in text for word in tech_words):
        tags.append('技術')

    return tags
