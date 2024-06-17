# Music Recommendations using pgvector and gensim

The goal of this project is to build a music recommendation system based on songs by bands that users have liked. The system used the `gensim` library to build a Word2Vec model offline, and the `pgvector` extension to store the vectors in a PostgreSQL database for retrieval from an API.

## What is a "vector"

In the context of machine learning, a "vector" is a numerical representation of data. Vectors are used to represent features or characteristics of data points in a structured way that can be processed by machine learning algorithms, using an ordered array of numbers that represents data in a multi-dimensional space. Each number in the vector is called a "component" or "element".

Vectors can be thought of as points or directions in a multi-dimensional space, where each dimension corresponds to a feature of the data.

This project uses natural language processing (NLP), where vectors (or embeddings) represent words (such as the name of a band) in a continuous vector space where semantically similar words are close to each other. In this project, the vectors also account for the popularity of the band based on how many users liked songs by that band.

In this API application, if a user likes songs by Maroon 5 and Ed Sheeran, searching for one of those bands will return the other band as a "similar" result.

## What is `gensim`

[`gensim`](https://github.com/piskvorky/gensim) is a popular open-source Python library designed for topic modeling, document indexing, and similarity retrieval with large corpora. It is particularly well-suited for natural language processing (NLP) tasks and is widely used in industry and academia. It is designed to handle large text corpora efficiently. It supports distributed computing, can process data that doesn't fit into memory, and allows querying for similarity between documents or words using vector space models.

## What is `pgvector`

[`pgvector`](https://github.com/pgvector/pgvector) is an open-source PostgreSQL extension that provides support for vector data types and similarity search. This extension allows you to store, index, and query high-dimensional vector data directly within a PostgreSQL database, enabling efficient similarity searches, such as those needed for machine learning and data science applications.

`pgvector` is supported at Render. See the [Render documentation](https://render.com/docs/deploy-postgres-pgvector) for more information.

## Source data

The source data for this project started from [this user on Kaggle](https://www.kaggle.com/datasets/usasha/million-music-playlists?resource=download). The dataset claimed 100M rows of data.

After cleaning the data to only include printable ASCII characters, and removing song titles that contained obscenities or offensive language, along with some repetitive data (the same song_id was listed over and over with different titles), the dataset was reduced to about 25M rows. The file called `user_item_interaction.csv` was renamed to `user_favorites.csv` and the `track_meta.csv` file was renamed to `songs.csv`.

More work could be done to clean up the band names, as there are many variations of the same band name in the data. For example, "The Beatles" is listed as "Beatles", "The Beatles", "Beatles, The", and "The Beatles". This could be normalized into a separate table in PostgreSQL to reduce the size of the data.

## The preparation scripts and process

The project started with a Python script called `generate_fake_data.py` which used the Faker library to generate fake usernames, bands, song titles and such, and also included many features not used in the final API. Since there was no easy way to tell which bands were similar to each other, the new data source was used instead.

The new `generate_playlist_and_vectors.py` script uses the CSV data to produce a "playlist" of all bands favorited by a user and stored into a new `playlists.csv` file.

The "user_favorites.csv" file was then scrubbed of any song_id that wasn't present in the "songs.csv" file.

The final song list was just under 5 million songs, and the favorites was about 24 million rows.

Next, we used the `gensim` libraary to build a Word2Vec model of the songs and bands, using a vector size of 100. This process took 15 to 20 minutes on a MacBook Pro M2 Max. The final data was "pickled" and stored in a file so the data would not need to be retrained later.

Finally, the vector data was extracted from the `gensim` model, and exported into a final CSV file called `band_vectors.csv`.

## Loading the database

The source data turns into about 3GB of PostgreSQL data. This could be reduced if the band names were normalized into a separate lookup table in PostgreSQL.

The `load_data.py` script uses Python's `multiprocessing` library to load the data into the database using multiple threads since Render will allow nearly 100 client connections to the database. Each thread would connect to the database, load 1000 rows of CSV data, commit the data, and then close the connection. To avoid problems with rapid connections, each thread would sleep for 200ms before ending.

## The API

The API is a simple FastAPI implementation using `asyncpg` and a `pydantic` model to return the data. The API is a single endpoint that takes a band name and returns similar bands to the one provided. If the band is not found, the API returns a 404 error with a "band not found" error.

Typical usage:

`curl -X 'GET' 'https://your-application.onrender.com/api/v1/recommend?band=Maroon%205'`
