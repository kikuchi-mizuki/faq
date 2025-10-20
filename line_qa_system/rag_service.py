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
            
            logger.warning("RAGServiceの設定を読み込みました")
            
            # シンプルな初期化ロジック
            self._initialize_rag_service()
            
            # デバッグ用ログ
            logger.warning(f"RAGService初期化完了: is_enabled={self.is_enabled}")
            
        except Exception as e:
            logger.error("RAGServiceの初期化中にエラーが発生しました", error=str(e))
            self.is_enabled = False

    def _initialize_rag_service(self):
        """RAGサービスの初期化（シンプル版）"""
        try:
            logger.warning("RAGサービスの初期化を開始します")
            
            # データベース接続の初期化を試行
            database_success = self._try_database_connection()
            logger.warning(f"データベース接続の結果: {database_success}")
            
            if database_success:
                # データベース接続が成功した場合、完全RAG機能を初期化
                logger.warning("データベース接続が成功したため、完全RAG機能を初期化します")
                self._initialize_full_rag()
            else:
                # データベース接続が失敗した場合、代替RAG機能を初期化
                logger.warning("データベース接続が失敗したため、代替RAG機能を初期化します")
                self._initialize_fallback_rag()
            
        except Exception as e:
            logger.error("RAGサービスの初期化に失敗しました", error=str(e))
            self.is_enabled = False

    def _initialize_fallback_rag(self):
        """代替RAG機能の初期化（pgvectorなし）"""
        try:
            logger.warning("代替RAG機能の初期化を開始します")
            
            # Gemini APIのみを使用したRAG機能
            if self.gemini_api_key:
                genai.configure(api_key=self.gemini_api_key)
                
                # 利用可能なモデルを確認
                try:
                    models = genai.list_models()
                    available_models = [model.name for model in models if 'generateContent' in model.supported_generation_methods]
                    logger.warning(f"RAG利用可能なモデル: {available_models}")
                    
                    # 利用可能なモデルから選択（-001を優先）
                    if 'models/gemini-1.5-flash-001' in available_models:
                        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash-001')
                        logger.info("RAG: gemini-1.5-flash-001を使用します")
                    elif 'models/gemini-1.5-flash' in available_models:
                        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                        logger.info("RAG: gemini-1.5-flashを使用します")
                    elif 'models/gemini-1.5-pro' in available_models:
                        self.gemini_model = genai.GenerativeModel('gemini-1.5-pro')
                        logger.info("RAG: gemini-1.5-proを使用します")
                    else:
                        logger.warning("RAG: 利用可能なGeminiモデルが見つかりません")
                        return
                        
                except Exception as model_error:
                    logger.error("RAG: モデル一覧の取得に失敗しました", error=str(model_error))
                    # フォールバック: 直接モデルを試す
                    self.gemini_model = genai.GenerativeModel('gemini-1.5-flash-001')
                    logger.info("RAG: フォールバック: gemini-1.5-flash-001を試します")
                
                logger.warning("代替RAG機能（Geminiのみ）を初期化しました")
                self.is_enabled = True
            else:
                logger.warning("Gemini APIキーが設定されていません")
                logger.warning("代替RAG機能は無効化されます。基本機能のみ利用可能です。")
                self.is_enabled = False
        except Exception as e:
            logger.error("代替RAG機能の初期化に失敗しました", error=str(e))
            logger.warning("代替RAG機能は無効化されます。基本機能のみ利用可能です。")
            self.is_enabled = False

    def _try_database_connection(self):
        """データベース接続を試行（成功/失敗を返す）"""
        try:
            self.db_connection = psycopg2.connect(self.database_url)
            logger.info("データベース接続を確立しました")
            
            # pgvector拡張の確認
            with self.db_connection.cursor() as cursor:
                # 利用可能な拡張機能を全て確認
                cursor.execute("SELECT name FROM pg_available_extensions ORDER BY name;")
                all_extensions = cursor.fetchall()
                logger.info(f"利用可能な拡張機能: {[ext[0] for ext in all_extensions]}")
                
                # pgvector拡張機能の確認
                cursor.execute("SELECT * FROM pg_available_extensions WHERE name = 'vector';")
                available_extensions = cursor.fetchall()
                logger.info(f"pgvector拡張機能: {available_extensions}")
                
                if not available_extensions:
                    logger.warning("pgvector拡張機能が利用できません")
                    logger.warning("Railway PostgreSQLではpgvectorが利用できない可能性があります")
                    logger.warning("データベース接続は成功したが、pgvectorが利用できないためFalseを返します")
                    logger.warning("=== RAGService初期化デバッグ: pgvector利用不可 ===")
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
            # Gemini APIの初期化
            if self.gemini_api_key:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
                logger.info("Gemini APIを初期化しました")
            
            self.is_enabled = True
            logger.info("完全RAG機能の初期化が完了しました")
            
        except Exception as e:
            logger.error("完全RAG機能の初期化に失敗しました", error=str(e))
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
                    cursor.execute("""
                        INSERT INTO document_embeddings (document_id, embedding)
                        VALUES (%s, %s);
                    """, (document_id, embedding.tolist()))
                
                self.db_connection.commit()
                logger.info(f"文書を追加しました: {source_type}/{source_id}")
                return True
                
        except Exception as e:
            logger.error("文書追加中にエラーが発生しました", error=str(e))
            return False

    def search_similar_documents(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """類似文書を検索"""
        if not self.is_enabled:
            logger.warning("RAGServiceが無効です")
            return []
        
        try:
            # クエリの埋め込みベクトルを生成
            query_embedding = self._generate_embedding(query)
            
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # 類似度検索
                cursor.execute("""
                    SELECT 
                        d.id,
                        d.source_type,
                        d.source_id,
                        d.title,
                        d.content,
                        d.metadata,
                        1 - (de.embedding <=> %s) as similarity
                    FROM documents d
                    JOIN document_embeddings de ON d.id = de.document_id
                    WHERE 1 - (de.embedding <=> %s) > %s
                    ORDER BY similarity DESC
                    LIMIT %s;
                """, (query_embedding.tolist(), query_embedding.tolist(), self.similarity_threshold, limit))
                
                results = cursor.fetchall()
                
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
                
                logger.info(f"類似文書を検索しました: {len(documents)}件")
                return documents
                
        except Exception as e:
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
