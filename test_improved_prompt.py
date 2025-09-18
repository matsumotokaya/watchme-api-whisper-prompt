#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改善されたプロンプト生成のテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from timeblock_endpoint_v2 import generate_timeblock_prompt_v2

def test_sleep_scenario():
    """5歳児の深夜睡眠シナリオ"""
    print("=" * 60)
    print("テスト1: 5歳児の深夜2時（完全無音）")
    print("=" * 60)
    
    # OpenSMILEデータ（60秒間、全てJitter=0）
    opensmile_data = []
    for i in range(60):
        opensmile_data.append({
            'timestamp': f'02:00:{i:02d}',
            'features': {
                'Loudness_sma3': 0.140,
                'jitterLocal_sma3nz': 0.000000  # 全て無音
            }
        })
    
    prompt = generate_timeblock_prompt_v2(
        transcription="",
        sed_data=[],
        time_block="02-00",
        date="2025-01-15",
        subject_info={'age': 5, 'gender': '男性'},
        opensmile_data=opensmile_data
    )
    
    print(prompt)
    print("\n期待される判断: 睡眠中、behavior=睡眠、vibe_score=+20〜+40")
    print("\n")

def test_holiday_scenario():
    """祝日の午前中シナリオ"""
    print("=" * 60)
    print("テスト2: 5歳児の祝日午前10時（断続的な発話）")
    print("=" * 60)
    
    # OpenSMILEデータ（発話あり）
    opensmile_data = []
    for i in range(60):
        jitter = 0.005 if i % 3 == 0 else 0.000000  # 3秒に1回発話
        opensmile_data.append({
            'timestamp': f'10:00:{i:02d}',
            'features': {
                'Loudness_sma3': 0.200,
                'jitterLocal_sma3nz': jitter
            }
        })
    
    # 環境音データ
    sed_data = [
        {'label': 'Speech', 'prob': 0.9},
        {'label': 'Television', 'prob': 0.6},
        {'label': 'Child speech, kid speaking', 'prob': 0.5}
    ]
    
    prompt = generate_timeblock_prompt_v2(
        transcription="ママ見て！これすごいでしょ",
        sed_data=sed_data,
        time_block="10-00",
        date="2025-01-01",  # 元日
        subject_info={'age': 5, 'gender': '女性'},
        opensmile_data=opensmile_data
    )
    
    print(prompt)
    print("\n期待される判断: 家族と遊んでいる、behavior=遊び,会話,家族団らん、vibe_score=+40〜+60")
    print("\n")

def test_afternoon_nap():
    """昼寝時間シナリオ"""
    print("=" * 60)
    print("テスト3: 3歳児の午後2時（ほぼ無音）")
    print("=" * 60)
    
    # OpenSMILEデータ（ほぼ無音、わずかな動き）
    opensmile_data = []
    for i in range(60):
        jitter = 0.001 if i == 15 or i == 45 else 0.000000  # 2回だけ小さな音
        opensmile_data.append({
            'timestamp': f'14:00:{i:02d}',
            'features': {
                'Loudness_sma3': 0.120,
                'jitterLocal_sma3nz': jitter
            }
        })
    
    prompt = generate_timeblock_prompt_v2(
        transcription="",
        sed_data=[],
        time_block="14-00",
        date="2025-01-15",
        subject_info={'age': 3, 'gender': '男性'},
        opensmile_data=opensmile_data
    )
    
    print(prompt)
    print("\n期待される判断: 昼寝中、behavior=睡眠、vibe_score=+20〜+30")
    print("\n")

if __name__ == "__main__":
    print("改善されたプロンプト生成テスト")
    print("=" * 60)
    print("重要: LLMの常識的判断が働くことを確認")
    print("=" * 60)
    print()
    
    test_sleep_scenario()
    test_holiday_scenario()
    test_afternoon_nap()
    
    print("=" * 60)
    print("テスト完了")
    print("改善ポイント:")
    print("1. OpenSMILE時系列データ（Jitter）を明確に表示")
    print("2. 年齢と時間帯から自然な推論を促す")
    print("3. ルールベースを削除し、常識的判断を重視")
    print("=" * 60)