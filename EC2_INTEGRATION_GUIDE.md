# EC2連携API開発ガイド - ChatGPT分析API向け

## 🎯 概要

このガイドは、プロンプト生成APIの開発経験から得た知見をもとに、次のChatGPT分析API開発で同じ問題を避けるためのものです。

## 📋 想定する処理フロー

```
EC2サーバー → プロンプト取得 → ChatGPT分析 → 結果をEC2に保存
```

## ⚠️ 必ず遭遇する問題と解決策

### 1. **直接EC2保存の制限**

**問題**: EC2サーバーに直接ファイルを書き込めない

**解決策**: 
- 一度ローカルファイルシステムに保存
- その後EC2のアップロードAPIを使用

```python
# ❌ 直接EC2保存（不可能）
# with open(f"{ec2_path}/result.json", "w") as f:

# ✅ ローカル経由での保存
local_path = f"/Users/kaya.matsumoto/data/data_accounts/{user_id}/{date}/analysis/"
os.makedirs(local_path, exist_ok=True)
with open(f"{local_path}/emotion_analysis.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# EC2にアップロード
await upload_to_ec2(local_path, result)
```

### 2. **必要なライブラリ**

**重要**: 最初から以下のライブラリを`requirements.txt`に追加

```txt
fastapi
uvicorn
pydantic
python-multipart
requests
aiohttp  # ← EC2連携で必須
openai   # ← ChatGPT API用
```

**理由**: 後から追加すると依存関係の問題が発生する可能性

### 3. **ディレクトリ構造の設計**

**推奨構造**:
```
/Users/kaya.matsumoto/data/data_accounts/{user_id}/{date}/
├── transcriptions/          # 音声転写（既存）
├── prompt/                  # プロンプト（既存）
└── analysis/               # ChatGPT分析結果（新規）
    └── emotion_analysis.json
```

**重要**: 最初からディレクトリ作成処理を実装

```python
def ensure_directories(user_id: str, date: str):
    base_path = f"/Users/kaya.matsumoto/data/data_accounts/{user_id}/{date}"
    directories = ["transcriptions", "prompt", "analysis"]
    
    for dir_name in directories:
        dir_path = os.path.join(base_path, dir_name)
        os.makedirs(dir_path, exist_ok=True)
        
    return base_path
```

### 4. **EC2 APIエンドポイント設計**

**必要なエンドポイント**:

1. **プロンプト取得**: 
   ```
   GET {EC2_BASE_URL}/status/{user_id}/{date}/prompt/emotion-timeline_gpt_prompt.json
   ```

2. **分析結果アップロード**:
   ```
   POST {EC2_BASE_URL}/upload-analysis
   ```

**重要**: アップロードエンドポイントの仕様を事前に確認

### 5. **非同期処理の実装**

**必須**: EC2との通信は非同期で実装

```python
import aiohttp
import asyncio

async def fetch_prompt_from_ec2(user_id: str, date: str):
    async with aiohttp.ClientSession() as session:
        url = f"{EC2_BASE_URL}/status/{user_id}/{date}/prompt/emotion-timeline_gpt_prompt.json"
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

async def upload_analysis_to_ec2(user_id: str, date: str, analysis_data: dict):
    async with aiohttp.ClientSession() as session:
        url = f"{EC2_BASE_URL}/upload-analysis"
        data = {
            "user_id": user_id,
            "date": date,
            "file_path": f"/data/data_accounts/{user_id}/{date}/analysis/emotion_analysis.json",
            "content": json.dumps(analysis_data, ensure_ascii=False)
        }
        async with session.post(url, json=data) as response:
            return response.status == 200
```

### 6. **エラーハンドリングパターン**

**重要**: 以下のエラーパターンを最初から実装

```python
async def analyze_with_chatgpt_ec2(user_id: str, date: str):
    try:
        # 1. プロンプト取得
        prompt_data = await fetch_prompt_from_ec2(user_id, date)
        if not prompt_data:
            return {"status": "error", "message": "プロンプトが見つかりません"}
        
        # 2. ChatGPT分析
        analysis_result = await call_chatgpt_api(prompt_data["prompt"])
        
        # 3. ローカル保存
        local_path = save_analysis_locally(user_id, date, analysis_result)
        
        # 4. EC2アップロード
        upload_success = await upload_analysis_to_ec2(user_id, date, analysis_result)
        
        return {
            "status": "success",
            "local_path": local_path,
            "ec2_upload_status": "success" if upload_success else "failed"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### 7. **環境変数の管理**

**必要な環境変数**:
```bash
export EC2_BASE_URL="https://api.hey-watch.me"
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_MODEL="gpt-4"  # または使用するモデル
```

### 8. **ChatGPT API統合**

**推奨実装**:
```python
import openai
from openai import AsyncOpenAI

