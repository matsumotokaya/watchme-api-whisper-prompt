FROM python:3.11.8-slim

# 作業ディレクトリの設定
WORKDIR /app

# システムパッケージの更新とクリーンアップ
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY main.py .
COPY supabase_client.py .
COPY timeblock_endpoint.py .

# データディレクトリのマウントポイントを作成
RUN mkdir -p /Users/kaya.matsumoto/data

# ポート8009を公開
EXPOSE 8009

# 環境変数の設定
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8009/health')" || exit 1

# アプリケーションの起動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8009"] 