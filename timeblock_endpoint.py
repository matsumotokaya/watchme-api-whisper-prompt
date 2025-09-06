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


async def get_opensmile_data(supabase_client, device_id: str, date: str, time_block: str) -> Optional[list]:
    """
    emotion_opensmileテーブルから特定のタイムブロックのOpenSMILEデータを取得
    selected_features_timelineカラムから音声特徴の時系列データを取得
    """
    try:
        result = supabase_client.table('emotion_opensmile').select('selected_features_timeline').eq(
            'device_id', device_id
        ).eq(
            'date', date
        ).eq(
            'time_block', time_block
        ).execute()
        
        if result.data and len(result.data) > 0:
            # selected_features_timelineは既にJSONとしてパースされているはず
            timeline = result.data[0].get('selected_features_timeline', [])
            # JSON文字列の場合はパース
            if isinstance(timeline, str):
                import json
                timeline = json.loads(timeline)
            return timeline
        return None
    except Exception as e:
        print(f"Error fetching OpenSMILE data from emotion_opensmile: {e}")
        return None



def generate_timeblock_prompt(transcription: Optional[str], sed_data: Optional[list], time_block: str, 
                              date: str = None, subject_info: Optional[Dict] = None, 
                              opensmile_data: Optional[list] = None) -> str:
    """
    Transcription + SEDデータ + OpenSMILEデータ + 観測対象者情報でプロンプト生成
    時系列データを含む包括的な分析を促す
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
    prompt_parts.append(f"""📊 マルチモーダル時系列分析依頼

録音デバイスによる30分間の音声データから抽出された以下の情報を総合的に分析してください：
1. 発話内容（音声認識結果）
2. 音響イベント（YAMNet）の時系列変化
3. 音声特徴（OpenSMILE）の1秒毎の時系列変化
4. 観測対象者の属性情報

【分析対象時間】
{date if date else ''}の{time_block.replace('-', ':')}〜{time_block.split('-')[0]}:{str(int(time_block.split('-')[1])+30).zfill(2) if int(time_block.split('-')[1])+30 < 60 else str(int(time_block.split('-')[0])+1).zfill(2)+':'+str((int(time_block.split('-')[1])+30)%60).zfill(2)}（{time_context}）

