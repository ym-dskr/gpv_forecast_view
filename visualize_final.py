#!/usr/bin/env python3
"""
Modernized MSM Visualization Script
- Multiprocessing for memory safety (Matplotlib isolation)
- Modern dark-themed aesthetics
- Correct precipitation accumulation handling
"""
import os
import glob
import gc
import time
import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import cfgrib
import imageio
import xarray as xr
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import LinearSegmentedColormap

# Configuration
DATA_DIR = "data"
OUTPUT_DIR = "output"
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames")
MAX_WORKERS = max(1, multiprocessing.cpu_count() - 1)

# --- Modern Style Configuration ---
STYLE_CONFIG = {
    'facecolor': '#1a1a1a',
    'text_color': '#e0e0e0',
    'grid_color': '#404040',
    'coast_color': '#808080',
    'border_color': '#606060',
    'font_family': 'sans-serif',
}

def create_custom_colormaps():
    """標準的な気象予報用カラーマップを作成する。

    気象データ可視化用の専用カラーマップを生成する。
    降水量用にはJMA（気象庁）スタイルの透明→青→黄→赤→紫のグラデーション、
    風速用には標準的な青→緑→黄→赤のグラデーションを提供する。

    Returns:
        dict[str, LinearSegmentedColormap]: カラーマップ辞書
            'Precipitation': 降水量用カラーマップ（透明→青→黄→赤→紫）
            'Wind Speed': 風速用カラーマップ（青→緑→黄→赤）

    Note:
        降水量カラーマップは0mm/hで透明、強い降水で紫色になるよう設計。
        風速カラーマップは穏やかな風で青、強風で赤になるよう設計。
    """
    # Precipitation: JMA-style (Transparent -> Blue -> Yellow -> Red -> Purple)
    precip_colors = [
        (0.0, (1, 1, 1, 0)),      # Transparent for 0
        (0.02, '#c0e0ff'),        # Very Light Blue
        (0.1, '#4080ff'),         # Blue
        (0.3, '#40ff40'),         # Green
        (0.5, '#ffff40'),         # Yellow
        (0.7, '#ff8040'),         # Orange
        (0.85, '#ff4040'),        # Red
        (1.0, '#ff40ff')          # Magenta/Purple
    ]
    precip_cmap = LinearSegmentedColormap.from_list('weather_precip', precip_colors)

    # Wind: Standard Blue -> Green -> Yellow -> Red
    wind_colors = [
        (0.0, '#4040ff'),         # Blue (Calm)
        (0.3, '#40ff40'),         # Green
        (0.6, '#ffff40'),         # Yellow
        (0.85, '#ff8040'),        # Orange
        (1.0, '#ff4040')          # Red (Strong)
    ]
    wind_cmap = LinearSegmentedColormap.from_list('weather_wind', wind_colors)
    
    return {'Precipitation': precip_cmap, 'Wind Speed': wind_cmap}

CUSTOM_CMAPS = create_custom_colormaps()

