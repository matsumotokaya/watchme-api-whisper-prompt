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


def generate_age_context(subject_info: Optional[Dict]) -> str:
    """観測対象者の基本情報のみを提供（決めつけを排除）"""
    if not subject_info:
        return "観測対象者情報：不明"
    
    age = subject_info.get('age')
    gender = subject_info.get('gender', '不明')
    notes = subject_info.get('notes', '')
    
    context_parts = []
    
    # 基本情報のみ
    if age is not None:
        context_parts.append(f"{age}歳 {gender}")
    else:
        context_parts.append(f"年齢不明 {gender}")
    
    # 個別の備考情報を重視
    if notes:
        context_parts.append(f"備考：{notes}")
    
    return " / ".join(context_parts)


def generate_time_context(hour: int, minute: int) -> str:
    """時刻を表示用フォーマットで返す"""
    return f"{hour:02d}:{minute:02d}"

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
    minute = int(time_block.split('-')[1])
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
    
    # 終了時刻の計算（30分後）
    end_minute = minute + 30
    end_hour = hour
    if end_minute >= 60:
        end_hour = hour + 1
        end_minute = end_minute - 60
    
    # ==================== 1. ヘッダー（タスク宣言） ====================
    prompt_parts.append(f"""📊 マルチモーダル時系列分析タスク

30分ブロックの音声データから感情状態を分析し、JSON形式で出力してください。

    # ==================== 2. 出力スキーマと厳格ルール ====================
    
**出力形式（必須）:**
```json
{{
  "time_block": "{time_block}",
  "summary": "30分間の全体的な状況と感情の流れを2-3文で説明",
  "vibe_score": -36,
  "confidence_score": 0.85,
  "temporal_analysis": {{
    "emotion_trajectory": "前半は穏やか→中盤で興奮→後半は落ち着く",
    "peak_moments": ["特定時刻の感情ピーク説明"],
    "quiet_periods": ["静寂期間の説明"]
  }},
  "acoustic_features": {{
    "average_loudness": 0.186,
    "loudness_trend": "increasing/stable/decreasing",
    "voice_stability": "安定/やや不安定/不安定",
    "notable_patterns": ["観察された音声パターン"]
  }},
  "key_observations": [
    "時系列データから観察された重要な点"
  ],
  "detected_mood": "neutral/positive/negative/anxious/relaxed/excited/tired",
  "detected_activities": ["推定される活動"],
  "context_notes": "詳細な状況説明"
}}
```

**厳格ルール:**
- JSONのみを返す（説明や補足は一切不要）
- すべてのフィールドは必須
- vibe_scoreは必ず-100〜+100の整数値
- confidence_scoreは0.0〜1.0の小数値

    # ==================== 3. 分析の前提条件と制約（最重要） ====================
    
**観測対象者のプロファイリング:**
{generate_age_context(subject_info)}

**分析の優先順位（厳守）:**
1. 第1優先: 発話内容と観測対象者の年齢・特性の照合
2. 第2優先: 時間帯・季節との整合性確認
3. 第3優先: 音響特徴（補完的に使用、主判断を覆すには強い根拠が必要）

**誤解析防止の鉄則:**
- 子供の演技的発話・ごっこ遊び → 年齢相応の正常な発達行動として評価
- 独り言・自己対話 → 幼児〜学童期では正常（むしろ認知発達の証）
- 時間帯のみでの異常判定 → 禁止（個人の生活リズムを尊重）
- 感情の起伏 → 年齢・状況を考慮（子供は感情表現が豊か）

**コンテキストを踏まえた解釈:**
- 5歳児が怪獣ごっこで叫ぶ → ポジティブな遊び（ネガティブ判定しない）
- 夕方の騒がしさ → 子供の活動時間として正常
- 大人の独り言 → ストレス処理の可能性（必ずしもネガティブではない）

    # ==================== 4. 採点・スコア分布ポリシー ====================
    
**vibe_scoreの採点基準:**
- **-100〜+100の全範囲を積極的に使用**
- スコア分布：
  * 非常にポジティブ: 60〜100
  * ポジティブ: 20〜60
  * ニュートラル: -20〜20
  * ネガティブ: -60〜-20
  * 非常にネガティブ: -100〜-60

**採点要素（観測対象者の年齢を考慮して調整）:**
- 音量が大きい時間帯: +10〜20（子供の場合は正常範囲）
- 声の震えが多い: -10〜30（状況と年齢による）
- 長い沈黙: -5〜15（集中や休息の可能性も考慮）
- 活発な会話: +15〜25
- 早朝の活動: +20〜30（年齢により判断）
- 深夜の活動: -20〜30（個人差を考慮）

**confidence_scoreの決定基準:**
- データの完全性（全モダリティが揃っている）: 0.8〜1.0
- 部分的データ: 0.4〜0.8
- 単一モダリティのみ: 0.2〜0.4

    # ==================== 5. メタ情報 ====================
    
    # 曜日情報を取得
    weekday_info = get_weekday_info(date) if date else {"weekday": "不明", "day_type": "不明"}
    
    prompt_parts.append(f"""【分析対象】
- 地域: 日本
- 季節: {get_season(int(date.split('-')[1])) if date else '不明'}
- 日付: {date if date else '不明'}
- 曜日: {weekday_info['weekday']}（{weekday_info['day_type']}）
- 時刻: {generate_time_context(hour, minute)}
- 時間範囲: {hour:02d}:{minute:02d}〜{end_hour:02d}:{end_minute:02d}（30分ブロック）
""")
    
    # 観測対象者情報をメタ情報に含める
    if subject_info:
        subject_parts = []
        if subject_info.get('name'):
            subject_parts.append(f"名前: {subject_info['name']}")
        if subject_info.get('age') is not None:
            subject_parts.append(f"年齢: {subject_info['age']}歳")
        if subject_info.get('gender'):
            subject_parts.append(f"性別: {subject_info['gender']}")
        if subject_info.get('notes'):
            subject_parts.append(f"備考: {subject_info['notes']}")
        
        prompt_parts.append("- 観測対象者: " + ", ".join(subject_parts) + "\n")
    else:
        prompt_parts.append("- 観測対象者: 情報なし\n")
    
    # ==================== 6. 要約統計 ====================
    prompt_parts.append("\n【要約統計】\n")
    
    # 発話の要約
    if transcription and transcription.strip():
        prompt_parts.append(f"◆ 発話: あり（{len(transcription)}文字）")
    else:
        prompt_parts.append("◆ 発話: なし（録音はされたが言語的な情報なし）")
    
    # OpenSMILEの統計情報を先に計算
    if opensmile_data and len(opensmile_data) > 0:
        loudness_values = [item.get('features', {}).get('Loudness_sma3', 0) for item in opensmile_data]
        jitter_values = [item.get('features', {}).get('jitterLocal_sma3nz', 0) for item in opensmile_data]
        
        avg_loudness = sum(loudness_values) / len(loudness_values)
        max_loudness = max(loudness_values)
        min_loudness = min(loudness_values)
        avg_jitter = sum(jitter_values) / len(jitter_values)
        max_jitter = max(jitter_values)
        
        prompt_parts.append(f"""◆ 音声特徴（OpenSMILE）統計:
  - 記録時間: {len(opensmile_data)}秒
  - 平均音量: {avg_loudness:.3f} (範囲: {min_loudness:.3f}〜{max_loudness:.3f})
  - 平均声の震え: {avg_jitter:.6f} (最大: {max_jitter:.6f})
  - 無音区間: {jitter_values.count(0)}秒 / {len(jitter_values)}秒""")
    else:
        prompt_parts.append("◆ 音声特徴（OpenSMILE）: データなし")
    
    # SEDデータ（音響イベント）の統計
    if sed_data:
        # 確率の高い上位イベントを抽出
        sorted_events = sorted(sed_data, key=lambda x: x.get('prob', 0), reverse=True)
        
        # 主要な音響イベントの統計
        high_prob_events = [e for e in sorted_events if e.get('prob', 0) >= 0.7]
        mid_prob_events = [e for e in sorted_events if 0.4 <= e.get('prob', 0) < 0.7]
        
        speech_prob = next((e.get('prob', 0)*100 for e in sorted_events if 'Speech' in e.get('label', '')), 0)
        has_child_voice = any('Child' in e.get('label', '') or 'Baby' in e.get('label', '') for e in sorted_events[:20])
        has_noise = any('Noise' in e.get('label', '') for e in sorted_events[:10])
        activity_diversity = len([e for e in sorted_events[:20] if e.get('prob', 0) > 0.3])
        
        prompt_parts.append(f"""◆ 音響イベント（YAMNet）統計:
  - 検出イベント総数: {len(sed_data)}種類
  - 高確率イベント（70%以上）: {len(high_prob_events)}個
  - 中確率イベント（40-70%）: {len(mid_prob_events)}個
  - Speech検出率: {speech_prob:.1f}%
  - 子供の声: {'検出' if has_child_voice else '未検出'}
  - 環境ノイズ: {'高' if has_noise else '低'}
  - 活動音の多様性: {activity_diversity}種類""")
    else:
        prompt_parts.append("◆ 音響イベント（YAMNet）: データなし")
    
    
    # ==================== 7. 詳細データ ====================
    prompt_parts.append("\n\n【詳細データ】\n")
    
    # 発話内容の詳細
    if transcription and transcription.strip():
        prompt_parts.append(f"""◆ 発話内容（全文）:
{transcription}
""")
    
    # OpenSMILEの時系列データ（詳細）
    if opensmile_data and len(opensmile_data) > 0:
        prompt_parts.append("◆ 音声特徴の時系列（OpenSMILE、1秒毎）:")
        prompt_parts.append("時刻 | 音量(Loudness) | 声の震え(Jitter)")
        prompt_parts.append("-----|---------------|----------------")
        
        for item in opensmile_data[:60]:  # 最大60秒分
            timestamp = item.get('timestamp', 'N/A')
            features = item.get('features', {})
            loudness = features.get('Loudness_sma3', 0)
            jitter = features.get('jitterLocal_sma3nz', 0)
            prompt_parts.append(f"{timestamp} | {loudness:.3f} | {jitter:.6f}")
    
    # SEDイベントの詳細リスト
    if sed_data:
        sorted_events = sorted(sed_data, key=lambda x: x.get('prob', 0), reverse=True)
        prompt_parts.append("\n◆ 音響イベント詳細（YAMNet、確率順）:")
        
        # 上位20個のイベントのみ表示
        for i, event in enumerate(sorted_events[:20], 1):
            label = event.get('label', 'Unknown')
            prob = event.get('prob', 0)
            prompt_parts.append(f"  {i}. {label}: {prob*100:.1f}%")
    
    return "\n".join(prompt_parts)


async def update_whisper_status(supabase_client, device_id: str, date: str, time_block: str):
    """
    vibe_whisperテーブルのstatusをcompletedに更新
    """
    try:
        data = {
            'status': 'completed'
        }
        
        result = supabase_client.table('vibe_whisper').update(data).eq(
            'device_id', device_id
        ).eq(
            'date', date
        ).eq(
            'time_block', time_block
        ).execute()
        
        print(f"✅ Updated vibe_whisper status to completed for {time_block}")
        return True
    except Exception as e:
        print(f"⚠️ Error updating vibe_whisper status: {e}")
        return False


async def update_yamnet_status(supabase_client, device_id: str, date: str, time_block: str):
    """
    behavior_yamnetテーブルのstatusをcompletedに更新
    """
    try:
        data = {
            'status': 'completed'
        }
        
        result = supabase_client.table('behavior_yamnet').update(data).eq(
            'device_id', device_id
        ).eq(
            'date', date
        ).eq(
            'time_block', time_block
        ).execute()
        
        print(f"✅ Updated behavior_yamnet status to completed for {time_block}")
        return True
    except Exception as e:
        print(f"⚠️ Error updating behavior_yamnet status: {e}")
        return False


async def update_opensmile_status(supabase_client, device_id: str, date: str, time_block: str):
    """
    emotion_opensmileテーブルのstatusをcompletedに更新
    """
    try:
        data = {
            'status': 'completed'
        }
        
        result = supabase_client.table('emotion_opensmile').update(data).eq(
            'device_id', device_id
        ).eq(
            'date', date
        ).eq(
            'time_block', time_block
        ).execute()
        
        print(f"✅ Updated emotion_opensmile status to completed for {time_block}")
        return True
    except Exception as e:
        print(f"⚠️ Error updating emotion_opensmile status: {e}")
        return False


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
    プロンプト生成後、使用されたデータソースのstatusをcompletedに更新
    """
    # データ取得
    transcription = await get_whisper_data(supabase_client, device_id, date, time_block)
    sed_data = await get_sed_data(supabase_client, device_id, date, time_block)
    opensmile_data = await get_opensmile_data(supabase_client, device_id, date, time_block)
    subject_info = await get_subject_info(supabase_client, device_id)
    
    # データ存在フラグを記録
    has_whisper = transcription is not None
    has_yamnet = sed_data is not None and len(sed_data) > 0
    has_opensmile = opensmile_data is not None and len(opensmile_data) > 0
    
    # プロンプト生成（OpenSMILEデータも含めて渡す）
    prompt = generate_timeblock_prompt(transcription, sed_data, time_block, date, subject_info, opensmile_data)
    
    # デバッグ用：取得したデータの情報を出力
    print(f"📊 Data retrieved for {time_block}:")
    print(f"  - Transcription: {'Yes' if has_whisper else 'No'} ({len(transcription) if transcription else 0} chars)")
    print(f"  - SED Events: {'Yes' if has_yamnet else 'No'} ({len(sed_data) if sed_data else 0} events)")
    print(f"  - OpenSMILE Timeline: {'Yes' if has_opensmile else 'No'} ({len(opensmile_data) if opensmile_data else 0} seconds)")
    print(f"  - Subject Info: {'Yes' if subject_info else 'No'}")
    
    # プロンプト保存（dashboardテーブルへ）
    dashboard_saved = await save_prompt_to_dashboard(supabase_client, device_id, date, time_block, prompt)
    
    # dashboardへの保存が成功した場合のみ、各データソースのstatusを更新
    status_updates = {
        "whisper_updated": False,
        "yamnet_updated": False,
        "opensmile_updated": False
    }
    
    if dashboard_saved:
        print(f"\n📝 Updating status for used data sources...")
        
        # 実際にデータが存在した場合のみstatusを更新
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
        
        # 更新結果のサマリー
        print(f"\n✨ Status update summary:")
        print(f"  - vibe_whisper: {'✅ Updated' if status_updates['whisper_updated'] else '⏭️ Skipped (no data)' if not has_whisper else '⚠️ Update failed'}")
        print(f"  - behavior_yamnet: {'✅ Updated' if status_updates['yamnet_updated'] else '⏭️ Skipped (no data)' if not has_yamnet else '⚠️ Update failed'}")
        print(f"  - emotion_opensmile: {'✅ Updated' if status_updates['opensmile_updated'] else '⏭️ Skipped (no data)' if not has_opensmile else '⚠️ Update failed'}")
    else:
        print(f"⚠️ Dashboard save failed, skipping status updates")
    
    return {
        "status": "success",
        "version": "v3",  # バージョンをv3に更新
        "device_id": device_id,
        "date": date,
        "time_block": time_block,
        "prompt": prompt,  # プロンプトを返り値に追加
        "prompt_length": len(prompt),
        "has_transcription": has_whisper and len(transcription.strip()) > 0,
        "has_sed_data": has_yamnet,
        "has_opensmile_data": has_opensmile,
        "sed_events_count": len(sed_data) if sed_data else 0,
        "opensmile_seconds": len(opensmile_data) if opensmile_data else 0,
        "dashboard_saved": dashboard_saved,
        "status_updates": status_updates
    }