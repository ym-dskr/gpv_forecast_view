#!/usr/bin/env python3
"""インタラクティブ地図ビューアー生成スクリプト（再構築版）

station_data.jsonを読み込んで、インタラクティブな地図ビューアーHTMLを生成する。
テンプレートファイルを使用せず、スクリプト内でHTMLを直接構築することで、
依存関係を減らし、より堅牢な動作を実現する。

主な機能:
    - station_data.jsonの読み込み
    - 全画面地図レイアウトのHTML生成
    - Leaflet.jsとChart.jsの統合
    - エラーハンドリングとデバッグ機能

使用例:
    python generate_map_viewer.py
"""

import os
import json

OUTPUT_DIR = "output"

def generate_map_viewer():
    """地図ビューアーHTMLを生成する。

    station_data.jsonファイルを読み込み、インタラクティブな地図ビューアーHTMLを生成する。
    テンプレートファイルを使用せず、スクリプト内でHTMLを直接構築することで、
    依存関係を減らし、より堅牢な動作を実現する。

    主な機能:
        - station_data.jsonの読み込みと検証
        - 全画面レイアウトのHTML地図生成
        - Leaflet.jsとChart.jsの統合
        - レスポンシブなダークテーマUI
        - 気象データの時系列グラフ表示

    Args:
        なし

    Returns:
        なし

    Raises:
        FileNotFoundError: station_data.jsonが見つからない場合
        IOError: HTMLファイルの保存に失敗した場合

    Note:
        出力HTMLファイルは output/html/map_viewer.html に保存される。
        ブラウザで表示するには run_map_viewer.py を使用することを推奨。
    """
    print("=== 地図ビューアー生成（再構築版） ===\n")
    
    # station_data.jsonを読み込む
    json_path = os.path.join(OUTPUT_DIR, "station_data.json")
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found!")
        print("Please run station_timeseries.py first.")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        station_data = json.load(f)
    
    print(f"Loaded data for {len(station_data)} stations")
    
    # HTMLコンテンツを構築
    # テンプレートを使わず、ここで直接HTML文字列を作成する
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GPV予報 - 官署地図ビューアー</title>
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html, body {{
            height: 100%;
            width: 100%;
            overflow: hidden;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #1a1a1a;
            color: #e0e0e0;
        }}
        
        /* 全画面地図 */
        #map {{
            height: 100%;
            width: 100%;
            z-index: 1;
        }}
        
        /* フロートサイドバー */
        .sidebar {{
            position: absolute;
            top: 20px;
            right: 20px;
            width: 400px;
            max-height: calc(100% - 40px);
            background: rgba(26, 26, 26, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
            z-index: 1000;
            overflow-y: auto;
            padding: 20px;
            transition: transform 0.3s ease;
        }}
        
        .sidebar.hidden {{
            transform: translateX(120%);
        }}
        
        .header {{
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        h1 {{
            font-size: 1.5em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 5px;
        }}
        
        .subtitle {{
            color: #999;
            font-size: 0.85em;
        }}
        
        .station-info {{
            margin-bottom: 20px;
        }}
        
        .station-name {{
            font-size: 1.4em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        
        .station-coords {{
            color: #999;
            font-size: 0.9em;
        }}
        
        .chart-container {{
            background: rgba(255, 255, 255, 0.03);
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 15px;
        }}
        
        .chart-title {{
            font-size: 1em;
            font-weight: bold;
            margin-bottom: 5px;
            color: #e0e0e0;
        }}
        
        canvas {{
            max-height: 150px;
        }}
        
        .no-selection {{
            text-align: center;
            color: #666;
            padding: 40px 20px;
        }}
        
        .no-selection-icon {{
            font-size: 3em;
            margin-bottom: 15px;
        }}
        
        /* Leaflet popup styling */
        .leaflet-popup-content-wrapper {{
            background: rgba(26, 26, 26, 0.95);
            color: #e0e0e0;
            border-radius: 8px;
        }}
        
        .leaflet-popup-tip {{
            background: rgba(26, 26, 26, 0.95);
        }}
        
        .popup-station-name {{
            font-size: 1.1em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 3px;
        }}
        
        /* Scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.05);
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="sidebar" id="sidebar">
        <div class="header">
            <h1>GPV予報ビューアー</h1>
            <p class="subtitle">地図上のマーカーをクリックして詳細を表示</p>
        </div>
        
        <div id="sidebar-content">
            <div class="no-selection">
                <div class="no-selection-icon">📍</div>
                <p>地図上の官署マーカーをクリックすると<br>時系列予報グラフが表示されます</p>
            </div>
        </div>
    </div>
    
    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    
    <script>
        // 官署データを埋め込み
        const stationData = {json.dumps(station_data, ensure_ascii=False)};
        
        console.log('Station data loaded:', Object.keys(stationData).length, 'stations');
        
        // 地図を初期化
        const map = L.map('map', {{
            zoomControl: false
        }}).setView([36.5, 138], 6);
        
        // ズームコントロールを右下に配置（サイドバーと被らないように）
        L.control.zoom({{
            position: 'bottomright'
        }}).addTo(map);
        
        // OpenStreetMap タイル（標準）
        L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }}).addTo(map);
        
        // カスタムアイコン
        const stationIcon = L.divIcon({{
            className: 'custom-marker',
            html: '<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); width: 24px; height: 24px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 12px;"></div>',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        }});
        
        // パラメータの色設定
        const paramColors = {{
            '気温': '#ff6b6b',
            '気圧': '#4ecdc4',
            '湿度': '#45b7d1',
            '風速': '#96ceb4',
            '降水量': '#5f9ea0',
            '雲量': '#95a5a6'
        }};
        
        // パラメータごとの最小値・最大値を計算（Y軸統一用）
        const paramRanges = {{}};
        const paramNames = Object.keys(paramColors);
        
        paramNames.forEach(paramName => {{
            let allValues = [];
            Object.values(stationData).forEach(station => {{
                if (station.data && station.data[paramName]) {{
                    allValues = allValues.concat(station.data[paramName].values);
                }}
            }});
            
            // NaNを除外
            allValues = allValues.filter(v => !isNaN(v));
            
            if (allValues.length > 0) {{
                const minVal = Math.min(...allValues);
                const maxVal = Math.max(...allValues);
                
                // 雲量と湿度は0-100%に固定
                if (['雲量', '湿度'].includes(paramName)) {{
                    paramRanges[paramName] = {{ min: 0, max: 100 }};
                }} else {{
                    // 余裕を持たせる（上下10%）
                    let margin = (maxVal - minVal) * 0.1;
                    if (margin === 0) margin = maxVal === 0 ? 1.0 : Math.abs(maxVal) * 0.1;
                    
                    paramRanges[paramName] = {{
                        min: minVal - margin,
                        max: maxVal + margin
                    }};
                }}
            }}
        }});
        
        // 各官署にマーカーを配置
        const markers = [];
        Object.entries(stationData).forEach(([stationName, stationInfo]) => {{
            const {{ coords, data }} = stationInfo;
            
            if (!coords || !coords.lat || !coords.lon) return;
            
            const marker = L.marker([coords.lat, coords.lon], {{ icon: stationIcon }})
                .addTo(map)
                .bindPopup(`
                    <div class="popup-station-name">${{stationName}}</div>
                    <div style="font-size:0.8em; color:#999">クリックして詳細を表示</div>
                `);
            
            marker.on('click', () => {{
                showStationData(stationName, stationInfo);
            }});
            
            markers.push(marker);
        }});
        
        // 全てのマーカーが収まるように地図の表示範囲を調整
        if (markers.length > 0) {{
            const group = new L.featureGroup(markers);
            map.fitBounds(group.getBounds().pad(0.1));
        }}
        
        // グラフインスタンス管理用
        let charts = [];
        
        // 官署データを表示
        function showStationData(stationName, stationInfo) {{
            const contentDiv = document.getElementById('sidebar-content');
            const {{ coords, data }} = stationInfo;
            
            // 既存のグラフを破棄
            charts.forEach(chart => chart.destroy());
            charts = [];
            
            let html = `
                <div class="station-info">
                    <div class="station-name">${{stationName}}</div>
                    <div class="station-coords">
                        📍 緯度: ${{coords.lat.toFixed(2)}}°N, 経度: ${{coords.lon.toFixed(2)}}°E
                    </div>
                </div>
            `;
            
            // 各パラメータのグラフコンテナを作成
            Object.entries(data).forEach(([paramName, paramData]) => {{
                const chartId = `chart-${{stationName}}-${{paramName}}`.replace(/\\s+/g, '-');
                html += `
                    <div class="chart-container">
                        <div class="chart-title">${{paramName}}</div>
                        <canvas id="${{chartId}}"></canvas>
                    </div>
                `;
            }});
            
            contentDiv.innerHTML = html;
            
            // Chart.jsでグラフを描画
            Object.entries(data).forEach(([paramName, paramData]) => {{
                const chartId = `chart-${{stationName}}-${{paramName}}`.replace(/\\s+/g, '-');
                const ctx = document.getElementById(chartId);
                
                if (ctx) {{
                    const chart = new Chart(ctx, {{
                        type: 'line',
                        data: {{
                            labels: paramData.times.map(t => {{
                                const date = new Date(t);
                                return `${{date.getMonth() + 1}}/${{date.getDate()}} ${{date.getHours()}}:00`;
                            }}),
                            datasets: [{{
                                label: paramName,
                                data: paramData.values,
                                borderColor: paramColors[paramName] || '#667eea',
                                backgroundColor: (paramColors[paramName] || '#667eea') + '20',
                                borderWidth: 2,
                                fill: true,
                                tension: 0.4,
                                pointRadius: 2,
                                pointHoverRadius: 4
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{ display: false }},
                                tooltip: {{
                                    mode: 'index',
                                    intersect: false,
                                    backgroundColor: 'rgba(0,0,0,0.8)',
                                    titleColor: '#fff',
                                    bodyColor: '#fff'
                                }}
                            }},
                            scales: {{
                                x: {{
                                    ticks: {{
                                        color: '#999',
                                        maxRotation: 0,
                                        autoSkip: true,
                                        maxTicksLimit: 6,
                                        font: {{ size: 10 }}
                                    }},
                                    grid: {{
                                        color: 'rgba(255, 255, 255, 0.05)',
                                        drawBorder: false
                                    }}
                                }},
                                y: {{
                                    min: paramRanges[paramName] ? paramRanges[paramName].min : undefined,
                                    max: paramRanges[paramName] ? paramRanges[paramName].max : undefined,
                                    ticks: {{
                                        color: '#999',
                                        font: {{ size: 10 }}
                                    }},
                                    grid: {{
                                        color: 'rgba(255, 255, 255, 0.05)',
                                        drawBorder: false
                                    }}
                                }}
                            }},
                            interaction: {{
                                mode: 'nearest',
                                axis: 'x',
                                intersect: false
                            }}
                        }}
                    }});
                    charts.push(chart);
                }}
            }});
        }}
    </script>
</body>
</html>"""
    
    # HTMLファイルを保存
    output_dir_html = os.path.join(OUTPUT_DIR, "html")
    os.makedirs(output_dir_html, exist_ok=True)
    output_path = os.path.join(output_dir_html, "map_viewer.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n地図ビューアーを生成しました: {output_path}")
    print("run_map_viewer.pyを実行して表示してください。")
    print("\n=== 完了 ===")


if __name__ == "__main__":
    generate_map_viewer()
