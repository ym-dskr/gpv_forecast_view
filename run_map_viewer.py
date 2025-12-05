#!/usr/bin/env python3
"""地図ビューアー起動スクリプト

ローカルサーバーを起動して地図ビューアーを表示する。
ブラウザのセキュリティ制限（CORS）を回避するために必要。
"""

import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 8000
DIRECTORY = os.path.join("output", "html")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def run_server():
    """HTTPサーバーを起動してブラウザで地図ビューアーを表示する。

    ローカルHTTPサーバーを起動し、地図ビューアーHTMLを配信する。
    CORS制限を回避するために必要で、指定ポートでサーバーを開始後、
    デフォルトブラウザで地図ページを自動的に開く。

    Args:
        なし

    Returns:
        なし

    Raises:
        OSError: 指定ポートが使用中の場合
        KeyboardInterrupt: Ctrl+Cでサーバー停止時

    Note:
        - デフォルトポート8000使用
        - output/htmlディレクトリを配信ルートに設定
        - Ctrl+Cで安全にサーバー停止可能
    """
    if not os.path.exists(DIRECTORY):
        print(f"Error: {DIRECTORY} directory not found.")
        return

    # ポートが使用中かチェック
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Serving at http://localhost:{PORT}")
            print("Press Ctrl+C to stop the server.")
            
            # ブラウザを開く
            url = f"http://localhost:{PORT}/map_viewer.html"
            webbrowser.open(url)
            
            # サーバーを実行
            httpd.serve_forever()
    except OSError as e:
        print(f"Error: Port {PORT} is already in use or cannot be bound.")
        print(e)
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    run_server()
