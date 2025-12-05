# MSM GPV予報可視化システム

京都大学RISHデータベースから気象庁MSM（メソスケールモデル）GPVデータをダウンロードし、インタラクティブな気象予報図を生成するPythonシステムです。

## 🌟 主な機能

- **自動データダウンロード**: 最新のMSM GPVデータを自動取得
- **多変数可視化**: 気温、気圧、湿度、降水量、風速、雲量を統合表示
- **インタラクティブビューアー**: 複数の表示方式を提供
  - 🎬 **フレームビューアー**: スライダーで時系列予報を確認
  - 🗺️ **地図ビューアー**: 官署データの時系列グラフ表示
  - 📊 **GIFアニメーション**: 時間変化のアニメーション
- **モダンUI**: ダークテーマのレスポンシブデザイン
- **高性能処理**: マルチプロセッシングによる並列処理

## 📁 プロジェクト構造

```
gpv_forecast_view/
├── README.md                    # このファイル
├── download_msm.py              # MSMデータダウンローダー
├── visualize_final.py           # メイン可視化エンジン
├── create_frame_viewer.py       # フレームビューアー生成
├── run_frame_viewer.py          # フレームビューアー起動
├── generate_map_viewer.py       # 地図ビューアー生成
├── run_map_viewer.py            # 地図ビューアー起動
├── data/                        # ダウンロードしたGRIBファイル
│   ├── Z__C_RJTD_*.grib2.bin   # MSM GPVバイナリファイル
│   └── metadata.json            # ダウンロード履歴
└── output/                      # 生成された成果物
    ├── frames/                  # 予報図画像とメタデータ
    │   ├── frame_0000.png
    │   └── frame_0000_metadata.json
    ├── html/                    # Webビューアー
    │   ├── frame_viewer.html
    │   └── map_viewer.html
    ├── msm_forecast_modern.gif  # アニメーション
    ├── station_data.json        # 官署データ
    └── station_timeseries.png   # 時系列グラフ
```

## 🛠️ 必要な環境

### Python依存関係

```bash
pip install numpy matplotlib cartopy xarray cfgrib imageio beautifulsoup4 requests
```

### 主要ライブラリ
- **numpy**: 数値計算
- **matplotlib**: プロット作成
- **cartopy**: 地図投影
- **xarray**: 多次元データ処理
- **cfgrib**: GRIBファイル読み込み
- **imageio**: GIF生成
- **beautifulsoup4**: HTMLパース（ダウンロード用）
- **requests**: HTTP通信

## 🚀 クイックスタート

### 1. データダウンロード
```bash
python download_msm.py
```
最新のMSM GPVデータを京都大学RISHから自動取得します。

### 2. 可視化実行
```bash
python visualize_final.py
```
予報図の生成とビューアーを一括作成します。

### 3. ビューアー起動

#### 📱 フレームビューアー
```bash
python run_frame_viewer.py
```
- **URL**: http://localhost:8001/html/frame_viewer.html
- **機能**: スライダーで予報時刻を選択して画像確認

#### 🗺️ 地図ビューアー
```bash
python run_map_viewer.py
```
- **URL**: http://localhost:8000/map_viewer.html  
- **機能**: 官署マーカークリックで時系列グラフ表示

## 📋 スクリプト詳細

### `download_msm.py`
**MSMデータダウンローダー**
```python
"""GPV MSMデータダウンローダー

このモジュールは京都大学RISHデータベースから最新のMSM（メソスケールモデル）
GPV（格子点値）データをダウンロードします。
"""
```
- 最新データの自動検索
- 差分ダウンロード（新しいデータのみ）
- 古いファイルの自動削除
- タイムスタンプ管理

### `visualize_final.py`
**メイン可視化エンジン**
```python
"""Modernized MSM Visualization Script
- Multiprocessing for memory safety (Matplotlib isolation)
- Modern dark-themed aesthetics
- Correct precipitation accumulation handling
"""
```
- マルチプロセッシング並列処理
- 6変数の統合可視化
- 累積降水量の差分計算
- GIF・ビューアー自動生成

### `create_frame_viewer.py`
**フレームビューアー生成**
```python
"""フレームビューアー生成スクリプト

output/framesディレクトリ内のPNG画像とメタデータJSONを読み込んで、
スライダーで予報時間を選択できるインタラクティブなHTMLビューアーを生成する。
"""
```
- メタデータベース時刻情報管理
- レスポンシブHTML生成
- JavaScript制御機能統合

### `run_frame_viewer.py`
**フレームビューアー起動**
```python
"""フレームビューアー起動スクリプト

ローカルサーバーを起動してフレームビューアーを表示する。
ブラウザのセキュリティ制限（CORS）を回避するために必要。
"""
```
- HTTPサーバー（ポート8001）
- 依存関係チェック機能
- 自動ブラウザ起動