async def call_chatgpt_api(prompt: str):
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            messages=[
                {"role": "system", "content": "あなたは感情分析の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        return {
            "analysis": response.choices[0].message.content,
            "usage": response.usage.dict(),
            "model": response.model
        }
        
    except Exception as e:
        raise Exception(f"ChatGPT API エラー: {str(e)}")
```

## 🚨 よくある落とし穴

### 1. **JSONレスポンスの解析**
```python
# ❌ 直接JSON解析（エラーの原因）
result = json.loads(chatgpt_response)

# ✅ 安全な解析
try:
    # ChatGPTのレスポンスからJSON部分を抽出
    json_start = chatgpt_response.find('{')
    json_end = chatgpt_response.rfind('}') + 1
    json_str = chatgpt_response[json_start:json_end]
    result = json.loads(json_str)
except json.JSONDecodeError:
    # フォールバック処理
    result = {"error": "JSON解析失敗", "raw_response": chatgpt_response}
```

### 2. **ファイルパスの統一**
```python
# 統一されたパス管理
class PathManager:
    BASE_PATH = "/Users/kaya.matsumoto/data/data_accounts"
    
    @classmethod
    def get_analysis_path(cls, user_id: str, date: str) -> str:
        return f"{cls.BASE_PATH}/{user_id}/{date}/analysis"
    
    @classmethod
    def get_prompt_path(cls, user_id: str, date: str) -> str:
        return f"{cls.BASE_PATH}/{user_id}/{date}/prompt"
```

### 3. **レート制限対応**
```python
import asyncio

async def call_chatgpt_with_retry(prompt: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await call_chatgpt_api(prompt)
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 60  # 指数バックオフ
                await asyncio.sleep(wait_time)
                continue
            raise e
```

## 📊 推奨API構造

```python
from fastapi import FastAPI, HTTPException
import os
import json
import aiohttp
from openai import AsyncOpenAI

app = FastAPI(title="ChatGPT Analysis API")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/analyze-mood-ec2")
async def analyze_mood_ec2(user_id: str, date: str):
    """EC2連携でChatGPT分析を実行"""
    # 実装内容...
    pass

@app.get("/analyze-mood")  
async def analyze_mood_local(user_id: str, date: str):
    """ローカルファイルでChatGPT分析を実行"""
    # 実装内容...
    pass
```

## 🔧 デバッグ機能

**重要**: 最初からデバッグ機能を実装

```python
async def debug_ec2_connection(user_id: str, date: str):
    """EC2接続のデバッグ情報を取得"""
    debug_info = {
        "ec2_base_url": os.getenv("EC2_BASE_URL"),
        "prompt_url": f"{EC2_BASE_URL}/status/{user_id}/{date}/prompt/emotion-timeline_gpt_prompt.json",
        "upload_url": f"{EC2_BASE_URL}/upload-analysis",
        "local_analysis_dir": f"/Users/kaya.matsumoto/data/data_accounts/{user_id}/{date}/analysis"
    }
    
    # 接続テスト
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(debug_info["prompt_url"]) as response:
                debug_info["prompt_fetch_status"] = response.status
        except Exception as e:
            debug_info["prompt_fetch_error"] = str(e)
    
    return debug_info
```

## 🎯 開発の進め方

1. **Phase 1**: ローカル版の動作確認
2. **Phase 2**: EC2連携機能の追加（プロンプト取得）
3. **Phase 3**: EC2アップロード機能の実装
4. **Phase 4**: エラーハンドリングとデバッグ機能
5. **Phase 5**: パフォーマンス最適化

## 📝 チェックリスト

- [ ] 必要なライブラリをすべて`requirements.txt`に追加
- [ ] ディレクトリ作成処理を実装
- [ ] 非同期処理でEC2通信を実装
- [ ] ChatGPT APIのエラーハンドリング
- [ ] ローカル保存 → EC2アップロードの流れ
- [ ] 環境変数の設定
- [ ] デバッグエンドポイントの実装
- [ ] レート制限対応
- [ ] JSON解析の安全な実装

このガイドに従うことで、プロンプト生成APIで遭遇した問題の大部分を事前に回避できます。 