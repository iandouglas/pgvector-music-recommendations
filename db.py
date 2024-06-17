from config import PG_URL

import psycopg2

def get_db():
    return psycopg2.connect(PG_URL)

def create_tables(conn):
    cur = conn.cursor()

    print('dropping user_favorites')
    cur.execute('DROP TABLE IF EXISTS user_favorites')
    print('dropping songs')
    cur.execute('DROP TABLE IF EXISTS songs')
    print('dropping music_vectors')
    cur.execute('DROP TABLE IF EXISTS music_vectors')

    print('creating songs')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            song_id INT PRIMARY KEY,
            song_title varchar(1000),
            band_name varchar(1000)
        )
    ''')

    print('creating user_favorites')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_favorites (
            user_id INT,
            song_id INT,
            FOREIGN KEY (song_id) REFERENCES songs (song_id)
        )
    ''')

    print('creating music_vectors')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS music_vectors (
            band_name varchar(200) PRIMARY KEY,
            vector VECTOR(100)
        )
    ''')

    conn.commit()
    conn.close()
