"""
文書収集サービス
Google Sheets、Google Docs、Google Driveから文書を収集
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import Config
from .rag_service import RAGService

logger = structlog.get_logger(__name__)


class DocumentCollector:
    """文書収集サービス"""

    def __init__(self, rag_service: RAGService):
        """初期化"""
        self.rag_service = rag_service
        self.sheet_id = Config.SHEET_ID_QA
        
        # Google認証情報の取得
        self.credentials = self._get_credentials()
        self.drive_service = None
        self.docs_service = None
        
        if self.credentials:
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.docs_service = build('docs', 'v1', credentials=self.credentials)

    def _get_credentials(self) -> Optional[Credentials]:
        """Google認証情報を取得"""
        try:
            service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            if not service_account_json:
                logger.error("GOOGLE_SERVICE_ACCOUNT_JSON環境変数が設定されていません")
                return None
            
            credentials_info = json.loads(service_account_json)
            credentials = Credentials.from_service_account_info(
                credentials_info,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/documents'
                ]
            )
            
            logger.info("Google認証情報を取得しました")
            return credentials
            
        except Exception as e:
            logger.error("Google認証情報の取得に失敗しました", error=str(e))
            return None

    def collect_all_documents(self) -> bool:
        """全ての文書を収集"""
        try:
            logger.info("文書収集を開始します")
            
            # Google Sheetsから文書を収集
            self._collect_sheets_documents()
            
            # Google Docsから文書を収集
            self._collect_docs_documents()
            
            # Google Driveから文書を収集
            self._collect_drive_documents()
            
            logger.info("文書収集が完了しました")
            return True
            
        except Exception as e:
            logger.error("文書収集中にエラーが発生しました", error=str(e))
            return False

    def _collect_sheets_documents(self):
        """Google Sheetsから文書を収集"""
        try:
            gc = gspread.authorize(self.credentials)
            spreadsheet = gc.open_by_key(self.sheet_id)
            
            # 各シートを処理
            for worksheet in spreadsheet.worksheets():
                sheet_name = worksheet.title
                logger.info(f"シート '{sheet_name}' を処理中...")
                
                # シートのデータを取得
                data = worksheet.get_all_records()
                
                if not data:
                    continue
                
                # シートの内容をテキストに変換
                content = self._convert_sheet_to_text(data, sheet_name)
                
                if content:
                    # RAGサービスに追加
                    self.rag_service.add_document(
                        source_type="google_sheets",
                        source_id=f"{self.sheet_id}_{sheet_name}",
                        title=f"スプレッドシート: {sheet_name}",
                        content=content,
                        metadata={
                            "sheet_name": sheet_name,
                            "row_count": len(data),
                            "collected_at": datetime.now().isoformat()
                        }
                    )
                    
                    logger.info(f"シート '{sheet_name}' を収集しました")
            
        except Exception as e:
            logger.error("Google Sheets収集中にエラーが発生しました", error=str(e))

    def _collect_docs_documents(self):
        """Google Docsから文書を収集"""
        if not self.docs_service:
            logger.warning("Google Docsサービスが利用できません")
            return
        
        try:
            # Google Docsファイルを検索
            query = "mimeType='application/vnd.google-apps.document'"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, modifiedTime)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Google Docsファイルを{len(files)}件発見しました")
            
            for file in files:
                try:
                    # 文書の内容を取得
                    doc = self.docs_service.documents().get(documentId=file['id']).execute()
                    content = self._extract_docs_content(doc)
                    
                    if content:
                        # RAGサービスに追加
                        self.rag_service.add_document(
                            source_type="google_docs",
                            source_id=file['id'],
                            title=file['name'],
                            content=content,
                            metadata={
                                "file_id": file['id'],
                                "modified_time": file['modifiedTime'],
                                "collected_at": datetime.now().isoformat()
                            }
                        )
                        
                        logger.info(f"Google Docs '{file['name']}' を収集しました")
                
                except Exception as e:
                    logger.error(f"Google Docs '{file['name']}' の処理中にエラーが発生しました", error=str(e))
                    continue
            
        except Exception as e:
            logger.error("Google Docs収集中にエラーが発生しました", error=str(e))

    def _collect_drive_documents(self):
        """Google Driveから文書を収集"""
        if not self.drive_service:
            logger.warning("Google Driveサービスが利用できません")
            return
        
        try:
            # テキストファイルを検索
            query = "mimeType='text/plain' or mimeType='text/csv' or mimeType='application/pdf'"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType, modifiedTime)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Google Driveファイルを{len(files)}件発見しました")
            
            for file in files:
                try:
                    # ファイルの内容を取得
                    content = self._extract_drive_file_content(file)
                    
                    if content:
                        # RAGサービスに追加
                        self.rag_service.add_document(
                            source_type="google_drive",
                            source_id=file['id'],
                            title=file['name'],
                            content=content,
                            metadata={
                                "file_id": file['id'],
                                "mime_type": file['mimeType'],
                                "modified_time": file['modifiedTime'],
                                "collected_at": datetime.now().isoformat()
                            }
                        )
                        
                        logger.info(f"Google Driveファイル '{file['name']}' を収集しました")
                
                except Exception as e:
                    logger.error(f"Google Driveファイル '{file['name']}' の処理中にエラーが発生しました", error=str(e))
                    continue
            
        except Exception as e:
            logger.error("Google Drive収集中にエラーが発生しました", error=str(e))

    def _convert_sheet_to_text(self, data: List[Dict[str, Any]], sheet_name: str) -> str:
        """シートデータをテキストに変換"""
        if not data:
            return ""
        
        # ヘッダーを取得
        headers = list(data[0].keys()) if data else []
        
        # テキストを構築
        text_parts = [f"シート名: {sheet_name}"]
        text_parts.append(f"列: {', '.join(headers)}")
        text_parts.append("")
        
        # 各行を処理
        for i, row in enumerate(data, 1):
            row_text = f"行{i}: "
            row_parts = []
            
            for header in headers:
                value = row.get(header, '')
                if value:
                    row_parts.append(f"{header}={value}")
            
            if row_parts:
                row_text += " | ".join(row_parts)
                text_parts.append(row_text)
        
        return "\n".join(text_parts)

    def _extract_docs_content(self, doc: Dict[str, Any]) -> str:
        """Google Docsの内容を抽出"""
        try:
            content_parts = []
            
            # 文書の構造を解析
            if 'body' in doc and 'content' in doc['body']:
                for element in doc['body']['content']:
                    if 'paragraph' in element:
                        paragraph = element['paragraph']
                        if 'elements' in paragraph:
                            for elem in paragraph['elements']:
                                if 'textRun' in elem and 'content' in elem['textRun']:
                                    content_parts.append(elem['textRun']['content'])
            
            return ''.join(content_parts).strip()
            
        except Exception as e:
            logger.error("Google Docs内容抽出中にエラーが発生しました", error=str(e))
            return ""

    def _extract_drive_file_content(self, file: Dict[str, Any]) -> str:
        """Google Driveファイルの内容を抽出"""
        try:
            # ファイルの内容をダウンロード
            request = self.drive_service.files().get_media(fileId=file['id'])
            content = request.execute()
            
            # テキストとしてデコード
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Google Driveファイル内容抽出中にエラーが発生しました: {file['name']}", error=str(e))
            return ""

    def health_check(self) -> bool:
        """文書収集サービスの健全性チェック"""
        return self.credentials is not None and self.rag_service.health_check()
