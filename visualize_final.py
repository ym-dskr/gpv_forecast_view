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
    """Create premium custom colormaps"""
    # Precipitation: Transparent -> Blue -> Purple -> Red
    precip_colors = [
        (0.0, (0, 0, 0, 0)),
        (0.05, '#00aaff'),
        (0.2, '#0044ff'),
        (0.5, '#aa00ff'),
        (1.0, '#ff0000')
    ]
    precip_cmap = LinearSegmentedColormap.from_list('modern_precip', precip_colors)

    # Wind: Dark -> Blue -> Cyan -> Yellow -> Magenta
    wind_colors = [
        (0.0, '#1a1a2e'),
        (0.2, '#16213e'),
        (0.4, '#0f3460'),
        (0.6, '#533483'),
        (0.8, '#e94560'),
        (1.0, '#fffb00')
    ]
    wind_cmap = LinearSegmentedColormap.from_list('modern_wind', wind_colors)
    
    return {'Precipitation': precip_cmap, 'Wind Speed': wind_cmap}

CUSTOM_CMAPS = create_custom_colormaps()

def get_variable_config():
    """Get configuration for variables"""
    return {
        'Temperature': {
            'source_names': ['t', '2t', 't2m'],
            'cmap': 'magma',
            'vmin': -10, 'vmax': 35,
            'unit': '°C',
            'convert': lambda x: x - 273.15 if np.nanmean(x) > 200 else x
        },
        'Pressure': {
            'source_names': ['prmsl', 'msl', 'sp'],
            'cmap': 'viridis',
            'vmin': 990, 'vmax': 1025,
            'unit': 'hPa',
            'convert': lambda x: x / 100.0 if np.nanmean(x) > 80000 else x
        },
        'Humidity': {
            'source_names': ['r', '2r', 'r2'],
            'cmap': 'GnBu',
            'vmin': 40, 'vmax': 100,
            'unit': '%'
        },
        'Precipitation': {
            'source_names': ['precipitation', 'tp', 'apcp', 'unknown'],
            'cmap': CUSTOM_CMAPS['Precipitation'],
            'vmin': 0.1, 'vmax': 50,
            'unit': 'mm/h',
            'is_accum': True
        },
        'Wind Speed': {
            'source_names': ['wind_speed'],
            'cmap': CUSTOM_CMAPS['Wind Speed'],
            'vmin': 0, 'vmax': 25,
            'unit': 'm/s'
        }
    }

def render_frame_task(task_data):
    """
    Worker function to render a single frame.
    Running in a separate process ensures memory is fully released on exit.
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
        
        return output_path
        
    except Exception as e:
        print(f"Error in worker for frame {frame_idx}: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
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
                                                
                                            base_var = ds[s_name].sel(step=step)
                                            values = base_var.values.copy()
                                            found_ds = ds
                                            found_var_name = s_name
                                            break
                                        except Exception:
                                            continue
                                if found_ds:
                                    break
                            
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
    else:
        print("No frames generated.")

if __name__ == "__main__":
    # Fix for Windows multiprocessing
    multiprocessing.freeze_support()
    main()