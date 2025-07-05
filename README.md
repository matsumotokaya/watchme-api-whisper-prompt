# Mood Chart Prompt Generator API

1日分（48個）のトランスクリプションファイルを統合し、ChatGPT分析に適したプロンプトを生成するFastAPIアプリケーション

## 📋 詳細仕様書

**完全な仕様書**: [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md) をご参照ください

## 🔥 重要：正式版ファイル

**正式版**: `main.py` を使用してください

- ❌ `app.py`: 古いバージョン（廃止予定）
- ✅ `main.py`: 正式版（EC2連携対応）

## 🚀 クイックスタート

### インストール

```bash
# 仮想環境の作成と有効化
python3 -m venv venv
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 起動

**本番環境（EC2連携）**:
```bash
export EC2_BASE_URL="https://api.hey-watch.me"
uvicorn main:app --host 0.0.0.0 --port 8009 --reload
```

**開発環境（ローカル）**:
```bash
export EC2_BASE_URL="local"
uvicorn main:app --host 0.0.0.0 --port 8009 --reload
```

### 基本的な使用方法

```bash
# EC2連携でプロンプト生成（推奨）
curl -X GET "http://localhost:8009/generate-mood-prompt-ec2?device_id=d067d407-cf73-4174-a9c1-d91fb60d64d0&date=2025-07-05"

# ヘルスチェック
curl -X GET "http://localhost:8009/health"
```

## 機能

### 主要エンドポイント

1. **`/generate-mood-prompt-ec2`** - EC2連携処理（推奨）
2. **`/generate-mood-prompt`** - ローカルファイル処理
3. **`/health`** - ヘルスチェック

### EC2連携機能

- EC2サーバーからのファイル取得
- ローカル処理
- EC2サーバーへの結果アップロード
- 環境変数による設定制御

## 📁 ファイル構造

### 入力ファイル（トランスクリプション）
```
/Users/kaya.matsumoto/data/data_accounts/{device_id}/{date}/transcriptions/
├── 00-00.json  # 00:00-00:30の音声転写
├── 00-30.json  # 00:30-01:00の音声転写
├── 01-00.json
├── ...
└── 23-30.json  # 23:30-24:00の音声転写
```

### 出力ファイル（生成プロンプト）
```
/Users/kaya.matsumoto/data/data_accounts/{device_id}/{date}/prompt/
└── emotion-timeline_gpt_prompt.json  # ChatGPT分析用プロンプト
```

## 🔧 環境変数

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `EC2_BASE_URL` | `"https://api.hey-watch.me"` | 本番EC2サーバー |
| `EC2_BASE_URL` | `"local"` | ローカル開発モード |

## 📊 レスポンス例

### 成功時
```json
{
  "status": "success",
  "message": "プロンプトが正常に生成され、EC2にアップロードされました",
  "output_path": "/data/data_accounts/d067d407-cf73-4174-a9c1-d91fb60d64d0/2025-07-05/prompt/emotion-timeline_gpt_prompt.json",
  "files_processed": 45,
  "missing_files": ["02-00.json", "14-30.json", "23-00.json"],
  "ec2_upload_status": "success"
}
```

### エラー時
```json
{
  "status": "error",
  "message": "ディレクトリが存在しません",
  "error_code": "DIRECTORY_NOT_FOUND",
  "details": {
    "device_id": "d067d407-cf73-4174-a9c1-d91fb60d64d0",
    "date": "2025-07-05"
  }
}
```

## 🔄 処理フロー

### EC2連携処理（推奨）
1. **EC2からファイル取得**: `{ec2_base_url}/status/{device_id}/{date}/transcriptions/{filename}`
2. **ローカル処理**: メモリ上でテキスト抽出・プロンプト生成
3. **ローカル保存**: `/Users/kaya.matsumoto/data/data_accounts/{device_id}/{date}/prompt/`
4. **EC2アップロード**: `{ec2_base_url}/upload-prompt`

### ローカル処理
1. **ローカルファイル読み込み**: `/Users/kaya.matsumoto/data/data_accounts/{device_id}/{date}/transcriptions/`
2. **プロンプト生成**: メモリ上でテキスト抽出・プロンプト生成
3. **ローカル保存**: `/Users/kaya.matsumoto/data/data_accounts/{device_id}/{date}/transcriptions/`

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

サーバー起動後、以下のURLでインタラクティブなAPIドキュメントにアクセスできます：
- **Swagger UI**: `http://localhost:8009/docs`
- **ReDoc**: `http://localhost:8009/redoc`
- **ヘルスチェック**: `http://localhost:8009/health`

## 🐛 トラブルシューティング

### よくある問題と解決方法

| 問題 | 原因 | 解決方法 |
|------|------|----------|
| **404エラー** | EC2サーバー上にファイルが存在しない | 正常な状態です。欠損ファイルとして処理されます |
| **422エラー** | EC2アップロードエンドポイントの仕様変更 | EC2サーバーの仕様を確認してください |
| **Address already in use** | 既存のプロセスが動作中 | `pkill -f uvicorn` でプロセスを停止 |
| **Permission denied** | ファイルアクセス権限不足 | ディレクトリの読み書き権限を確認 |

### デバッグコマンド

```bash
# プロセス確認
ps aux | grep uvicorn

# プロセス停止
pkill -f uvicorn

# デバッグモードで起動
uvicorn main:app --host 0.0.0.0 --port 8009 --reload --log-level debug

# 権限確認
ls -la /Users/kaya.matsumoto/data/data_accounts/
```

## 🤝 Streamlit連携

```python
import requests
import streamlit as st

# 環境選択
environment = st.selectbox("環境", ["Local", "EC2"])
base_url = "http://localhost:8009"

# API呼び出し
response = requests.get(
    f"{base_url}/generate-mood-prompt-ec2",
    params={"device_id": device_id, "date": date}
)

if response.status_code == 200:
    result = response.json()
    st.success(f"✅ プロンプト生成完了: {result['output_path']}")
    st.json(result)
else:
    st.error(f"❌ エラー: {response.text}")
``` 