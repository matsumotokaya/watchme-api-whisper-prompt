#!/usr/bin/env python3
"""
vibe_whisper_promptテーブルの内容を確認するスクリプト
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

# 最新のデータを取得
device_id = "d067d407-cf73-4174-a9c1-d91fb60d64d0"
date = "2025-07-06"

response = supabase.table('vibe_whisper_prompt').select('*').eq('device_id', device_id).eq('date', date).execute()

if response.data:
    record = response.data[0]
    print(f"✅ データが正常に保存されました")
    print(f"📅 日付: {record['date']}")
    print(f"🆔 デバイスID: {record['device_id']}")
    print(f"📊 処理ファイル数: {record['processed_files']}")
    print(f"❌ 欠損ファイル数: {len(record['missing_files'])}")
    print(f"⏰ 生成日時: {record['generated_at']}")
    print(f"\n📝 プロンプト（最初の500文字）:")
    print(record['prompt'][:500] + "...")
else:
    print("❌ データが見つかりませんでした")