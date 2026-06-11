import http.server
import json
import sqlite3
import urllib.parse
import hashlib
import os
import sys
import re
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'natura.db')
SECRET = 'natura-admin-secret-2026'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL,
            dni TEXT,
            cargo TEXT DEFAULT '',
            area TEXT DEFAULT '',
            sueldo REAL DEFAULT 0,
            fecha_ingreso TEXT DEFAULT '',
            telefono TEXT DEFAULT '',
            direccion TEXT DEFAULT '',
            email TEXT DEFAULT '',
            estado TEXT DEFAULT 'Activo' CHECK(estado IN ('Activo','Inactivo')),
            rol TEXT NOT NULL DEFAULT 'worker' CHECK(rol IN ('admin','worker')),
            foto TEXT DEFAULT '',
            fecha_registro TEXT DEFAULT (datetime('now','-5 hours'))
        );
    ''')
    try:
        conn.execute("ALTER TABLE usuarios ADD COLUMN foto TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    cur = conn.execute("SELECT id FROM usuarios WHERE username='admin'")
    if not cur.fetchone():
        pw = hashlib.sha256(f'admin123{SECRET}'.encode()).hexdigest()
        conn.execute(
            "INSERT INTO usuarios (username, password, nombre, rol) VALUES (?, ?, ?, 'admin')",
            ('admin', pw, 'Administrador')
        )
        conn.commit()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT DEFAULT '',
            precio REAL NOT NULL,
            categoria TEXT DEFAULT '',
            imagen TEXT DEFAULT '',
            stock INTEGER DEFAULT 0,
            destacado INTEGER DEFAULT 0,
            fecha_registro TEXT DEFAULT (datetime('now','-5 hours'))
        );
    ''')
    cur = conn.execute("SELECT COUNT(*) FROM productos")
    if cur.fetchone()[0] == 0:
        sample = [
            ('STEM CELL', 'Cápsulas naturales para fortalecer el sistema inmunológico', 18, 'Capsulas', 'https://naturasanaperu.com/wp-content/uploads/2023/06/1.png', 50, 1),
            ('T-OSITO', 'Bebida reconfortante 700ml a base de hierbas naturales', 21, 'Bebidas', 'https://naturasanaperu.com/wp-content/uploads/2023/06/3-2.png', 30, 1),
            ('COLAGENO H.', 'Colágeno hidrolizado bebida 500ml para piel y articulaciones', 18, 'Bebidas', 'https://naturasanaperu.com/wp-content/uploads/2023/06/6-2.png', 40, 1),
            ('PROPOLEO', 'Propóleo bebida 1.2L, refuerzo natural para defensas', 25, 'Bebidas', 'https://naturasanaperu.com/wp-content/uploads/2023/06/2-2.png', 25, 1),
            ('WOMEN PROT', 'Proteína vegetal x 500gr para mujer', 28, 'Harinas', 'https://naturasanaperu.com/wp-content/uploads/2023/06/4-2.png', 20, 1),
            ('PRO MAX', 'Bebida energética 500ml con proteínas y vitaminas', 18, 'Bebidas', 'https://naturasanaperu.com/wp-content/uploads/2023/06/5-2.png', 35, 0),
            ('ALOE VERA', 'Jugo de Aloe Vera 1L, depurativo natural', 22, 'Bebidas', '', 30, 0),
            ('MACA NEGRA', 'Cápsulas de Maca Negra x 60, energía natural', 15, 'Capsulas', '', 45, 0),
            ('QUINUA ORGÁNICA', 'Harina de Quinua Orgánica x 1kg', 12, 'Harinas', '', 50, 0),
            ('TÉ VERDE', 'Té Verde en hojas x 100g, antioxidante natural', 10, 'Harinas', '', 60, 0),
        ]
        conn.executemany(
            "INSERT INTO productos (nombre, descripcion, precio, categoria, imagen, stock, destacado) VALUES (?,?,?,?,?,?,?)",
            sample
        )
        conn.commit()
    conn.close()

