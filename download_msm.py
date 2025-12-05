"""GPV MSMデータダウンローダー

このモジュールは京都大学RISHデータベースから最新のMSM（メソスケールモデル）
GPV（格子点値）データをダウンロードします。既存のローカルデータと比較して、
新しいデータがある場合のみダウンロードを実行します。古いデータファイルは
自動的にクリーンアップされます。

ダウンロードされたデータは'data'ディレクトリに保存され、メタデータは
'data/metadata.json'で管理されます。

主な機能:
    - 最新のMSM GPVデータの自動検索
    - 既存データとの比較による差分ダウンロード
    - 古いデータファイルの自動削除
    - タイムスタンプ管理によるデータ更新追跡

使用例:
    python download_msm.py
"""

import os
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

BASE_URL = "https://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/original/"
DATA_DIR = "data"
METADATA_FILE = os.path.join(DATA_DIR, "metadata.json")

def get_soup(url):
    """URLからHTMLコンテンツを取得してパースする
    
    指定されたURLにHTTPリクエストを送信し、レスポンスをBeautifulSoupで
    パースして返す。エラーが発生した場合はNoneを返す。
    
    Args:
        url (str): HTMLコンテンツを取得するURL
        
    Returns:
        BeautifulSoup: パースされたHTMLコンテンツ、エラー時はNone
        
    Raises:
        None: 例外はキャッチされ、エラーメッセージを出力してNoneを返す
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_latest_link(url, pattern):
    """ディレクトリリストからパターンに一致する最新のリンクを検索
    
    指定されたURLをスクレイピングし、正規表現パターンに一致するリンクの中から
    辞書順で最後（最新）のものを返す。ディレクトリ構造が日付ベースの場合、
    これにより最新のディレクトリやファイルを取得できる。
    
    Args:
        url (str): スクレイピングするディレクトリリストのURL
        pattern (str): リンクのhrefと照合する正規表現パターン
        
    Returns:
        str: 最新の一致するリンクhref、見つからない場合はNone
        
    Note:
        辞書順ソートを使用しているため、YYYYMMDD形式などの
        日付ベースのディレクトリ名で正しく動作する。
    """
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

def get_existing_timestamp():
    """既存のGPVデータファイルのタイムスタンプを取得
    
    まずメタデータファイルを確認し、利用できない場合はファイル名を
    パースしてタイムスタンプを取得する。これにより、既存データの
    バージョンを特定できる。
    
    Returns:
        str: YYYYMMDDHHMM00形式のタイムスタンプ文字列、データがない場合はNone
        
    Note:
        メタデータファイルが優先され、存在しない場合のみファイル名から
        タイムスタンプを抽出する。
    """
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                metadata = json.load(f)
                return metadata.get('timestamp')
        except Exception as e:
            print(f"Error reading metadata: {e}")
    
    # メタデータファイルがない場合、ファイル名から取得
    if os.path.exists(DATA_DIR):
        msm_pattern = re.compile(r"Z__C_RJTD_(\d{14})_MSM_GPV_Rjp_Lsurf_FH\d{2}-\d{2}_grib2\.bin")
        for filename in os.listdir(DATA_DIR):
            match = msm_pattern.match(filename)
            if match:
                return match.group(1)
    
    return None

def clean_old_data(latest_timestamp):
    """最新のタイムスタンプと一致しないGPVデータファイルを削除
    
    dataディレクトリをスキャンし、指定された最新タイムスタンプと異なる
    タイムスタンプを持つMSM GPVファイルを全て削除する。これにより、
    ディスク容量を節約し、データの一貫性を保つ。
    
    Args:
        latest_timestamp (str): 保持するタイムスタンプ（形式: YYYYMMDDHHMM00）
        
    Note:
        削除されたファイル数を標準出力に表示する。
        削除対象はMSM Surface GPVファイルのみ。
    """
    if not os.path.exists(DATA_DIR):
        return
    
    msm_pattern = re.compile(r"Z__C_RJTD_(\d{14})_MSM_GPV_Rjp_Lsurf_FH\d{2}-\d{2}_grib2\.bin")
    deleted_count = 0
    
    for filename in os.listdir(DATA_DIR):
        match = msm_pattern.match(filename)
        if match:
            timestamp = match.group(1)
            if timestamp != latest_timestamp:
                filepath = os.path.join(DATA_DIR, filename)
                try:
                    os.remove(filepath)
                    print(f"Deleted old file: {filename}")
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting {filename}: {e}")
    
    if deleted_count > 0:
        print(f"Deleted {deleted_count} old file(s).")
    else:
        print("No old files to delete.")

def save_metadata(timestamp):
    """タイムスタンプメタデータをJSONファイルに保存
    
    現在のタイムスタンプとダウンロード日時を含むメタデータファイルを
    作成または更新する。これにより、次回実行時に既存データの
    バージョンを迅速に確認できる。
    
    Args:
        timestamp (str): 保存するデータのタイムスタンプ（形式: YYYYMMDDHHMM00）
        
    Note:
        メタデータにはタイムスタンプとダウンロード日時（ISO形式）が含まれる。
    """
    metadata = {
        'timestamp': timestamp,
        'download_date': datetime.now().isoformat()
    }
    
    try:
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"Metadata saved: {timestamp}")
    except Exception as e:
        print(f"Error saving metadata: {e}")

def download_file(url, filepath):
    """URLからローカルパスにファイルをダウンロード
    
    8KBチャンクのストリーミングモードでファイルをダウンロードする。
    ファイルが既に存在する場合はスキップ。エラー時は部分ファイルを削除。
    
    Args:
        url (str): ダウンロード元のURL
        filepath (str): 保存先のローカルパス
        
    Note:
        - ストリーミングダウンロードによりメモリ効率が良い
        - 既存ファイルは上書きせずスキップ
        - エラー時は不完全なファイルを自動削除
    """
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
    """最新のMSM GPVデータをダウンロードするメイン関数
    
    このモジュールの主要な処理を統括する関数。以下の手順で実行される:
    
    処理フロー:
        1. 既存データのタイムスタンプを確認
        2. サーバー上の最新データを検索（年/月/日のディレクトリ構造をナビゲート）
        3. タイムスタンプを比較し、新しいデータがある場合のみダウンロード
        4. 新しいデータをダウンロードする前に古いデータファイルをクリーンアップ
        5. 将来の参照用にメタデータを保存
    
    このモジュールはRISHデータベースのディレクトリ構造（年/月/日）を
    ナビゲートして最新のMSM Surface GPVファイルを見つける。
    
    Note:
        - データが既に最新の場合、ダウンロードはスキップされる
        - MSM Surface GPVファイル（Lsurf）のみを対象とする
        - 複数のファイル（予報時間範囲ごと）をダウンロード
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    print("=== GPV Data Downloader ===")
    
    # 既存のタイムスタンプを取得
    existing_timestamp = get_existing_timestamp()
    if existing_timestamp:
        print(f"Existing data timestamp: {existing_timestamp}")
    else:
        print("No existing data found.")
    
    print("\nFinding latest data...")
    
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
    print(f"\nLatest timestamp found: {latest_timestamp}")
    
    # 既存データと比較
    if existing_timestamp == latest_timestamp:
        print("Data is already up to date. No download needed.")
        return
    elif existing_timestamp:
        print(f"New data available! Updating from {existing_timestamp} to {latest_timestamp}")
        print("\nCleaning old data...")
        clean_old_data(latest_timestamp)
    else:
        print("Downloading new data...")
    
    target_files = files_map[latest_timestamp]
    print(f"\nDownloading {len(target_files)} files for timestamp {latest_timestamp}...")

    for filename in target_files:
        file_url = day_url + filename
        local_path = os.path.join(DATA_DIR, filename)
        download_file(file_url, local_path)
    
    # メタデータを保存
    save_metadata(latest_timestamp)
    print("\n=== Download Complete ===")

if __name__ == "__main__":
    main()
