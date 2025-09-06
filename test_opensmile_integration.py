#!/usr/bin/env python3
"""
OpenSMILE統合テストスクリプト
"""

import asyncio
import requests
import json
from datetime import datetime

# テスト用のデータ
TEST_DEVICE_ID = "9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93"
TEST_DATE = "2025-09-06"
TEST_TIME_BLOCK = "11-30"

# APIエンドポイント
API_BASE_URL = "http://localhost:8009"

def test_timeblock_endpoint():
    """
    /generate-timeblock-prompt エンドポイントのテスト
    """
    print("=" * 60)
    print("🧪 Testing /generate-timeblock-prompt endpoint")
    print("=" * 60)
    
    # パラメータ
    params = {
        "device_id": TEST_DEVICE_ID,
        "date": TEST_DATE,
        "time_block": TEST_TIME_BLOCK
    }
    
    print(f"📝 Request Parameters:")
    print(f"  - Device ID: {params['device_id']}")
    print(f"  - Date: {params['date']}")
    print(f"  - Time Block: {params['time_block']}")
    print()
    
    try:
        # APIコール
        response = requests.get(f"{API_BASE_URL}/generate-timeblock-prompt", params=params)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"  - Status: {result.get('status')}")
            print(f"  - Version: {result.get('version')}")
            print(f"  - Prompt Length: {result.get('prompt_length')} characters")
            print(f"  - Has Transcription: {result.get('has_transcription')}")
            print(f"  - Has SED Data: {result.get('has_sed_data')} ({result.get('sed_events_count')} events)")
            print(f"  - Has OpenSMILE Data: {result.get('has_opensmile_data')} ({result.get('opensmile_seconds')} seconds)")
            
            # プロンプトの一部を表示
            if result.get('prompt'):
                print("\n📋 Generated Prompt (first 500 chars):")
                print("-" * 40)
                print(result['prompt'][:500])
                print("...")
                
                # OpenSMILE部分があるか確認
                if "【音声特徴の時系列変化（OpenSMILE）】" in result['prompt']:
                    print("\n✨ OpenSMILE data successfully integrated into prompt!")
                else:
                    print("\n⚠️ Warning: OpenSMILE section not found in prompt")
                    
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"  Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_health_endpoint():
    """
    /health エンドポイントのテスト
    """
    print("\n" + "=" * 60)
    print("🧪 Testing /health endpoint")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API is healthy")
            print(f"  - Status: {result.get('status')}")
            print(f"  - Timestamp: {result.get('timestamp')}")
        else:
            print(f"❌ Error: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    """
    メイン実行関数
    """
    print("\n" + "=" * 60)
    print("🚀 OpenSMILE Integration Test")
    print(f"   API URL: {API_BASE_URL}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # ヘルスチェック
    test_health_endpoint()
    
    # メインテスト
    test_timeblock_endpoint()
    
    print("\n" + "=" * 60)
    print("✨ Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()