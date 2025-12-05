#!/usr/bin/env python3
"""フレームビューアー生成スクリプト

output/framesディレクトリ内のPNG画像とメタデータJSONを読み込んで、
スライダーで予報時間を選択できるインタラクティブなHTMLビューアーを生成する。

主な機能:
    - フレーム画像の読み込みとメタデータ分析
    - スライダーによる時間選択機能
    - 現在時刻と予報時刻の表示
    - 変数情報の表示
    - レスポンシブデザイン

使用例:
    python create_frame_viewer.py
"""

import os
import json
import glob
from datetime import datetime

OUTPUT_DIR = "output"
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames")
HTML_DIR = os.path.join(OUTPUT_DIR, "html")

def collect_frame_data():
    """フレームディレクトリからメタデータを収集する。

    output/framesディレクトリ内のメタデータJSONファイルを読み込み、
    フレーム番号順にソートしたデータリストを返す。

    Returns:
        list[dict]: フレームメタデータのリスト、各要素は以下を含む:
            frame_index (int): フレーム番号
            valid_time (str): 有効時刻（ISO形式）
            variables (list[str]): 変数名リスト
            image_path (str): 画像ファイル名

    Raises:
        FileNotFoundError: framesディレクトリが存在しない場合
        json.JSONDecodeError: メタデータファイルの形式が不正な場合
    """
    if not os.path.exists(FRAMES_DIR):
        raise FileNotFoundError(f"Frames directory not found: {FRAMES_DIR}")
    
    metadata_files = glob.glob(os.path.join(FRAMES_DIR, "*_metadata.json"))
    frames_data = []
    
    for metadata_file in metadata_files:
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                frames_data.append(metadata)
        except Exception as e:
            print(f"Warning: Could not read {metadata_file}: {e}")
    
    # フレーム番号でソート
    frames_data.sort(key=lambda x: x['frame_index'])
    print(f"Found {len(frames_data)} frame metadata files")
    
    return frames_data

