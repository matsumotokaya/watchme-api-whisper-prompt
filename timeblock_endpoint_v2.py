"""
Time Block Processing Endpoint V2
==================================
改善版：AIの常識的判断を活用し、シンプルで効果的なプロンプト生成
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import traceback


def get_season(month: int) -> str:
    """月から季節を判定（日本の季節）"""
    if month in [3, 4, 5]:
        return "春"
    elif month in [6, 7, 8]:
        return "夏"
    elif month in [9, 10, 11]:
        return "秋"
    else:
        return "冬"


def get_weekday_info(date_str: str) -> Dict[str, Any]:
    """日付文字列から曜日情報を取得"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        
        # 曜日名（日本語）
        weekdays_ja = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
        weekday_ja = weekdays_ja[date_obj.weekday()]
        
        # 週末判定
        is_weekend = date_obj.weekday() >= 5  # 土曜日(5)または日曜日(6)
        
        return {
            "weekday": weekday_ja,
            "is_weekend": is_weekend,
            "day_type": "週末" if is_weekend else "平日"
        }
    except (ValueError, TypeError):
        return {
            "weekday": "不明",
            "is_weekend": None,
            "day_type": "不明"
        }


def get_holiday_context(date: str) -> Dict[str, Any]:
    """
    祝日情報を取得（jpholidayが利用可能な場合）
    """
    try:
        import jpholiday
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        holiday_name = jpholiday.is_holiday_name(date_obj)
        is_holiday = holiday_name is not None
        
        return {
            "is_holiday": is_holiday,
            "holiday_name": holiday_name,
            "is_weekend": date_obj.weekday() >= 5
        }
    except:
        # jpholidayが利用できない場合
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        return {
            "is_holiday": False,
            "holiday_name": None,
            "is_weekend": date_obj.weekday() >= 5
        }


def generate_timeblock_prompt_v2(transcription: Optional[str], sed_data: Optional[list], time_block: str,
                                 date: str = None, subject_info: Optional[Dict] = None,
                                 opensmile_data: Optional[list] = None) -> str:
    """
    改善版プロンプト生成：AIの常識的判断を活用
    """
    
    # 時間情報の解析
    hour = int(time_block.split('-')[0])
    minute = int(time_block.split('-')[1])
    
    # 観測対象者情報
    age = subject_info.get('age', '不明') if subject_info else '不明'
    gender = subject_info.get('gender', '不明') if subject_info else '不明'
    
    # 曜日・祝日情報
    weekday_info = get_weekday_info(date) if date else {"weekday": "不明", "day_type": "不明"}
    holiday_info = get_holiday_context(date) if date else {"is_holiday": False, "holiday_name": None}
    
    # 日付コンテキスト
    if holiday_info['is_holiday']:
        day_context = f"祝日（{holiday_info['holiday_name']}）"
    elif holiday_info['is_weekend']:
        day_context = "週末"
    else:
        day_context = "平日"
    
    # 環境音の要約
    sound_events = ""
    if sed_data and len(sed_data) > 0:
        # 主要な音響イベントを抽出
        events = []
        for event in sed_data[:10]:  # 上位10個まで
            label = event.get('label', '')
            prob = event.get('prob', 0)
            if prob > 0.3:  # 確率が30%以上のもの
                events.append(label)
        
        if events:
            sound_events = f"検出された音: {', '.join(events[:5])}"  # 最大5個まで表示
        else:
            sound_events = "特徴的な環境音なし"
    else:
        sound_events = "環境音データなし"
    
    # 音声特徴の要約
    acoustic_context = ""
    if opensmile_data and len(opensmile_data) > 0:
        loudness_values = [item.get('features', {}).get('Loudness_sma3', 0) for item in opensmile_data]
        if loudness_values:
            avg_loudness = sum(loudness_values) / len(loudness_values)
            if avg_loudness > -20:
                acoustic_context = "音量: 大きめ（活発な活動の可能性）"
            elif avg_loudness < -40:
                acoustic_context = "音量: 小さめ（静かな環境）"
            else:
                acoustic_context = "音量: 普通レベル"
    
    # プロンプト生成
    prompt = f"""## 音声サンプル分析（30分中の1分間録音）

これは30分ブロックのうち約1分間をサンプリング録音したデータです。
観測対象者の年齢と時間帯を考慮し、録音データから状況を分析してください。

### 観測情報
観測対象者: {age}歳 {gender}
時刻: {date} {hour:02d}:{minute:02d}〜{hour:02d}:{minute+30 if minute+30 < 60 else minute-30:02d}の30分ブロック
曜日: {weekday_info['weekday']}（{day_context}）
季節: {get_season(int(date.split('-')[1])) if date else '不明'}

{'【注意】本日は祝日のため、教育機関は休業です。' if holiday_info['is_holiday'] else ''}

### 録音データ

#### 発話内容
{f'「{transcription}」' if transcription and transcription.strip() else 'この1分間の録音では発話は記録されませんでした'}

#### 環境音
{sound_events}

{f'#### 音声特徴' + chr(10) + acoustic_context if acoustic_context else ''}

### 分析依頼

以下の4つのフィールドを持つJSONで回答してください（全フィールド必須）:

```json
{{
  "time_block": "{time_block}",
  "summary": "【1文目】録音時点での観測対象者の具体的な行動や状況。【2文目】そこから推測される心理状態や感情。",
  "behavior": "推測される主な行動を最大3つ、カンマ区切りで記載（例: 食事,会話,テレビ視聴）",
  "vibe_score": -100〜+100の整数値
}}
```

**重要な注意事項:**
- これは30分間のうち1分間のサンプルです。「30分間ずっと〜」という表現は避けてください
- summaryには観測対象者の名前、年齢、性別、時刻は記載しないでください（既知情報のため）
- 発話がなくても「沈黙」と決めつけず、「この録音では発話なし」と事実を述べてください

**vibe_scoreの基本方針:**
- 発話がない場合は基本的に0点付近（-10〜+10）としてください
- ただし、音楽鑑賞、テレビ視聴、歌唱など、環境音から活動が推測される場合は状況に応じて加減点してください
- スコア分布の目安：
  * 非常にポジティブ（活発・楽しい）: 60〜100
  * ポジティブ（穏やか・安定）: 20〜60
  * ニュートラル（特に感情なし）: -20〜20
  * ネガティブ（疲れ・不満）: -60〜-20
  * 非常にネガティブ（泣き・怒り）: -100〜-60

**behaviorの記述例:**
- 朝の場合: "朝食,準備,会話"
- 昼の場合: "遊び,発話,移動"
- 夜の場合: "入浴,休息,テレビ視聴"
- 発話なしの場合も時間帯から推測: "休息,静観,思考"
"""
    
    return prompt


