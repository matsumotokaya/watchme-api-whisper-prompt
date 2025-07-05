# Mood Chart Prompt Generator API 仕様書

## 概要

Mood Chart Prompt Generator APIは、1日分（48個）のトランスクリプションファイルを処理し、ChatGPTによる感情分析用のプロンプトを生成するFastAPIアプリケーションです。

## システム要件

- **Python**: 3.11.8
- **フレームワーク**: FastAPI
- **ポート**: 8009
- **依存関係**: fastapi, uvicorn, pydantic, python-multipart, requests, aiohttp

## API エンドポイント

### 1. ヘルスチェック

```
GET /health
```

**説明**: APIサーバーの稼働状況を確認

**レスポンス**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-XX XX:XX:XX"
}
```

### 2. ローカルファイル処理

```
GET /generate-mood-prompt
```

**説明**: ローカルファイルシステムからトランスクリプションファイルを読み込み、プロンプトを生成

**パラメータ**:
- `user_id` (string, required): ユーザーID
- `date` (string, required): 日付 (YYYY-MM-DD形式)

**入力パス**:
```
/Users/kaya.matsumoto/data/data_accounts/{user_id}/{date}/transcriptions/
```

**出力パス**:
```
/Users/kaya.matsumoto/data/data_accounts/{user_id}/{date}/transcriptions/emotion-timeline_gpt_prompt.json
```

**レスポンス例**:
```json
{
  "status": "success",
  "message": "プロンプトが正常に生成されました",
  "output_path": "/Users/kaya.matsumoto/data/data_accounts/user123/2025-06-15/transcriptions/emotion-timeline_gpt_prompt.json",
  "files_processed": 48,
  "missing_files": []
}
```

### 3. EC2連携処理（推奨）

```
GET /generate-mood-prompt-ec2
```

**説明**: EC2サーバーからファイルを取得し、処理後にEC2サーバーにアップロード

**パラメータ**:
- `user_id` (string, required): ユーザーID
- `date` (string, required): 日付 (YYYY-MM-DD形式)

**処理フロー**:
1. EC2サーバーからトランスクリプションファイルを取得
2. ローカルでプロンプト生成処理
3. ローカルファイルシステムに保存
4. EC2サーバーにプロンプトファイルをアップロード

**EC2 API エンドポイント**:
- **取得**: `GET {EC2_BASE_URL}/status/{user_id}/{date}/transcriptions/{filename}`
- **アップロード**: `POST {EC2_BASE_URL}/upload-prompt`

**出力パス**:
```
/Users/kaya.matsumoto/data/data_accounts/{user_id}/{date}/prompt/emotion-timeline_gpt_prompt.json
```

**レスポンス例**:
```json
{
  "status": "success",
  "message": "プロンプトが正常に生成され、EC2にアップロードされました",
  "output_path": "/data/data_accounts/user123/2025-06-15/prompt/emotion-timeline_gpt_prompt.json",
  "files_processed": 45,
  "missing_files": ["02-00.json", "14-30.json", "23-00.json"],
  "ec2_upload_status": "success"
}
```

## 入力ファイル仕様

### ファイル命名規則
- **形式**: `HH-MM.json`
- **時間範囲**: 00-00.json から 23-30.json まで（30分間隔）
- **総数**: 48ファイル/日

### JSONファイル構造
以下のフィールドからテキストを抽出します：

```json
{
  "text": "テキスト内容",
  "transcript": "転写内容", 
  "content": "コンテンツ",
  "transcription": "トランスクリプション",
  "nested": {
    "text": "ネストされたテキスト"
  }
}
```

**対応フィールド**: `text`, `transcript`, `content`, `transcription`（ネスト構造も対応）

## 出力ファイル仕様

### ファイル名
`emotion-timeline_gpt_prompt.json`

### 出力JSON構造

```json
{
  "prompt": "以下のテキストを分析し、感情の時系列変化をJSONで出力してください...",
  "metadata": {
    "user_id": "user123",
    "date": "2025-06-15",
    "total_files": 48,
    "processed_files": 45,
    "missing_files": ["02-00.json", "14-30.json", "23-00.json"],
    "generated_at": "2025-01-XX XX:XX:XX"
  },
  "expected_output_format": {
    "timePoints": ["00:00", "00:30", "01:00", "...", "23:30"],
    "emotionScores": [-50, 20, 0, "...", 30],
    "dominantEmotions": ["sadness", "joy", "neutral", "...", "excitement"],
    "insights": "全体的な感情の傾向や特徴的なパターンの分析"
  }
}
```

## ChatGPTプロンプト仕様

### 生成されるプロンプトの構造

1. **基本指示**: 感情分析の目的と方法
2. **出力形式**: 厳密なJSON構造の指定
3. **時間軸**: 48個の時間ポイント（00:00-23:30）
4. **感情スコア**: -100から+100の整数値
5. **感情カテゴリ**: 主要な感情の分類
6. **分析ルール**: 欠損データの処理方法
7. **完全な出力例**: 48要素すべてを含む具体例

### 期待される出力形式

```json
{
  "timePoints": [
    "00:00", "00:30", "01:00", "01:30", "02:00", "02:30",
    "03:00", "03:30", "04:00", "04:30", "05:00", "05:30",
    "06:00", "06:30", "07:00", "07:30", "08:00", "08:30",
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00", "16:30", "17:00", "17:30",
    "18:00", "18:30", "19:00", "19:30", "20:00", "20:30",
    "21:00", "21:30", "22:00", "22:30", "23:00", "23:30"
  ],
  "emotionScores": [48個の整数値またはnull（欠損値）],
  "averageScore": 15.2,
  "positiveHours": 18.0,
  "negativeHours": 2.0,
  "neutralHours": 28.0,
  "insights": ["分析結果の文字列配列"],
  "emotionChanges": [{"time": "HH:MM", "event": "イベント", "score": 整数値}]
}
```

### JSON品質要件

- **欠損値の扱い**: 必ず `null` を使用（NaN、undefined、Infinityは禁止）
- **感情スコア**: -100から+100の整数値または`null`
- **averageScore**: `null`を除外して計算、全て`null`の場合は0.0
- **時間集計**: `null`を無視して集計

## 環境設定

### 環境変数

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `EC2_BASE_URL` | `"https://api.hey-watch.me"` | 本番EC2サーバーURL |
| `EC2_BASE_URL` | `"local"` | ローカル開発モード |

### 起動コマンド

**本番環境**:
```bash
export EC2_BASE_URL="https://api.hey-watch.me"
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8009 --reload
```

**開発環境**:
```bash
export EC2_BASE_URL="local"
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8009 --reload
```

## エラーハンドリング

### HTTPステータスコード

- **200**: 正常処理完了
- **400**: リクエストパラメータエラー
- **403**: ファイルアクセス権限エラー
- **404**: ファイル/ディレクトリが存在しない
- **422**: EC2アップロードエラー
- **500**: サーバー内部エラー

### エラーレスポンス例

```json
{
  "status": "error",
  "message": "エラーの詳細説明",
  "error_code": "PERMISSION_DENIED",
  "details": {
    "user_id": "user123",
    "date": "2025-06-15",
    "missing_permissions": ["/path/to/directory"]
  }
}
```

## デバッグ機能

### EC2連携デバッグ情報

- ディレクトリ存在確認
- ファイルアクセス権限チェック
- 親ディレクトリの内容表示
- 詳細なエラーログ出力

### ログレベル設定

```bash
uvicorn main:app --host 0.0.0.0 --port 8009 --reload --log-level debug
```

## パフォーマンス

### 処理時間
- **ローカル処理**: 通常1-3秒
- **EC2連携処理**: 通常5-10秒（ネットワーク状況による）

### メモリ使用量
- **基本**: 約50-100MB
- **48ファイル処理時**: 約100-200MB

## セキュリティ

### アクセス制御
- ローカルファイルシステムへの読み書き権限が必要
- EC2 APIエンドポイントへのHTTPS接続

### データ保護
- 一時的なメモリ処理（永続化なし）
- ローカルファイルシステムでの安全な保存

## 互換性

### Streamlitダッシュボード連携

```python
import requests
import streamlit as st

# 環境選択
environment = st.selectbox("環境", ["Local", "EC2"])
base_url = "http://localhost:8009" if environment == "Local" else "https://your-api-server.com"

# API呼び出し
response = requests.get(
    f"{base_url}/generate-mood-prompt-ec2",
    params={"user_id": user_id, "date": date}
)

if response.status_code == 200:
    result = response.json()
    st.success(f"プロンプト生成完了: {result['output_path']}")
else:
    st.error(f"エラー: {response.text}")
```

## 今後の拡張予定

- 複数日分の一括処理
- 感情分析結果の直接取得
- リアルタイム処理対応
- 追加の出力形式サポート 