【分析方針】
- 時系列データの変化パターンに注目し、感情や活動の推移を捉える
- 複数のモダリティを相互補完的に活用する
- 音声特徴の変化から感情の微細な変動を読み取る
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
    
    # OpenSMILEデータ（音声特徴の時系列）
    if opensmile_data:
        prompt_parts.append("""
【音声特徴の時系列変化（OpenSMILE）】
※1秒毎の音声特徴量を示します。声の大きさ（Loudness）と声の震え（Jitter）から感情状態を推定してください。
""")
        
        # 時系列データを表形式で表示
        timeline_parts = []
        timeline_parts.append("時刻 | 音量(Loudness) | 声の震え(Jitter) | 解釈のヒント")
        timeline_parts.append("-----|---------------|-----------------|-------------")
        
        for item in opensmile_data[:60]:  # 最大60秒分
            timestamp = item.get('timestamp', 'N/A')
            features = item.get('features', {})
            loudness = features.get('Loudness_sma3', 0)
            jitter = features.get('jitterLocal_sma3nz', 0)
            
            # 解釈のヒントを追加
            hint = ""
            if loudness > 0.3:
                hint = "大声/興奮"
            elif loudness < 0.15:
                hint = "小声/静か"
            if jitter > 0.01:
                hint += " 緊張/不安定" if hint else "緊張/不安定"
            elif jitter == 0:
                hint += " 無音" if not hint else "/無音"
                
            timeline_parts.append(f"{timestamp} | {loudness:.3f} | {jitter:.6f} | {hint}")
        
        prompt_parts.append("\n".join(timeline_parts))
        
        # 統計情報
        if len(opensmile_data) > 0:
            loudness_values = [item.get('features', {}).get('Loudness_sma3', 0) for item in opensmile_data]
            jitter_values = [item.get('features', {}).get('jitterLocal_sma3nz', 0) for item in opensmile_data]
            
            avg_loudness = sum(loudness_values) / len(loudness_values)
            max_loudness = max(loudness_values)
            min_loudness = min(loudness_values)
            avg_jitter = sum(jitter_values) / len(jitter_values)
            max_jitter = max(jitter_values)
            
            prompt_parts.append(f"""
【音声特徴の統計サマリー】
- 平均音量: {avg_loudness:.3f} (範囲: {min_loudness:.3f}〜{max_loudness:.3f})
- 平均声の震え: {avg_jitter:.6f} (最大: {max_jitter:.6f})
- 無音区間: {jitter_values.count(0)}秒 / {len(jitter_values)}秒
""")
    else:
        prompt_parts.append("""【音声特徴（OpenSMILE）】
データなし
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
※環境音や活動音の検出結果です。発話内容と時間帯から総合的に判断してください。
{chr(10).join(events_formatted)}
""")
    else:
        prompt_parts.append("""【音響イベント（YAMNet）】
データなし
""")
    
    # 分析指示（時系列分析を重視）
    prompt_parts.append(f"""
✅ 総合分析と出力形式

以下のJSON形式で、時系列変化を踏まえた分析結果を返してください。

**出力例:**
```json
{{
  "time_block": "{time_block}",
  "summary": "30分間の全体的な状況と感情の流れを2-3文で説明",
  "vibe_score": -36,
  "confidence_score": 0.85,
  "temporal_analysis": {{
    "emotion_trajectory": "前半は穏やか→中盤で興奮→後半は落ち着く",
    "peak_moments": ["11:30:06 - 大声での発話（興奮）", "11:30:23 - 活発な活動"],
    "quiet_periods": ["11:30:16-11:30:21 - ほぼ無音（集中または休息）"]
  }},
  "acoustic_features": {{
    "average_loudness": 0.186,
    "loudness_trend": "increasing/stable/decreasing",
    "voice_stability": "安定/やや不安定/不安定",
    "notable_patterns": ["声の震えが増加（緊張の兆候）"]
  }},
  "key_observations": [
    "時系列データから観察された重要な点1",
    "発話と音響特徴の相関から判明した点2"
  ],
  "detected_mood": "neutral/positive/negative/anxious/relaxed/excited/tired等",
  "detected_activities": [
    "推定される主な活動",
    "副次的な活動"
  ],
  "context_notes": "時間帯、音声特徴の変化パターン、環境音から推測される詳細な状況"
}}
```

🔍 **分析の重点**
| 要素 | 指示内容 |
|------|----------|
| **vibe_score** | -100〜+100の整数値。時系列データ全体の傾向を反映。瞬間的なピークよりも全体的な流れを重視 |
| **時系列分析** | 音声特徴の変化パターンから感情の推移を読み取る。急激な変化に注目 |
| **マルチモーダル統合** | 発話内容 × 音声特徴 × 環境音を総合的に解釈 |
| **confidence_score** | データの質と量、各モダリティの一致度を考慮。時系列データが豊富なら高く |
| **temporal_analysis** | 必ず時間軸での変化を記述。「前半」「中盤」「後半」や具体的な時刻を使用 |
| **acoustic_features** | OpenSMILEデータの統計値と変化傾向を必ず含める |

📊 **スコアリング指示**
- **-100〜+100の全範囲を積極的に使用してください**
- スコア分布の目安：
  * 非常にポジティブ: 60〜100
  * ポジティブ: 20〜60  
  * ニュートラル: -20〜20
  * ネガティブ: -60〜-20
  * 非常にネガティブ: -100〜-60
- 以下の要素で加点/減点：
  * 音量が大きい時間帯: +10〜20
  * 声の震えが多い: -10〜30
  * 長い沈黙: -5〜15
  * 活発な会話: +15〜25
  * 早朝の活動: +20〜30
  * 深夜の活動: -20〜30（内容による）

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
    処理: Whisper + SEDデータ（behavior_yamnetテーブル使用）+ OpenSMILEデータ + 観測対象者情報
    """
    # データ取得
    transcription = await get_whisper_data(supabase_client, device_id, date, time_block)
    sed_data = await get_sed_data(supabase_client, device_id, date, time_block)
    opensmile_data = await get_opensmile_data(supabase_client, device_id, date, time_block)
    subject_info = await get_subject_info(supabase_client, device_id)
    
    # プロンプト生成（OpenSMILEデータも含めて渡す）
    prompt = generate_timeblock_prompt(transcription, sed_data, time_block, date, subject_info, opensmile_data)
    
    # デバッグ用：取得したデータの情報を出力
    print(f"📊 Data retrieved for {time_block}:")
    print(f"  - Transcription: {'Yes' if transcription else 'No'} ({len(transcription) if transcription else 0} chars)")
    print(f"  - SED Events: {'Yes' if sed_data else 'No'} ({len(sed_data) if sed_data else 0} events)")
    print(f"  - OpenSMILE Timeline: {'Yes' if opensmile_data else 'No'} ({len(opensmile_data) if opensmile_data else 0} seconds)")
    print(f"  - Subject Info: {'Yes' if subject_info else 'No'}")
    
    # プロンプト保存（dashboardテーブルへ）
    await save_prompt_to_dashboard(supabase_client, device_id, date, time_block, prompt)
    
    return {
        "status": "success",
        "version": "v3",  # バージョンをv3に更新
        "device_id": device_id,
        "date": date,
        "time_block": time_block,
        "prompt": prompt,  # プロンプトを返り値に追加
        "prompt_length": len(prompt),
        "has_transcription": transcription is not None and len(transcription.strip()) > 0,
        "has_sed_data": sed_data is not None and len(sed_data) > 0,
        "has_opensmile_data": opensmile_data is not None and len(opensmile_data) > 0,
        "sed_events_count": len(sed_data) if sed_data else 0,
        "opensmile_seconds": len(opensmile_data) if opensmile_data else 0
    }