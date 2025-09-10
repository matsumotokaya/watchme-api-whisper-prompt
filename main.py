#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
| 発話なし | "(発話なし)"と記載されている時間帯は、録音は成功したが言語的な情報がなかった時間帯です。0 をスコアとして記入してください。 |
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
                        # 発話あり：テキストを分析
                        texts.append(f"[{time_block}] {transcription}")
                        processed_files.append(time_block)
                    else:
                        # 空文字列の場合：録音は成功したが発話なし（0点として処理）
                        texts.append(f"[{time_block}] (発話なし)")
                        processed_files.append(time_block)
                else:
                    # レコードが存在しない場合のみ欠損として処理（nullとして扱う）
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

# ===============================
# 新規: タイムブロック単位の処理エンドポイント
# ===============================
from timeblock_endpoint import (
    process_timeblock_v2,
    process_and_save_to_dashboard
)

@app.get("/generate-timeblock-prompt")
async def generate_timeblock_prompt(
    device_id: str = Query(..., description="デバイスID"),
    date: str = Query(..., description="日付 (YYYY-MM-DD)"),
    time_block: str = Query(..., description="タイムブロック (例: 14-30)")
):
    """
    30分単位でWhisper + SEDデータ + 観測対象者情報を使用してプロンプト生成
    """
    try:
        # Supabaseクライアント取得
        supabase = get_supabase_client()
        
        # 処理実行
        result = await process_timeblock_v2(supabase, device_id, date, time_block)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test-timeblock")
async def test_timeblock_processing():
    """
    テスト用エンドポイント: サンプルデータで動作確認
    """
    try:
        # テスト用の固定値
        test_device_id = "d067d407-cf73-4174-a9c1-d91fb60d64d0"
        test_date = "2025-08-31"
        test_time_block = "14-30"
        
        supabase = get_supabase_client()
        
        # V3（OpenSMILE統合版）をテスト
        result = await process_timeblock_v2(supabase, test_device_id, test_date, test_time_block)
        
        return {
            "message": "テスト完了（OpenSMILE統合版）",
            "result": result
        }
        
    except Exception as e:
        return {"error": str(e)}


