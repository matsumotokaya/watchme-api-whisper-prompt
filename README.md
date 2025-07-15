# Mood Chart Prompt Generator API

1日分（48個）のトランスクリプションファイルを統合し、ChatGPT分析に適したプロンプトを生成するFastAPIアプリケーション

## ✅ 最新アップデート (2025-07-15)

**🆕 外部URL公開**: `https://api.hey-watch.me/vibe-aggregator/` で外部からアクセス可能
**✅ Nginxリバースプロキシ設定**: SSL/HTTPS対応、CORS設定完了
**✅ マイクロサービス対応**: 他のサービスから簡単にAPI呼び出し可能
**✅ プロンプト形式更新**: 心理グラフ用JSON生成形式に変更（感情スコア配列、時間軸、統計情報を含む）
**✅ Systemd統合完了**: EC2での自動起動・常時稼働に対応
**✅ 古いエンドポイント削除**: ローカル版・EC2版を削除し、Supabase統合版のみに統一
**✅ Supabase統合**: `vibe_whisper`テーブルから読み込み、`vibe_whisper_prompt`テーブルに保存
**✅ 本番稼働中**: EC2（3.24.16.82:8009）で正常稼働中
**✅ Docker対応**: Docker Composeによる簡単デプロイ

## 📋 詳細仕様書

**完全な仕様書**: [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md) をご参照ください

## 🔥 重要：正式版ファイル

**正式版**: `main.py` を使用してください

- ❌ `app.py`: 古いバージョン（廃止予定）
- ✅ `main.py`: 正式版（Supabase統合版）

## 🚀 クイックスタート

### 環境設定

```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集してSupabase認証情報を設定
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=your-anon-key
```

### インストール

```bash
# 仮想環境の作成と有効化
python3 -m venv venv
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 起動

```bash
uvicorn main:app --host 0.0.0.0 --port 8009 --reload
```

### 基本的な使用方法

```bash
# 🆕 外部URL（本番環境）- マイクロサービス間で使用
curl -X GET "https://api.hey-watch.me/vibe-aggregator/generate-mood-prompt-supabase?device_id=d067d407-cf73-4174-a9c1-d91fb60d64d0&date=2025-07-15"

# ヘルスチェック（外部URL）
curl -X GET "https://api.hey-watch.me/vibe-aggregator/health"

# ローカル開発用
curl -X GET "http://localhost:8009/generate-mood-prompt-supabase?device_id=d067d407-cf73-4174-a9c1-d91fb60d64d0&date=2025-07-15"
```

### 成功レスポンス例

```json
{
  "status": "success",
  "message": "プロンプトが正常に生成され、データベースに保存されました。処理済み: 1個、欠損: 47個",
  "output_path": null
}
```

### 最新テスト結果（2025-07-15）

```bash
# 外部URL経由でのテスト
curl "https://api.hey-watch.me/vibe-aggregator/generate-mood-prompt-supabase?device_id=d067d407-cf73-4174-a9c1-d91fb60d64d0&date=2025-07-15"

# 結果
{
  "status": "success",
  "message": "プロンプトが正常に生成され、データベースに保存されました。処理済み: 1個、欠損: 47個",
  "output_path": null
}
```

## ✅ 実装完了状況

### ✅ 完了済みエンドポイント

| エンドポイント | 機能 | 状態 | 出力先 | デバイスID対応 |
|---------------|------|------|-------------|-------------|
| `GET /health` | ヘルスチェック | ✅ **完了** | - | N/A |
| `GET /generate-mood-prompt-supabase` | Supabase統合版 | ✅ **完了** | vibe_whisper_promptテーブル | ✅ |

### ✅ 実装完了機能

1. **🆕 Supabase統合**: `vibe_whisper`テーブルからデータ読み込み、`vibe_whisper_prompt`テーブルへ保存
2. **✅ デバイスID対応**: `device_id`を使用したデータ処理
3. **✅ プロンプト生成**: 48個（24時間分）のトランスクリプション統合処理

### 🔄 WatchMeエコシステムでの位置づけ

```
iOS App → Whisper API → vibe_whisper → [このAPI] → vibe_whisper_prompt → ChatGPT API
                                             ↑
                                    プロンプト生成・DB保存
