import pymysql
import pymysql.cursors
from config import Config

def get_conn():
    return pymysql.connect(**Config.DB, cursorclass=pymysql.cursors.DictCursor, autocommit=True)

def query(sql, args=None, one=False):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchone() if one else cur.fetchall()
    finally:
        conn.close()

def execute(sql, args=None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.lastrowid
    finally:
        conn.close()

def executemany(sql, rows):
    if not rows:
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
    finally:
        conn.close()
