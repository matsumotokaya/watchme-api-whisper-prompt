#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Summary vibe_scores機能テストスクリプト
修正後のエンドポイントが正しく動作するかを確認
"""

import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
from supabase import create_client

# .envファイルを読み込み
load_dotenv()

# Supabase設定
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# APIエンドポイント
API_BASE_URL = "http://localhost:8009"

def test_dashboard_summary():
    """
    /generate-dashboard-summaryエンドポイントのテスト
    """
    print("=" * 60)
    print("Dashboard Summary APIテスト")
    print("=" * 60)
    
    # テスト用パラメータ（実際のデータに合わせて変更してください）
    device_id = "9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93"
    date = "2025-09-09"
    
    # APIコール
    url = f"{API_BASE_URL}/generate-dashboard-summary"
    params = {
        "device_id": device_id,
        "date": date
    }
    
    print(f"\n📡 APIリクエスト:")
    print(f"  URL: {url}")
    print(f"  Params: {params}")
    
    try:
        response = requests.get(url, params=params)
        
        print(f"\n📥 レスポンス:")
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  Status: {result.get('status')}")
            print(f"  Message: {result.get('message')}")
            print(f"  Processed Count: {result.get('processed_count')}")
            print(f"  Valid Score Count: {result.get('vibe_scores_count')}")
            print(f"  Average Vibe: {result.get('average_vibe')}")
            
            # Supabaseから保存されたデータを確認
            verify_saved_data(device_id, date)
            
        else:
            print(f"  Error: {response.text}")
            
    except Exception as e:
        print(f"❌ エラー: {e}")


def verify_saved_data(device_id: str, date: str):
    """
    Supabaseに保存されたデータを確認
    """
    print("\n" + "=" * 60)
    print("📊 保存データの確認")
    print("=" * 60)
    
    try:
        # Supabaseクライアント作成
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # dashboard_summaryテーブルから取得
        response = supabase.table("dashboard_summary").select("*").eq(
            "device_id", device_id
        ).eq(
            "date", date
        ).execute()
        
        if response.data and len(response.data) > 0:
            data = response.data[0]
            
            print("\n✅ データが正常に保存されています:")
            
            # vibe_scores配列の確認
            vibe_scores = data.get("vibe_scores")
            if vibe_scores:
                print(f"\n📈 vibe_scores配列:")
                print(f"  - 要素数: {len(vibe_scores)}")
                print(f"  - 最初の10要素: {vibe_scores[:10]}")
                
                # null以外の値をカウント
                non_null_count = sum(1 for score in vibe_scores if score is not None)
                print(f"  - 有効な値の数: {non_null_count}/48")
                
                # 配列の妥当性チェック
                if len(vibe_scores) == 48:
                    print("  ✅ 配列長が正しい（48要素）")
                else:
                    print(f"  ⚠️ 配列長が不正: {len(vibe_scores)} (期待値: 48)")
            
            # average_vibeの確認
            average_vibe = data.get("average_vibe")
            if average_vibe is not None:
                print(f"\n📊 average_vibe: {average_vibe:.2f}")
                
                # 手動計算と比較
                if vibe_scores:
                    manual_sum = sum(score for score in vibe_scores if score is not None)
                    manual_count = sum(1 for score in vibe_scores if score is not None)
                    manual_avg = manual_sum / manual_count if manual_count > 0 else None
                    
                    if manual_avg and abs(manual_avg - average_vibe) < 0.01:
                        print(f"  ✅ 平均値の計算が正しい（手動計算: {manual_avg:.2f}）")
                    else:
                        print(f"  ⚠️ 平均値が一致しない（手動計算: {manual_avg:.2f}）")
            
            # その他のフィールド確認
            print(f"\n📋 その他のフィールド:")
            print(f"  - processed_count: {data.get('processed_count')}")
            print(f"  - last_time_block: {data.get('last_time_block')}")
            print(f"  - updated_at: {data.get('updated_at')}")
            
            # integrated_dataの存在確認（互換性）
            if data.get("integrated_data"):
                print("  ✅ integrated_dataも保存されています（互換性維持）")
            
        else:
            print("❌ データが見つかりません")
            
    except Exception as e:
        print(f"❌ Supabase確認エラー: {e}")


def display_vibe_scores_format(vibe_scores):
    """
    vibe_scoresの形式を視覚的に表示
    """
    print("\n" + "=" * 60)
    print("📊 vibe_scores形式（時刻とスコアの対応）")
    print("=" * 60)
    
    time_blocks = []
    for hour in range(24):
        for minute in ["00", "30"]:
            time_blocks.append(f"{hour:02d}:{minute}")
    
    print("\n時刻     | スコア")
    print("---------|--------")
    
    for i, (time, score) in enumerate(zip(time_blocks[:10], vibe_scores[:10])):
        score_str = str(score) if score is not None else "null"
        print(f"{time}    | {score_str:>6}")
    
    print("...      | ...")
    print(f"（合計48個の時間ブロック）")


if __name__ == "__main__":
    print("\n🚀 Dashboard Summary vibe_scores機能テスト開始\n")
    
    # メインテスト実行
    test_dashboard_summary()
    
    print("\n" + "=" * 60)
    print("✅ テスト完了")
    print("=" * 60)