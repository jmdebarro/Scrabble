import json
import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

class ScrabbleBotRequestHandler(BaseHTTPRequestHandler):
    
    def _set_cors_headers(self):
        """Enable Cross-Origin Resource Sharing (CORS) for local React app dev client."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        """Respond to CORS preflight requests."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/bot_move":
            try:
                # 1. Read request body
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                
                print(f"\n[POST] Received bot move request. Forwarding to C++ GADDAG solver...")
                
                # 2. Paths configuration
                src_dir = os.path.dirname(os.path.abspath(__file__))
                executable_path = os.path.join(src_dir, "gaddag_solver")
                
                # Fallback to local execution if path doesn't exist
                if not os.path.exists(executable_path):
                    executable_path = "./gaddag_solver"

                # 3. Spawn C++ subprocess and pipe the JSON input to stdin
                process = subprocess.Popen(
                    [executable_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=src_dir
                )
                
                # Pipe input and wait for result
                stdout_data, stderr_data = process.communicate(input=post_data)
                
                if process.returncode != 0:
                    error_msg = stderr_data.decode("utf-8") if stderr_data else "C++ solver crashed"
                    raise RuntimeError(f"C++ solver returned exit code {process.returncode}: {error_msg}")

                # 4. Decode JSON response from C++ solver
                response_payload = json.loads(stdout_data.decode("utf-8"))
                
                # 5. Send success response back to React client
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._set_cors_headers()
                self.end_headers()
                
                self.wfile.write(json.dumps(response_payload).encode("utf-8"))
                
                word_played = response_payload.get("word", "PASS")
                score_played = response_payload.get("score", 0)
                print(f" -> C++ Solver completed! Best play: '{word_played}' ({score_played} pts).")
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"error": "Endpoint not found"}')


def run_server(port=5001):
    print("=== Starting High-Performance C++ Scrabble Bot Web Server ===")
    print("Pre-compilation check: 'gaddag_solver' binary will be invoked.")
    
    server_address = ("", port)
    httpd = HTTPServer(server_address, ScrabbleBotRequestHandler)
    print(f"\n✓ Scrabble Bot Server running at http://localhost:{port}")
    print("Forwarding all bot requests to compiled C++ GADDAG solver.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
