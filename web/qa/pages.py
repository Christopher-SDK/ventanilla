"""Serves web/dist the way GitHub Pages does: under /ventanilla/, with 404.html and status 404.

Usage: uv run python qa/pages.py [port]   (default 4912) → http://127.0.0.1:4912/ventanilla/
"""
import http.server, os, sys

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dist')
BASE = '/ventanilla'


class Pages(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIST, **k)

    def translate_path(self, path):
        if not path.startswith(BASE + '/'):
            return os.path.join(DIST, '__no_existe__')
        return super().translate_path(path[len(BASE):])

    def send_head(self):
        # GitHub Pages answers Range requests with 206; without it Chrome cannot seek a video.
        rango = self.headers.get('Range', '')
        ruta = self.translate_path(self.path.split('?')[0])
        if not rango.startswith('bytes=') or not os.path.isfile(ruta):
            return super().send_head()
        total = os.path.getsize(ruta)
        ini, _, fin = rango[6:].split(',')[0].partition('-')
        ini, fin = (int(ini), int(fin) if fin else total - 1) if ini else (total - int(fin), total - 1)
        fin = min(fin, total - 1)
        if ini > fin:
            self.send_response(416); self.send_header('Content-Range', f'bytes */{total}'); self.end_headers()
            return None
        f = open(ruta, 'rb'); f.seek(ini)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(ruta))
        self.send_header('Content-Range', f'bytes {ini}-{fin}/{total}')
        self.send_header('Content-Length', str(fin - ini + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        self._resto = fin - ini + 1
        return f

    def copyfile(self, origen, destino):
        resto = getattr(self, '_resto', None)
        if resto is None:
            return super().copyfile(origen, destino)
        self._resto = None
        while resto > 0:
            trozo = origen.read(min(65536, resto))
            if not trozo:
                break
            destino.write(trozo); resto -= len(trozo)

    def send_error(self, code, message=None, explain=None):
        if code != 404:
            return super().send_error(code, message, explain)
        with open(os.path.join(DIST, '404.html'), 'rb') as f:
            cuerpo = f.read()
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(cuerpo)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(cuerpo)

    def log_message(self, *a):
        pass


puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 4912
http.server.ThreadingHTTPServer(('127.0.0.1', puerto), Pages).serve_forever()
