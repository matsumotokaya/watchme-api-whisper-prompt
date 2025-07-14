#!/usr/bin/env python3
"""
vibe_whisper_promptテーブルから保存されたプロンプトを確認
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# .envファイルの読み込み
load_dotenv()

# Supabaseクライアントの初期化
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# 指定のデバイスIDと日付でデータを取得
device_id = "d067d407-cf73-4174-a9c1-d91fb60d64d0"
date = "2025-07-13"

try:
    # vibe_whisper_promptテーブルから取得
    response = supabase.table('vibe_whisper_prompt').select('*').eq('device_id', device_id).eq('date', date).execute()
    
    if response.data and len(response.data) > 0:
        data = response.data[0]
        print(f"✅ データが見つかりました:")
        print(f"device_id: {data.get('device_id')}")
        print(f"date: {data.get('date')}")
        print(f"generated_at: {data.get('generated_at')}")
        print(f"processed_files: {data.get('processed_files')}")
        print(f"\n📝 保存されているプロンプト:")
        print("=" * 80)
        print(data.get('prompt'))
        print("=" * 80)
    else:
        print(f"❌ device_id={device_id}, date={date} のデータが見つかりません")
        
except Exception as e:
    print(f"❌ エラー: {e}")