from fastapi  import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.scholar import SemanticScholarClient


app = FastAPI()
SemanticScholar = SemanticScholarClient()

origins = [
    "https://paperproj.github.io",
    "http://localhost:5173",
]

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )


@app.get("/feed")
def fetch_papers(limit: int = 1, field: str = None):
    return SemanticScholar.get_fallback_batch(limit=limit, query=field)


@app.post("/recommendations")
async def recommendations(request: Request):

    payload = await request.json()
    positive_ids = payload.get("positivePaperIds", [])
    negative_ids = payload.get("negativePaperIds", [])

    if not positive_ids or not negative_ids:
        print("⚠️ main.py: /recommendations: No liked/disliked papers, returning fallback.")
        return [SemanticScholar.get_fallback_paper() for _ in range(5)]

    batch = SemanticScholar.get_recommendations(
        positive_ids=positive_ids,
        negative_ids=negative_ids,
        limit=5)

    if isinstance(batch, dict) and "error" in batch:
        print("⚠️ main.py: /recommendations. Error, returning fallback")
        return [SemanticScholar.get_fallback_paper() for _ in range(5)]

    return batch if isinstance(batch, list) else [batch]

@app.post("/reset-fallback")
def reset_fallback():
    SemanticScholar.reset_fallback_state()
    return {"status": "fallback state reset"}
