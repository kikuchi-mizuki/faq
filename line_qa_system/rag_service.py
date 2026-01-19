"""
RAG（Retrieval-Augmented Generation）サービス
AI要約機能の実装
"""

import os
import json
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import structlog

import psycopg2
from psycopg2.extras import RealDictCursor

# 条件付きインポート（軽量化版）
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

import google.generativeai as genai
from google.oauth2.service_account import Credentials
import gspread

from .config import Config
from .utils import normalize_text

logger = structlog.get_logger(__name__)


class RAGService:
    """RAG（Retrieval-Augmented Generation）サービス"""

    def __init__(self):
        """初期化"""
        try:
            print("=" * 60)
            print("📝 RAGServiceの初期化を開始します")
            logger.warning("RAGServiceの初期化を開始します")

            self.embedding_model = None
            self.db_connection = None
            self.is_enabled = False

            # 設定の読み込み
            self.gemini_api_key = os.getenv('GEMINI_API_KEY')
            self.database_url = os.getenv('DATABASE_URL')
            self.embedding_model_name = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
            self.vector_dimension = int(os.getenv('VECTOR_DIMENSION', '384'))
            self.similarity_threshold = float(os.getenv('SIMILARITY_THRESHOLD', '0.6'))
            self.gemini_model = None

            print(f"✅ GEMINI_API_KEY設定: {'あり' if self.gemini_api_key else 'なし'}")
            print(f"✅ DATABASE_URL設定: {'あり' if self.database_url else 'なし'}")
            logger.warning("RAGServiceの設定を読み込みました")

            # シンプルな初期化ロジック
            self._initialize_rag_service()

            # デバッグ用ログ
            print(f"🎯 RAGService初期化完了: is_enabled={self.is_enabled}")
            print(f"🎯 Geminiモデル: {self.gemini_model is not None}")
            print(f"🎯 DB接続: {self.db_connection is not None}")
            print("=" * 60)
            logger.warning(f"RAGService初期化完了: is_enabled={self.is_enabled}")

        except Exception as e:
            print(f"❌ RAGServiceの初期化中にエラー: {e}")
            logger.error("RAGServiceの初期化中にエラーが発生しました", error=str(e))
            self.is_enabled = False

    def _initialize_rag_service(self):
        """RAGサービスの初期化（シンプル版）"""
        try:
            print("🔧 RAGサービスの内部初期化を開始します")
            logger.warning("RAGサービスの初期化を開始します")

            # データベース接続の初期化を試行
            print("🔍 データベース接続を試行しています...")
            database_success = self._try_database_connection()
            print(f"🔍 データベース接続の結果: {database_success}")
            logger.warning(f"データベース接続の結果: {database_success}")

            if database_success:
                # データベース接続が成功した場合、完全RAG機能を初期化
                print("✅ データベース接続が成功したため、完全RAG機能を初期化します")
                logger.warning("データベース接続が成功したため、完全RAG機能を初期化します")
                self._initialize_full_rag()
            else:
                # データベース接続が失敗した場合、代替RAG機能を初期化
                print("⚠️ データベース接続が失敗したため、代替RAG機能を初期化します")
                logger.warning("データベース接続が失敗したため、代替RAG機能を初期化します")
                self._initialize_fallback_rag()

        except Exception as e:
            print(f"❌ RAGサービスの内部初期化に失敗しました: {e}")
            logger.error("RAGサービスの初期化に失敗しました", error=str(e))
            self.is_enabled = False

    def _initialize_fallback_rag(self):
        """代替RAG機能の初期化（pgvectorなし）"""
        try:
            print("🔧 代替RAG機能の初期化を開始します")
            logger.warning("代替RAG機能の初期化を開始します")

            # Gemini APIのみを使用したRAG機能
            if self.gemini_api_key:
                print("🔑 Gemini APIキーが設定されています")
                genai.configure(api_key=self.gemini_api_key)

                # モデル一覧の取得をスキップして、直接モデルを使用（高速化）
                try:
                    # gemini-2.0-flash-expを直接使用（モデル一覧取得は遅いのでスキップ）
                    print("🤖 Geminiモデル 'gemini-2.0-flash-exp' を初期化しています...")
                    self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    print("✅ RAG: gemini-2.0-flash-expを使用します")
                    logger.info("RAG: gemini-2.0-flash-expを使用します")

                except Exception as model_error:
                    print(f"❌ RAG: モデルの初期化に失敗しました: {model_error}")
                    logger.error("RAG: モデルの初期化に失敗しました", error=str(model_error))
                    self.gemini_model = None
                    logger.warning("RAG: Geminiモデルの初期化に失敗しました")
                    self.is_enabled = False
                    return

                print("✅ 代替RAG機能（Geminiのみ）を初期化しました")
                logger.warning("代替RAG機能（Geminiのみ）を初期化しました")
                self.is_enabled = True
                print(f"🎯 is_enabled を True に設定しました")
            else:
                print("❌ Gemini APIキーが設定されていません")
                logger.warning("Gemini APIキーが設定されていません")
                logger.warning("代替RAG機能は無効化されます。基本機能のみ利用可能です。")
                self.is_enabled = False
        except Exception as e:
            print(f"❌ 代替RAG機能の初期化に失敗しました: {e}")
            logger.error("代替RAG機能の初期化に失敗しました", error=str(e))
            logger.warning("代替RAG機能は無効化されます。基本機能のみ利用可能です。")
            self.is_enabled = False

    def _try_database_connection(self):
        """データベース接続を試行（成功/失敗を返す）"""
        try:
            # タイムアウト設定付きで接続（5秒）
            self.db_connection = psycopg2.connect(
                self.database_url,
                connect_timeout=5
            )
            logger.info("データベース接続を確立しました")
            
            # pgvector拡張の確認（簡略版）
            with self.db_connection.cursor() as cursor:
                # pgvector拡張機能の確認（詳細なチェックはスキップして高速化）
                cursor.execute("SELECT * FROM pg_available_extensions WHERE name = 'vector';")
                available_extensions = cursor.fetchall()

                if not available_extensions:
                    logger.warning("pgvector拡張機能が利用できません。代替RAGモードに切り替えます。")
                    return False

                # pgvector拡張機能の有効化を試行
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                self.db_connection.commit()
                logger.info("pgvector拡張機能を有効化しました")
            
            # テーブルの作成
            self.create_tables()
            logger.info("データベース接続が確立されました")
            logger.info("データベース接続とpgvectorの両方が成功したためTrueを返します")
            return True
            
        except Exception as e:
            logger.error("データベース接続に失敗しました", error=str(e))
            self.db_connection = None
            return False

    def _initialize_full_rag(self):
        """完全RAG機能の初期化"""
        try:
            # Embeddingモデルの初期化
            if SENTENCE_TRANSFORMERS_AVAILABLE and NUMPY_AVAILABLE:
                logger.info(f"Embeddingモデルを読み込んでいます: {self.embedding_model_name}")
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                logger.info("Embeddingモデルの読み込みが完了しました")
            else:
                logger.error("sentence-transformersまたはnumpyが利用できません")
                raise ImportError("sentence-transformersまたはnumpyが利用できません")

            # Gemini APIの初期化
            if self.gemini_api_key:
                genai.configure(api_key=self.gemini_api_key)

                # 利用可能なモデルを確認
                try:
                    models = genai.list_models()
                    available_models = [model.name for model in models if 'generateContent' in model.supported_generation_methods]
                    logger.info(f"RAG利用可能なモデル: {available_models[:5]}")  # 最初の5つのみログ

                    # 利用可能なモデルから選択（2.0を優先）
                    if 'models/gemini-2.0-flash-001' in available_models:
                        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-001')
                        logger.info("RAG: gemini-2.0-flash-001を使用します")
                    elif 'models/gemini-flash-latest' in available_models:
                        self.gemini_model = genai.GenerativeModel('gemini-flash-latest')
                        logger.info("RAG: gemini-flash-latestを使用します")
                    elif 'models/gemini-2.5-flash' in available_models:
                        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
                        logger.info("RAG: gemini-2.5-flashを使用します")
                    else:
                        # フォールバック
                        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
                        logger.info("RAG: gemini-1.5-flash-latestを使用します（フォールバック）")

                except Exception as model_error:
                    logger.warning("モデル一覧の取得に失敗しました、フォールバックモデルを使用します", error=str(model_error))
                    self.gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')

                logger.info("Gemini APIを初期化しました")

            self.is_enabled = True
            logger.info("完全RAG機能の初期化が完了しました")

        except Exception as e:
            logger.error("完全RAG機能の初期化に失敗しました", error=str(e), exc_info=True)
            self.is_enabled = False

    def create_tables(self):
        """必要なテーブルを作成"""
        if not self.db_connection:
            logger.error("データベース接続がありません")
            return False
        
        try:
            with self.db_connection.cursor() as cursor:
                # 文書テーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        source_type VARCHAR(50) NOT NULL,
                        source_id VARCHAR(100) NOT NULL,
                        title TEXT,
                        content TEXT NOT NULL,
                        chunk_index INTEGER DEFAULT 0,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # ベクトルテーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS document_embeddings (
                        id SERIAL PRIMARY KEY,
                        document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                        embedding vector(%s),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """, (self.vector_dimension,))
                
                # インデックスの作成
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector 
                    ON document_embeddings USING ivfflat (embedding vector_cosine_ops);
                """)
                
                self.db_connection.commit()
                logger.info("データベーステーブルを作成しました")
                return True
                
        except Exception as e:
            logger.error("テーブル作成中にエラーが発生しました", error=str(e))
            return False

    def add_document(self, source_type: str, source_id: str, title: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """文書を追加"""
        if not self.is_enabled:
            logger.warning("RAGServiceが無効です")
            return False

        # 代替RAG機能（Geminiのみ）の場合、文書追加は利用できない
        if not self.db_connection or not self.embedding_model:
            logger.info("代替RAG機能では文書追加は利用できません（ベクトルDB未接続）")
            return False

        try:
            # 文書をチャンクに分割
            chunks = self._split_text(content)
            
            with self.db_connection.cursor() as cursor:
                for i, chunk in enumerate(chunks):
                    # 文書を保存
                    cursor.execute("""
                        INSERT INTO documents (source_type, source_id, title, content, chunk_index, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (source_type, source_id, title, chunk, i, json.dumps(metadata or {})))
                    
                    document_id = cursor.fetchone()[0]
                    
                    # 埋め込みベクトルを生成
                    embedding = self._generate_embedding(chunk)
                    
                    # ベクトルを保存
                    # 埋め込みベクトルを文字列形式に変換
                    embedding_str = '[' + ','.join(map(str, embedding.tolist())) + ']'
                    cursor.execute("""
                        INSERT INTO document_embeddings (document_id, embedding)
                        VALUES (%s, %s::vector);
                    """, (document_id, embedding_str))
                
                self.db_connection.commit()
                logger.info(f"文書を追加しました: {source_type}/{source_id}")
                return True
                
        except Exception as e:
            logger.error("文書追加中にエラーが発生しました", error=str(e))
            return False

    def search_similar_documents(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """類似文書を検索"""
        print(f"🔍 search_similar_documents 呼び出し: query='{query}'")
        logger.info(f"search_similar_documents 呼び出し: query='{query}'")

        if not self.is_enabled:
            print("❌ RAGServiceが無効です")
            logger.warning("RAGServiceが無効です")
            return []

        # 代替RAG機能（Geminiのみ）の場合、ベクトル検索は利用できない
        if not self.db_connection or not self.embedding_model:
            print(f"⚠️ DB接続: {self.db_connection is not None}, Embeddingモデル: {self.embedding_model is not None}")
            logger.warning(f"代替RAG機能チェック: DB接続={self.db_connection is not None}, Embeddingモデル={self.embedding_model is not None}")
            return []

        try:
            print("✅ ベクトル検索を開始します")
            # クエリの埋め込みベクトルを生成
            query_embedding = self._generate_embedding(query)
            print(f"✅ クエリのEmbeddingを生成しました: shape={query_embedding.shape if hasattr(query_embedding, 'shape') else 'N/A'}")
            
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # 埋め込みベクトルを文字列形式に変換
                embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'

                # 類似度検索
                cursor.execute("""
                    SELECT
                        d.id,
                        d.source_type,
                        d.source_id,
                        d.title,
                        d.content,
                        d.metadata,
                        1 - (de.embedding <=> %s::vector) as similarity
                    FROM documents d
                    JOIN document_embeddings de ON d.id = de.document_id
                    WHERE 1 - (de.embedding <=> %s::vector) > %s
                    ORDER BY similarity DESC
                    LIMIT %s;
                """, (embedding_str, embedding_str, self.similarity_threshold, limit))
                
                results = cursor.fetchall()
                print(f"✅ DB検索結果: {len(results)}件")

                # 辞書形式に変換
                documents = []
                for row in results:
                    documents.append({
                        'id': row['id'],
                        'source_type': row['source_type'],
                        'source_id': row['source_id'],
                        'title': row['title'],
                        'content': row['content'],
                        'metadata': row['metadata'],
                        'similarity': float(row['similarity'])
                    })

                print(f"🎯 類似文書を検索しました: {len(documents)}件")
                logger.info(f"類似文書を検索しました: {len(documents)}件")
                return documents

        except Exception as e:
            print(f"❌ 類似文書検索中にエラー: {e}")
            logger.error("類似文書検索中にエラーが発生しました", error=str(e))
            return []

    def generate_answer(self, query: str, context: str = "") -> str:
        """コンテキストに基づいて回答を生成"""
        if not self.gemini_api_key or not self.gemini_model:
            logger.warning("Gemini APIキーまたはモデルが設定されていません")
            return "申し訳ございません。AI回答生成機能が利用できません。"
        
        try:
            # プロンプトを構築
            prompt = self._build_prompt(query, context)
            
            # Gemini APIを呼び出し
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1000,
                    temperature=0.7,
                )
            )
            
            answer = response.text
            logger.info("Gemini AI回答を生成しました")
            return answer
            
        except Exception as e:
            logger.error("Gemini AI回答生成中にエラーが発生しました", error=str(e))
            return "申し訳ございません。回答を生成できませんでした。"

    def _split_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """テキストをチャンクに分割"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # 文の境界で分割
            if end < len(text):
                # 最後の句点を探す
                last_period = text.rfind('。', start, end)
                if last_period > start:
                    end = last_period + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks

    def _generate_embedding(self, text: str):
        """テキストの埋め込みベクトルを生成"""
        if not NUMPY_AVAILABLE:
            raise ValueError("numpyが利用できません。軽量化版では無効化されています")
        
        if not self.embedding_model:
            raise ValueError("Embeddingモデルが初期化されていません")
        
        # テキストを正規化
        normalized_text = normalize_text(text)
        
        # 埋め込みベクトルを生成
        embedding = self.embedding_model.encode(normalized_text)
        
        return embedding

    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """コンテキストを構築"""
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"【文書{i}】")
            context_parts.append(f"タイトル: {doc['title']}")
            context_parts.append(f"内容: {doc['content']}")
            context_parts.append(f"類似度: {doc['similarity']:.3f}")
            context_parts.append("")
        
        return "\n".join(context_parts)

    def _build_prompt(self, query: str, context: str) -> str:
        """プロンプトを構築"""
        if context:
            return f"""
質問: {query}

以下の情報を参考にして、質問に答えてください：

{context}

回答は以下の形式でお願いします：
1. 結論
2. 手順（必要に応じて）
3. 参考情報

日本語で、分かりやすく回答してください。
"""
        else:
            return f"""
質問: {query}

質問に答えてください。動画制作会社のカスタマーサポートとして、親しみやすく丁寧に回答してください。

回答は以下の形式でお願いします：
1. 結論
2. 手順（必要に応じて）
3. 参考情報

日本語で、分かりやすく回答してください。
"""

    def health_check(self) -> bool:
        """RAGサービスの健全性チェック"""
        return self.is_enabled and self.gemini_model is not None
