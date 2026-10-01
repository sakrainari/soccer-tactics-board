"""Local-only live bridge for the football tactics board. No third party packages."""
import argparse
import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / 'board-state.json'
LOCK = threading.Lock()
STATE = None
REVISION = 0
if STATE_FILE.exists():
    try:
        STATE = json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        pass


class Handler(BaseHTTPRequestHandler):
    def reply(self, payload, code=200, mime='application/json; charset=utf-8'):
        if not isinstance(payload, bytes):
            payload = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        route = self.path.split('?', 1)[0]
        if route == '/api/health':
            self.reply({'app': 'tactics-board', 'version': 1, 'workspace': str(ROOT)})
        elif route == '/api/state':
            with LOCK:
                self.reply({'revision': REVISION, 'state': STATE})
        elif route in ('/', '/index.html', '/tactics-board.html'):
            self.reply((ROOT / 'index.html').read_bytes(), mime='text/html; charset=utf-8')
        elif route == '/favicon.ico':
            self.reply(b'', code=204, mime='image/x-icon')
        else:
            self.reply({'error': 'not found'}, code=404)

    def do_POST(self):
        global STATE, REVISION
        if self.path != '/api/state':
            self.reply({'error': 'not found'}, code=404)
            return
        origin = self.headers.get('Origin')
        if origin and origin != f'http://127.0.0.1:{self.server.server_port}':
            self.reply({'error': 'origin rejected'}, code=403)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 300000:
                raise ValueError('invalid size')
            state = json.loads(self.rfile.read(length).decode('utf-8'))
            if not isinstance(state, dict) or state.get('version') != 1:
                raise ValueError('invalid version')
            with LOCK:
                temporary = STATE_FILE.with_suffix('.tmp')
                temporary.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
                temporary.replace(STATE_FILE)
                STATE = state
                REVISION += 1
                revision = REVISION
            self.reply({'revision': revision})
        except (ValueError, UnicodeError):
            self.reply({'error': 'invalid board'}, code=400)
        except OSError:
            self.reply({'error': 'unable to save'}, code=500)

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Tactics board: http://127.0.0.1:{args.port}/', flush=True)
    server.serve_forever()