def get_variable_config():
    """気象変数の設定情報を取得する。

    各気象変数（気温、気圧、湿度、降水量、風速、雲量）に対する描画設定を
    提供する。ソース変数名、カラーマップ、値域、単位、変換関数などを含む。

    Returns:
        dict[str, dict]: 変数設定辞書。各キーは表示名、値は以下を含む辞書:
            source_names (list[str]): GRIBファイル内での変数名候補
            cmap (str|LinearSegmentedColormap): カラーマップ
            vmin (float): 最小表示値
            vmax (float): 最大表示値
            unit (str): 表示単位
            convert (callable, optional): 単位変換関数
            is_accum (bool, optional): 累積変数フラグ
            required_stepType (str, optional): 必須ステップタイプ
            is_cloud (bool, optional): 雲量変数フラグ

    Note:
        累積変数（降水量）は前ステップとの差分を計算。
        雲量は複数層の最大値を使用。
        温度・気圧は自動的に単位変換される。
    """
    return {
        'Temperature': {
            'source_names': ['t', '2t', 't2m'],
            'cmap': 'RdYlBu_r',  # Standard: Blue (Cold) -> Yellow -> Red (Hot)
            'vmin': -10, 'vmax': 35,
            'unit': '°C',
            'convert': lambda x: x - 273.15 if np.nanmean(x) > 200 else x
        },
        'Pressure': {
            'source_names': ['prmsl', 'msl', 'sp'],
            'cmap': 'RdYlGn_r',  # Red (Low) -> Yellow -> Green (High)
            'vmin': 990, 'vmax': 1025,
            'unit': 'hPa',
            'convert': lambda x: x / 100.0 if np.nanmean(x) > 80000 else x
        },
        'Humidity': {
            'source_names': ['r', '2r', 'r2'],
            'cmap': 'YlGnBu',  # Yellow (Dry) -> Green -> Blue (Wet)
            'vmin': 40, 'vmax': 100,
            'unit': '%'
        },
        'Precipitation': {
            'source_names': ['precipitation', 'tp', 'apcp', 'unknown'],
            'cmap': CUSTOM_CMAPS['Precipitation'],
            'vmin': 0.0, 'vmax': 50,
            'unit': 'mm/h',
            'is_accum': True,
            'required_stepType': 'accum'
        },
        'Wind Speed': {
            'source_names': ['wind_speed'],
            'cmap': CUSTOM_CMAPS['Wind Speed'],
            'vmin': 0, 'vmax': 25,
            'unit': 'm/s'
        },
        'Cloud Cover': {
            'source_names': ['tcc', 'lcc', 'mcc', 'hcc'],
            'cmap': 'Greys_r',  # Black (Clear) -> White (Cloudy)
            'vmin': 0, 'vmax': 100,
            'unit': '%',
            'is_cloud': True  # Special flag for cloud combination logic
        }
    }

