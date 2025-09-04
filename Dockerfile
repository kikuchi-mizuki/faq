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
COPY pyproject.toml poetry.lock ./

# 依存関係のインストール
RUN poetry install --no-dev

# アプリケーションコードのコピー
COPY . .

# ポート設定
EXPOSE 8000

# 環境変数設定
ENV FLASK_APP=line_qa_system.app
ENV FLASK_ENV=production
ENV PORT=8000

# 起動コマンド
CMD ["poetry", "run", "python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8000"]