```

**このAPIの役割**: 
- vibe_whisperテーブルから読み込み → プロンプト生成 → vibe_whisper_promptテーブルに保存

## 📁 データ構造

### 入力データ（vibe_whisperテーブル）
- `device_id`: デバイス識別子
- `date`: 日付（YYYY-MM-DD）
- `time_block`: 時間帯（例: "00-00", "00-30"）
- `transcription`: 音声転写テキスト

### 出力データ（vibe_whisper_promptテーブル）
- `device_id`: デバイス識別子
- `date`: 日付（YYYY-MM-DD）
- `prompt`: 生成されたChatGPT用プロンプト（心理グラフJSON生成形式）
- `processed_files`: 処理されたレコード数
- `missing_files`: 欠損している時間帯のリスト
- `generated_at`: 生成日時

### プロンプト形式の特徴
生成されるプロンプトは、ChatGPTに心理グラフ用のJSONデータを生成させるための専用形式です：
- **timePoints**: 48個の時間点（00:00〜23:30）
- **emotionScores**: -100〜+100の感情スコア配列（欠損はnull）
- **統計情報**: 平均スコア、ポジティブ/ネガティブ/ニュートラルな時間
- **insights**: 1日の心理的傾向の自然文記述
- **emotionChanges**: 感情の大きな変化点

## 🔧 環境変数

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `SUPABASE_URL` | `https://your-project.supabase.co` | SupabaseプロジェクトURL |
| `SUPABASE_KEY` | `your-anon-key` | Supabase Anonymous Key |

## 🧪 テスト実績

### 2025年7月6日Supabase統合版テスト結果

**テストデバイス**: `d067d407-cf73-4174-a9c1-d91fb60d64d0`

```bash
# ✅ Supabase統合版テスト
curl "http://localhost:8009/generate-mood-prompt-supabase?device_id=d067d407-cf73-4174-a9c1-d91fb60d64d0&date=2025-07-06"
# → 成功: vibe_whisper_promptテーブルに保存

# ✅ データベース確認
python3 check_result.py
# → 成功: データ保存確認完了
```

**処理結果**:
- 📊 処理ファイル数: 2個
- 📊 欠損ファイル数: 46個
- ✅ プロンプト生成: 正常完了
- ✅ データベース保存: 正常完了


## 📊 レスポンス例

### 成功時
```json
{
  "status": "success",
  "message": "プロンプトが正常に生成され、データベースに保存されました。処理済み: 5個、欠損: 43個",
  "output_path": null
}
```

### エラー時
```json
{
  "status": "error",
  "detail": "無効な日付形式です。YYYY-MM-DD形式で入力してください。"
}
```

## 🔄 処理フロー

### Supabase統合処理
1. **vibe_whisperテーブルから読み込み**: 指定device_id、dateのレコードを取得
2. **プロンプト生成**: transcriptionフィールドからテキスト抽出・統合
3. **vibe_whisper_promptテーブルに保存**: UPSERT（既存レコードは更新）

## 🛡️ 堅牢性

- **欠損ファイル対応**: ファイルが存在しない場合でも正常処理
- **空データ対応**: 空のログでも適切なプロンプト生成
- **エラーハンドリング**: 詳細なエラー情報とデバッグ機能
- **権限チェック**: ファイルアクセス権限の事前確認

## 🔧 技術仕様

- **Python**: 3.11.8
- **フレームワーク**: FastAPI
- **非同期処理**: aiohttp
- **ファイル処理**: pathlib
- **ポート**: 8009

## 📚 API ドキュメント

### 本番環境（外部URL）
- **Swagger UI**: `https://api.hey-watch.me/vibe-aggregator/docs`
- **ReDoc**: `https://api.hey-watch.me/vibe-aggregator/redoc`
- **ヘルスチェック**: `https://api.hey-watch.me/vibe-aggregator/health`

### ローカル開発環境
- **Swagger UI**: `http://localhost:8009/docs`
- **ReDoc**: `http://localhost:8009/redoc`
- **ヘルスチェック**: `http://localhost:8009/health`

## 🚀 本番環境デプロイ（EC2）

### 初回デプロイ手順

