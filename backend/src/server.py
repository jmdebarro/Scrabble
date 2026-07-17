import json
import os
import subprocess
import threading
import atexit
from http.server import HTTPServer, BaseHTTPRequestHandler

class PersistentSolver:
    """Owns one native solver process whose GADDAG is reused across requests."""

    def __init__(self):
        self._process = None
        self._lock = threading.Lock()
        self._src_dir = os.path.dirname(os.path.abspath(__file__))
        self._executable_path = os.path.join(self._src_dir, "gaddag_solver")

    def _start_locked(self):
        if self._process is not None and self._process.poll() is None:
            return
        self._process = subprocess.Popen(
            [self._executable_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self._src_dir,
            text=True,
            bufsize=1,
        )

    def _stop_locked(self):
        if self._process is None:
            return
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        self._process = None

    def solve(self, request_payload):
        request_line = json.dumps(json.loads(request_payload), separators=(",", ":"))
        with self._lock:
            for attempt in range(2):
                self._start_locked()
                try:
                    self._process.stdin.write(request_line + "\n")
                    self._process.stdin.flush()
                    response_line = self._process.stdout.readline()
                    if not response_line:
                        stderr = self._process.stderr.read().strip()
                        raise RuntimeError(stderr or "C++ solver exited without a response")
                    return json.loads(response_line)
                except (BrokenPipeError, OSError, ValueError, RuntimeError):
                    self._stop_locked()
                    if attempt == 1:
                        raise
        raise RuntimeError("C++ solver request failed")

    def close(self):
        with self._lock:
            self._stop_locked()


solver_process = PersistentSolver()
atexit.register(solver_process.close)

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
                
                # 2. Reuse the native process; its GADDAG is loaded only once.
                response_payload = solver_process.solve(post_data)
                
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
