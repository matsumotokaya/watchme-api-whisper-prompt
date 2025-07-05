#!/usr/bin/env python3
"""
⚠️ 【廃止予定】このファイルは古いバージョンです ⚠️

このファイル（app.py）は開発初期の古いバージョンで、以下の機能が不足しています：
- EC2サーバーとのHTTP通信機能
- 環境変数による設定制御
- 適切なエラーハンドリング（ログツール対応）
- ファイルアップロード機能

🔥 正式版は main.py を使用してください 🔥

main.py の機能：
- ✅ EC2サーバーとのHTTP通信
- ✅ 環境変数 EC2_BASE_URL による制御
- ✅ ローカル/EC2両対応
- ✅ ログツールとして適切なエラーハンドリング
- ✅ ファイルアップロード機能

起動コマンド:
export EC2_BASE_URL="https://api.hey-watch.me" && uvicorn main:app --host 0.0.0.0 --port 8009 --reload

このファイルは削除予定です。
"""

# 以下は古いコードです - 使用しないでください

import os
import json
import uvicorn
import aiohttp
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

import inspect, pathlib, logging


# FastAPIアプリケーションの初期化
app = FastAPI(
    title="Mood Chart Prompt Generator API",
    description="1日分のトランスクリプションファイルを統合し、ChatGPT分析用プロンプトを生成",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_log():
    here = pathlib.Path(inspect.getfile(startup_log)).resolve()
    logging.basicConfig(level=logging.INFO)
    logging.info("⭐️ MoodPrompt API startup")
    logging.info(f"📄 imported: {here}")
    logging.info(f"🔧 EC2_BASE_URL = {os.getenv('EC2_BASE_URL')}")

class PromptResponse(BaseModel):
    status: str
    output_path: str

class ErrorResponse(BaseModel):
    detail: str

def extract_text_from_json(data: Dict[str, Any]) -> str:
    """
    JSONデータからテキストを抽出する関数
    複数のフィールド名（text, transcript, content, transcription）に対応
    """
    text_fields = ["text", "transcript", "content", "transcription"]
    
    def recursive_extract(obj):
        if isinstance(obj, dict):
            # 直接テキストフィールドを探す
            for field in text_fields:
                if field in obj and isinstance(obj[field], str) and obj[field].strip():
                    return obj[field].strip()
            
            # 再帰的に探索
            for value in obj.values():
                result = recursive_extract(value)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = recursive_extract(item)
                if result:
                    return result
        elif isinstance(obj, str) and obj.strip():
            return obj.strip()
        
        return None
    
    return recursive_extract(data) or ""

def load_transcription_files_ec2(user_id: str, date: str) -> tuple[List[str], List[str], List[str]]:
    """
    EC2用：指定されたユーザーと日付のトランスクリプションファイルを読み込む
    パス: /data/data_accounts/{user_id}/{date}/transcriptions/
    
    Returns:
        tuple: (texts, processed_files, missing_files)
    """
    base_dir = Path(f"/data/data_accounts/{user_id}/{date}/transcriptions")
    
    if not base_dir.exists():
        raise HTTPException(status_code=404, detail=f"ディレクトリが見つかりません: {base_dir}")
    
    texts = []
    processed_files = []
    missing_files = []
    
    # 48個のファイル（00-00.json ～ 23-30.json）を処理
    for hour in range(24):
        for minute in [0, 30]:
            filename = f"{hour:02d}-{minute:02d}.json"
            file_path = base_dir / filename
            
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    text = extract_text_from_json(data)
                    if text:
                        texts.append(f"[{hour:02d}:{minute:02d}] {text}")
                        processed_files.append(filename)
                    else:
                        missing_files.append(f"{filename} (テキストなし)")
                
                except (json.JSONDecodeError, Exception) as e:
                    missing_files.append(f"{filename} (読み込みエラー: {str(e)})")
            else:
                missing_files.append(filename)
    
    return texts, processed_files, missing_files

def load_transcription_files(user_id: str, date: str) -> tuple[List[str], List[str], List[str]]:
    """
    指定されたユーザーと日付のトランスクリプションファイルを読み込む
    
    Returns:
        tuple: (texts, processed_files, missing_files)
    """
    base_dir = Path(f"/Users/kaya.matsumoto/data/data_accounts/{user_id}/{date}/transcriptions")
    
    if not base_dir.exists():
        raise HTTPException(status_code=404, detail=f"ディレクトリが見つかりません: {base_dir}")
    
    texts = []
    processed_files = []
    missing_files = []
    
    # 48個のファイル（00-00.json ～ 23-30.json）を処理
    for hour in range(24):
        for minute in [0, 30]:
            filename = f"{hour:02d}-{minute:02d}.json"
            file_path = base_dir / filename
            
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    text = extract_text_from_json(data)
                    if text:
                        texts.append(f"[{hour:02d}:{minute:02d}] {text}")
                        processed_files.append(filename)
                    else:
                        missing_files.append(f"{filename} (テキストなし)")
                
                except (json.JSONDecodeError, Exception) as e:
                    missing_files.append(f"{filename} (読み込みエラー: {str(e)})")
            else:
                missing_files.append(filename)
    
    return texts, processed_files, missing_files

def generate_chatgpt_prompt(user_id: str, date: str, texts: List[str]) -> str:
    """
    ChatGPT分析用のプロンプトを生成
    """
    prompt_header = f"""📝 依頼概要
発話ログを元に1日分の心理状態を分析し、心理グラフ用のJSONデータを生成してください。

🚨 重要：JSON品質要件
- 欠損データは必ず null で表現してください（NaN、undefined、Infinityは禁止）
- 出力は有効なJSON形式でなければなりません
- "測定していない" vs "音声はあったが感情ニュートラル(0)" を区別してください

✅ 出力形式・ルール
以下の形式・ルールに厳密に従ってJSONを生成してください。

**完全な出力例（必ずこの形式で全項目を含めること）:**
```json
{{
  "timePoints": ["00:00", "00:30", "01:00", "01:30", "02:00", "02:30", "03:00", "03:30", "04:00", "04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00", "22:30", "23:00", "23:30"],
  "emotionScores": [null, null, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 20, 25, 30, 75, 80, 40, 35, 30, 25, 20, 15, 10, 5, 0, -5, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 25, 20, 15, 10, 5, 0, null, 0],
  "averageScore": 15.2,
  "positiveHours": 18.0,
  "negativeHours": 2.0,
  "neutralHours": 28.0,
  "insights": [
    "午前中は発話がなく静かな状態が続いたが、9時台にポジティブな感情の高まりが見られた。",
    "午後は感情の変動が少なく、落ち着いた時間帯が多かった。",
    "全体として安定した心理状態が維持されていたと考えられる。"
  ],
  "emotionChanges": [
    {{ "time": "09:00", "event": "誕生日を祝うシーン", "score": 75 }},
    {{ "time": "15:00", "event": "感情が落ち着く", "score": 0 }}
  ],
  "date": "{date}"
}}
```

🔍 **必須遵守ルール**
| 要素 | 指示内容 |
|------|----------|
| **timePoints** | **必ず出力JSONに含める必須項目です。** "00:00"〜"23:30"の48個を順に全て列挙してください。 |
| **emotionScores** | **必ず48個の整数値で出力してください。** -100〜+100 の範囲で、小数は使用せず四捨五入して整数で返してください。 |
| 空の発話ログ | 明確に発話がない（ドット記号のみなど）の場合は 0 をスコアとして記入してください。 |
| 測定不能な欠損 | その時間帯のログが完全に欠損している（処理失敗やデータ未取得）場合は null をスコアとして記入してください。**NaNは使用禁止です。** |
| averageScore | nullは計算対象から除外し、全体の平均スコアを小数1桁で記入してください。全スロットがnullの場合は0.0で出力してください。 |
| positiveHours / negativeHours / neutralHours | それぞれスコア > 0、< 0、= 0 の時間帯の合計時間（単位：0.5時間）を算出してください。nullは無視して構いません。 |
| insights | その日全体を見たときの感情的・心理的な傾向を自然文で3件程度記述してください。 |
| emotionChanges | 特に感情が大きく変化した時間帯について、時刻＋簡単な出来事＋そのときのスコアを記載してください。最大3件程度。 |
| date | "{date}" を文字列で記入してください。 |
| **出力形式** | **上記の完全な出力例の形式で、全項目を含むJSON形式のみを返してください。解説や補足は一切不要です。** |
| **JSON品質要件** | **必ず有効なJSON形式で出力してください。NaNやInfinityは絶対に使用せず、欠損値は必ずnullで表現してください。** |

📊 分析対象の発話ログ（{date}）:
"""
    
    prompt_body = "\n".join(texts)
    
    return prompt_header + prompt_body

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/generate-mood-prompt", response_model=PromptResponse)
async def generate_mood_prompt(
    user_id: str = Query(..., description="ユーザーID"),
    date: str = Query(..., description="日付（YYYY-MM-DD形式）")
):
    """
    指定されたユーザーと日付のトランスクリプションファイルを統合し、
    ChatGPT分析用プロンプトを生成してJSONファイルに保存
    """
    try:
        # 日付形式の検証
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="無効な日付形式です。YYYY-MM-DD形式で入力してください。")
        
        # トランスクリプションファイルの読み込み
        texts, processed_files, missing_files = load_transcription_files(user_id, date)
        
        if not texts:
            raise HTTPException(status_code=404, detail="有効なトランスクリプションファイルが見つかりません。")
        
        # ChatGPT用プロンプトの生成
        prompt = generate_chatgpt_prompt(user_id, date, texts)
        
        # 出力ディレクトリの作成
        output_dir = Path(f"/Users/kaya.matsumoto/data/data_accounts/{user_id}/{date}/transcriptions")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 出力データの準備
        output_data = {
            "user_id": user_id,
            "date": date,
            "prompt": prompt,
            "processed_files": len(processed_files),
            "missing_files": missing_files,
            "generated_at": datetime.now().isoformat()
        }
        
        # JSONファイルの保存
        output_path = output_dir / "emotion-timeline_gpt_prompt.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            # 注意：ChatGPTからの応答を処理する際は、NaN/Infinityをnullに変換するサニタイズ処理が必要
            # json.dumps(obj, ensure_ascii=False, allow_nan=False) でNaN/Infinityを検出可能
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        return PromptResponse(
            status="success",
            output_path=str(output_path)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部サーバーエラー: {str(e)}")

@app.get("/generate-mood-prompt-ec2", response_model=PromptResponse)
async def generate_mood_prompt_ec2(
    user_id: str = Query(..., description="ユーザーID"),
    date: str = Query(..., description="日付（YYYY-MM-DD形式）")
):
    """
    EC2用エンドポイント：指定されたユーザーと日付のトランスクリプションファイルを統合し、
    ChatGPT分析用プロンプトを生成してJSONファイルに保存
    
    入力パス: /data/data_accounts/{user_id}/{date}/transcriptions/
    出力パス: /data/data_accounts/{user_id}/{date}/prompt/emotion-timeline_gpt_prompt.json
    """
    try:
        # 日付形式の検証
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="無効な日付形式です。YYYY-MM-DD形式で入力してください。")
        
        # トランスクリプションファイルの読み込み（EC2パス使用）
        texts, processed_files, missing_files = load_transcription_files_ec2(user_id, date)
        
        if not texts:
            raise HTTPException(status_code=404, detail="有効なトランスクリプションファイルが見つかりません。")
        
        # ChatGPT用プロンプトの生成
        prompt = generate_chatgpt_prompt(user_id, date, texts)
        
        # 出力ディレクトリの作成（EC2用パス）
        output_dir = Path(f"/data/data_accounts/{user_id}/{date}/prompt")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 出力データの準備
        output_data = {
            "user_id": user_id,
            "date": date,
            "prompt": prompt,
            "processed_files": len(processed_files),
            "missing_files": missing_files,
            "generated_at": datetime.now().isoformat()
        }
        
        # JSONファイルの保存
        output_path = output_dir / "emotion-timeline_gpt_prompt.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            # 注意：ChatGPTからの応答を処理する際は、NaN/Infinityをnullに変換するサニタイズ処理が必要
            # json.dumps(obj, ensure_ascii=False, allow_nan=False) でNaN/Infinityを検出可能
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        return PromptResponse(
            status="success",
            output_path=str(output_path)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部サーバーエラー: {str(e)}")

if __name__ == "__main__":
    print("🚀 Mood Chart Prompt Generator API を起動中...")
    print("📍 サーバー: http://localhost:8009")
    print("📚 ドキュメント: http://localhost:8009/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8009,
        reload=True,
        log_level="info"
    ) 