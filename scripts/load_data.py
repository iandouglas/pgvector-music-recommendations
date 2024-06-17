import time
from multiprocessing import Pool
import pandas as pd

from db import get_db, create_tables
from psycopg2 import sql



chunked = {
	'songs': 'COPY songs(song_id, song_title, band_name) FROM STDIN WITH CSV HEADER',
	'music_vectors': 'COPY music_vectors(band_name, vector) FROM STDIN WITH CSV HEADER',
	'user_favorites': 'COPY user_favorites(user_id, song_id) FROM STDIN WITH CSV HEADER'
}

def format_vector_column(df, vector_column_name):
    df[vector_column_name] = df[vector_column_name].apply(lambda x: '[' + ','.join(map(str, eval(x))) + ']')
    return df


def insert_chunk(params):
	chunk, chunk_data, vector_column_name = params
	print('.', end='', flush=True)
	conn = get_db()
	cur = conn.cursor()
	try:
		if vector_column_name:
			chunk_data = format_vector_column(chunk_data, vector_column_name)
		chunk_csv = chunk_data.to_csv(index=False)
		from io import StringIO
		csv_file_like_object = StringIO(chunk_csv)
		cur.copy_expert(chunked[chunk], csv_file_like_object)
		conn.commit()
	except Exception as e:
		print(f"Error inserting chunk: {e}")
	finally:
		cur.close()
		conn.close()
		time.sleep(0.2)

		
def count_lines(file_path):
    with open(file_path, 'r') as file:
        return sum(1 for line in file)
	
def work(file_path, workers, has_vector):
	lines = count_lines(file_path)
	# chunk_size = (lines // workers) + 1
	chunk_size = min((lines // workers) + 1, 1000)
	print(f'processing {file_path} with {lines} lines and {workers} workers, chunk_size={chunk_size}, steps={lines // chunk_size}')
    # Read the CSV file_path in chunks
	chunks = pd.read_csv(file_path, chunksize=chunk_size, delimiter='\t')
	# print(f'chunks: {chunks}')
    
	vector = 'vector' if has_vector else None
	chunk_params = [(file_path.split('.')[0], chunk, vector) for chunk in chunks]

	with Pool(workers) as pool:
		pool.map(insert_chunk, chunk_params)

if __name__ == "__main__":
	print('opening database connection')
	db = get_db()
	print('dropping/creating tables')
	create_tables(db)

	print('inserting data')
	# work(file_path='songs.csv', workers=50, has_vector=False)
	# work(file_path='user_favorites.csv', workers=50, has_vector=False)
	work(file_path='music_vectors.csv', workers=50, has_vector=True)
	
	print('finished')