import os
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

BASE_URL = "https://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/original/"
DATA_DIR = "data"

def get_soup(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_latest_link(url, pattern):
    soup = get_soup(url)
    if not soup:
        return None
    
    links = []
    for a in soup.find_all('a'):
        href = a.get('href')
        if href and re.match(pattern, href):
            links.append(href)
    
    if not links:
        return None
    
    # Sort to find the latest (assuming lexicographical order works for dates)
    links.sort()
    return links[-1]

def download_file(url, filepath):
    if os.path.exists(filepath):
        print(f"File already exists: {filepath}")
        return

    print(f"Downloading {url} to {filepath}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("Download complete.")
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)

def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    print("Finding latest data...")
    
    # 1. Find latest Year
    latest_year_link = get_latest_link(BASE_URL, r"^\d{4}/$")
    if not latest_year_link:
        print("Could not find year directory.")
        return
    print(f"Latest year: {latest_year_link}")

    # 2. Find latest Month
    year_url = BASE_URL + latest_year_link
    latest_month_link = get_latest_link(year_url, r"^\d{2}/$")
    if not latest_month_link:
        print("Could not find month directory.")
        return
    print(f"Latest month: {latest_month_link}")

    # 3. Find latest Day
    month_url = year_url + latest_month_link
    latest_day_link = get_latest_link(month_url, r"^\d{2}/$")
    if not latest_day_link:
        print("Could not find day directory.")
        return
    print(f"Latest day: {latest_day_link}")

    # 4. Find latest MSM files
    day_url = month_url + latest_day_link
    soup = get_soup(day_url)
    if not soup:
        return

    # Pattern for MSM Surface files
    # Z__C_RJTD_20251127150000_MSM_GPV_Rjp_Lsurf_FH00-15_grib2.bin
    # We want to group by the timestamp (e.g., 20251127150000)
    msm_pattern = re.compile(r"Z__C_RJTD_(\d{14})_MSM_GPV_Rjp_Lsurf_FH\d{2}-\d{2}_grib2\.bin")
    
    timestamps = set()
    files_map = {}

    for a in soup.find_all('a'):
        href = a.get('href')
        if href:
            match = msm_pattern.match(href)
            if match:
                timestamp = match.group(1)
                timestamps.add(timestamp)
                if timestamp not in files_map:
                    files_map[timestamp] = []
                files_map[timestamp].append(href)
    
    if not timestamps:
        print("No MSM Surface files found.")
        return

    latest_timestamp = sorted(list(timestamps))[-1]
    print(f"Latest timestamp found: {latest_timestamp}")
    
    target_files = files_map[latest_timestamp]
    print(f"Found {len(target_files)} files for this timestamp.")

    for filename in target_files:
        file_url = day_url + filename
        local_path = os.path.join(DATA_DIR, filename)
        download_file(file_url, local_path)

if __name__ == "__main__":
    main()
