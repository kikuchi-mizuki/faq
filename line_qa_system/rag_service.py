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
from psycopg2 import pool
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
            self.db_pool = None  # 接続プール
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
            print(f"🎯 DB接続プール: {self.db_pool is not None}")
            print("=" * 60)
            logger.warning(f"RAGService初期化完了: is_enabled={self.is_enabled}")

        except Exception as e:
            print(f"❌ RAGServiceの初期化中にエラー: {e}")
            logger.error("RAGServiceの初期化中にエラーが発生しました", error=str(e))
            self.is_enabled = False

    def __del__(self):
        """デストラクタ - 接続プールをクローズ"""
        try:
            if self.db_pool:
                self.db_pool.closeall()
                print("✅ データベース接続プールをクローズしました")
        except Exception as e:
            print(f"⚠️ 接続プールのクローズ中にエラー: {e}")

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
        # DATABASE_URLが設定されていない場合は即座にFalseを返す
        if not self.database_url:
            print("⚠️ DATABASE_URLが設定されていません。代替RAGモードに切り替えます")
            logger.warning("DATABASE_URLが設定されていません")
            return False

        try:
            # タイムアウト設定付きで接続プールを作成（10秒に延長）
            # Railway環境ではネットワーク遅延があるため
            print("🔌 データベース接続プールを作成しています...")
            self.db_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                dsn=self.database_url,
                connect_timeout=10
            )
            # 初期接続テスト用
            self.db_connection = self.db_pool.getconn()
            print("✅ データベース接続プールを作成しました")
            logger.info("データベース接続プールを作成しました")

            # pgvector拡張の確認（簡略版）
            with self.db_connection.cursor() as cursor:
                # pgvector拡張機能の確認（詳細なチェックはスキップして高速化）
                cursor.execute("SELECT * FROM pg_available_extensions WHERE name = 'vector';")
                available_extensions = cursor.fetchall()

                if not available_extensions:
                    print("⚠️ pgvector拡張機能が利用できません。代替RAGモードに切り替えます")
                    logger.warning("pgvector拡張機能が利用できません。代替RAGモードに切り替えます。")
                    return False

                # pgvector拡張機能の有効化を試行
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                self.db_connection.commit()
                print("✅ pgvector拡張機能を有効化しました")
                logger.info("pgvector拡張機能を有効化しました")

            # テーブルの作成
            print("📋 データベーステーブルを作成しています...")
            self.create_tables()
            print("✅ データベーステーブルの作成が完了しました")
            logger.info("データベース接続が確立されました")
            logger.info("データベース接続とpgvectorの両方が成功したためTrueを返します")

            # 初期接続を返却
            self.db_pool.putconn(self.db_connection)
            self.db_connection = None

            return True

        except Exception as e:
            print(f"❌ データベース接続に失敗しました: {e}")
            logger.error("データベース接続に失敗しました", error=str(e), exc_info=True)
            if self.db_connection and self.db_pool:
                self.db_pool.putconn(self.db_connection)
            self.db_connection = None
            self.db_pool = None
            return False

    def _initialize_full_rag(self):
        """完全RAG機能の初期化"""
        try:
            # 軽量起動モードの確認（環境変数でRAG機能を完全に無効化可能）
            rag_lightweight_mode = os.getenv('RAG_LIGHTWEIGHT_MODE', 'false').lower() == 'true'

            if rag_lightweight_mode:
                print("⚡ RAG軽量モードが有効です。Embeddingモデルの読み込みをスキップします")
                logger.warning("RAG軽量モード: Embeddingモデルの読み込みをスキップします")
                # 代替RAG機能に切り替え
                self._initialize_fallback_rag()
                return

            # Embeddingモデルの初期化
            if SENTENCE_TRANSFORMERS_AVAILABLE and NUMPY_AVAILABLE:
                print(f"📚 Embeddingモデルを読み込んでいます: {self.embedding_model_name}")
                print("⚠️ この処理には時間がかかる場合があります...")
                logger.info(f"Embeddingモデルを読み込んでいます: {self.embedding_model_name}")
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                print("✅ Embeddingモデルの読み込みが完了しました")
                logger.info("Embeddingモデルの読み込みが完了しました")
            else:
                logger.warning("sentence-transformersまたはnumpyが利用できません")
                logger.warning("完全RAG機能は利用できないため、代替RAG機能に切り替えます")
                # 代替モードに切り替え
                self._initialize_fallback_rag()
                return

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

    def add_document(self, source_type: str, source_id: str, title: str, content: str, metadata: Dict[str, Any] = None, generate_embeddings: bool = True) -> bool:
        """文書を追加

        Args:
            source_type: ソースタイプ
            source_id: ソースID
            title: タイトル
            content: 内容
            metadata: メタデータ
            generate_embeddings: Embeddingを即座に生成するか（False=後で生成）
        """
        if not self.is_enabled:
            logger.warning("RAGServiceが無効です")
            return False

        # 代替RAG機能（Geminiのみ）の場合、文書追加は利用できない
        if not self.db_pool or not self.embedding_model:
            logger.info("代替RAG機能では文書追加は利用できません（ベクトルDB未接続）")
            return False

        conn = None
        try:
            # 文書をチャンクに分割
            chunks = self._split_text(content)
            logger.info(f"文書を{len(chunks)}個のチャンクに分割しました")

            document_ids = []

            # 接続プールから接続を取得
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                # 1. まず全文を保存（Gems方式の学習用）
                cursor.execute("""
                    INSERT INTO documents (source_type, source_id, title, content, full_content, chunk_index, is_full_text_chunk, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (source_type, source_id, title, content[:1000], content, -1, True, json.dumps(metadata or {})))

                full_text_doc_id = cursor.fetchone()[0]
                logger.info(f"全文を保存しました: {source_type}/{source_id}, サイズ={len(content)}文字")

                # 2. チャンクを保存（ベクトル検索用）
                for i, chunk in enumerate(chunks):
                    # 文書を保存
                    cursor.execute("""
                        INSERT INTO documents (source_type, source_id, title, content, full_content, chunk_index, is_full_text_chunk, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (source_type, source_id, title, chunk, content, i, False, json.dumps(metadata or {})))

                    document_id = cursor.fetchone()[0]
                    document_ids.append(document_id)

                    # Embeddingを即座に生成する場合のみ
                    if generate_embeddings:
                        # 埋め込みベクトルを生成
                        embedding = self._generate_embedding(chunk)

                        # ベクトルを保存
                        embedding_str = '[' + ','.join(map(str, embedding.tolist())) + ']'
                        cursor.execute("""
                            INSERT INTO document_embeddings (document_id, embedding)
                            VALUES (%s, %s::vector);
                        """, (document_id, embedding_str))

                conn.commit()

                if generate_embeddings:
                    logger.info(f"文書（全文+チャンク）とEmbeddingを追加しました: {source_type}/{source_id}, {len(chunks)}チャンク")
                else:
                    logger.info(f"文書（全文+チャンク）を追加しました（Embeddingは後で生成）: {source_type}/{source_id}, {len(chunks)}チャンク")

                return True

        except Exception as e:
            logger.error("文書追加中にエラーが発生しました", error=str(e), exc_info=True)
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            return False
        finally:
            # 接続をプールに返却
            if conn and self.db_pool:
                self.db_pool.putconn(conn)

    def search_similar_documents(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """類似文書を検索"""
        print(f"🔍 search_similar_documents 呼び出し: query='{query}'")
        logger.info(f"search_similar_documents 呼び出し: query='{query}'")

        if not self.is_enabled:
            print("❌ RAGServiceが無効です")
            logger.warning("RAGServiceが無効です")
            return []

        # 代替RAG機能（Geminiのみ）の場合、ベクトル検索は利用できない
        if not self.db_pool or not self.embedding_model:
            print(f"⚠️ DB接続プール: {self.db_pool is not None}, Embeddingモデル: {self.embedding_model is not None}")
            logger.warning(f"代替RAG機能チェック: DB接続プール={self.db_pool is not None}, Embeddingモデル={self.embedding_model is not None}")
            return []

        conn = None
        try:
            print("✅ ベクトル検索を開始します")
            # クエリの埋め込みベクトルを生成
            query_embedding = self._generate_embedding(query)
            print(f"✅ クエリのEmbeddingを生成しました: shape={query_embedding.shape if hasattr(query_embedding, 'shape') else 'N/A'}")

            # 接続プールから接続を取得
            conn = self.db_pool.getconn()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # 埋め込みベクトルを文字列形式に変換
                embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'

                # 類似度検索（通常チャンクのみ対象 - is_full_text_chunk=false）
                print(f"🔍 類似度閾値: {self.similarity_threshold}")
                cursor.execute("""
                    SELECT
                        d.id,
                        d.source_type,
                        d.source_id,
                        d.title,
                        d.content,
                        d.full_content,
                        d.metadata,
                        1 - (de.embedding <=> %s::vector) as similarity
                    FROM documents d
                    JOIN document_embeddings de ON d.id = de.document_id
                    WHERE d.is_full_text_chunk = FALSE
                    ORDER BY similarity DESC
                    LIMIT 10;
                """, (embedding_str,))

                all_results = cursor.fetchall()
                print(f"🔍 全文書の類似度TOP10:")
                for i, row in enumerate(all_results[:5]):
                    print(f"  {i+1}. similarity={row['similarity']:.4f}, title={row['title'][:50]}")

                # 閾値でフィルタリング
                results = [r for r in all_results if r['similarity'] > self.similarity_threshold]
                print(f"✅ 閾値 {self.similarity_threshold} 以上: {len(results)}件")

                # limitで絞る（ただしsource_idごとに1件のみ）
                seen_source_ids = set()
                unique_results = []
                for r in results:
                    if r['source_id'] not in seen_source_ids:
                        seen_source_ids.add(r['source_id'])
                        unique_results.append(r)
                        if len(unique_results) >= limit:
                            break

                results = unique_results
                print(f"✅ DB検索結果（最終、重複除外）: {len(results)}件")

                # 辞書形式に変換（full_contentを使用 - Gems方式）
                documents = []
                for row in results:
                    documents.append({
                        'id': row['id'],
                        'source_type': row['source_type'],
                        'source_id': row['source_id'],
                        'title': row['title'],
                        'content': row['full_content'] if row['full_content'] else row['content'],  # 全文を優先
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
        finally:
            # 接続をプールに返却
            if conn and self.db_pool:
                self.db_pool.putconn(conn)

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
        """コンテキストを構築（自然な会話用に簡素化）"""
        # 文書の内容のみを結合（タイトルや類似度などのメタ情報は含めない）
        context_parts = []

        for doc in documents:
            # 文書の内容のみを追加
            context_parts.append(doc['content'])

        # 改行で区切って結合
        return "\n\n".join(context_parts)

    def _build_prompt(self, query: str, context: str) -> str:
        """プロンプトを構築"""
        if context:
            return f"""
あなたは親しみやすいカスタマーサポート担当者です。以下の資料を参考にして、質問に自然な会話で答えてください。

【質問】
{query}

【参考資料】
{context}

【回答のルール】
- 友達に説明するように、自然で親しみやすい口調で答える
- 「1. 結論」「2. 手順」などの構造化された見出しや番号付けは使わない
- 簡潔に、わかりやすく説明する
- 必要に応じて具体例を挙げる
- 参考資料の情報を基に回答する
- 回答の最後に注意書きなどは付けない（システム側で自動追加されます）
"""
        else:
            return f"""
あなたは親しみやすいカスタマーサポート担当者です。質問に自然な会話で答えてください。

【質問】
{query}

【回答のルール】
- 友達に説明するように、自然で親しみやすい口調で答える
- 「1. 結論」「2. 手順」などの構造化された見出しや番号付けは使わない
- 簡潔に、わかりやすく説明する
- 必要に応じて具体例を挙げる
"""

    def health_check(self) -> bool:
        """RAGサービスの健全性チェック"""
        return self.is_enabled and self.gemini_model is not None