```bash
# 1. EC2サーバーにSSH接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# 2. プロジェクトディレクトリに移動
cd api_gen-prompt_mood-chart_v1

# 3. .envファイルを作成（Supabase認証情報を設定）
nano .env

# 4. Dockerイメージをビルド
docker-compose build

# 5. サービスを起動
docker-compose up -d
```

### Systemdによる自動起動設定（設定済み）

本番環境では、Systemdサービスとして設定されており、EC2インスタンスの起動時に自動的にAPIが起動します。

```bash
# サービスの状態確認
sudo systemctl status mood-chart-api

# サービスの再起動
sudo systemctl restart mood-chart-api

# サービスのログ確認
sudo journalctl -u mood-chart-api -f

# 手動でサービスを停止
sudo systemctl stop mood-chart-api

# 手動でサービスを開始
sudo systemctl start mood-chart-api
```

### コード更新時の手順

```bash
# 1. EC2サーバーにSSH接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# 2. プロジェクトディレクトリに移動
cd api_gen-prompt_mood-chart_v1

# 3. 最新コードを取得（Gitを使用している場合）
git pull origin main

# 4. Dockerイメージを再ビルド
docker-compose build

# 5. サービスを再起動
sudo systemctl restart mood-chart-api

# 6. 動作確認
curl http://localhost:8009/health
```

## 🐛 トラブルシューティング

### よくある問題と解決方法

| 問題 | 原因 | 解決方法 |
|------|------|----------|
| **Invalid API key** | Supabase認証情報が無効 | .envファイルのSUPABASE_URLとSUPABASE_KEYを確認 |
| **Address already in use** | 既存のプロセスが動作中 | `sudo systemctl stop mood-chart-api` でサービスを停止 |
| **データが見つからない** | 指定日付のデータが存在しない | vibe_whisperテーブルにデータが存在するか確認 |
| **ModuleNotFoundError: supabase** | Supabaseライブラリバージョンの不一致 | requirements.txtでsupabase==2.0.0を指定 |

### デバッグコマンド

```bash
# Dockerコンテナの状態確認
docker-compose ps

# Dockerコンテナのログ確認
docker-compose logs -f

# コンテナ内に入って調査
docker exec -it api_gen_prompt_mood_chart bash

# API直接テスト（EC2上で）
curl -X GET "http://localhost:8009/generate-mood-prompt-supabase?device_id=d067d407-cf73-4174-a9c1-d91fb60d64d0&date=2025-07-14"
```

## 🤝 Streamlit連携

```python
import requests
import streamlit as st

# 本番環境での使用
base_url = "https://api.hey-watch.me/vibe-aggregator"

# API呼び出し
response = requests.get(
    f"{base_url}/generate-mood-prompt-supabase",
    params={"device_id": device_id, "date": date}
)

if response.status_code == 200:
    result = response.json()
    st.success(f"✅ プロンプト生成完了")
    st.json(result)
else:
    st.error(f"❌ エラー: {response.text}")
```

## 🔗 マイクロサービス統合

### 外部サービスからの利用方法

```python
import requests
import asyncio
import aiohttp

# 同期版
def generate_mood_prompt(device_id: str, date: str):
    url = "https://api.hey-watch.me/vibe-aggregator/generate-mood-prompt-supabase"
    params = {"device_id": device_id, "date": date}
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error: {response.text}")

# 非同期版
async def generate_mood_prompt_async(device_id: str, date: str):
    url = "https://api.hey-watch.me/vibe-aggregator/generate-mood-prompt-supabase"
    params = {"device_id": device_id, "date": date}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"API Error: {await response.text()}")

# 使用例
result = generate_mood_prompt("d067d407-cf73-4174-a9c1-d91fb60d64d0", "2025-07-15")
print(result)
```

### 利用可能なエンドポイント

| エンドポイント | メソッド | 説明 | パラメータ |
|---------------|---------|------|-----------|
| `/health` | GET | ヘルスチェック | なし |
| `/generate-mood-prompt-supabase` | GET | プロンプト生成 | `device_id`, `date` |
| `/docs` | GET | Swagger UI | なし |
| `/redoc` | GET | ReDoc | なし |

### セキュリティ設定

- ✅ HTTPS対応（SSL証明書あり）
- ✅ CORS設定済み
- ✅ 適切なヘッダー設定
- ✅ レート制限対応（Nginxレベル） 