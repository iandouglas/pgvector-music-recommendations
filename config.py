import os

username = os.getenv('PG_USERNAME')
password = os.getenv('PG_PASSWORD')
hostname = os.getenv('PG_HOSTNAME')
database = os.getenv('PG_DATABASE')

PG_URL = f"postgres://{username}:{password}@{hostname}/{database}"