def render_frame_task(task_data):
    """単一フレームを描画するワーカー関数。

    マルチプロセッシング環境で実行され、1つの予報フレームを生成する。
    別プロセスで実行することで、Matplotlibのメモリリークを防ぎ、
    大量のフレーム生成時の安定性を確保する。

    Args:
        task_data (tuple): フレーム描画に必要なデータのタプル
            frame_idx (int): フレーム番号
            plot_data (dict): 描画データ（変数名→データ辞書）
            valid_time_str (str): 有効時刻文字列
            output_path (str): 出力PNG画像パス

    Returns:
        str|None: 成功時は出力ファイルパス、失敗時はNone

    Note:
        - プロセス内でMatplotlib環境を独立設定
        - 日本域の地図投影でCartopy使用
        - ダークテーマの現代的なデザイン適用
        - メタデータJSONファイルも併せて生成
    """
    try:
        frame_idx, plot_data, valid_time_str, output_path = task_data
        
        # Setup Matplotlib for this process
        matplotlib.use('Agg')
        plt.style.use('dark_background')
        
        num_vars = len(plot_data)
        if num_vars == 0:
            return None

        # Layout
        cols = min(2, num_vars)
        rows = (num_vars + cols - 1) // cols
        
        fig = plt.figure(figsize=(16, 9 * rows / 2), dpi=100)
        fig.patch.set_facecolor(STYLE_CONFIG['facecolor'])
        
        # Create subplots
        axes = []
        for i in range(num_vars):
            ax = fig.add_subplot(rows, cols, i + 1, projection=ccrs.PlateCarree())
            axes.append(ax)
            
        # Plot each variable
        for idx, (var_name, data_info) in enumerate(plot_data.items()):
            ax = axes[idx]
            values = data_info['values']
            lons = data_info['lons']
            lats = data_info['lats']
            config = data_info['config']
            
            # Map extent (Japan)
            ax.set_extent([128, 148, 30, 46], crs=ccrs.PlateCarree())
            
            # Plot data
            cmap = config.get('cmap', 'viridis')
            if isinstance(cmap, str) and cmap in CUSTOM_CMAPS:
                cmap = CUSTOM_CMAPS[cmap]
                
            im = ax.pcolormesh(
                lons, lats, values,
                transform=ccrs.PlateCarree(),
                cmap=cmap,
                vmin=config['vmin'],
                vmax=config['vmax'],
                shading='auto'
            )
            
            # Add features
            ax.add_feature(cfeature.COASTLINE, edgecolor=STYLE_CONFIG['coast_color'], linewidth=0.8)
            ax.add_feature(cfeature.BORDERS, edgecolor=STYLE_CONFIG['border_color'], linewidth=0.5, linestyle=':')
            
            # Styling
            ax.set_title(var_name, color=STYLE_CONFIG['text_color'], fontsize=14, pad=10, fontweight='bold')
            
            # Colorbar
            cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.03)
            cbar.set_label(f"{var_name} [{config['unit']}]", color=STYLE_CONFIG['text_color'])
            cbar.ax.yaxis.set_tick_params(color=STYLE_CONFIG['text_color'])
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color=STYLE_CONFIG['text_color'])
            
            # Gridlines
            gl = ax.gridlines(draw_labels=True, linewidth=0.5, color=STYLE_CONFIG['grid_color'], alpha=0.5, linestyle='--')
            gl.top_labels = False
            gl.right_labels = False
            gl.xlabel_style = {'color': STYLE_CONFIG['text_color']}
            gl.ylabel_style = {'color': STYLE_CONFIG['text_color']}

        # Global Title
        plt.suptitle(f"MSM Forecast | {valid_time_str}", color=STYLE_CONFIG['text_color'], fontsize=18, y=0.98)
        
        # Timestamp
        plt.figtext(0.98, 0.02, f"Generated: {time.strftime('%Y-%m-%d %H:%M')}", 
                   ha='right', color='#666666', fontsize=8)

        plt.tight_layout()
        plt.savefig(output_path, dpi=100, facecolor=STYLE_CONFIG['facecolor'], bbox_inches='tight')
        plt.close(fig)
        
        # Save metadata for this frame
        metadata = {
            'frame_index': frame_idx,
            'valid_time': valid_time_str,
            'variables': list(plot_data.keys()),
            'image_path': os.path.basename(output_path)
        }
        
        metadata_path = output_path.replace('.png', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return output_path
        
    except Exception as e:
        print(f"Error in worker for frame {frame_idx}: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """メインの可視化処理を実行する。

    MSM GPVデータファイルを読み込み、マルチプロセッシングで気象予報図を生成する。
    GIFアニメーション、インタラクティブビューアー、地図ビューアーも併せて作成。

    処理フロー:
        1. dataディレクトリからGRIBファイル検索
        2. 各ファイルから気象変数データ抽出
        3. マルチプロセッシングで並列フレーム生成
        4. GIFアニメーション作成
        5. インタラクティブHTMLビューアー生成
        6. 官署データによる地図ビューアー生成

    Note:
        - CPU数-1のワーカープロセス使用
        - メモリ効率のためプロセス当たり1タスク制限
        - 累積降水量は前ステップとの差分計算
        - エラー時も可能な限り処理継続
    """
    print("=== Modern MSM Visualizer ===")
    print(f"Workers: {MAX_WORKERS}")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FRAMES_DIR, exist_ok=True)
    
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.bin")))
    if not files:
        print("No files found!")
        return

    var_configs = get_variable_config()
    all_tasks = []
    frame_counter = 0
    
    # Track previous values for accumulation calculation
    # Key: (file_path, var_name) -> numpy array of previous step
    
    for file_path in files:
        print(f"\nScanning: {os.path.basename(file_path)}")
        
        try:
            # Use open_datasets to handle mixed levels/stepTypes (e.g. 10m wind vs 1.5m temp)
            datasets = cfgrib.open_datasets(
                file_path, 
                backend_kwargs={'read_keys': ['shortName', 'typeOfLevel', 'level', 'stepRange']}
            )
            
            if not datasets:
                print("  No datasets found in file.")
                continue

            # Find all unique steps across all datasets
            all_steps = set()
            for ds in datasets:
                if 'step' in ds.coords:
                    all_steps.update(ds.step.values)
            
            if not all_steps:
                steps = [0]
            else:
                steps = sorted(list(all_steps))
                
            print(f"  Found {len(steps)} steps")
            
            # Accumulation state for this file
            prev_accum_values = {} 
            
            for step in steps:
                plot_data = {}
                valid_time = None
                
                # Extract data for this step
                for disp_name, cfg in var_configs.items():
                    try:
                        # Helper to find variable in any dataset
                        found_ds = None
                        found_var_name = None
                        
                        # Handle Wind Speed (Vector calc)
                        if disp_name == 'Wind Speed':
                            # Try to find u/v pair
                            u_name = None
                            v_name = None
                            
                            # Check each dataset for both components
                            for ds in datasets:
                                # Check for u10/v10
                                if 'u10' in ds.data_vars and 'v10' in ds.data_vars:
                                    found_ds = ds
                                    u_name, v_name = 'u10', 'v10'
                                    break
                                # Check for u/v
                                elif 'u' in ds.data_vars and 'v' in ds.data_vars:
                                    found_ds = ds
                                    u_name, v_name = 'u', 'v'
                                    break
                            
                            if found_ds is not None:
                                try:
                                    u_var = found_ds[u_name].sel(step=step)
                                    v_var = found_ds[v_name].sel(step=step)
                                    values = np.sqrt(u_var.values**2 + v_var.values**2)
                                    base_var = u_var
                                except KeyError:
                                    # Step might not exist in this dataset
                                    continue
                            else:
                                continue
                        
                        else:
                            # Standard variables
                            for ds in datasets:
                                for s_name in cfg['source_names']:
                                    if s_name in ds.data_vars:
                                        try:
                                            # Check if step exists
                                            if 'step' in ds.coords and step not in ds.step.values:
                                                continue
                                            
                                            # Check required stepType (e.g. accum for precip)
                                            if 'required_stepType' in cfg:
                                                var_step_type = ds[s_name].attrs.get('GRIB_stepType', '')
                                                if var_step_type != cfg['required_stepType']:
                                                    continue

                                            base_var = ds[s_name].sel(step=step)
                                            values = base_var.values.copy()
                                            found_ds = ds
                                            found_var_name = s_name
                                            break
                                        except Exception:
                                            continue
                                if found_ds:
                                    break
                            
                            # Special handling for Cloud Cover: combine lcc/mcc/hcc if tcc not found
                            if not found_ds and cfg.get('is_cloud', False):
                                cloud_layers = []
                                for ds in datasets:
                                    for cloud_var in ['lcc', 'mcc', 'hcc']:
                                        if cloud_var in ds.data_vars:
                                            try:
                                                if 'step' in ds.coords and step in ds.step.values:
                                                    cloud_data = ds[cloud_var].sel(step=step)
                                                    cloud_layers.append(cloud_data.values)
                                            except Exception:
                                                pass
                                
                                if cloud_layers:
                                    # Take maximum of all cloud layers
                                    values = np.maximum.reduce(cloud_layers)
                                    base_var = cloud_data  # Use last one for coordinates
                                    found_ds = ds
                                    found_var_name = 'cloud_combined'
                            
                            if not found_ds:
                                continue

                        # Handle Accumulation (Precipitation)
                        if cfg.get('is_accum', False):
                            current_val = values.copy()
                            if disp_name in prev_accum_values:
                                # Calculate diff
                                diff = current_val - prev_accum_values[disp_name]
                                # Fix negative values (reset or artifacts)
                                diff[diff < 0] = 0
                                values = diff
                            else:
                                # First step: plot zeros to maintain layout
                                values = np.zeros_like(current_val)
                            
                            # Update previous
                            prev_accum_values[disp_name] = current_val

                        # Unit Conversion
                        if 'convert' in cfg:
                            values = cfg['convert'](values)

                        # Store for plotting
                        # Create a clean config for the worker (remove non-picklable functions)
                        worker_cfg = cfg.copy()
                        if 'convert' in worker_cfg:
                            del worker_cfg['convert']
                            
                        plot_data[disp_name] = {
                            'values': values,
                            'lons': base_var.longitude.values,
                            'lats': base_var.latitude.values,
                            'config': worker_cfg
                        }
                        
                        if valid_time is None and hasattr(base_var, 'valid_time'):
                            valid_time = str(base_var.valid_time.values).split('.')[0]
                            
                    except Exception as e:
                        # print(f"    Failed to extract {disp_name}: {e}")
                        pass

                if plot_data:
                    output_path = os.path.join(FRAMES_DIR, f"frame_{frame_counter:04d}.png")
                    all_tasks.append((frame_counter, plot_data, valid_time or f"Step {step}", output_path))
                    frame_counter += 1
            
            # Close all datasets
            for ds in datasets:
                ds.close()
            gc.collect()
            
        except Exception as e:
            print(f"  Error reading file: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nGenerating {len(all_tasks)} frames with {MAX_WORKERS} workers...")
    
    # Process frames in parallel
    # maxtasksperchild=1 ensures worker process dies after 1 task, releasing ALL memory
    generated_frames = []
    with multiprocessing.Pool(processes=MAX_WORKERS, maxtasksperchild=1) as pool:
        for i, result in enumerate(pool.imap(render_frame_task, all_tasks)):
            if result:
                generated_frames.append(result)
            if i % 5 == 0:
                print(f"  Progress: {i+1}/{len(all_tasks)}")

    # Create Animation
    if generated_frames:
        print("\nCreating GIF...")
        gif_path = os.path.join(OUTPUT_DIR, "msm_forecast_modern.gif")
        with imageio.get_writer(gif_path, mode='I', duration=0.5, loop=0) as writer:
            for frame_path in generated_frames:
                image = imageio.v2.imread(frame_path)
                writer.append_data(image)
        print(f"Done! Saved to: {gif_path}")
        
        # Generate Interactive Viewer
        print("\nGenerating interactive viewer...")
        generate_interactive_viewer(generated_frames)
        
        # Generate Station Timeseries and Map Viewer
        print("\nGenerating station timeseries and map viewer...")
        try:
            import subprocess
            subprocess.run(["python", "station_timeseries.py"], check=True)
            subprocess.run(["python", "generate_map_viewer.py"], check=True)
        except Exception as e:
            print(f"Note: Could not generate station analysis: {e}")
            print("You can run 'python station_timeseries.py' and 'python generate_map_viewer.py' manually.")
    else:
        print("No frames generated.")

def generate_interactive_viewer(frame_paths):
    """予報フレーム用のインタラクティブHTMLビューアーを生成する。

    生成されたPNGフレーム群からWebブラウザで操作可能なビューアーを作成する。
    ユーザーはスライダーやボタンでフレーム間を移動でき、時刻や変数情報も表示される。

    Args:
        frame_paths (list[str]): 生成されたPNGフレームのパス一覧

    Note:
        - viewer_template.htmlテンプレートが必要
        - フレームメタデータJSONから時刻・変数情報取得
        - 出力はoutput/interactive_viewer.htmlに保存
        - JavaScriptによるクライアントサイド制御
    """
    
    # Collect metadata from all frames
    frames_info = []
    for frame_path in frame_paths:
        metadata_path = frame_path.replace('.png', '_metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                frames_info.append(metadata)
    
    if not frames_info:
        print("No frame metadata found for interactive viewer.")
        return
    
    # Load HTML template
    template_path = os.path.join(os.path.dirname(__file__), "viewer_template.html")
    if not os.path.exists(template_path):
        print(f"Template file not found: {template_path}")
        return
    
    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()
    
    # Prepare data for template
    first_variables_html = ' '.join([f'<span class="variable-tag">{var}</span>' 
                                      for var in frames_info[0]['variables']])
    
    # Replace placeholders
    html_content = html_template.replace('{{FIRST_IMAGE}}', frames_info[0]['image_path'])
    html_content = html_content.replace('{{FIRST_TIME}}', frames_info[0]['valid_time'])
    html_content = html_content.replace('{{MAX_INDEX}}', str(len(frames_info) - 1))
    html_content = html_content.replace('{{TOTAL_FRAMES}}', str(len(frames_info)))
    html_content = html_content.replace('{{FIRST_VARIABLES}}', first_variables_html)
    html_content = html_content.replace('{{FRAMES_DATA}}', json.dumps(frames_info, ensure_ascii=False))
    
    # Save HTML file
    html_path = os.path.join(OUTPUT_DIR, "interactive_viewer.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Interactive viewer saved to: {html_path}")
    print("Open this file in a web browser to view the interactive forecast.")


if __name__ == "__main__":
    # Fix for Windows multiprocessing
    multiprocessing.freeze_support()
    main()