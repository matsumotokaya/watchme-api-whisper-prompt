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
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import jpholiday
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
    process_and_save_to_dashboard,
    get_weekday_info,
    get_season,
    generate_age_context
)
from timeblock_endpoint_v2 import process_timeblock_v3

def get_holiday_context(date: str) -> Dict[str, Any]:
    """
    指定日の祝日・連休情報を取得
    
    Args:
        date: 日付 (YYYY-MM-DD形式)
    
    Returns:
        祝日情報と連休コンテキストを含む辞書
    """
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        
        # 祝日判定
        holiday_name = jpholiday.is_holiday_name(date_obj)
        is_holiday = holiday_name is not None
        
        # 前後の日付を確認して連休判定
        day_before = date_obj - timedelta(days=1)
        day_after = date_obj + timedelta(days=1)
        
        holiday_before = jpholiday.is_holiday_name(day_before)
        holiday_after = jpholiday.is_holiday_name(day_after)
        is_weekend_before = day_before.weekday() >= 5
        is_weekend_after = day_after.weekday() >= 5
        is_weekend_current = date_obj.weekday() >= 5
        
        # 連休のコンテキスト生成
        consecutive_context = ""
        if (holiday_before or is_weekend_before) and (holiday_after or is_weekend_after):
            consecutive_context = "3連休の中日"
        elif holiday_after or is_weekend_after:
            consecutive_context = "連休初日"
        elif holiday_before or is_weekend_before:
            consecutive_context = "連休最終日"
        elif is_holiday:
            consecutive_context = "祝日"
        elif is_weekend_current:
            consecutive_context = "週末"
        
        return {
            "is_holiday": is_holiday,
            "holiday_name": holiday_name,
            "consecutive_context": consecutive_context,
            "is_weekend": is_weekend_current
        }
    except Exception as e:
        print(f"祝日情報の取得に失敗: {e}")
        return {
            "is_holiday": False,
            "holiday_name": None,
            "consecutive_context": "",
            "is_weekend": False
        }

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
        
        # 処理実行（改善版V3を使用）
        result = await process_timeblock_v3(supabase, device_id, date, time_block)
        
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
        
        # 観測対象者情報を取得（devicesテーブルとsubjectsテーブルを結合）
        subject_info = None
        try:
            # devicesテーブルからsubject_idを取得
            device_response = supabase.table("devices").select("subject_id").eq(
                "device_id", device_id
            ).single().execute()
            
            if device_response.data and device_response.data.get("subject_id"):
                subject_id = device_response.data["subject_id"]
                # subjectsテーブルから情報を取得
                subject_response = supabase.table("subjects").select("*").eq(
                    "subject_id", subject_id
                ).single().execute()
                
                if subject_response.data:
                    subject_info = subject_response.data
        except Exception as e:
            # エラーが発生しても処理を継続（subject_info = Noneのまま）
            print(f"観測対象者情報の取得に失敗しました（処理は継続）: {e}")
        
        # 統合プロンプトの生成（累積型、subject_info追加）
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
            last_time_block=last_time_block,
            subject_info=subject_info
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


def detect_burst_events(timeline: List[Dict], threshold: int = 30) -> List[Dict]:
    """
    タイムラインから感情の大きな変化点（バーストイベント）を検出
    
    Args:
        timeline: タイムブロックごとのデータリスト
        threshold: 変化を検出する閾値（デフォルト30ポイント）
    
    Returns:
        List[Dict]: 検出された変化点のリスト
    """
    burst_events = []
    
    for i in range(1, len(timeline)):
        prev_score = timeline[i-1].get('vibe_score')
        curr_score = timeline[i].get('vibe_score')
        
        if prev_score is not None and curr_score is not None:
            change = curr_score - prev_score
            
            # 大きな変化を検出
            if abs(change) >= threshold:
                time_block = timeline[i]['time_block']
                time_str = time_block.replace('-', ':')
                
                burst_events.append({
                    'time': time_str,
                    'from_score': prev_score,
                    'to_score': curr_score,
                    'change': change,
                    'summary': timeline[i].get('summary', '')
                })
    
    return burst_events


