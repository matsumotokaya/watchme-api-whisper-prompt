"""
Time Block Processing Endpoint
===============================
30分単位（タイムブロック）でデータを処理するエンドポイント
Phase 1: Transcriptionデータのみ
Phase 2: + SEDデータ (behavior_summary)
Phase 3: + OpenSMILE
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import traceback

async def get_whisper_data(supabase_client, device_id: str, date: str, time_block: str) -> Optional[str]:
    """
    vibe_whisperテーブルから特定のタイムブロックのトランスクリプトを取得
    """
    try:
        # time_blockをtime_block形式に変換 (14-30 -> 14:30形式などに対応)
        result = supabase_client.table('vibe_whisper').select('transcription').eq(
            'device_id', device_id
        ).eq(
            'date', date
        ).eq(
            'time_block', time_block
        ).execute()
        
        if result.data and len(result.data) > 0:
            # カラム名は 'transcription' (not 'transcript')
            return result.data[0].get('transcription', '')
        return None
    except Exception as e:
        print(f"Error fetching whisper data: {e}")
        return None


async def get_subject_info(supabase_client, device_id: str) -> Optional[Dict]:
    """
    device_idから観測対象者情報を取得
    devices → subjects テーブルを結合して情報を取得
    """
    try:
        # まず devices テーブルから subject_id を取得
        device_result = supabase_client.table('devices').select('subject_id').eq(
            'device_id', device_id
        ).execute()
        
        if not device_result.data or len(device_result.data) == 0:
            print(f"Device not found: {device_id}")
            return None
            
        subject_id = device_result.data[0].get('subject_id')
        if not subject_id:
            print(f"No subject_id for device: {device_id}")
            return None
        
        # subjects テーブルから情報を取得
        subject_result = supabase_client.table('subjects').select(
            'subject_id', 'name', 'age', 'gender', 'notes'
        ).eq(
            'subject_id', subject_id
        ).execute()
        
        if subject_result.data and len(subject_result.data) > 0:
            return subject_result.data[0]
        
        return None
    except Exception as e:
        print(f"Error fetching subject info: {e}")
        return None

async def get_sed_data(supabase_client, device_id: str, date: str, time_block: str) -> Optional[list]:
    """
    behavior_yamnetテーブルから特定のタイムブロックのSEDデータを取得
    eventsカラムからYAMNetの音響イベント検出結果を取得
    """
    try:
        result = supabase_client.table('behavior_yamnet').select('events').eq(
            'device_id', device_id
        ).eq(
            'date', date
        ).eq(
            'time_block', time_block
        ).execute()
        
        if result.data and len(result.data) > 0:
            # eventsは既にJSONとしてパースされているはず
            return result.data[0].get('events', [])
        return None
    except Exception as e:
        print(f"Error fetching SED data from behavior_yamnet: {e}")
        return None



def generate_timeblock_prompt(transcription: Optional[str], sed_data: Optional[list], time_block: str, 
                              date: str = None, subject_info: Optional[Dict] = None) -> str:
    """
    Transcription + SEDデータ + 観測対象者情報でプロンプト生成
    英語ラベルと確率をそのまま使用し、コンテキストを重視した分析を促す
    """
    prompt_parts = []
    
    # 時間情報から時間帯を判定
    hour = int(time_block.split('-')[0])
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
    
    # ヘッダー
    prompt_parts.append(f"""📝 分析依頼
以下は録音デバイスによる1分間音声データから抽出された、発話内容と音響イベント特徴情報のマルチモーダルデータです。
観測対象者情報と、発話内容、音響イベント、日時、日本における季節、一般的な季節のイベントなど観測対象の生活をリアルに総合的に分析し、そ心理状態と活動を推定してください。
【日時】
{date if date else ''}の{time_block}（{time_context}）

🚨 重要な注意事項：
- 音響イベント検出（YAMNet）は誤検出が多いため参考程度に
- 発話内容、時間帯、文脈を優先して判断してください
""")
    
    # 観測対象者情報
    if subject_info:
        subject_parts = []
        subject_parts.append("【観測対象者情報】")
        if subject_info.get('name'):
            subject_parts.append(f"- 名前: {subject_info['name']}")
        if subject_info.get('age') is not None:
            subject_parts.append(f"- 年齢: {subject_info['age']}歳")
        if subject_info.get('gender'):
            subject_parts.append(f"- 性別: {subject_info['gender']}")
        if subject_info.get('notes'):
            subject_parts.append(f"- 備考: {subject_info['notes']}")
        
        prompt_parts.append("\n".join(subject_parts) + "\n")
    else:
        prompt_parts.append("【観測対象者情報】\n情報なし\n")
    
    # トランスクリプション
    if transcription and transcription.strip():
        prompt_parts.append(f"""
【発話内容】
{transcription}
""")
    else:
        prompt_parts.append("""【発話内容】
(発話なし) - 録音はされたが言語的な情報なし
""")
    
    # SEDデータ（音響イベント）
    if sed_data:
        # 確率の高い上位20個のイベントのみ表示
        sorted_events = sorted(sed_data, key=lambda x: x.get('prob', 0), reverse=True)[:20]
        
        events_formatted = []
        for event in sorted_events:
            prob = event.get('prob', 0)
            label = event.get('label', 'Unknown')
            # 確率をパーセンテージで表示
            events_formatted.append(f"- {label}: {prob*100:.1f}%")
        
        prompt_parts.append(f"""
