#!/usr/bin/env python3
"""
Vibe Aggregator(Prompt Generator) API | 心理グラフ生成用API
https://api.hey-watch.me/vibe-aggregator
1日分（48個）のトランスクリプションを統合し、ChatGPT分析に適したプロンプトを生成するFastAPIアプリケーション
Supabase対応版: vibe_whisperテーブルから読み込み、vibe_whisper_promptテーブルに保存
"""

import os
import json
import uvicorn
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# .envファイルの読み込み
load_dotenv()

from supabase import create_client, Client

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="Mood Chart Prompt Generator API",
    description="1日分のトランスクリプションを統合し、ChatGPT分析用プロンプトを生成 (Supabase対応版)",
    version="2.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限してください
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabaseクライアントの遅延初期化
supabase_client = None

def get_supabase_client():
    """Supabaseクライアントを遅延初期化して取得"""
    global supabase_client
    if supabase_client is None:
        try:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
            
            supabase_client = create_client(url, key)
            print(f"✅ Supabase client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Supabase client: {e}")
            raise
    return supabase_client

# レスポンスモデル
class PromptResponse(BaseModel):
    status: str
    message: Optional[str] = None
    output_path: Optional[str] = None

def generate_chatgpt_prompt(device_id: str, date: str, texts: List[str]) -> str:
    """
    ChatGPT分析用のプロンプトを生成
    
    Args:
        device_id: デバイスID
        date: 日付（YYYY-MM-DD形式）
        texts: 時間帯ごとのテキストリスト
        
    Returns:
        str: ChatGPT用プロンプト
    """
    # テキストが空の場合の処理
    if not texts:
        timeline_text = "本日は記録されたテキストがありませんでした。"
    else:
        timeline_text = "\n".join(texts)
    
    prompt = f"""📝 依頼概要
発話ログを元に1日分の心理状態を分析し、心理グラフ用のJSONデータを生成してください。

🚨 重要：JSON品質要件
- 欠損データは必ず null で表現してください（NaN、undefined、Infinityは禁止）
- 出力は有効なJSON形式でなければなりません
- "測定していない(null)" vs "音声はあったが感情ニュートラル(0)" を区別してください

✅ 出力形式・ルール
以下の形式・ルールに厳密に従ってJSONを生成してください。

**完全な出力例（必ずこの形式で全項目を含めること）:**
```json
{{
  "timePoints": ["00:00", "00:30", "01:00", "01:30", "02:00", "02:30", "03:00", "03:30", "04:00", "04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00", "22:30", "23:00", "23:30"],
  "emotionScores": [null, null, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 20, 25, 30, 75, 80, 40, 35, 30, 25, 20, 15, 10, 5, 0, -50, -72, -5, 0, 5, 10, 15, 20, 25, 88, 35, 25, 20, 15, 10, 5, 0, null, 0],
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
| 測定不能な欠損 | その時間帯のログが完全に欠損している（処理失敗やデータ未取得）場合は null をスコアとして記入してください。**欠損データのスコアは0ではありません** |
| averageScore | nullは計算対象から除外し、全体の平均スコアを小数1桁で記入してください。全スロットがnullの場合は0.0で出力してください。 |
| positiveHours / negativeHours / neutralHours | それぞれスコア > 0、< 0、= 0 の時間帯の合計時間（単位：0.5時間）を算出してください。nullは無視して構いません。 |
| insights | その日全体を見たときの感情的・心理的な傾向を自然文で3件程度記述してください。 |
| emotionChanges | 特に感情が大きく変化した時間帯について、時刻＋簡単な出来事＋そのときのスコアを記載してください。最大3件程度。 |
| date | "{date}" を文字列で記入してください。 |
| **出力形式** | **上記の完全な出力例の形式で、全項目を含むJSON形式のみを返してください。解説や補足は一切不要です。** |
| **JSON品質要件** | **必ず有効なJSON形式で出力してください。NaNやInfinityは絶対に使用せず、欠損値は必ずnullで表現してください。** |

📊 分析対象の発話ログ（{date}）:
{timeline_text}"""
    
    return prompt

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/generate-mood-prompt-supabase", response_model=PromptResponse)
async def generate_mood_prompt_supabase(
    device_id: str = Query(..., description="デバイスID"),
    date: str = Query(..., description="日付（YYYY-MM-DD形式）")
):
    """
    Supabase統合版：vibe_whisperテーブルから指定されたデバイスと日付のトランスクリプションを取得し、
    ChatGPT分析用プロンプトを生成してvibe_whisper_promptテーブルに保存
    
    処理フロー:
    1. vibe_whisperテーブルから指定device_id、dateのレコードを取得
    2. transcriptionフィールドからテキストを抽出・統合
    3. ChatGPT用プロンプトを生成
    4. vibe_whisper_promptテーブルにUPSERT（既存レコードは更新）
    
    入力テーブル: vibe_whisper
    - device_id: デバイス識別子
    - date: 日付（YYYY-MM-DD）
    - time_block: 時間帯（例: "00-00", "00-30"）
    - transcription: 音声転写テキスト
    
    出力テーブル: vibe_whisper_prompt
    - device_id: デバイス識別子
    - date: 日付（YYYY-MM-DD）
    - prompt: 生成されたChatGPT用プロンプト
    - processed_files: 処理されたレコード数
    - missing_files: 欠損している時間帯のリスト
    - generated_at: 生成日時
    """
    print(f"🌟 Supabaseエンドポイントが呼ばれました: device_id={device_id}, date={date}")
    
    try:
        # 日付形式の検証
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="無効な日付形式です。YYYY-MM-DD形式で入力してください。")
        
        # Supabaseクライアントの取得
        try:
            client = get_supabase_client()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Supabaseクライアントの初期化に失敗しました: {str(e)}")
        
        # vibe_whisperテーブルからデータを取得
        texts = []
        processed_files = []
        missing_files = []
        
        # 時間帯リスト（00-00から23-30まで）
        time_blocks = []
        for hour in range(24):
            for minute in ["00", "30"]:
                time_blocks.append(f"{hour:02d}-{minute}")
        
        # 各時間帯のデータを取得
        for time_block in time_blocks:
            try:
                # Supabaseから該当レコードを取得
                response = client.table('vibe_whisper').select('transcription').eq('device_id', device_id).eq('date', date).eq('time_block', time_block).execute()
                
                if response.data and len(response.data) > 0:
                    transcription = response.data[0].get('transcription', '').strip()
                    if transcription:
                        texts.append(f"[{time_block}] {transcription}")
                        processed_files.append(time_block)
                    else:
                        missing_files.append(f"{time_block} (テキストなし)")
                else:
                    missing_files.append(time_block)
                    
            except Exception as e:
                print(f"❌ 時間帯 {time_block} の取得エラー: {e}")
                missing_files.append(f"{time_block} (取得エラー)")
        
        # デバッグ情報
        print(f"✅ 処理済み: {len(processed_files)}個の時間帯")
        print(f"❌ 欠損: {len(missing_files)}個の時間帯")
        if missing_files[:5]:  # 最初の5個だけ表示
            print(f"   欠損時間帯例: {missing_files[:5]}...")
        
        # ChatGPT用プロンプトの生成
        prompt = generate_chatgpt_prompt(device_id, date, texts)
        
        # vibe_whisper_promptテーブルに保存（UPSERT）
        prompt_data = {
            'device_id': device_id,
            'date': date,
            'prompt': prompt,
            'processed_files': len(processed_files),
            'missing_files': missing_files,
            'generated_at': datetime.now().isoformat()
        }
        
        try:
            # 既存レコードを更新または新規作成
            response = client.table('vibe_whisper_prompt').upsert(prompt_data, on_conflict='device_id,date').execute()
            
            print(f"✅ vibe_whisper_promptテーブルに保存完了")
            
            return PromptResponse(
                status="success",
                message=f"プロンプトが正常に生成され、データベースに保存されました。処理済み: {len(processed_files)}個、欠損: {len(missing_files)}個"
            )
            
        except Exception as e:
            print(f"❌ データベース保存エラー: {e}")
            raise HTTPException(status_code=500, detail=f"データベース保存エラー: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        raise HTTPException(status_code=500, detail=f"内部サーバーエラー: {str(e)}")

if __name__ == "__main__":
    # アプリケーションの起動
    uvicorn.run(app, host="0.0.0.0", port=8009)