import http.server
import socketserver
import webbrowser
from pathlib import Path

PORT = 8501
DIRECTORY = Path(__file__).resolve().parent

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.path = "/dashboard.html"
        return super().do_GET()

def main():
    # Ensure dashboard.html exists
    html_file = DIRECTORY / "dashboard.html"
    if not html_file.exists():
        print("Generating dashboard.html...")
        import generate_modern_dashboard
        
    print(f"==================================================")
    print(f" Thailand Labor Market Dashboard (Ultra-Modern UI)")
    print(f" Server running at: http://localhost:{PORT}")
    print(f" Press Ctrl+C to stop the server.")
    print(f"==================================================")
    
    webbrowser.open(f"http://localhost:{PORT}")
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    main()
