import os
import requests
import random
import time, datetime
from dotenv import load_dotenv

load_dotenv()
S2_API_KEY = os.getenv('S2_API_KEY')

class SemanticScholarClient:


    def __init__(self):

        if not S2_API_KEY:
            raise RuntimeError("❌ Semantic Scholar API key is not set in the environment.")
        self.api_key = S2_API_KEY

        self.seed_queries = ["Asymptomatic infection of COVID-19",
                             "Single-cell RNA sequencing",
                             "Protein-protein interactions",
                             "CRISPR gene editing",
                             "Deep learning in healthcare",
                             "Microbiome diversity and health",
                             "Cancer immunotherapy targets",
                             "Neuroscience of memory",
                             "Antibiotic resistance mechanisms",
                             "Climate change and species migration"]

        self.default_query = random.choice(self.seed_queries)
        self.fallback_cache = []
        self.fallback_index = 0
        self.fallback_page = 0
        self.seen_ids = set()
        self.last_call_time = None


    def _throttle(self):
        if self.last_call_time:
            elapsed = time.time() - self.last_call_time
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
        self.last_call_time = time.time()


    def search_paper(self, query:str, limit:int=1, offset:int=0):

        self._throttle()
        print("📡 [search_paper]", datetime.datetime.now().isoformat())

        query = query or self.default_query
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        headers = {'x-api-key': self.api_key}
        params = {"query":query,
                  "limit":limit,
                  "offset": offset,
                  "fields":"title,abstract,authors,url,paperId,publicationDate,journal,publicationTypes,openAccessPdf,externalIds,citationCount"
                 }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 429:
                print("⚠️ scholar.py: Rate limit exceeded")
                return {"error": "Rate limit exceeded. Please wait and try again shortly."}

            response.raise_for_status()
            data = response.json()
            results = data.get("data", [])
            return results if limit > 1 else (results[0] if results else {"error": "No papers found."})

        except requests.RequestException as e:
            print(f"❌ scholar.py, function search_paper: Request failed {e}")
            return {"error": f"Request failed: {str(e)}"}


    def get_recommendations(self, positive_ids, negative_ids, limit=1):

        self._throttle()
        print("📡 [get_recommended_paper]", datetime.datetime.now().isoformat())

        url = "https://api.semanticscholar.org/recommendations/v1/papers"
        headers = {'x-api-key': self.api_key,
                   'Content-Type':'application/json'
        }
        params = {
            "fields": "title,abstract,authors,url,paperId,citationCount,publicationDate,journal,publicationTypes,openAccessPdf,externalIds,citationCount",
            "limit": limit
        }
        payload = {
            "positivePaperIds" : positive_ids,
            "negativePaperIds" : negative_ids
        }

        try:
            response = requests.post(url, headers=headers, params=params, json=payload)

            if response.status_code == 429:
                print("⚠️ scholar.py, function get_recommendations: Rate limit exceeded.")
                return {"error": "Rate limit exceeded."}

            response.raise_for_status()
            papers = response.json().get("recommendedPapers", [])
            return papers if limit > 1 else (papers[0] if papers else {"error": "No recommended papers returned."})

        except requests.RequestException as e:
            print(f"❌ scholar.py, function get_recommendations: Request failed {e}")
            return {"error": f"Request failed: {str(e)}"}


    def get_fallback_paper(self, query=None):

        while True:

            # Refill the cache if need be
            if self.fallback_index >= len(self.fallback_cache):
                offset = self.fallback_page * 20
                print(f"📥 Fetching fallback page {self.fallback_page} with offset {offset}...")
                effective_query = query or self.default_query
                self.fallback_cache = self.search_paper(query=effective_query, limit=20, offset=offset)
                self.fallback_index = 0
                self.fallback_page += 1

                # Exit if no data returned
                if not isinstance(self.fallback_cache, list) or not self.fallback_cache:
                    return {"error": "No fallback papers available."}

            # Check for unseen paper
            while self.fallback_index < len(self.fallback_cache):
                paper = self.fallback_cache[self.fallback_index]
                self.fallback_index += 1

                if paper["paperId"] not in self.seen_ids:
                    self.seen_ids.add(paper["paperId"])
                    return paper


    def get_fallback_batch(self, limit=5, query=None):
        batch = []
        while len(batch) < limit:
            paper = self.get_fallback_paper(query=query)
            if isinstance(paper, dict) and "paperId" in paper:
                batch.append(paper)
            else:
                break
        return batch

    def reset_fallback_state(self):
        self.fallback_cache = []
        self.fallback_index = 0
        self.fallback_page = 0
        self.seen_ids.clear()