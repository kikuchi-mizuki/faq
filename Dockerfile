FROM python:3.9-slim

WORKDIR /app

# 最小限の依存関係のみインストール
COPY requirements.minimal.txt ./
RUN pip install -r requirements.minimal.txt

# アプリケーションファイルをコピー
COPY minimal_app.py ./

# ポートを公開
EXPOSE 5000

# 環境変数を設定
ENV PORT=5000

# アプリケーションを起動
CMD ["python3", "minimal_app.py"]