@app.get("/generate-dashboard-summary")
async def generate_dashboard_summary(
    device_id: str = Query(..., description="デバイスID"),
    date: str = Query(..., description="日付 (YYYY-MM-DD)")
):
    """
    dashboardテーブルの1日分の分析結果を統合してdashboard_summaryテーブルに保存
    
    処理内容:
    1. dashboardテーブルから該当日のstatus='completed'のレコードを取得
    2. summaryとvibe_scoreから累積型プロンプトを生成
    3. vibe_scoreから48要素の配列を生成（グラフ描画用）
    4. プロンプトをdashboard_summaryテーブルのpromptカラムに保存
    """
    try:
        # 日付形式の検証
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="無効な日付形式です。YYYY-MM-DD形式で入力してください。"
            )
        
        # Supabaseクライアント取得
        supabase = get_supabase_client()
        
        # dashboardテーブルから該当日のcompletedレコードを取得（時系列順）
        dashboard_response = supabase.table("dashboard").select("*").eq(
            "device_id", device_id
        ).eq(
            "date", date
        ).eq(
            "status", "completed"
        ).order(
            "time_block", desc=False
        ).execute()
        
        if not dashboard_response.data:
            return {
                "status": "warning",
                "message": f"処理済みデータが見つかりません。device_id: {device_id}, date: {date}",
                "processed_count": 0
            }
        
        # データの整理と統合
        processed_blocks = dashboard_response.data
        processed_count = len(processed_blocks)
        
        # 最後のタイムブロックを取得
        last_time_block = processed_blocks[-1]["time_block"] if processed_blocks else None
        
        # ========== 処理B: vibe_scores配列の生成（新規追加） ==========
        # 48要素の配列を初期化（全てnull）
        vibe_scores_array = [None] * 48
        
        # 時間ブロックのマッピング辞書を作成
        time_block_to_index = {}
        for hour in range(24):
            for minute_idx, minute in enumerate(["00", "30"]):
                time_block = f"{hour:02d}-{minute}"
                index = hour * 2 + minute_idx
                time_block_to_index[time_block] = index
        
        # vibe_scoreデータを配列の適切な位置に配置
        vibe_score_sum = 0
        vibe_score_count = 0
        
        for block in processed_blocks:
            time_block = block.get("time_block")
            vibe_score = block.get("vibe_score")
            
            # 対応するインデックスにvibe_scoreを設定
            if time_block in time_block_to_index and vibe_score is not None:
                index = time_block_to_index[time_block]
                vibe_scores_array[index] = vibe_score
                vibe_score_sum += vibe_score
                vibe_score_count += 1
        
        # vibe_scoreの平均値を計算（nullを除外）
        average_vibe = vibe_score_sum / vibe_score_count if vibe_score_count > 0 else None
        
        # ========== シンプル化されたタイムライン生成処理 ==========
        # summaryとvibe_scoreのみを使用
        timeline = []
        total_vibe_score = 0
        valid_score_count = 0
        positive_blocks = 0
        negative_blocks = 0
        neutral_blocks = 0
        
        for block in processed_blocks:
            # summaryとvibe_scoreのみを取得（analysis_resultは使わない）
            summary = block.get("summary", "")
            vibe_score = block.get("vibe_score")
            
            # スコアの統計
            if vibe_score is not None:
                total_vibe_score += vibe_score
                valid_score_count += 1
                
                if vibe_score > 20:
                    positive_blocks += 1
                elif vibe_score < -20:
                    negative_blocks += 1
                else:
                    neutral_blocks += 1
            
            # シンプルなタイムラインエントリの作成（summaryとvibe_scoreのみ）
            timeline_entry = {
                "time_block": block["time_block"],
                "summary": summary,
                "vibe_score": vibe_score
            }
            
            timeline.append(timeline_entry)
        
        # 統計情報の計算（既存処理用）
        avg_vibe_score = total_vibe_score / valid_score_count if valid_score_count > 0 else None
        
        # 統合プロンプトの生成（累積型、last_time_blockパラメータを追加）
        daily_summary_prompt = generate_daily_summary_prompt(
            device_id=device_id,
            date=date,
            timeline=timeline,
            statistics={
                "avg_vibe_score": avg_vibe_score,
                "positive_blocks": positive_blocks,
                "negative_blocks": negative_blocks,
                "neutral_blocks": neutral_blocks,
                "total_blocks": processed_count
            },
            last_time_block=last_time_block
        )
        
        # dashboard_summaryテーブルにUPSERT
        upsert_data = {
            "device_id": device_id,
            "date": date,
            "prompt": daily_summary_prompt,  # dashboardのsummaryとvibe_scoreから生成したプロンプト
            "vibe_scores": vibe_scores_array,  # グラフ描画用（48要素）
            "average_vibe": average_vibe,
            "processed_count": processed_count,
            "last_time_block": last_time_block,
            "updated_at": datetime.now().isoformat()
        }
        
        # UPSERTの実行（既存データは上書き）
        summary_response = supabase.table("dashboard_summary").upsert(
            upsert_data,
            on_conflict="device_id,date"
        ).execute()
        
        return {
            "status": "success",
            "message": f"ダッシュボードサマリーを生成しました。処理済みブロック数: {processed_count}",
            "device_id": device_id,
            "date": date,
            "processed_count": processed_count,
            "last_time_block": last_time_block,
            "vibe_scores_count": vibe_score_count,  # 新規追加: 有効なスコア数
            "average_vibe": average_vibe,           # 新規追加: 平均値
            "statistics": {
                "avg_vibe_score": avg_vibe_score,
                "positive_blocks": positive_blocks,
                "negative_blocks": negative_blocks,
                "neutral_blocks": neutral_blocks,
                "valid_score_count": valid_score_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"エラー詳細: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")


def generate_daily_summary_prompt(device_id: str, date: str, timeline: List[Dict], statistics: Dict, last_time_block: str) -> str:
    """
    シンプル化された累積型プロンプト生成
    summaryとvibe_scoreのみを使用し、コンパクトに
    
    Args:
        device_id: デバイスID
        date: 日付
        timeline: タイムブロックごとのデータリスト（summaryとvibe_scoreのみ）
        statistics: 統計情報
        last_time_block: 最後に処理したタイムブロック
        
    Returns:
        str: ChatGPT用の累積評価プロンプト
    """
    # 時間帯の判定（timeblock_endpoint.py参考）
    hour = int(last_time_block.split('-')[0])
    minute = int(last_time_block.split('-')[1])
    
    time_context = ""
    if 5 <= hour < 9:
        time_context = "早朝"
    elif 9 <= hour < 12:
        time_context = "午前"
    elif 12 <= hour < 14:
        time_context = "昼"
    elif 14 <= hour < 17:
        time_context = "午後"
    elif 17 <= hour < 20:
        time_context = "夕方"
    elif 20 <= hour < 23:
        time_context = "夜"
    else:
        time_context = "深夜"
    
    # タイムラインテキストの生成（シンプル版）
    timeline_texts = []
    for entry in timeline:
        time = entry["time_block"].replace("-", ":")
        summary = entry.get("summary", "")
        score = entry.get("vibe_score")
        
        # データがある場合のみ追加
        if summary and summary.strip():
            # スコアを見やすく表示（正の値は+、負の値は-、nullは--）
            score_str = f"+{score}" if score and score > 0 else str(score) if score else "--"
            timeline_texts.append(f"[{time}] {score_str:>4} | {summary}")
    
    timeline_text = "\n".join(timeline_texts) if timeline_texts else "記録されたデータがありません。"
    
    # 終了時刻の算出
    end_minute = minute + 30
    end_hour = hour
    if end_minute >= 60:
        end_hour += 1
        end_minute = 0
    end_time = f"{end_hour:02d}:{end_minute:02d}"
    
    # ==================== timeblock_endpoint.pyスタイルのプロンプト ====================
    prompt = f"""📊 累積心理状態分析タスク

あなたは「時系列の要約データから心理状態の変化を分析することに特化した臨床心理士」です。
観測データは1日48回、30分ごとのブロックに区切られています。
現在時刻（{hour:02d}:{minute:02d}）までの要約とスコアを基に、その時点での総合的な心理状態を評価してください。

## ==================== 出力形式（必須） ====================
```json
{{
  "current_time": "{hour:02d}:{minute:02d}",
  "time_context": "{time_context}",
  "cumulative_evaluation": "この時点までの総合的な心理状態を2-3文で簡潔に記載。朝からの流れと現在の状態を含む。",
  "mood_trajectory": "positive_trend/negative_trend/stable/fluctuating",
  "current_state_score": 0
}}
```

## ==================== 厳格ルール ====================
- **JSONのみを返す**（説明や補足は一切不要）
- **cumulative_evaluationは必ず2-3文**で簡潔に記載
- **current_state_scoreは-100〜+100の整数値**
- この時点までのデータのみで評価（未来のデータは考慮しない）
- 観測対象者の年齢・性別は不明として、決めつけない

## ==================== 分析対象データ ====================

### メタ情報
- 日付: {date}
- 現在時刻: {hour:02d}:{minute:02d}（{time_context}）
- 分析範囲: 00:00〜{end_time}
- データ数: {statistics.get('total_blocks', 0)}ブロック

### 統計サマリー
- 平均スコア: {statistics.get('avg_vibe_score', 0):.1f}
- ポジティブ（>20）: {statistics.get('positive_blocks', 0)}回
- ネガティブ（<-20）: {statistics.get('negative_blocks', 0)}回
- ニュートラル（-20〜20）: {statistics.get('neutral_blocks', 0)}回

### 時系列サマリー（要約とスコアのみ）
{timeline_text}

## ==================== 分析の観点 ====================
1. **朝からの流れ**: 時間帯ごとの変化パターン
2. **現在の状態**: {hour:02d}:{minute:02d}時点での心理状態
3. **全体的な傾向**: スコアの推移から見る心理的軌跡

重要: データから直接観察できる事実を重視し、推測は最小限に留めてください。"""
    
    return prompt


if __name__ == "__main__":
    # アプリケーションの起動
    uvicorn.run(app, host="0.0.0.0", port=8009)