def generate_frame_viewer_html(frames_data):
    """フレーム用HTMLビューアーを生成する。

    収集されたフレームデータからインタラクティブなHTMLビューアーを作成する。
    スライダーで時間を選択でき、各フレームの予報時刻と変数情報が表示される。

    Args:
        frames_data (list[dict]): フレームメタデータリスト

    Returns:
        str: 完成したHTMLコンテンツ

    Note:
        - ダークテーマのモダンなデザイン
        - レスポンシブレイアウト対応
        - 時刻情報の自動フォーマット
        - 変数タグの色分け表示
    """
    if not frames_data:
        return "<html><body><h1>No frame data found</h1></body></html>"
    
    # 最初と最後の時刻を取得
    first_time = datetime.fromisoformat(frames_data[0]['valid_time'].replace('Z', '+00:00'))
    last_time = datetime.fromisoformat(frames_data[-1]['valid_time'].replace('Z', '+00:00'))
    
    # 変数の色マッピング
    variable_colors = {
        'Temperature': '#ff6b6b',
        'Pressure': '#4ecdc4', 
        'Humidity': '#45b7d1',
        'Precipitation': '#96ceb4',
        'Wind Speed': '#ffa726',
        'Cloud Cover': '#95a5a6'
    }
    
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MSM予報フレームビューアー</title>
    
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        h1 {{
            font-size: 2.5em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            color: #999;
            font-size: 1.1em;
        }}
        
        .controls {{
            background: rgba(255, 255, 255, 0.05);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .time-info {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .current-time {{
            font-size: 1.4em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .time-range {{
            color: #999;
            font-size: 0.9em;
        }}
        
        .frame-info {{
            color: #ccc;
            font-size: 0.95em;
        }}
        
        .slider-container {{
            margin: 20px 0;
        }}
        
        .slider-label {{
            display: block;
            margin-bottom: 10px;
            font-weight: bold;
            color: #e0e0e0;
        }}
        
        .slider {{
            width: 100%;
            height: 8px;
            border-radius: 4px;
            background: #404040;
            outline: none;
            -webkit-appearance: none;
        }}
        
        .slider::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            cursor: pointer;
            border: 2px solid #fff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }}
        
        .slider::-moz-range-thumb {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            cursor: pointer;
            border: 2px solid #fff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }}
        
        .variables {{
            margin-top: 15px;
        }}
        
        .variables-label {{
            margin-bottom: 8px;
            font-weight: bold;
            color: #e0e0e0;
        }}
        
        .variable-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        
        .variable-tag {{
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            color: #fff;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }}
        
        .image-container {{
            text-align: center;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .forecast-image {{
            max-width: 100%;
            height: auto;
            border-radius: 10px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s ease;
        }}
        
        .forecast-image:hover {{
            transform: scale(1.02);
        }}
        
        .play-controls {{
            margin: 15px 0;
            text-align: center;
        }}
        
        .play-button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            color: white;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
            margin: 0 5px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }}
        
        .play-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }}
        
        .loading {{
            text-align: center;
            color: #999;
            font-style: italic;
            margin: 20px 0;
        }}
        
        @media (max-width: 768px) {{
            .time-info {{
                flex-direction: column;
                text-align: center;
            }}
            
            h1 {{
                font-size: 2em;
            }}
            
            .controls {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MSM予報フレームビューアー</h1>
            <p class="subtitle">スライダーで予報時間を選択してフレームを確認</p>
        </div>
        
        <div class="controls">
            <div class="time-info">
                <div class="current-time" id="currentTime">{first_time.strftime('%Y年%m月%d日 %H:%M')}</div>
                <div class="time-range">
                    {first_time.strftime('%m/%d %H:%M')} ～ {last_time.strftime('%m/%d %H:%M')} 
                    ({len(frames_data)}フレーム)
                </div>
                <div class="frame-info" id="frameInfo">Frame 1 / {len(frames_data)}</div>
            </div>
            
            <div class="slider-container">
                <label class="slider-label" for="timeSlider">予報時刻を選択:</label>
                <input type="range" 
                       id="timeSlider" 
                       class="slider" 
                       min="0" 
                       max="{len(frames_data) - 1}" 
                       value="0" 
                       step="1">
            </div>
            
            <div class="play-controls">
                <button class="play-button" id="playButton" onclick="toggleAutoPlay()">▶ 自動再生</button>
                <button class="play-button" onclick="resetFrame()">⏮ 最初に戻る</button>
            </div>
            
            <div class="variables">
                <div class="variables-label">表示中の変数:</div>
                <div class="variable-tags" id="variableTags">
                    <!-- Dynamic content -->
                </div>
            </div>
        </div>
        
        <div class="image-container">
            <img id="forecastImage" 
                 class="forecast-image" 
                 src="../frames/{frames_data[0]['image_path']}" 
                 alt="MSM予報図"
                 onerror="this.nextElementSibling.style.display='block';">
            <div class="loading" style="display: none;">画像を読み込めませんでした</div>
        </div>
    </div>

    <script>
        // フレームデータを埋め込み
        const framesData = {json.dumps(frames_data, ensure_ascii=False)};
        
        // 変数の色マッピング
        const variableColors = {json.dumps(variable_colors, ensure_ascii=False)};
        
        // 現在のフレームインデックス
        let currentFrame = 0;
        let isPlaying = false;
        let playInterval = null;
        
        // DOM要素
        const slider = document.getElementById('timeSlider');
        const image = document.getElementById('forecastImage');
        const currentTime = document.getElementById('currentTime');
        const frameInfo = document.getElementById('frameInfo');
        const variableTags = document.getElementById('variableTags');
        const playButton = document.getElementById('playButton');
        
        // スライダーイベント
        slider.addEventListener('input', function() {{
            currentFrame = parseInt(this.value);
            updateFrame();
        }});
        
        // フレーム更新関数
        function updateFrame() {{
            const frame = framesData[currentFrame];
            
            // 画像更新
            image.src = `../frames/${{frame.image_path}}`;
            
            // 時刻表示更新
            const validTime = new Date(frame.valid_time);
            currentTime.textContent = validTime.toLocaleString('ja-JP', {{
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }});
            
            // フレーム情報更新
            frameInfo.textContent = `Frame ${{currentFrame + 1}} / ${{framesData.length}}`;
            
            // 変数タグ更新
            variableTags.innerHTML = '';
            frame.variables.forEach(variable => {{
                const tag = document.createElement('span');
                tag.className = 'variable-tag';
                tag.textContent = variable;
                tag.style.backgroundColor = variableColors[variable] || '#666';
                variableTags.appendChild(tag);
            }});
            
            // スライダー位置同期
            slider.value = currentFrame;
        }}
        
        // 自動再生制御
        function toggleAutoPlay() {{
            if (isPlaying) {{
                stopAutoPlay();
            }} else {{
                startAutoPlay();
            }}
        }}
        
        function startAutoPlay() {{
            isPlaying = true;
            playButton.textContent = '⏸ 停止';
            playInterval = setInterval(() => {{
                currentFrame = (currentFrame + 1) % framesData.length;
                updateFrame();
            }}, 500); // 0.5秒間隔
        }}
        
        function stopAutoPlay() {{
            isPlaying = false;
            playButton.textContent = '▶ 自動再生';
            if (playInterval) {{
                clearInterval(playInterval);
                playInterval = null;
            }}
        }}
        
        function resetFrame() {{
            currentFrame = 0;
            updateFrame();
            if (isPlaying) {{
                stopAutoPlay();
            }}
        }}
        
        // キーボードショートカット
        document.addEventListener('keydown', function(event) {{
            switch(event.key) {{
                case 'ArrowLeft':
                    currentFrame = Math.max(0, currentFrame - 1);
                    updateFrame();
                    break;
                case 'ArrowRight':
                    currentFrame = Math.min(framesData.length - 1, currentFrame + 1);
                    updateFrame();
                    break;
                case ' ':
                    event.preventDefault();
                    toggleAutoPlay();
                    break;
                case 'Home':
                    resetFrame();
                    break;
            }}
        }});
        
        // 初期化
        updateFrame();
        
        // 画像プリロード
        framesData.forEach(frame => {{
            const img = new Image();
            img.src = `../frames/${{frame.image_path}}`;
        }});
        
        console.log(`Loaded ${{framesData.length}} frames`);
    </script>
</body>
</html>"""
    
    return html_content

def main():
    """フレームビューアー生成のメイン処理。

    framesディレクトリからメタデータを収集し、
    インタラクティブなHTMLビューアーを生成してoutput/htmlに保存する。

    処理フロー:
        1. framesディレクトリの存在確認
        2. メタデータJSONファイルの収集と分析
        3. HTMLビューアーの生成
        4. output/html/frame_viewer.htmlに保存

    Raises:
        FileNotFoundError: 必要なディレクトリが存在しない場合
        IOError: ファイル操作に失敗した場合
    """
    print("=== MSM フレームビューアー生成 ===\n")
    
    # 出力ディレクトリ作成
    os.makedirs(HTML_DIR, exist_ok=True)
    
    try:
        # フレームデータ収集
        frames_data = collect_frame_data()
        
        if not frames_data:
            print("Error: No frame data found!")
            return
        
        print(f"Time range: {frames_data[0]['valid_time']} ～ {frames_data[-1]['valid_time']}")
        
        # HTMLビューアー生成
        html_content = generate_frame_viewer_html(frames_data)
        
        # HTMLファイル保存
        output_path = os.path.join(HTML_DIR, "frame_viewer.html")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\nフレームビューアーを生成しました: {output_path}")
        print("run_frame_viewer.pyを実行して表示してください。")
        print("\n操作方法:")
        print("  - スライダー: 予報時刻を選択")
        print("  - 自動再生ボタン: フレームの自動切り替え")
        print("  - 左右矢印キー: フレーム切り替え")
        print("  - スペースキー: 自動再生/停止")
        print("  - Homeキー: 最初のフレームに戻る")
        print("\n=== 完了 ===")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()