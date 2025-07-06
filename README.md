# Mood Chart Prompt Generator API

1日分（48個）のトランスクリプションファイルを統合し、ChatGPT分析に適したプロンプトを生成するFastAPIアプリケーション

## ✅ 最新アップデート (2025-07-06)

**🆕 Supabase統合完了**: `vibe_whisper`テーブルから読み込み、`vibe_whisper_prompt`テーブルに保存
**✅ 本番テスト完了**: 2025-07-06データで正常動作確認済み（処理ファイル数: 2個、欠損: 46個）
**✅ カラム名修正**: `time_slot` → `time_block` への対応完了
**✅ デバイスID移行完了**: `user_id` → `device_id` アーキテクチャへの完全移行
**✅ Vault連携確認済み**: `emotion-timeline_gpt_prompt.json` のVaultサーバーへの正常アップロード
**✅ 本番稼働準備完了**: EC2連携でのプロダクション環境対応

## 📋 詳細仕様書

**完全な仕様書**: [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md) をご参照ください

## 🔥 重要：正式版ファイル

**正式版**: `main.py` を使用してください

- ❌ `app.py`: 古いバージョン（廃止予定）
- ✅ `main.py`: 正式版（EC2連携対応、デバイスID移行済み）

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
# 🆕 Supabase統合版（推奨）- vibe_whisperテーブルから読み込み、vibe_whisper_promptテーブルに保存
curl -X GET "http://localhost:8009/generate-mood-prompt-supabase?device_id=d067d407-cf73-4174-a9c1-d91fb60d64d0&date=2025-07-06"

# EC2連携でプロンプト生成 - デバイスID使用
curl -X GET "http://localhost:8009/generate-mood-prompt-ec2?device_id=d067d407-cf73-4174-a9c1-d91fb60d64d0&date=2025-07-05"

# ローカル処理 - デバイスID使用
curl -X GET "http://localhost:8009/generate-mood-prompt?device_id=d067d407-cf73-4174-a9c1-d91fb60d64d0&date=2025-07-05"

# ヘルスチェック
curl -X GET "http://localhost:8009/health"
```

### 成功レスポンス例

```json
{
  "status": "success",
  "output_path": "/data/data_accounts/d067d407-cf73-4174-a9c1-d91fb60d64d0/2025-07-05/prompt/emotion-timeline_gpt_prompt.json"
}
```

## ✅ 実装完了状況

### ✅ 完了済みエンドポイント

| エンドポイント | 機能 | 状態 | 出力先 | デバイスID対応 |
|---------------|------|------|-------------|-------------|
| `GET /health` | ヘルスチェック | ✅ **完了** | - | N/A |
| `GET /generate-mood-prompt` | ローカルプロンプト生成 | ✅ **完了** | ローカルファイル | ✅ |
| `GET /generate-mood-prompt-ec2` | EC2プロンプト生成・Vaultアップロード | ✅ **完了** | EC2/Vault | ✅ |
| `GET /generate-mood-prompt-supabase` | Supabase統合版 | ✅ **完了** | vibe_whisper_promptテーブル | ✅ |

### ✅ 実装完了機能

1. **🆕 Supabase統合**: `vibe_whisper`テーブルからデータ読み込み、`vibe_whisper_prompt`テーブルへ保存
2. **✅ デバイスID移行**: 全エンドポイントで`user_id` → `device_id`移行完了
3. **✅ プロンプト生成**: 48時間分のトランスクリプション統合処理
4. **✅ Vault統合**: `emotion-timeline_gpt_prompt.json`のVaultサーバーアップロード
5. **✅ EC2連携**: 本番環境での動作確認済み

### 🔄 WatchMeエコシステムでの位置づけ

```
[Supabase統合版]
iOS App → Whisper API → vibe_whisper → [このAPI] → vibe_whisper_prompt → ChatGPT API
                                             ↑
                                    プロンプト生成・DB保存

[既存版]
iOS App → Vault API → Whisper API → [このAPI] → ChatGPT API → 最終結果
                                         ↑
                              emotion-timeline_gpt_prompt.json
                                    Vault保存完了
```

**このAPIの役割**: 
- Supabase版: vibe_whisperテーブルから読み込み → プロンプト生成 → vibe_whisper_promptテーブルに保存
- 既存版: Whisperトランスクリプション → ChatGPT分析用プロンプト生成・Vault保存

### EC2連携機能

- EC2サーバーからのファイル取得
- ローカル処理
- EC2サーバーへの結果アップロード
- 環境変数による設定制御

## 📁 ファイル構造

### 入力ファイル（トランスクリプション）
```
# ローカル
/Users/kaya.matsumoto/data/data_accounts/{device_id}/{date}/transcriptions/
├── 00-00.json  # 00:00-00:30の音声転写
├── 00-30.json  # 00:30-01:00の音声転写
├── 01-00.json
├── ...
└── 23-30.json  # 23:30-24:00の音声転写

# Vault (EC2)
/data/data_accounts/{device_id}/{date}/transcriptions/
```

### 出力ファイル（生成プロンプト）
```
# ローカル
/Users/kaya.matsumoto/data/data_accounts/{device_id}/{date}/prompt/
└── emotion-timeline_gpt_prompt.json  # ChatGPT分析用プロンプト

# Vault (EC2) - 自動アップロード
/data/data_accounts/{device_id}/{date}/prompt/
└── emotion-timeline_gpt_prompt.json  # ChatGPT分析用プロンプト
```

## 🔧 環境変数

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `SUPABASE_URL` | `https://your-project.supabase.co` | SupabaseプロジェクトURL |
| `SUPABASE_KEY` | `your-anon-key` | Supabase Anonymous Key |
| `EC2_BASE_URL` | `"https://api.hey-watch.me"` | 本番EC2サーバー（Vault連携） |
| `EC2_BASE_URL` | `"local"` | ローカル開発モード |

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

### 2025年7月5日従来版テスト結果

**テストデバイス**: `d067d407-cf73-4174-a9c1-d91fb60d64d0`

```bash
# ✅ ローカル処理テスト
curl "http://localhost:8009/generate-mood-prompt?device_id=d067d407-cf73-4174-a9c1-d91fb60d64d0&date=2025-07-05"
# → 成功: ローカルファイル生成

# ✅ EC2連携テスト  
curl "http://localhost:8009/generate-mood-prompt-ec2?device_id=d067d407-cf73-4174-a9c1-d91fb60d64d0&date=2025-07-05"
# → 成功: Vaultサーバーにアップロード

# ✅ Vault確認
curl "https://api.hey-watch.me/status/d067d407-cf73-4174-a9c1-d91fb60d64d0/2025-07-05/prompt/emotion-timeline_gpt_prompt.json"
# → 成功: ファイル確認完了
```

**処理結果**:
- 📊 処理ファイル数: 5個
- 📊 欠損ファイル数: 43個
- ✅ プロンプト生成: 正常完了
- ✅ Vaultアップロード: 正常完了

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

### Supabase統合処理（新規・推奨）
1. **vibe_whisperテーブルから読み込み**: 指定device_id、dateのレコードを取得
2. **プロンプト生成**: transcriptionフィールドからテキスト抽出・統合
3. **vibe_whisper_promptテーブルに保存**: UPSERT（既存レコードは更新）

### EC2連携処理
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