### `generate_map_viewer.py`
**地図ビューアー生成**
```python
"""インタラクティブ地図ビューアー生成スクリプト（再構築版）

station_data.jsonを読み込んで、インタラクティブな地図ビューアーHTMLを生成する。
"""
```
- Leaflet.js地図統合
- Chart.js時系列グラフ
- 官署データポイント表示

### `run_map_viewer.py`
**地図ビューアー起動**
```python
"""地図ビューアー起動スクリプト

ローカルサーバーを起動して地図ビューアーを表示する。
"""
```
- HTTPサーバー（ポート8000）
- CORS制限回避
- 自動ブラウザ起動

## 🎮 操作方法

### フレームビューアー操作
- **スライダー**: 予報時刻選択
- **自動再生ボタン**: アニメーション再生/停止
- **左右矢印キー**: フレーム切り替え
- **スペースキー**: 再生/停止切り替え
- **Homeキー**: 最初のフレームに戻る

### 地図ビューアー操作
- **マーカークリック**: 官署の時系列グラフ表示
- **地図ズーム/パン**: 標準的な地図操作
- **グラフホバー**: 詳細値表示

## 🎨 可視化される気象要素

| 要素 | 単位 | カラーマップ | 特徴 |
|------|------|-------------|------|
| **気温** | °C | RdYlBu_r | 青(寒)→黄→赤(暖) |
| **気圧** | hPa | RdYlGn_r | 赤(低)→黄→緑(高) |
| **湿度** | % | YlGnBu | 黄(乾)→緑→青(湿) |
| **降水量** | mm/h | JMA式 | 透明→青→黄→赤→紫 |
| **風速** | m/s | 独自 | 青(穏)→緑→黄→赤(強) |
| **雲量** | % | Greys_r | 黒(快晴)→白(曇天) |

## 📊 出力ファイル

### 画像・アニメーション
- `output/frames/frame_*.png`: 個別予報図（40フレーム）
- `output/msm_forecast_modern.gif`: アニメーション
- `output/station_timeseries.png`: 官署時系列図

### Webビューアー
- `output/html/frame_viewer.html`: スライダー付きビューアー
- `output/html/map_viewer.html`: インタラクティブ地図

### データファイル
- `output/frames/frame_*_metadata.json`: フレームメタデータ
- `output/station_data.json`: 官署データ（時系列）

## 🔧 カスタマイズ

### 設定変更可能項目

#### `visualize_final.py`
```python
# ワーカープロセス数
MAX_WORKERS = max(1, multiprocessing.cpu_count() - 1)

# スタイル設定
STYLE_CONFIG = {
    'facecolor': '#1a1a1a',
    'text_color': '#e0e0e0',
    'grid_color': '#404040',
}
```

#### ポート設定
- フレームビューアー: `run_frame_viewer.py` の `PORT = 8001`
- 地図ビューアー: `run_map_viewer.py` の `PORT = 8000`

### 変数追加方法
`get_variable_config()` 関数に新しい変数設定を追加:
```python
'新変数名': {
    'source_names': ['grib変数名'],
    'cmap': 'カラーマップ名',
    'vmin': 最小値, 'vmax': 最大値,
    'unit': '単位'
}
```

## ⚠️ 注意事項

### データソース
- **提供元**: 京都大学RISH (Research Institute for Sustainable Humanosphere)
- **データ**: 気象庁MSM GPV (Meso-Scale Model Grid Point Value)
- **更新**: 1日4回（03, 09, 15, 21 UTC）
- **予報時間**: 39時間先まで

### システム要件
- **Python**: 3.7以上
- **メモリ**: 推奨4GB以上（マルチプロセッシング時）
- **ディスク容量**: ~500MB（データ + 画像）

### パフォーマンス
- **40フレーム生成**: 約2-5分（CPU数依存）
- **メモリ使用量**: プロセス当たり ~200MB
- **出力ファイルサイズ**: 約100MB

## 🐛 トラブルシューティング

### よくある問題

#### 1. 画像が表示されない
```bash
# 依存関係確認
python run_frame_viewer.py --check
```

#### 2. ダウンロードエラー
- ネットワーク接続確認
- RISHサーバーの可用性確認
- `data/metadata.json` の削除を試行

#### 3. メモリエラー
- `MAX_WORKERS` の値を減らす
- システムメモリを増設

#### 4. ポート競合
```bash
# 使用中ポート確認
netstat -an | grep 800[01]
```

## 🙏 謝辞

- **京都大学RISH**: MSM GPVデータの提供
- **気象庁**: MSMモデルの開発・運用
- **オープンソースコミュニティ**: 使用ライブラリの開発

---

**作成日**: 2025年12月5日  
**最終更新**: 2025年12月5日  
**バージョン**: 1.0.0