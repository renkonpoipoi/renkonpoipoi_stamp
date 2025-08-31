# Python 3.11 ベースの軽量イメージを使用
FROM python:3.11-slim

# 作業ディレクトリの作成
WORKDIR /app

# 依存ファイルのコピーとインストール
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# アプリ本体をコピー
COPY . .

# ポート指定（Render用では実質不要だが明記すると安心）
EXPOSE 10000

# アプリの起動コマンド（app.py 内に Flask の app がある場合）
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:10000", "app2:app"]



