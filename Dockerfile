FROM python:3.9-slim

WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Poetryのインストール
RUN pip install poetry==1.7.1

# Poetry設定
RUN poetry config virtualenvs.create false

# 依存関係ファイルのコピー
COPY pyproject.toml ./
COPY poetry.lock ./

# ファイルの存在確認
RUN ls -la && echo "=== Files copied successfully ==="

# Poetryで依存関係をエクスポートしてpipでインストール
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes
RUN pip install -r requirements.txt
# STEP2で追加されたredisパッケージを明示的にインストール
RUN pip install redis==5.0.0

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
EXPOSE $PORT

# 環境変数はRailwayで設定されるため、ここでは設定しない

# 起動コマンド
CMD ["python", "start.py"]
