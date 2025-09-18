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
    改善版プロンプト生成：LLMの常識的判断を最大限活用
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
    
    # OpenSMILEデータの分析と時系列表示
    speech_analysis = ""
    if opensmile_data and len(opensmile_data) > 0:
        # Jitterから発話の有無を判定
        jitter_values = []
        loudness_values = []
        for item in opensmile_data:
            features = item.get('features', {})
            jitter_values.append(features.get('jitterLocal_sma3nz', 0))
            loudness_values.append(features.get('Loudness_sma3', 0))
        
        speaking_seconds = sum(1 for j in jitter_values if j > 0)
        total_seconds = len(jitter_values)
        speech_ratio = speaking_seconds / total_seconds if total_seconds > 0 else 0
        
        # 時系列の最初の20秒を表示
        timeline = ["時刻|音量|Jitter|状態"]
        timeline.append("---|---|---|---")
        for i in range(min(20, len(opensmile_data))):
            features = opensmile_data[i].get('features', {})
            loudness = features.get('Loudness_sma3', 0)
            jitter = features.get('jitterLocal_sma3nz', 0)
            state = "発話" if jitter > 0 else "無音"
            timeline.append(f"{i:02d}秒|{loudness:.3f}|{jitter:.6f}|{state}")
        
        speech_analysis = f"""
### 音響分析（60秒間の客観的データ）
- **発話検出**: {speaking_seconds}秒/{total_seconds}秒（{speech_ratio:.0%}が発話）
- **重要**: Jitter=0は発話なし、Jitter>0は人の声あり

#### 音響データ時系列（最初の20秒）
{chr(10).join(timeline)}
"""
    
    # 環境音の簡潔な要約
    sound_summary = "環境音データなし"
    if sed_data and len(sed_data) > 0:
        top_sounds = []
        for e in sed_data[:5]:
            if e.get('prob', 0) > 0.3:
                top_sounds.append(e.get('label', ''))
        if top_sounds:
            sound_summary = f"検出音: {', '.join(top_sounds)}"
    
    # プロンプト生成
    prompt = f"""
あなたは子どもの行動観察の専門家です。
与えられたデータから、その時点で最も可能性の高い状況を、あなたの専門知識と常識を使って推測してください。

## 観測対象者
{age}歳 {gender}

## 時間情報  
- 日時: {date} {hour:02d}:{minute:02d}
- 曜日: {weekday_info['weekday']}（{weekday_info['day_type']}）
{'- 🎌 祝日: ' + holiday_info['holiday_name'] if holiday_info['is_holiday'] else ''}

{speech_analysis}

### 発話内容
{f'「{transcription}」' if transcription and transcription.strip() else '録音された明確な発話なし'}

### 環境音
{sound_summary}

## 分析依頼

上記のデータから、**この{age}歳の人が{hour:02d}:{minute:02d}に何をしていた可能性が最も高いか**、
あなたの専門知識と常識を使って判断してください。

特に重要な判断材料：
- 年齢と時間帯の組み合わせ（例：幼児の深夜なら通常は睡眠）
- Jitterデータが示す発話の有無（0=発話なし、>0=発話あり）
- 休日/平日の違い

以下のJSON形式で回答してください：

```json
{{
  "time_block": "{time_block}",
  "summary": "最も可能性の高い状況を2文で説明。常識的に考えて最も自然な解釈を。",
  "behavior": "主な行動（以下から選択、カンマ区切りで最大3つ）",
  "vibe_score": -100〜+100（状況に応じて）
}}
```

**behaviorの選択肢**：
【基本的な生活行動】
睡眠, 食事, 入浴, トイレ, 着替え, 歯磨き

【活動】  
遊び, 学習, 宿題, 読書, 運動, 散歩, 移動, 外出

【社会的行動】
会話, 電話, 家族団らん, 友達と遊ぶ

【メディア・娯楽】
テレビ, YouTube, ゲーム, 音楽, タブレット

【その他】
準備, 片付け, 家事手伝い, 休憩, 待機

**判断のポイント：**
- ルールに縛られず、最も自然で常識的な解釈をしてください
- 例：5歳児の午前2時＋Jitter全て0 → 「睡眠」が最も自然
- 例：休日の午前中＋断続的な発話 → 「家族と過ごしている」が自然
- 健康的な睡眠は+20〜+40点、深夜の覚醒は-20〜-40点など、状況に応じて採点
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