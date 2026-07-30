import os
import pymysql

cfg = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Ak@120799',
    'db': 'grillista_admin',
    'cursorclass': pymysql.cursors.DictCursor,
}

conn = pymysql.connect(**cfg)
cur = conn.cursor()
cur.execute('SELECT id, title, image_path FROM gallery')
rows = cur.fetchall()
print('rows:', rows)
base = os.path.dirname(os.path.abspath(__file__))
print('base:', base)
for r in rows:
    path = os.path.join(base, 'static', r['image_path'])
    print(r['id'], r['image_path'], os.path.exists(path), path)
conn.close()