def generate_daily_summary_prompt(device_id: str, date: str, timeline: List[Dict], statistics: Dict, last_time_block: str, subject_info: Optional[Dict] = None) -> str:
    """
    改善版：コンテキストを活用し、実データから得られる価値ある情報に集中
    バーストイベント検出機能を追加
    
    Args:
        device_id: デバイスID
        date: 日付
        timeline: タイムブロックごとのデータリスト（summaryとvibe_scoreのみ）
        statistics: 統計情報
        last_time_block: 最後に処理したタイムブロック
        subject_info: 観測対象者情報（オプション）
        
    Returns:
        str: ChatGPT用の累積評価プロンプト（バーストイベント検出を含む）
    """
    # 時間・曜日・季節のコンテキスト取得
    hour = int(last_time_block.split('-')[0])
    minute = int(last_time_block.split('-')[1])
    
    # 曜日情報と季節を取得
    weekday_info = get_weekday_info(date)
    season = get_season(int(date.split('-')[1]))
    
    # 祝日・連休情報を取得
    holiday_info = get_holiday_context(date)
    
    # 日付コンテキストの生成（祝日を明示的に表現）
    if holiday_info['is_holiday']:
        day_context = f"祝日（{holiday_info['holiday_name']}）"
        if holiday_info['consecutive_context']:
            day_context += f"・{holiday_info['consecutive_context']}"
    elif holiday_info['is_weekend']:
        day_context = weekday_info['day_type']
        if holiday_info['consecutive_context']:
            day_context += f"（{holiday_info['consecutive_context']}）"
    else:
        day_context = weekday_info['day_type']
    
    # 観測対象者の詳細情報を構成
    if subject_info:
        age = subject_info.get('age', '不明')
        gender = subject_info.get('gender', '不明')
        notes = subject_info.get('notes', '')
        subject_description = f"{age}歳の{gender}"
        if notes:
            subject_description += f"（{notes}）"
    else:
        subject_description = "観測対象者情報なし"
    
    # 時間帯の判定
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
    
    # 意味のあるタイムラインテキストの生成（自明な内容を除外）
    timeline_texts = []
    trivial_patterns = ["静か", "無言", "発話なし", "データなし", "睡眠", "就寝", "起床前", "活動なし"]
    
    for entry in timeline:
        time = entry["time_block"].replace("-", ":")
        summary = entry.get("summary", "").strip()
        score = entry.get("vibe_score")
        
        # summaryに実質的な内容がある場合のみ追加
        if summary and not any(pattern in summary for pattern in trivial_patterns):
            score_str = f"+{score}" if score and score > 0 else str(score) if score else "0"
            timeline_texts.append(f"[{time}] {score_str:>4} | {summary}")
    
    timeline_text = "\n".join(timeline_texts) if timeline_texts else "有意なデータが記録されていません。"
    
    # バーストイベントの検出
    burst_events = detect_burst_events(timeline)
    burst_events_text = ""
    if burst_events:
        burst_events_text = "\n### 検出された感情の変化点（参考情報）\n"
        for event in burst_events[:5]:  # 最大5件まで表示
            burst_events_text += f"- {event['time']}: スコアが{event['from_score']}から{event['to_score']}へ変化（変化量: {event['change']:+d}）\n"
            if event['summary']:
                burst_events_text += f"  状況: {event['summary'][:50]}\n"
    
    # 終了時刻の算出
    end_minute = minute + 30
    end_hour = hour
    if end_minute >= 60:
        end_hour += 1
        end_minute = 0
    end_time = f"{end_hour:02d}:{end_minute:02d}"
    
    # ==================== 改善版プロンプト：1日全体の総合評価を促す ====================
    prompt = f"""## 1日全体の総合分析依頼
    
### 分析対象
観測対象者: {subject_description}
日付: {date}（{weekday_info['weekday']}、{day_context}）
季節: {season}、地域: 日本
分析範囲: **1日全体（00:00〜{hour:02d}:{minute:02d}）の記録**

{'【注意】本日は祝日のため、学校・幼稚園等の教育機関は休業です。観測場所は自宅または外出先と推測してください。' if holiday_info['is_holiday'] else ''}

録音される音声には本人だけでなく、周囲の人物（家族、友人、テレビ等）の声も含まれます。
観測対象者のプロファイルと発話内容に乖離がある場合は、周囲の人物の発話である可能性を考慮してください。
（例：年齢や発達段階に不相応な専門的内容は周囲の大人の会話、観測対象者の属性と異なる声質は他者の発話など）

### 1日の活動記録（{statistics.get('total_blocks', 0)}ブロック記録）
{timeline_text}
{burst_events_text}

### 重要：1日全体を総合的に評価してください
これは{hour:02d}:{minute:02d}時点での**1日全体のラップアップ**です。
朝から現在までの全タイムブロックのデータを俯瞰し、1日の流れと変化を総合的に評価してください。
特定の時間帯だけでなく、1日を通しての活動パターン、感情の推移、特徴的な出来事を含めてください。

### 出力形式
以下のJSON形式で出力してください。

```json
{{
  "current_time": "{hour:02d}:{minute:02d}",
  "time_context": "{time_context}",
  "cumulative_evaluation": "【最初の2文：1日のラップアップ】朝から{hour:02d}:{minute:02d}までの観測対象者の1日を総括。主要な活動、感情の流れ、特徴的な出来事を時系列で要約。【最後の1文：インサイト】この日の観測データから読み取れる、観測対象者の心理状態、行動パターン、または環境との相互作用に関する洞察。",
  "mood_trajectory": "positive_trend/negative_trend/stable/fluctuating",
  "current_state_score": -100から+100の整数（1日全体の総合スコア）,
  "burst_events": [
    {{
      "time": "HH:MM",
      "event": "感情変化の要因となった出来事や状況の説明（日本語で簡潔に）",
      "score_change": 変化量（-100〜+100の整数）,
      "from_score": 変化前のスコア（-100〜+100の整数）,
      "to_score": 変化後のスコア（-100〜+100の整数）
    }}
  ]
}}
```

### cumulative_evaluationの記述ガイドライン
1. **最初の2文（ラップアップ）**：
   - 1文目：朝〜昼の主要な活動と感情状態
   - 2文目：午後〜現在までの活動と感情の変化
   
2. **最後の1文（インサイト）**：
   - 1日のデータから見える観測対象者の特徴、パターン、または注目すべき変化についての洞察
   - 例：「終日を通して○○の傾向が見られ、特に△△の時間帯に□□という特徴的な反応を示している」

### 分析の視点
- 1日の時間経過に沿った活動と感情の変化を追跡
- 朝・昼・午後・夕方の各時間帯の特徴を統合
- 観測対象者の年齢・特性を考慮した自然な解釈
- データから読み取れる行動パターンや心理的傾向の発見

### burst_events（バーストイベント）の記述ガイドライン
感情が大きく変化した時点を特定し、以下の基準で記録してください：
1. **検出基準**：
   - 前後30分でスコアが30ポイント以上変化した時点
   - ポジティブ⇔ネガティブの転換点
   - 特定の出来事により感情が急変した瞬間

2. **eventの記述**：
   - その時間帯のsummaryから推測される具体的な出来事
   - 観測対象者の年齢・特性に応じた自然な解釈
   - 例: "朝の活動開始で気分が向上"、"昼食後の満足感"、"夕方の疲れによる気分低下"

3. **最大3〜5件程度**：
   - 1日で最も顕著な変化点のみを抽出
   - 些細な変動は除外し、意味のある変化に焦点"""
    
    return prompt


if __name__ == "__main__":
    # アプリケーションの起動
    uvicorn.run(app, host="0.0.0.0", port=8009)