import random
import csv
from multiprocessing import Pool
import pandas as pd

from faker import Faker
from db import get_db, create_tables
from psycopg2 import sql



def generate_data():
	all_songs = []
	limits = {
		'users': 1000,
		'artists': 100,
		'albums': {'min': 3, 'max': 8},
		'songs': {'min': 10, 'max': 15, 'vectors': 50},
		'user_playlists': {'min': 1, 'max': 10, 'vectors': 50},
		'user_playlist_songs': {'min': 10, 'max': 50},
		'user_dislikes': {'min': 50, 'max': 100}
	}

	fake = Faker()

	genres = ['Pop', 'Rock', 'Jazz', 'Classical', 'Hip-Hop', 'Country', 'Electronic', 'Reggae']

	song_id = 0
	print(f"generating {limits['artists']} fake artists, each with {limits['albums']['min']}-{limits['albums']['max']} albums, each album has {limits['songs']['min']}-{limits['songs']['max']} tracks")

	with open(f'songs.csv', mode='w', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(['song_id', 'song_title', 'artist_name', 'album_name', 'genre', 'album_date', 'vector'])

		for _ in range(limits['artists']):
			artist_name = fake.name()
			genre = random.choice(genres)
			for _ in range(random.randint(limits['albums']['min'],limits['albums']['max'])):
				songs = []
				album_name = fake.sentence(nb_words=3)[0:-1]
				album_date = fake.date_between(start_date='-30y', end_date='today')
				for _ in range(random.randint(limits['songs']['min'],limits['songs']['max'])):
					song_id += 1
					song_title = fake.sentence(nb_words=5)[0:-1]
					vector = [random.uniform(-1, 1) for _ in range(limits['songs']['vectors'])]  # Example of 100-dimension vector

					all_songs.append((song_id, song_title, artist_name, album_name, genre, album_date, vector))

					writer.writerow([song_id, song_title, artist_name, album_name, genre, album_date, vector])

	print(f"generating {limits['users']} fake users, each with {limits['user_playlists']['min']}-{limits['user_playlists']['max']} playlists, each playlist has {limits['user_playlist_songs']['min']}-{limits['user_playlist_songs']['max']} songs")
	print(f"each user will like all songs on their playlists and randomly dislike {limits['user_dislikes']['min']}-{limits['user_dislikes']['max']} other songs")

	with open(f'playlists.csv', mode='w', newline='') as fh:
		writer = csv.writer(fh)
		writer.writerow(['playlist_id', 'playlist_name', 'user_id', 'vector'])

	with open(f'playlist_songs.csv', mode='w', newline='') as fh:
		writer = csv.writer(fh)
		writer.writerow(['playlist_id', 'song_id'])

	with open(f'user_songs.csv', mode='w', newline='') as fh:
		writer = csv.writer(fh)
		writer.writerow(['user_id', 'song_id', 'liked'])

	with open(f'users.csv', mode='w', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(['user_id', 'username'])
		
		user_id = 0
		playlist_id = 0
		for user_id in range(limits['users']):
			user_id += 1
			username = fake.user_name()
			writer.writerow([user_id, username])

			playlist_songs = []
			liked_songs = []
			disliked_songs = []

			fh_playlists = open(f'playlists.csv', mode='a', newline='')
			csv_playlists = csv.writer(fh_playlists)
			fh_playlist_songs = open(f'playlist_songs.csv', mode='a', newline='')
			csv_playlist_songs = csv.writer(fh_playlist_songs)
			fh_user_songs = open(f'user_songs.csv', mode='a', newline='')
			csv_user_songs = csv.writer(fh_user_songs)

			for _ in range(random.randint(limits['user_playlists']['min'],limits['user_playlists']['max'])):
				playlist_id += 1
				playlist_name = f'{" ".join(fake.words(nb=2))} {fake.cryptocurrency_name()}'
				vector = [random.uniform(-1, 1) for _ in range(limits['user_playlists']['vectors'])]

				csv_playlists.writerow([playlist_id, playlist_name, user_id, vector])

				random_songs = random.choices(all_songs, weights=None, k=random.randint(limits['user_playlist_songs']['min'],limits['user_playlist_songs']['max']))
				for song in random_songs:
					if (playlist_id, song[0]) not in playlist_songs:
						playlist_songs.append((playlist_id, song[0]))
						csv_playlist_songs.writerow([playlist_id, song[0]])

				for song in random_songs:
					if song[0] not in liked_songs:
						liked_songs.append(song[0])
						csv_user_songs.writerow([user_id, song[0], True])

			dislike_count = random.randint(limits['user_dislikes']['min'],limits['user_dislikes']['max'])
			while len(disliked_songs) < dislike_count:
				random_songs = random.choices(all_songs, weights=None, k=10)
				for song in random_songs:
					if song[0] not in liked_songs and song[0] not in disliked_songs:
						disliked_songs.append(song[0])
						
			if len(disliked_songs) > limits['user_dislikes']['max']:
				disliked_songs = disliked_songs[:limits['user_dislikes']['max']]

			for song in disliked_songs:
				csv_user_songs.writerow([user_id, song, False])

		fh_playlists.close()
		fh_playlist_songs.close()
		fh_user_songs.close()


chunked = {
	'songs': 'COPY songs(song_id, song_title, artist_name, album_name, genre, album_date, vector) FROM STDIN WITH CSV HEADER',
	'users': 'COPY users(user_id, username) FROM STDIN WITH CSV HEADER',
	'playlists': 'COPY playlists(playlist_id, playlist_name, user_id, vector) FROM STDIN WITH CSV HEADER',
	'playlist_songs': 'COPY playlist_songs(playlist_id, song_id) FROM STDIN WITH CSV HEADER',
	'user_songs': 'COPY user_songs(user_id, song_id, liked) FROM STDIN WITH CSV HEADER'
}

def format_vector_column(df, vector_column_name):
    df[vector_column_name] = df[vector_column_name].apply(lambda x: '{' + ','.join(map(str, eval(x))) + '}')
    return df


def insert_chunk(params):
	chunk, chunk_data, vector_column_name = params
	print(f'{chunk} chunk')
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


def count_lines(file_path):
    with open(file_path, 'r') as file:
        return sum(1 for line in file)
	
def work(file_path, workers, has_vector):
	lines = count_lines(file_path)
	# chunk_size = (lines // workers) + 1
	chunk_size = min((lines // workers) + 1, 1000)
	print(f'processing {file_path} with {lines} lines and {workers} workers, chunk_size={chunk_size}, steps={lines // chunk_size}')
    # Read the CSV file_path in chunks
	chunks = pd.read_csv(file_path, chunksize=chunk_size)
	# print(f'chunks: {chunks}')
    
	vector = 'vector' if has_vector else None
	chunk_params = [(file_path.split('.')[0], chunk, vector) for chunk in chunks]

	with Pool(workers) as pool:
		pool.map(insert_chunk, chunk_params)


if __name__ == "__main__":
	generate_data()

	print('opening database connection')
	db = get_db()
	print('dropping/creating tables')
	create_tables(db)

	print('inserting data')
	work(file_path='songs.csv', workers=10, has_vector=True)
	work(file_path='users.csv', workers=10, has_vector=False)
	work(file_path='playlists.csv', workers=50, has_vector=True)
	work(file_path='playlist_songs.csv', workers=90, has_vector=False)
	work(file_path='user_songs.csv', workers=90, has_vector=False)

	print('finished')

