"""
ユーティリティ関数のテスト
"""

import pytest
from line_qa_system.utils import (
    normalize_text,
    katakana_to_hiragana,
    fullwidth_to_halfwidth,
    extract_keywords,
    calculate_similarity,
    split_comma_separated,
    extract_tags,
)


class TestNormalizeText:
    """テキスト正規化のテスト"""

    def test_normalize_text_basic(self):
        """基本的な正規化テスト"""
        assert normalize_text("請求書") == "請求書"
        assert normalize_text("　請求書　") == "請求書"
        assert normalize_text("請求書！") == "請求書"

    def test_normalize_text_katakana(self):
        """カタカナ正規化テスト"""
        assert normalize_text("インボイス") == "いんぼいす"
        assert normalize_text("パスワード") == "ぱすわーど"

    def test_normalize_text_fullwidth(self):
        """全角英数字正規化テスト"""
        assert normalize_text("ＡＢＣ") == "abc"
        assert normalize_text("１２３") == "123"

    def test_normalize_text_mixed(self):
        """混合文字の正規化テスト"""
        assert normalize_text("請求書　ＡＢＣ　１２３！") == "請求書 abc 123"
        assert normalize_text("インボイス　ＰＡＳＳＷＯＲＤ　９９９") == "いんぼいす password 999"


class TestKatakanaToHiragana:
    """カタカナ→ひらがな変換のテスト"""

    def test_katakana_to_hiragana_basic(self):
        """基本的な変換テスト"""
        assert katakana_to_hiragana("アイウエオ") == "あいうえお"
        assert katakana_to_hiragana("カキクケコ") == "かきくけこ"

    def test_katakana_to_hiragana_mixed(self):
        """混合文字の変換テスト"""
        assert katakana_to_hiragana("請求書") == "請求書"
        assert katakana_to_hiragana("インボイス") == "いんぼいす"
        assert katakana_to_hiragana("パスワード") == "ぱすわーど"


class TestFullwidthToHalfwidth:
    """全角→半角変換のテスト"""

    def test_fullwidth_to_halfwidth_letters(self):
        """全角英字の変換テスト"""
        assert fullwidth_to_halfwidth("ＡＢＣＤＥ") == "ABCDE"
        assert fullwidth_to_halfwidth("ａｂｃｄｅ") == "abcde"

    def test_fullwidth_to_halfwidth_numbers(self):
        """全角数字の変換テスト"""
        assert fullwidth_to_halfwidth("１２３４５") == "12345"

    def test_fullwidth_to_halfwidth_symbols(self):
        """全角記号の変換テスト"""
        assert fullwidth_to_halfwidth("！＠＃＄％") == "!@#$%"


class TestExtractKeywords:
    """キーワード抽出のテスト"""

    def test_extract_keywords_basic(self):
        """基本的なキーワード抽出テスト（AIベース）"""
        # AIシステムは助詞「の」を除去して正確に分割
        result1 = extract_keywords("請求書の発行方法")
        assert "請求書" in result1
        assert "発行" in result1 or "発行方法" in result1
        
        result2 = extract_keywords("パスワードを変更する")
        assert "パスワード" in result2
        assert "変更" in result2

    def test_extract_keywords_min_length(self):
        """最小文字数指定のテスト（AIベース）"""
        result = extract_keywords("請求書の発行方法", min_length=3)
        assert "請求書" in result
        # AIシステムは適切な長さのキーワードを抽出
        assert all(len(word) >= 3 for word in result)
        result = extract_keywords("請求書の発行方法", min_length=4)
        # min_length=4の場合、4文字未満の単語は除外される
        if result:  # 結果がある場合のみチェック
            assert all(len(word) >= 4 for word in result)


class TestCalculateSimilarity:
    """類似度計算のテスト"""

    def test_calculate_similarity_exact(self):
        """完全一致のテスト"""
        assert calculate_similarity("請求書", "請求書") == 1.0

    def test_calculate_similarity_partial(self):
        """部分一致のテスト"""
        assert calculate_similarity("請求書", "請求書の発行") == 0.8
        assert calculate_similarity("請求書の発行", "請求書") == 0.8

    def test_calculate_similarity_keywords(self):
        """キーワード一致のテスト"""
        similarity = calculate_similarity("請求書", "請求書 発行 方法")
        assert similarity > 0.0

    def test_calculate_similarity_no_match(self):
        """一致なしのテスト"""
        assert calculate_similarity("請求書", "パスワード") == 0.0


class TestSplitCommaSeparated:
    """カンマ区切り分割のテスト"""

    def test_split_comma_separated_basic(self):
        """基本的な分割テスト"""
        assert split_comma_separated("請求書,インボイス,領収書") == ["請求書", "インボイス", "領収書"]

    def test_split_comma_separated_with_spaces(self):
        """空白付きの分割テスト"""
        assert split_comma_separated(" 請求書 , インボイス , 領収書 ") == ["請求書", "インボイス", "領収書"]

    def test_split_comma_separated_empty(self):
        """空文字列のテスト"""
        assert split_comma_separated("") == []
        assert split_comma_separated("   ") == []


class TestExtractTags:
    """タグ抽出のテスト"""

    def test_extract_tags_basic(self):
        """基本的なタグ抽出テスト"""
        assert extract_tags("請求書 #経理 #手続き") == {"経理", "手続き"}

    def test_extract_tags_mixed(self):
        """混合文字のタグ抽出テスト"""
        assert extract_tags("パスワード変更 #設定 #セキュリティ #重要") == {"設定", "セキュリティ", "重要"}

    def test_extract_tags_no_tags(self):
        """タグなしのテスト（AIベース）"""
        # AIシステムは自動的にカテゴリタグを生成
        result1 = extract_tags("請求書の発行方法")
        assert len(result1) > 0  # 自動タグ生成により空ではない
        assert "経理" in result1  # 請求書から経理カテゴリを自動判定
        
        assert extract_tags("") == set()
