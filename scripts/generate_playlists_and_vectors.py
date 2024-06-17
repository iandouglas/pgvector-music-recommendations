import csv
import os
import pickle
import string

import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import tqdm
import gensim


if not os.path.exists('playlists.csv'):
    meta = pd.read_csv('track_meta.csv', sep='\t')
    meta['song_id'] = meta['song_id'].astype(int)
    meta['song_name'] = meta['song_name'].astype(str)
    meta['band'] = meta['band'].astype(str)

    id_to_band = meta.set_index('song_id')['band'].to_dict()

    for chunk in pd.read_csv('user_favorites.csv', sep='\t',
                                    iterator=True,
                                    chunksize=1000000,
                                    lineterminator='\n',
                                    # remove this to use whole dataset
                                    #    nrows=5000000,
                                    ):

        chunk.columns = ['user', 'track']
        chunk['band'] = chunk['track'].apply(lambda song_id: id_to_band.get(song_id, ''))
        chunk = chunk.groupby('user')['band'].apply(','.join).reset_index()

        chunk[['band']].to_csv('playlists.csv', header=None, index=None, mode='a')

# open songs.csv and pull song_id values into a list
songs = pd.read_csv('songs.csv', sep='\t')
songs['song_id'] = songs['song_id'].astype(int)
song_ids = songs['song_id'].tolist()

# open user_favorites.csv and remove any rows where the song_id is not in the song_ids list
favorites = pd.read_csv('user_favorites.csv', sep='\t')
favorites['user'] = favorites['user'].astype(int)
favorites['item'] = favorites['item'].astype(int)

favorites = favorites[favorites['item'].isin(song_ids)]
# write back to the file
favorites.to_csv('user_favorites.csv', sep='\t', index=False)



# train Word2Vec and save data for later if it doesn't already exist
if not os.path.exists('w2v_small.pkl'):
    class TextToW2V(object):
        def __init__(self, file_path):
            self.file_path = file_path


        def __iter__(self):
            for line in open(self.file_path, 'r'):
                yield line.lower().split(',')[::-1]  # reverse order (make old -> new)

    playlists = TextToW2V('playlists.csv')

    estimator = gensim.models.Word2Vec(
        playlists,
        vector_size=100,
        window=15,
        min_count=30,
        sg=1,
        workers=50,
        epochs=10,
        ns_exponent=0.8,
        )

    with open('w2v_small.pkl', 'wb') as f:
        pickle.dump(estimator, f)
    
# open w2v_small.pkl and un-pickle it back into estimator
with open('w2v_small.pkl', 'rb') as f:
    estimator = pickle.load(f)

band_vectors = {band: estimator.wv[band] for band in estimator.wv.index_to_key}
if not os.path.exists('band_vectors.csv'):
    # write vector data is csv
    with open('band_vectors.csv', 'w') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(['band', 'vector'])
        for band, vector in band_vectors.items():
            writer.writerow([band, vector.tolist()])

# user_music = ['the grateful dead', 'nine inch nails', 'haken']
# user_music = [m.lower().strip() for m in user_music]
# predicted = estimator.predict_output_word(user_music)

# print([a[0] for a in predicted if a[0] not in user_music])
