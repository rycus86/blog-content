import sys
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

        if '--ping' in sys.argv:
            self.wfile.write(bytes('Pong from %s\n' % socket.gethostname(), 'utf8'))

        elif '--hello' in sys.argv:
            name = self.path.split('/')[-1].capitalize()
            self.wfile.write(bytes(
                'Hello, %s! (from %s)\n' % (name, socket.gethostname()), 'utf8'
            ))


if __name__ == '__main__':
    HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