【検出された音響イベント（YAMNet）】
※発話内容と時間帯から総合的に判断してください。
{chr(10).join(events_formatted)}
""")
    else:
        prompt_parts.append("""【音響イベント】
データなし
""")
    
    # 分析指示（1日分のプロンプトから参考にした形式）
    prompt_parts.append(f"""
✅ 出力形式・ルール
以下のJSON形式で分析結果を返してください。

**出力例:**
```json
{{
  "time_block": "{time_block}",
  "summary": "この30分間の状況を2-3文で説明。発話内容と時間帯を重視。",
  "vibe_score": -36,
  "confidence_score": 0.85,
  "key_observations": [
    "観察された重要な点1",
    "観察された重要な点2"
  ],
  "detected_mood": "neutral/positive/negative/anxious/relaxed/focused等",
  "detected_activities": [
    "推定される活動1",
    "推定される活動2"
  ],
  "context_notes": "時間帯や文脈から推測される状況"
}}
```

🔍 **必須遵守ルール**
| 要素 | 指示内容 |
|------|----------|
| **vibe_score** | -100〜+100の整数値。ポジティブ感情は正、ネガティブ感情は負、中立は0付近 強い兆候がある場合は ±60 以上を積極使用 -100〜+100 をフルレンジで使い、中央付近に集中させない |
| **confidence_score** | 0.0〜1.0の小数値。分析の確信度（データが少ない場合は低く） |
| **発話なし時の処理** | "(発話なし)"の場合、音響イベントや時間帯から活動を推測（深夜なら睡眠、日中なら集中作業など） |
| **音響イベントの扱い** | 発話内容を補完。発話内容や時間帯と矛盾する場合は無視。文脈に合う場合のみ参考に |
| **summary** | 具体的で簡潔に。「〜している」「〜と思われる」など明確な表現を使用 |
| **detected_mood** | 英語で1単語。primary emotionを記載 |

**JSONのみを返してください。説明や補足は一切不要です。**
""")
    
    return "\n".join(prompt_parts)


async def save_prompt_to_dashboard(supabase_client, device_id: str, date: str, time_block: str, prompt: str):
    """
    生成したプロンプトをdashboardテーブルに保存
    """
    try:
        data = {
            'device_id': device_id,
            'date': date,
            'time_block': time_block,
            'prompt': prompt,
            'updated_at': datetime.now().isoformat()
        }
        
        result = supabase_client.table('dashboard').upsert(data).execute()
        print(f"✅ Prompt saved to dashboard table for {time_block}")
        return True
    except Exception as e:
        print(f"Error saving prompt to dashboard: {e}")
        traceback.print_exc()
        return False


async def process_and_save_to_dashboard(supabase_client, device_id: str, date: str, time_block: str, 
                                       summary: str = None, vibe_score: float = None):
    """
    処理結果をdashboardテーブルに保存
    """
    try:
        data = {
            'device_id': device_id,
            'date': date,
            'time_block': time_block,
            'updated_at': datetime.now().isoformat()
        }
        
        # NULLを許可するフィールドは値がある場合のみ追加
        if summary is not None:
            data['summary'] = summary
        if vibe_score is not None:
            data['vibe_score'] = vibe_score
        
        result = supabase_client.table('dashboard').upsert(data).execute()
        return True
    except Exception as e:
        print(f"Error saving to dashboard: {e}")
        traceback.print_exc()
        return False


# エクスポート用の処理関数


async def process_timeblock_v2(supabase_client, device_id: str, date: str, time_block: str) -> Dict[str, Any]:
    """
    処理: Whisper + SEDデータ（behavior_yamnetテーブル使用）+ 観測対象者情報
    """
    # データ取得
    transcription = await get_whisper_data(supabase_client, device_id, date, time_block)
    sed_data = await get_sed_data(supabase_client, device_id, date, time_block)
    subject_info = await get_subject_info(supabase_client, device_id)
    
    # プロンプト生成（dateパラメータと観測対象者情報も渡す）
    prompt = generate_timeblock_prompt(transcription, sed_data, time_block, date, subject_info)
    
    # デバッグ用：取得したデータの情報を出力
    print(f"📊 Data retrieved for {time_block}:")
    print(f"  - Transcription: {'Yes' if transcription else 'No'} ({len(transcription) if transcription else 0} chars)")
    print(f"  - SED Events: {'Yes' if sed_data else 'No'} ({len(sed_data) if sed_data else 0} events)")
    print(f"  - Subject Info: {'Yes' if subject_info else 'No'}")
    
    # プロンプト保存（dashboardテーブルへ）
    await save_prompt_to_dashboard(supabase_client, device_id, date, time_block, prompt)
    
    return {
        "status": "success",
        "version": "v2",
        "device_id": device_id,
        "date": date,
        "time_block": time_block,
        "prompt": prompt,  # プロンプトを返り値に追加
        "prompt_length": len(prompt),
        "has_transcription": transcription is not None and len(transcription.strip()) > 0,
        "has_sed_data": sed_data is not None and len(sed_data) > 0,
        "sed_events_count": len(sed_data) if sed_data else 0
    }