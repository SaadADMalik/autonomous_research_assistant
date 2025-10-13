import hashlib
import json
import os

class QueryCache:
    def __init__(self, cache_dir="data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_key(self, query):
        return hashlib.md5(query.lower().encode()).hexdigest()
    
    def get(self, query):
        cache_file = os.path.join(self.cache_dir, f"{self._get_cache_key(query)}.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)
        return None
    
    def set(self, query, result):
        cache_file = os.path.join(self.cache_dir, f"{self._get_cache_key(query)}.json")
        with open(cache_file, 'w') as f:
            json.dump(result, f)