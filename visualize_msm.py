import os
import glob
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
import cfgrib
import imageio
import gc

DATA_DIR = "data"
OUTPUT_DIR = "output"
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames")

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    if not os.path.exists(FRAMES_DIR):
        os.makedirs(FRAMES_DIR)

    # Find all bin files
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.bin")))
    if not files:
        print("No data files found.")
        return

    print(f"Found files: {files}")

    # Variable configuration
    variables = {
        'Temperature': {'names': ['2t', 't2m', 't'], 'cmap': 'coolwarm', 'unit': 'K', 'vmin': -30, 'vmax': 35}, 
        'Precipitation': {'names': ['precipitation', 'tp', 'apcp'], 'cmap': 'Blues', 'unit': 'mm', 'vmin': 0, 'vmax': 20}, 
        'Humidity': {'names': ['2r', 'r2', 'r'], 'cmap': 'Greens', 'unit': '%', 'vmin': 0, 'vmax': 100}, 
        'Pressure': {'names': ['prmsl', 'msl', 'sp'], 'cmap': 'viridis', 'unit': 'Pa', 'vmin': 980, 'vmax': 1030},
        'Wind Speed': {'names': ['wind_speed'], 'cmap': 'plasma', 'unit': 'm/s', 'vmin': 0, 'vmax': 30}
    }


    frame_files = []
    frame_counter = 0

    # Process each file separately to avoid memory issues
    for file_idx, f in enumerate(files):
        print(f"\n{'='*60}")
        print(f"Processing file {file_idx+1}/{len(files)}: {os.path.basename(f)}")
        print('='*60)
        
        try:
            # Open datasets from this file
            dss = cfgrib.open_datasets(f)
            print(f"Found {len(dss)} datasets in file")
            
            # Merge datasets from this file
            ds_file = xr.Dataset()
            precip_var = None  # 降水量用の変数
            
            for ds in dss:
                for var in ds.data_vars:
                    # unknown 変数の場合、stepType を確認
                    if var == 'unknown':
                        step_type = ds[var].attrs.get('GRIB_stepType', '')
                        if step_type == 'accum':
                            # 積算値 = 降水量
                            if 'precipitation' not in ds_file:
                                ds_file['precipitation'] = ds[var]
                                precip_var = 'precipitation'
                        elif step_type == 'instant':
                            # 瞬間値 = 全雲量
                            if 'total_cloud_cover' not in ds_file:
                                ds_file['total_cloud_cover'] = ds[var]
                    elif var not in ds_file:
                        ds_file[var] = ds[var]
            
            # Calculate wind speed if u10 and v10 are available
            if 'u10' in ds_file and 'v10' in ds_file:
                print("Calculating wind speed from u10 and v10...")
                ds_file['wind_speed'] = np.sqrt(ds_file['u10']**2 + ds_file['v10']**2)
            elif 'u' in ds_file and 'v' in ds_file:
                print("Calculating wind speed from u and v...")
                ds_file['wind_speed'] = np.sqrt(ds_file['u']**2 + ds_file['v']**2)
            
            # Get steps for this file
            if 'step' in ds_file.coords:
                steps = ds_file.step.values
                print(f"Available steps in this file: {len(steps)}")
            else:
                print("No step dimension found in this file")
                for ds in dss:
                    ds.close()
                continue

            # Find which variables are available
            ds_vars = list(ds_file.data_vars)
            print(f"Dataset variables: {ds_vars}")
            
            available_vars = {}
            for label, info in variables.items():
                var_name = None
                for name in info['names']:
                    if name in ds_file:
                        var_name = name
                        break
                if var_name:
                    available_vars[label] = (var_name, info)
            
            print(f"Available variables for plotting: {list(available_vars.keys())}")

            # Loop through all time steps in this file
            for i, step in enumerate(steps):
                print(f"  Processing step {i+1}/{len(steps)}: {step}")
                
                try:
                    ds_slice = ds_file.sel(step=step)
                    valid_time = ds_slice.valid_time.values
                    
                    # Create figure with subplots (2 rows x 3 columns)
                    # Reduced DPI for lower resolution
                    fig = plt.figure(figsize=(15, 10))
                    
                    plot_idx = 1
                    for label, (var_name, info) in available_vars.items():
                        ax = fig.add_subplot(2, 3, plot_idx, projection=ccrs.PlateCarree())
                        # Fixed extent for all frames
                        ax.set_extent([120, 150, 20, 50], crs=ccrs.PlateCarree())
                        
                        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
                        ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5)
                        
                        # Get data
                        data = ds_slice[var_name]
                        val = data.values
                        
                        # Convert units if necessary
                        if label == 'Temperature' and info['unit'] == 'K':
                            if np.nanmean(val) > 200:
                                val = val - 273.15
                            unit_label = '°C'
                        elif label == 'Pressure' and info['unit'] == 'Pa':
                            if np.nanmean(val) > 80000:
                                val = val / 100.0
                            unit_label = 'hPa'
                        else:
                            unit_label = info['unit']
                        
                        # Use fixed vmin/vmax
                        vmin = info['vmin']
                        vmax = info['vmax']
                        
                        # Plot with fixed color range
                        im = ax.pcolormesh(data.longitude, data.latitude, val, 
                                           transform=ccrs.PlateCarree(), 
                                           cmap=info['cmap'],
                                           vmin=vmin, vmax=vmax)
                        
                        cbar = plt.colorbar(im, ax=ax, label=f"{label} [{unit_label}]", 
                                          shrink=0.8, pad=0.05)
                        cbar.ax.tick_params(labelsize=8)
                        ax.set_title(f"{label}", fontsize=11, fontweight='bold')
                        
                        plot_idx += 1
                    
                    # Overall title
                    fig.suptitle(f"MSM Forecast - Valid Time: {valid_time}", 
                                fontsize=14, fontweight='bold')
                    
                    # Save frame with lower DPI
                    frame_path = os.path.join(FRAMES_DIR, f"forecast_{frame_counter:03d}.png")
                    plt.tight_layout()
                    plt.savefig(frame_path, dpi=80, bbox_inches='tight')
                    plt.close(fig)
                    frame_files.append(frame_path)
                    print(f"    Saved {os.path.basename(frame_path)}")
                    frame_counter += 1
                    
                    # Clear memory after each frame
                    gc.collect()
                    
                except Exception as e:
                    print(f"    Error processing step {i}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Close datasets to free memory
            for ds in dss:
                ds.close()
            del ds_file
            gc.collect()
            
        except Exception as e:
            print(f"Error processing file {f}: {e}")
            import traceback
            traceback.print_exc()
            gc.collect()
            continue
    
    # Create animation
    if frame_files:
        print(f"\n{'='*60}")
        print("Creating animation...")
        print('='*60)
        try:
            images = []
            for i, frame_path in enumerate(frame_files):
                print(f"  Reading frame {i+1}/{len(frame_files)}: {os.path.basename(frame_path)}")
                images.append(imageio.v2.imread(frame_path))
            
            animation_path = os.path.join(OUTPUT_DIR, "forecast_animation.gif")
            print(f"Saving animation to {animation_path}...")
            imageio.mimsave(animation_path, images, duration=0.5, loop=0)
            
            size_mb = os.path.getsize(animation_path) / (1024 * 1024)
            print(f"Animation saved successfully!")
            print(f"Total frames: {len(frame_files)}")
            print(f"File size: {size_mb:.2f} MB")
        except Exception as e:
            print(f"Error creating animation: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\nNo frames were created.")
    
    print("\n" + "="*60)
    print("Visualization complete!")
    print("="*60)

if __name__ == "__main__":
    main()
