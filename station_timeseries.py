#!/usr/bin/env python3
"""官署地点の時系列予報値グラフ生成スクリプト

主要な気象官署の位置でGPVデータから時系列データを抽出し、
パラメータごとのグラフを生成する。

主な機能:
    - 7つの主要官署（札幌、仙台、東京、名古屋、大阪、福岡、那覇）のデータ抽出
    - 6つの気象パラメータ（気温、気圧、湿度、風速、降水量、雲量）の時系列グラフ生成
    - PNG形式での一括出力
    - JSON形式でのデータエクスポート

使用例:
    python station_timeseries.py
"""

import os
import glob
import json
import numpy as np
import cfgrib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from datetime import datetime, timedelta
import pandas as pd

# 日本語フォント設定
plt.rcParams['font.family'] = ['MS Gothic', 'Yu Gothic', 'Meiryo', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False  # マイナス記号の文字化け対策

# 設定
DATA_DIR = "data"
OUTPUT_DIR = "output"

# 主要官署の座標（緯度、経度）
STATIONS = {
    '札幌': {'lat': 43.06, 'lon': 141.35},
    '仙台': {'lat': 38.27, 'lon': 140.87},
    '東京': {'lat': 35.69, 'lon': 139.69},
    '名古屋': {'lat': 35.17, 'lon': 136.91},
    '大阪': {'lat': 34.69, 'lon': 135.50},
    '福岡': {'lat': 33.58, 'lon': 130.38},
    '那覇': {'lat': 26.21, 'lon': 127.69}
}

# パラメータ設定
PARAMETERS = {
    '気温': {'unit': '°C', 'color': '#ff6b6b'},
    '気圧': {'unit': 'hPa', 'color': '#4ecdc4'},
    '湿度': {'unit': '%', 'color': '#45b7d1'},
    '風速': {'unit': 'm/s', 'color': '#96ceb4'},
    '降水量': {'unit': 'mm/h', 'color': '#5f9ea0'},
    '雲量': {'unit': '%', 'color': '#95a5a6'}
}


def find_nearest_gridpoint(lats, lons, target_lat, target_lon):
    """最も近い格子点のインデックスを見つける
    
    GPV格子点の中から、指定された緯度経度に最も近い点を検索する。
    簡易的なユークリッド距離を使用して計算。
    
    Args:
        lats (np.ndarray): 緯度の1次元または2次元配列（GPV格子点）
        lons (np.ndarray): 経度の1次元または2次元配列（GPV格子点）
        target_lat (float): 目標緯度（度）
        target_lon (float): 目標経度（度）
        
    Returns:
        tuple: (lat_idx, lon_idx) 最も近い格子点の2次元インデックス
        
    Note:
        距離計算は簡易的なユークリッド距離を使用しているため、
        広範囲の検索では精度が低下する可能性がある。
        1次元配列の場合は自動的にメッシュグリッドを作成する。
    """
    # 1次元配列の場合、メッシュグリッドを作成
    if lats.ndim == 1 and lons.ndim == 1:
        lon_grid, lat_grid = np.meshgrid(lons, lats)
    else:
        lat_grid = lats
        lon_grid = lons
    
    # 距離を計算（簡易的なユークリッド距離）
    distances = np.sqrt((lat_grid - target_lat)**2 + (lon_grid - target_lon)**2)
    min_idx = np.unravel_index(np.argmin(distances), distances.shape)
    return min_idx


def extract_station_data(files):
    """全官署の時系列データを抽出
    
    複数のGPVファイルから各官署位置のデータを抽出し、時系列データとして整理する。
    各パラメータ（気温、気圧、湿度、風速、降水量、雲量）について、
    最も近い格子点の値を取得し、適切な単位に変換する。
    
    Args:
        files (list): GPVデータファイル（.bin）のパスリスト
        
    Returns:
        dict: 以下の構造を持つ辞書
            {
                '官署名': {
                    'パラメータ名': {
                        'times': [datetime, ...],  # 予報時刻のリスト
                        'values': [float, ...]      # 予報値のリスト
                    },
                    ...
                },
                ...
            }
    
    Note:
        - 気温: ケルビンから摂氏に変換
        - 気圧: パスカルからヘクトパスカルに変換
        - 風速: u10とv10成分から合成風速を計算
        - 雲量: lcc、mcc、hccの最大値を使用
        - 降水量: 累積値の差分から時間降水量を計算
    """
    station_data = {station: {} for station in STATIONS.keys()}
    
    for file_path in files:
        print(f"Processing: {os.path.basename(file_path)}")
        
        try:
            datasets = cfgrib.open_datasets(file_path)
            
            # 各データセットから必要な変数を抽出
            for ds in datasets:
                # 座標を取得
                if 'latitude' not in ds.coords or 'longitude' not in ds.coords:
                    continue
                    
                lats = ds.latitude.values
                lons = ds.longitude.values
                
                # ステップ（予報時刻）を取得
                if 'step' not in ds.coords:
                    continue
                steps = ds.step.values
                
                # 基準時刻を取得
                if 'time' in ds.coords:
                    base_time = ds.time.values
                else:
                    continue
                
                # 各官署について処理
                for station_name, coords in STATIONS.items():
                    lat_idx, lon_idx = find_nearest_gridpoint(
                        lats, lons, coords['lat'], coords['lon']
                    )
                    
                    # 気温
                    if 't' in ds.data_vars:
                        var = ds['t']
                        values = var.values[:, lat_idx, lon_idx] - 273.15  # K -> °C
                        times = [base_time + step for step in steps]
                        
                        if '気温' not in station_data[station_name]:
                            station_data[station_name]['気温'] = {'times': [], 'values': []}
                        station_data[station_name]['気温']['times'].extend(times)
                        station_data[station_name]['気温']['values'].extend(values)
                    
                    # 気圧
                    if 'prmsl' in ds.data_vars:
                        var = ds['prmsl']
                        values = var.values[:, lat_idx, lon_idx] / 100.0  # Pa -> hPa
                        times = [base_time + step for step in steps]
                        
                        if '気圧' not in station_data[station_name]:
                            station_data[station_name]['気圧'] = {'times': [], 'values': []}
                        station_data[station_name]['気圧']['times'].extend(times)
                        station_data[station_name]['気圧']['values'].extend(values)
                    
                    # 湿度
                    if 'r' in ds.data_vars:
                        var = ds['r']
                        values = var.values[:, lat_idx, lon_idx]
                        times = [base_time + step for step in steps]
                        
                        if '湿度' not in station_data[station_name]:
                            station_data[station_name]['湿度'] = {'times': [], 'values': []}
                        station_data[station_name]['湿度']['times'].extend(times)
                        station_data[station_name]['湿度']['values'].extend(values)
                    
                    # 風速（u10, v10から計算）
                    if 'u10' in ds.data_vars and 'v10' in ds.data_vars:
                        u = ds['u10'].values[:, lat_idx, lon_idx]
                        v = ds['v10'].values[:, lat_idx, lon_idx]
                        values = np.sqrt(u**2 + v**2)
                        times = [base_time + step for step in steps]
                        
                        if '風速' not in station_data[station_name]:
                            station_data[station_name]['風速'] = {'times': [], 'values': []}
                        station_data[station_name]['風速']['times'].extend(times)
                        station_data[station_name]['風速']['values'].extend(values)
                    
                    # 雲量（lcc, mcc, hccの最大値）
                    cloud_layers = []
                    for cloud_var in ['lcc', 'mcc', 'hcc']:
                        if cloud_var in ds.data_vars:
                            cloud_layers.append(ds[cloud_var].values[:, lat_idx, lon_idx])
                    
                    if cloud_layers:
                        values = np.maximum.reduce(cloud_layers)
                        times = [base_time + step for step in steps]
                        
                        if '雲量' not in station_data[station_name]:
                            station_data[station_name]['雲量'] = {'times': [], 'values': []}
                        station_data[station_name]['雲量']['times'].extend(times)
                        station_data[station_name]['雲量']['values'].extend(values)
                    
                    # 降水量（accumulation）
                    if 'unknown' in ds.data_vars:
                        var = ds['unknown']
                        if var.attrs.get('GRIB_stepType') == 'accum':
                            accum_values = var.values[:, lat_idx, lon_idx]
                            # 差分を計算して時間降水量に
                            if len(accum_values) > 1:
                                values = np.diff(accum_values, prepend=0)
                                values[values < 0] = 0  # 負の値は0に
                                times = [base_time + step for step in steps]
                                
                                if '降水量' not in station_data[station_name]:
                                    station_data[station_name]['降水量'] = {'times': [], 'values': []}
                                station_data[station_name]['降水量']['times'].extend(times)
                                station_data[station_name]['降水量']['values'].extend(values)
            
            # データセットを閉じる
            for ds in datasets:
                ds.close()
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    return station_data


def plot_timeseries(station_data, output_path):
    """全官署・全パラメータの時系列グラフを生成
    
    7官署×6パラメータの時系列グラフを1枚の画像にまとめて出力する。
    各グラフは官署ごとに列、パラメータごとに行に配置される。
    ダークテーマのモダンなデザインで、各パラメータに固有の色を使用。
    
    Args:
        station_data (dict): extract_station_data()で取得した官署データ
        output_path (str): 出力PNG画像のファイルパス
        
    Note:
        - 画像サイズ: 20×(4×パラメータ数) インチ
        - 解像度: 150 DPI
        - 背景色: ダークグレー (#1a1a1a)
        - データがない場合は "No Data" と表示
    """
    num_params = len(PARAMETERS)
    num_stations = len(STATIONS)
    
    # 図のサイズを設定（横長に変更）
    fig = plt.figure(figsize=(30, 3 * num_params), facecolor='#1a1a1a')
    gs = GridSpec(num_params, num_stations, figure=fig, hspace=0.5, wspace=0.25)
    
    # パラメータごとの最小値・最大値を計算してY軸を統一
    param_ranges = {}
    for param_name in PARAMETERS.keys():
        all_values = []
        for station_name in STATIONS.keys():
            if param_name in station_data[station_name]:
                vals = station_data[station_name][param_name]['values']
                # NaNを除外
                valid_vals = [v for v in vals if not np.isnan(v)]
                all_values.extend(valid_vals)
        
        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
            # 余裕を持たせる（上下10%）
            margin = (max_val - min_val) * 0.1
            if margin == 0:
                margin = 1.0 if max_val == 0 else abs(max_val) * 0.1
            
            # 雲量と湿度は0-100%に固定するか、データに合わせるか
            if param_name in ['雲量', '湿度']:
                param_ranges[param_name] = (0, 100)
            else:
                param_ranges[param_name] = (min_val - margin, max_val + margin)
        else:
            param_ranges[param_name] = (0, 1)

    # パラメータごとに行を作成
    for param_idx, (param_name, param_config) in enumerate(PARAMETERS.items()):
        # 共通のY軸範囲を取得
        ylim = param_ranges.get(param_name)

        # 官署ごとに列を作成
        for station_idx, station_name in enumerate(STATIONS.keys()):
            ax = fig.add_subplot(gs[param_idx, station_idx])
            ax.set_facecolor('#2d2d2d')
            
            # Y軸の範囲を設定
            if ylim:
                ax.set_ylim(ylim)
            
            # データを取得
            if param_name in station_data[station_name]:
                data = station_data[station_name][param_name]
                times = data['times']
                values = data['values']
                
                if len(times) > 0:
                    # 時系列データをソート（時刻順に並べる）
                    sorted_indices = np.argsort(times)
                    times_sorted = [times[i] for i in sorted_indices]
                    values_sorted = [values[i] for i in sorted_indices]
                    
                    # numpy datetime64をPythonのdatetimeに変換
                    times_dt = [pd.Timestamp(t).to_pydatetime() for t in times_sorted]
                    
                    # プロット
                    ax.plot(times_dt, values_sorted, color=param_config['color'], 
                           linewidth=2, marker='o', markersize=3)
                    
                    # X軸の日時フォーマット設定
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d\n%H時'))
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
                    
                    # スタイリング
                    ax.set_title(f"{station_name}", color='#e0e0e0', fontsize=10, pad=5)
                    ax.set_ylabel(f"{param_config['unit']}", color='#e0e0e0', fontsize=9)
                    ax.tick_params(colors='#e0e0e0', labelsize=7)
                    ax.grid(True, alpha=0.2, color='#404040')
                    
                    # X軸のラベル回転
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')
                    
                    # 左端の列のみY軸ラベルを表示
                    if station_idx == 0:
                        ax.set_ylabel(f"{param_name}\n{param_config['unit']}", 
                                     color='#e0e0e0', fontsize=10, fontweight='bold')
            else:
                ax.text(0.5, 0.5, 'No Data', ha='center', va='center',
                       color='#666666', fontsize=10, transform=ax.transAxes)
                ax.set_title(f"{station_name}", color='#e0e0e0', fontsize=10, pad=5)
                ax.tick_params(colors='#e0e0e0')
    
    # 全体のタイトル
    fig.suptitle('主要官署の時系列予報値', color='#e0e0e0', fontsize=18, y=0.995)
    
    # 保存
    plt.savefig(output_path, dpi=150, facecolor='#1a1a1a', bbox_inches='tight')
    plt.close(fig)
    print(f"Time series plot saved to: {output_path}")


def save_station_data_json(station_data, output_path):
    """官署データをJSON形式で保存（地図ビューアー用）
    
    時系列データをJSON形式に変換して保存する。
    NumPy配列とdatetimeオブジェクトをJSON互換形式に変換し、
    地図ビューアーで読み込めるようにする。
    
    Args:
        station_data (dict): extract_station_data()で取得した官署データ
        output_path (str): 出力JSONファイルのパス
        
    Note:
        出力JSON構造:
        {
            "官署名": {
                "coords": {"lat": 緯度, "lon": 経度},
                "data": {
                    "パラメータ名": {
                        "times": ["時刻文字列", ...],
                        "values": [数値, ...]
                    },
                    ...
                }
            },
            ...
        }
    """
    # NumPy配列とdatetimeをJSON互換形式に変換
    json_data = {}
    
    for station_name, params in station_data.items():
        json_data[station_name] = {
            'coords': STATIONS[station_name],
            'data': {}
        }
        
        for param_name, data in params.items():
            json_data[station_name]['data'][param_name] = {
                'times': [str(t) for t in data['times']],
                'values': [float(v) for v in data['values']]
            }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"Station data JSON saved to: {output_path}")


def main():
    """メイン処理
    
    GPVデータファイルを読み込み、官署時系列データを抽出して、
    グラフ画像とJSONファイルを生成する。
    
    処理フロー:
        1. 出力ディレクトリの作成
        2. GPVファイルの検索
        3. 官署データの抽出
        4. 時系列グラフの生成（PNG）
        5. JSONデータの保存
    
    出力ファイル:
        - output/station_timeseries.png: 時系列グラフ画像
        - output/station_data.json: 時系列データ（JSON形式）
    """
    print("=== 官署時系列グラフ生成 ===\n")
    
    # 出力ディレクトリを作成
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # GPVファイルを取得
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.bin")))
    if not files:
        print("No GPV data files found!")
        return
    
    print(f"Found {len(files)} GPV files\n")
    
    # 官署データを抽出
    station_data = extract_station_data(files)
    
    # 時系列グラフを生成
    plot_path = os.path.join(OUTPUT_DIR, "station_timeseries.png")
    plot_timeseries(station_data, plot_path)
    
    # JSONデータを保存
    json_path = os.path.join(OUTPUT_DIR, "station_data.json")
    save_station_data_json(station_data, json_path)
    
    print("\n=== 完了 ===")


if __name__ == "__main__":
    main()