def next_username(conn):
    cur = conn.execute("SELECT username FROM usuarios WHERE username LIKE 'U%' ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        m = re.search(r'U(\d+)', row['username'])
        if m:
            return f"U{int(m.group(1)) + 1:04d}"
    return "U0001"

class APIHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _send_static(self, path):
        try:
            if path == '/' or path == '':
                path = '/index.html'
            filepath = os.path.join(os.path.dirname(__file__), path.lstrip('/'))
            if not os.path.exists(filepath) or not os.path.isfile(filepath):
                self.send_error(404)
                return
            ext = os.path.splitext(filepath)[1]
            types = {
                '.html': 'text/html; charset=utf-8',
                '.css': 'text/css; charset=utf-8',
                '.js': 'application/javascript; charset=utf-8',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon'
            }
            content_type = types.get(ext, 'application/octet-stream')
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))

    def _parse_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode())

    def _get_user_data(self, row):
        return {
            'id': row['id'],
            'username': row['username'],
            'nombre': row['nombre'],
            'dni': row['dni'],
            'cargo': row['cargo'],
            'area': row['area'],
            'sueldo': row['sueldo'],
            'fecha_ingreso': row['fecha_ingreso'],
            'telefono': row['telefono'],
            'direccion': row['direccion'],
            'email': row['email'],
            'estado': row['estado'],
            'rol': row['rol'],
            'foto': row['foto'],
            'fecha_registro': row['fecha_registro']
        }

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')
        query = urllib.parse.parse_qs(parsed.query)
        if path.startswith('/api/'):
            self._handle_api_get(path, query)
        else:
            self._send_static(path)

    def _handle_api_get(self, path, query):
        if path == '/api/workers':
            conn = get_db()
            search = query.get('search', [''])[0]
            if search:
                rows = conn.execute(
                    "SELECT * FROM usuarios WHERE rol='worker' AND (nombre LIKE ? OR dni LIKE ? OR cargo LIKE ? OR username LIKE ?) ORDER BY id DESC",
                    (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%')
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM usuarios WHERE rol='worker' ORDER BY id DESC").fetchall()
            conn.close()
            workers = [self._get_user_data(r) for r in rows]
            self._send_json({'ok': True, 'workers': workers})
            return

        if path == '/api/workers/count':
            conn = get_db()
            total = conn.execute("SELECT COUNT(*) FROM usuarios WHERE rol='worker'").fetchone()[0]
            activos = conn.execute("SELECT COUNT(*) FROM usuarios WHERE rol='worker' AND estado='Activo'").fetchone()[0]
            conn.close()
            self._send_json({'ok': True, 'total': total, 'activos': activos})
            return

        if path.startswith('/api/workers/'):
            wid = path.split('/')[-1]
            conn = get_db()
            row = conn.execute("SELECT * FROM usuarios WHERE id=? AND rol='worker'", (wid,)).fetchone()
            conn.close()
            if row:
                self._send_json({'ok': True, 'worker': self._get_user_data(row)})
            else:
                self._send_json({'error': 'No encontrado'}, 404)
            return

        if path == '/api/productos':
            conn = get_db()
            cat = query.get('categoria', [''])[0]
            if cat:
                rows = conn.execute("SELECT * FROM productos WHERE categoria=? ORDER BY destacado DESC, id DESC", (cat,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM productos ORDER BY destacado DESC, id DESC").fetchall()
            conn.close()
            productos = [dict(r) for r in rows]
            self._send_json({'ok': True, 'productos': productos})
            return

        if path.startswith('/api/productos/'):
            pid = path.split('/')[-1]
            conn = get_db()
            row = conn.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
            conn.close()
            if row:
                self._send_json({'ok': True, 'producto': dict(row)})
            else:
                self._send_json({'error': 'No encontrado'}, 404)
            return

        self._send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == '/api/workers':
            body = self._parse_body()
            conn = get_db()
            try:
                uname = next_username(conn)
                pw = hashlib.sha256(f'{body["dni"]}{SECRET}'.encode()).hexdigest()
                conn.execute(
                    "INSERT INTO usuarios (username, password, nombre, dni, cargo, area, sueldo, fecha_ingreso, telefono, direccion, email, estado, foto, rol) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'worker')",
                    (uname, pw, body['nombre'], body['dni'], body.get('cargo', ''), body.get('area', ''),
                     float(body.get('sueldo', 0)), body.get('fecha_ingreso', datetime.now().strftime('%Y-%m-%d')),
                     body.get('telefono', ''), body.get('direccion', ''),
                     body.get('email', ''), body.get('estado', 'Activo'),
                     body.get('foto', ''))
                )
                conn.commit()
                wid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                row = conn.execute("SELECT * FROM usuarios WHERE id=?", (wid,)).fetchone()
                conn.close()
                self._send_json({'ok': True, 'worker': self._get_user_data(row), 'generated_username': uname, 'generated_password': body['dni']}, 201)
            except Exception as e:
                conn.close()
                if 'UNIQUE' in str(e):
                    self._send_json({'error': 'El DNI ya existe'}, 400)
                else:
                    self._send_json({'error': str(e)}, 400)
            return

        if path == '/api/productos':
            body = self._parse_body()
            conn = get_db()
            try:
                conn.execute(
                    "INSERT INTO productos (nombre, descripcion, precio, categoria, imagen, stock) VALUES (?,?,?,?,?,?)",
                    (body['nombre'], body.get('descripcion', ''), float(body['precio']),
                     body.get('categoria', ''), body.get('imagen', ''), int(body.get('stock', 0)))
                )
                conn.commit()
                pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                row = conn.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
                conn.close()
                self._send_json({'ok': True, 'producto': dict(row)}, 201)
            except Exception as e:
                conn.close()
                self._send_json({'error': str(e)}, 400)
            return

        self._send_json({'error': 'Not found'}, 404)

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path.startswith('/api/productos/'):
            pid = path.split('/')[-1]
            body = self._parse_body()
            conn = get_db()
            try:
                conn.execute(
                    "UPDATE productos SET nombre=?, descripcion=?, precio=?, categoria=?, imagen=?, stock=? WHERE id=?",
                    (body['nombre'], body.get('descripcion', ''), float(body['precio']),
                     body.get('categoria', ''), body.get('imagen', ''), int(body.get('stock', 0)), pid)
                )
                conn.commit()
                row = conn.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
                conn.close()
                if row:
                    self._send_json({'ok': True, 'producto': dict(row)})
                else:
                    self._send_json({'error': 'No encontrado'}, 404)
            except Exception as e:
                conn.close()
                self._send_json({'error': str(e)}, 400)
            return

        if path.startswith('/api/workers/'):
            wid = path.split('/')[-1]
            body = self._parse_body()
            conn = get_db()
            try:
                conn.execute(
                    "UPDATE usuarios SET nombre=?, dni=?, cargo=?, area=?, sueldo=?, fecha_ingreso=?, telefono=?, direccion=?, email=?, estado=?, foto=? WHERE id=? AND rol='worker'",
                    (body['nombre'], body['dni'], body.get('cargo', ''), body.get('area', ''),
                     float(body.get('sueldo', 0)), body.get('fecha_ingreso', ''),
                     body.get('telefono', ''), body.get('direccion', ''),
                     body.get('email', ''), body.get('estado', 'Activo'),
                     body.get('foto', ''), wid)
                )
                conn.commit()
                if body.get('dni'):
                    new_pw = hashlib.sha256(f'{body["dni"]}{SECRET}'.encode()).hexdigest()
                    conn.execute("UPDATE usuarios SET password=? WHERE id=? AND rol='worker'", (new_pw, wid))
                    conn.commit()
                row = conn.execute("SELECT * FROM usuarios WHERE id=? AND rol='worker'", (wid,)).fetchone()
                conn.close()
                if row:
                    self._send_json({'ok': True, 'worker': self._get_user_data(row)})
                else:
                    self._send_json({'error': 'No encontrado'}, 404)
            except Exception as e:
                conn.close()
                self._send_json({'error': str(e)}, 400)
            return

        self._send_json({'error': 'Not found'}, 404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path.startswith('/api/productos/'):
            pid = path.split('/')[-1]
            conn = get_db()
            conn.execute("DELETE FROM productos WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            self._send_json({'ok': True})
            return

        if path.startswith('/api/workers/'):
            wid = path.split('/')[-1]
            conn = get_db()
            conn.execute("DELETE FROM usuarios WHERE id=? AND rol='worker'", (wid,))
            conn.commit()
            conn.close()
            self._send_json({'ok': True})
            return

        self._send_json({'error': 'Not found'}, 404)


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', sys.argv[1] if len(sys.argv) > 1 else '8000'))
    server = http.server.HTTPServer(('0.0.0.0', port), APIHandler)
    print(f'Servidor iniciado en http://localhost:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido')
        server.server_close()
