from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncpg
import numpy as np
from typing import List
from contextlib import asynccontextmanager
from config import PG_URL

app = FastAPI()

pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(PG_URL)
    yield
    await pool.close()

app.router.lifespan_context = lifespan

class Recommendation(BaseModel):
    band: str
    similarity: str

@app.get("/api/v1/recommend", response_model=List[Recommendation])
async def recommend(band: str):
    async with pool.acquire() as connection:
        # Get the vector of the input band
        band_vector = await connection.fetchval(
            "SELECT vector FROM music_vectors WHERE band_name = $1", band
        )
        if not band_vector:
            raise HTTPException(status_code=404, detail="Band not found")
        
        # Find the most similar bands based on the vector
        recommendations = await connection.fetch(
            """
            SELECT band_name, 1 - (vector <=> $1) AS closeness
            FROM music_vectors
            WHERE band_name != $2
            ORDER BY closeness DESC
            LIMIT 10
            """,
            band_vector, band
        )
        
        # Transform the results into a list of Recommendation models
        recommendations_list = [
            Recommendation(band=row['band_name'], similarity=f"{(round(row['closeness'] * 100, 2))}%")
            for row in recommendations
        ]

        recommendations_list.sort(key=lambda x: x.similarity, reverse=True)

        return recommendations_list

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
