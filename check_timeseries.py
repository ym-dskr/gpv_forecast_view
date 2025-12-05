#!/usr/bin/env python3
"""時系列データの確認スクリプト"""

import os
import glob
import json
import numpy as np
import cfgrib

DATA_DIR = "data"

# 主要官署の座標
STATIONS = {
    '東京': {'lat': 35.69, 'lon': 139.69},
}

def check_data():
    """データ構造を確認"""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.bin")))
    if not files:
        print("No files found!")
        return
    
    print(f"=== データ構造確認 ===\n")
    print(f"ファイル数: {len(files)}\n")
    
    for file_path in files[:1]:  # 最初のファイルのみ確認
        print(f"ファイル: {os.path.basename(file_path)}\n")
        
        datasets = cfgrib.open_datasets(file_path)
        
        for ds_idx, ds in enumerate(datasets):
            print(f"--- Dataset {ds_idx} ---")
            
            # 座標情報
            if 'latitude' in ds.coords and 'longitude' in ds.coords:
                lats = ds.latitude.values
                lons = ds.longitude.values
                print(f"緯度範囲: {lats.min():.2f} ~ {lats.max():.2f}")
                print(f"経度範囲: {lons.min():.2f} ~ {lons.max():.2f}")
                print(f"格子点数: {lats.shape}")
            
            # 時間情報
            if 'time' in ds.coords:
                print(f"基準時刻: {ds.time.values}")
            
            if 'step' in ds.coords:
                steps = ds.step.values
                print(f"予報ステップ数: {len(steps)}")
                print(f"予報ステップ: {steps[:3]}... (最初の3つ)")
            
            # 変数情報
            print(f"変数:")
            for var_name in ds.data_vars:
                var = ds[var_name]
                print(f"  {var_name}: shape={var.shape}, dtype={var.dtype}")
                
                # 気温の場合、東京付近のデータを確認
                if var_name == 't' and 'latitude' in ds.coords:
                    # 東京に最も近い格子点を探す
                    distances = np.sqrt((lats - 35.69)**2 + (lons - 139.69)**2)
                    min_idx = np.unravel_index(np.argmin(distances), distances.shape)
                    
                    print(f"    東京最寄り格子点: lat={lats[min_idx]:.2f}, lon={lons[min_idx]:.2f}")
                    
                    if 'step' in ds.coords:
                        tokyo_temps = var.values[:, min_idx[0], min_idx[1]] - 273.15
                        print(f"    東京の気温 (最初の3ステップ): {tokyo_temps[:3]}")
                        
                        # 時系列データを作成
                        base_time = ds.time.values
                        times = [base_time + step for step in steps]
                        print(f"    時刻 (最初の3つ):")
                        for i in range(min(3, len(times))):
                            print(f"      {times[i]}: {tokyo_temps[i]:.1f}°C")
            
            print()
        
        for ds in datasets:
            ds.close()

if __name__ == "__main__":
    check_data()
