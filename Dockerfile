FROM python:3.9-slim

WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Poetryのインストール
RUN pip install poetry

# Poetry設定
RUN poetry config virtualenvs.create false

# 依存関係ファイルのコピー
COPY pyproject.toml ./
COPY poetry.lock ./

# ファイルの存在確認
RUN ls -la && echo "=== Files copied successfully ==="

# 依存関係のインストール
RUN poetry install --no-dev --no-interaction

# アプリケーションコードのコピー
COPY line_qa_system/ ./line_qa_system/
COPY *.py ./
COPY *.md ./
COPY *.toml ./
COPY *.yaml ./
COPY *.yml ./

# 不要なファイルの削除
RUN rm -rf tests/ sample_data/ __pycache__/ .git/

# ポート設定
EXPOSE 8000

# 環境変数設定
ENV FLASK_APP=line_qa_system.app
ENV FLASK_ENV=production
ENV PORT=8000

# 起動コマンド
CMD ["poetry", "run", "python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8000"]