# 既存の関数をインポート可能にするため
from timeblock_endpoint import (
    get_whisper_data,
    get_sed_data,
    get_opensmile_data,
    get_subject_info,
    save_prompt_to_dashboard,
    update_whisper_status,
    update_yamnet_status,
    update_opensmile_status
)


async def process_timeblock_v3(supabase_client, device_id: str, date: str, time_block: str) -> Dict[str, Any]:
    """
    改善版処理: V2プロンプトを使用
    """
    # データ取得
    transcription = await get_whisper_data(supabase_client, device_id, date, time_block)
    sed_data = await get_sed_data(supabase_client, device_id, date, time_block)
    opensmile_data = await get_opensmile_data(supabase_client, device_id, date, time_block)
    subject_info = await get_subject_info(supabase_client, device_id)
    
    # データ存在フラグ
    has_whisper = transcription is not None
    has_yamnet = sed_data is not None and len(sed_data) > 0
    has_opensmile = opensmile_data is not None and len(opensmile_data) > 0
    
    # 改善版プロンプト生成
    prompt = generate_timeblock_prompt_v2(transcription, sed_data, time_block, date, subject_info, opensmile_data)
    
    # デバッグ出力
    print(f"📊 Data retrieved for {time_block}:")
    print(f"  - Transcription: {'Yes' if has_whisper else 'No'} ({len(transcription) if transcription else 0} chars)")
    print(f"  - SED Events: {'Yes' if has_yamnet else 'No'} ({len(sed_data) if sed_data else 0} events)")
    print(f"  - OpenSMILE Timeline: {'Yes' if has_opensmile else 'No'} ({len(opensmile_data) if opensmile_data else 0} seconds)")
    print(f"  - Subject Info: {'Yes' if subject_info else 'No'}")
    
    # プロンプト保存
    dashboard_saved = await save_prompt_to_dashboard(supabase_client, device_id, date, time_block, prompt)
    
    # ステータス更新
    status_updates = {
        "whisper_updated": False,
        "yamnet_updated": False,
        "opensmile_updated": False
    }
    
    if dashboard_saved:
        print(f"\n📝 Updating status for used data sources...")
        
        if has_whisper:
            status_updates["whisper_updated"] = await update_whisper_status(
                supabase_client, device_id, date, time_block
            )
        
        if has_yamnet:
            status_updates["yamnet_updated"] = await update_yamnet_status(
                supabase_client, device_id, date, time_block
            )
        
        if has_opensmile:
            status_updates["opensmile_updated"] = await update_opensmile_status(
                supabase_client, device_id, date, time_block
            )
    
    return {
        "status": "success",
        "version": "v3-improved",
        "device_id": device_id,
        "date": date,
        "time_block": time_block,
        "prompt": prompt,
        "prompt_length": len(prompt),
        "has_transcription": has_whisper and len(transcription.strip()) > 0 if transcription else False,
        "has_sed_data": has_yamnet,
        "has_opensmile_data": has_opensmile,
        "sed_events_count": len(sed_data) if sed_data else 0,
        "opensmile_seconds": len(opensmile_data) if opensmile_data else 0,
        "dashboard_saved": dashboard_saved,
        "status_updates": status_updates
    }