FROM python:3.9-slim

WORKDIR /app

# システムの更新と必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 依存関係をインストール
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY line_qa_system/ ./line_qa_system/
COPY *.py ./
COPY *.md ./
COPY *.toml ./
COPY *.yaml ./
COPY *.yml ./

# 不要なファイルを削除
RUN rm -rf tests/ sample_data/ __pycache__/ .git/

# ポートを公開
EXPOSE 5000

# 環境変数を設定
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

# アプリケーションを起動
CMD ["python3", "-m", "line_qa_system.app"]