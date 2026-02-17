import json
import os
import config
import logger

class Registry:
    def __init__(self):
        self.path = os.path.join(config.DOWNLOAD_DIR, config.REGISTRY_FILE)
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    return json.load(f)
            except: pass
        return {"ids": [], "queries": {}}

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def is_downloaded(self, query, ytid=None):
        """
        Flexible check:
        - If ytid is provided: Checks query OR ytid.
        - If only one arg provided: Checks if that arg exists as a key OR a value.
        """
        # Check if the query itself is a known key (Search string or ID)
        if query in self.data["queries"]:
            return True

        # Check if the ID exists in the master ID list
        if ytid and ytid in self.data["ids"]:
            return True

        # Fallback: if 'query' is actually an ID passed as the first arg
        if query in self.data["ids"]:
            return True

        return False

    def add(self, query, ytid):
        if ytid not in self.data["ids"]:
            self.data["ids"].append(ytid)
        self.data["queries"][query] = ytid

    def sync_with_disk(self, existing_ids):
        """
        Removes IDs and Queries from the registry if they
        are no longer present on the hard drive.
        """
        initial_count = len(self.data["ids"])

        # 1. Filter IDs: Keep only those found in the RAM index
        self.data["ids"] = [ytid for ytid in self.data["ids"] if ytid in existing_ids]

        # 2. Filter Queries: Remove queries that point to missing IDs
        # We create a new dictionary to avoid "RuntimeError: dictionary changed size during iteration"
        new_queries = {}
        for query, ytid in self.data["queries"].items():
            # Remove any existing entries that are playlist URLs
            if "list=" in query.lower():
                continue
            if ytid in existing_ids:
                new_queries[query] = ytid

        self.data["queries"] = new_queries

        removed = initial_count - len(self.data["ids"])
        if removed > 0:
            logger.log(4, f"   - Registry Sync: Removed {removed} entries for missing files.")
            self.save()
