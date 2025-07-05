#!/usr/bin/env python3
"""
テスト用のサンプルトランスクリプションデータを生成するスクリプト
"""

import os
import json
from pathlib import Path
from datetime import datetime

def create_sample_transcription_data(user_id: str = "test_user", date: str = "2025-01-08"):
    """
    指定されたユーザーと日付のサンプルトランスクリプションデータを作成
    """
    base_dir = Path(f"/Users/kaya.matsumoto/data/data_accounts/{user_id}/{date}/transcriptions")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    sample_texts = [
        "おはようございます。今日は良い天気ですね。",
        "コーヒーを飲みながら朝のニュースを見ています。",
        "今日の予定を確認しています。会議が3つありますね。",
        "通勤電車に乗りました。少し混雑しています。",
        "オフィスに到着しました。今日も頑張りましょう。",
        "朝の会議が始まりました。プロジェクトの進捗を確認します。",
        "資料作成に集中しています。",
        "同僚とランチの相談をしています。",
        "お昼休憩です。外でサンドイッチを食べています。",
        "午後の作業開始です。メールの返信をしています。",
        "クライアントとの打ち合わせがありました。",
        "データ分析の作業を進めています。",
        "少し疲れてきました。コーヒーブレイクにします。",
        "夕方の会議の準備をしています。",
        "一日の作業を振り返っています。",
        "残業になりそうです。もう少し頑張ります。",
        "ようやく仕事が終わりました。お疲れ様でした。",
        "帰りの電車に乗りました。今日は充実していました。",
        "自宅に到着しました。夕食の準備をします。",
        "テレビを見ながらリラックスしています。",
        "読書の時間です。新しい本を読んでいます。",
        "家族と会話を楽しんでいます。",
        "お風呂に入ってリフレッシュしました。",
        "明日の準備をしています。早めに寝る予定です。"
    ]
    
    # 48個のファイルを作成（00-00.json ～ 23-30.json）
    file_count = 0
    for hour in range(24):
        for minute in [0, 30]:
            filename = f"{hour:02d}-{minute:02d}.json"
            file_path = base_dir / filename
            
            # サンプルテキストを循環使用
            text_index = file_count % len(sample_texts)
            sample_text = sample_texts[text_index]
            
            # 時間帯に応じて感情を調整
            if 6 <= hour <= 9:
                emotion_suffix = " 朝は清々しい気分です。"
            elif 12 <= hour <= 13:
                emotion_suffix = " お昼は少しリラックスしています。"
            elif 18 <= hour <= 20:
                emotion_suffix = " 夕方は疲れを感じますが充実感もあります。"
            elif 21 <= hour <= 23:
                emotion_suffix = " 夜はゆったりとした気分です。"
            else:
                emotion_suffix = ""
            
            # JSONデータの作成
            transcription_data = {
                "timestamp": f"{date}T{hour:02d}:{minute:02d}:00",
                "text": sample_text + emotion_suffix,
                "confidence": 0.85 + (file_count % 10) * 0.01,
                "duration": 30,
                "metadata": {
                    "time_slot": f"{hour:02d}:{minute:02d}",
                    "file_index": file_count + 1
                }
            }
            
            # ファイルに保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(transcription_data, f, ensure_ascii=False, indent=2)
            
            file_count += 1
    
    print(f"✅ {file_count}個のサンプルトランスクリプションファイルを作成しました:")
    print(f"📁 {base_dir}")
    return base_dir

def create_output_directory(user_id: str = "test_user", date: str = "2025-01-08"):
    """
    出力ディレクトリを事前作成
    """
    output_dir = Path(f"/Users/kaya.matsumoto/data/data_accounts/{user_id}/{date}/transcriptions")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 出力ディレクトリを作成しました: {output_dir}")
    return output_dir

if __name__ == "__main__":
    print("🚀 テストデータ生成スクリプトを開始します...")
    
    # サンプルデータの作成
    user_id = "test_user"
    date = "2025-01-08"
    
    # ディレクトリ作成
    create_sample_transcription_data(user_id, date)
    create_output_directory(user_id, date)
    
    print(f"\n🎯 テスト実行例:")
    print(f"curl 'http://localhost:8009/generate-mood-prompt?user_id={user_id}&date={date}'")
    print(f"\n📖 詳細はREADME.mdを参照してください。") 