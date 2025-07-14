"""
Supabase Client for vibe_whisper and vibe_whisper_prompt tables
"""

import os
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from datetime import datetime, date
import json

class SupabaseClient:
    def __init__(self):
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        # proxyパラメータを除外してクライアントを作成
        self.client: Client = create_client(url, key)
        print(f"✅ Supabase client initialized: {url}")
    
    async def get_vibe_whisper_data(self, device_id: str, target_date: str) -> List[Dict[str, Any]]:
        """
        vibe_whisperテーブルから指定したdevice_idと日付のデータを取得
        
        Args:
            device_id: デバイスID
            target_date: 対象日付 (YYYY-MM-DD)
        
        Returns:
            List[Dict]: 取得したデータのリスト
        """
        try:
            # dateカラムで日付を絞り込み
            response = self.client.table('vibe_whisper').select('*').eq('device_id', device_id).eq('date', target_date).order('time_block').execute()
            
            if response.data:
                print(f"✅ Found {len(response.data)} records for device_id={device_id}, date={target_date}")
                return response.data
            else:
                print(f"📊 No records found for device_id={device_id}, date={target_date}")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching vibe_whisper data: {str(e)}")
            raise e
    
    async def save_to_vibe_whisper_prompt(self, device_id: str, target_date: str, prompt: str, processed_files: int, missing_files: List[str]) -> bool:
        """
        vibe_whisper_promptテーブルにデータを保存（UPSERT）
        
        Args:
            device_id: デバイスID
            target_date: 対象日付 (YYYY-MM-DD)
            prompt: 生成されたプロンプト
            processed_files: 処理されたファイル数
            missing_files: 欠損ファイルのリスト
        
        Returns:
            bool: 保存成功時True
        """
        try:
            data = {
                'device_id': device_id,
                'date': target_date,
                'prompt': prompt,
                'processed_files': processed_files,
                'missing_files': missing_files,
                'generated_at': datetime.now().isoformat()
            }
            
            # UPSERT (既存レコードがあれば更新、なければ挿入)
            response = self.client.table('vibe_whisper_prompt').upsert(data).execute()
            
            if response.data:
                print(f"✅ Successfully saved to vibe_whisper_prompt: device_id={device_id}, date={target_date}")
                return True
            else:
                print(f"❌ Failed to save to vibe_whisper_prompt")
                return False
                
        except Exception as e:
            print(f"❌ Error saving to vibe_whisper_prompt: {str(e)}")
            raise e
    
    def extract_text_from_transcription(self, transcription_data: Any) -> Optional[str]:
        """
        transcriptionフィールドからテキストを抽出
        JSONまたは文字列形式のデータに対応
        
        Args:
            transcription_data: transcriptionフィールドのデータ
        
        Returns:
            Optional[str]: 抽出されたテキスト
        """
        if transcription_data is None:
            return None
        
        # 文字列の場合
        if isinstance(transcription_data, str):
            try:
                # JSON文字列の場合はパース
                data = json.loads(transcription_data)
                if isinstance(data, dict):
                    # よくあるフィールド名をチェック
                    for field in ['text', 'transcript', 'transcription', 'content']:
                        if field in data:
                            return str(data[field]).strip()
                    # dictだが該当フィールドがない場合は文字列化
                    return str(data).strip()
                else:
                    # JSONだがdictでない場合
                    return str(data).strip()
            except json.JSONDecodeError:
                # JSON形式でない通常の文字列
                return transcription_data.strip()
        
        # dictの場合
        elif isinstance(transcription_data, dict):
            for field in ['text', 'transcript', 'transcription', 'content']:
                if field in transcription_data:
                    return str(transcription_data[field]).strip()
            # 該当フィールドがない場合は文字列化
            return str(transcription_data).strip()
        
        # その他の型の場合は文字列化
        else:
            text = str(transcription_data).strip()
            return text if text else None