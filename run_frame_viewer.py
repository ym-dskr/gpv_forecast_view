#!/usr/bin/env python3
"""フレームビューアー起動スクリプト

ローカルサーバーを起動してフレームビューアーを表示する。
ブラウザのセキュリティ制限（CORS）を回避するために必要。
"""

import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 8001  # map_viewerと異なるポートを使用
DIRECTORY = "output"  # outputディレクトリ全体を配信ルートに設定

class Handler(http.server.SimpleHTTPRequestHandler):
    """カスタムHTTPリクエストハンドラー。
    
    指定ディレクトリをドキュメントルートとして設定し、
    静的ファイル（HTML、PNG、JSON等）を配信する。
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def run_frame_viewer_server():
    """HTTPサーバーを起動してブラウザでフレームビューアーを表示する。

    ローカルHTTPサーバーを起動し、フレームビューアーHTMLを配信する。
    CORS制限を回避するために必要で、指定ポートでサーバーを開始後、
    デフォルトブラウザでフレームビューアーページを自動的に開く。

    Args:
        なし

    Returns:
        なし

    Raises:
        OSError: 指定ポートが使用中の場合
        KeyboardInterrupt: Ctrl+Cでサーバー停止時
        FileNotFoundError: HTMLディレクトリまたはビューアーファイルが存在しない場合

    Note:
        - デフォルトポート8001使用（地図ビューアーとの競合回避）
        - output/htmlディレクトリを配信ルートに設定
        - Ctrl+Cで安全にサーバー停止可能
        - framesディレクトリの画像ファイルにもアクセス可能
    """
    # 必要なディレクトリとファイルの存在確認
    if not os.path.exists(DIRECTORY):
        print(f"Error: {DIRECTORY} directory not found.")
        print("Please run create_frame_viewer.py first to generate the HTML file.")
        return
    
    frame_viewer_path = os.path.join(DIRECTORY, "html", "frame_viewer.html")
    if not os.path.exists(frame_viewer_path):
        print(f"Error: frame_viewer.html not found in {frame_viewer_path}")
        print("Please run create_frame_viewer.py first to generate the HTML file.")
        return
    
    frames_dir = os.path.join("output", "frames")
    if not os.path.exists(frames_dir):
        print(f"Error: {frames_dir} directory not found.")
        print("Please run visualize_final.py first to generate frame images.")
        return

    # ポートが使用中かチェック
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"=== MSM フレームビューアーサーバー ===")
            print(f"Serving at http://localhost:{PORT}")
            print(f"Document root: {DIRECTORY}")
            print("Press Ctrl+C to stop the server.")
            print()
            print("操作方法:")
            print("  - スライダー: 予報時刻を選択")
            print("  - 自動再生ボタン: フレームの自動切り替え")
            print("  - 左右矢印キー: フレーム切り替え")
            print("  - スペースキー: 自動再生/停止")
            print("  - Homeキー: 最初のフレームに戻る")
            print()
            
            # ブラウザを開く
            url = f"http://localhost:{PORT}/html/frame_viewer.html"
            print(f"Opening browser: {url}")
            webbrowser.open(url)
            
            # サーバーを実行
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down server...")
                httpd.shutdown()
                
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"Error: Port {PORT} is already in use.")
            print(f"Please close any application using port {PORT} or change the PORT variable.")
        else:
            print(f"Error: Cannot bind to port {PORT}")
            print(f"Details: {e}")
    except KeyboardInterrupt:
        print("\nServer stopped by user.")

def check_dependencies():
    """必要なファイルとディレクトリの存在をチェックする。
    
    フレームビューアーの動作に必要なファイル群が揃っているかを確認し、
    不足している場合は適切な指示を表示する。

    Returns:
        bool: 全ての依存関係が満たされている場合True、そうでなければFalse
    """
    checks = [
        (DIRECTORY, "Output directory"),
        (os.path.join(DIRECTORY, "html", "frame_viewer.html"), "Frame viewer HTML file"),
        (os.path.join(DIRECTORY, "frames"), "Frames directory"),
    ]
    
    all_ok = True
    for path, description in checks:
        if not os.path.exists(path):
            print(f"Missing: {description} ({path})")
            all_ok = False
        else:
            print(f"✓ Found: {description}")
    
    return all_ok

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        print("=== Dependency Check ===")
        if check_dependencies():
            print("All dependencies satisfied!")
        else:
            print("\nPlease run the following commands to generate missing files:")
            print("  python visualize_final.py    # Generate frame images")
            print("  python create_frame_viewer.py # Generate HTML viewer")
        sys.exit(0)
    
    run_frame_viewer_server()