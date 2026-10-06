"""
App Description Index
=====================

Purpose:
- Maintain a single source of truth for app descriptions
- Support read / write / update / lookup
- Designed for RAG embedding & prompt usage

Recommended storage: JSON (stable, human-editable, versionable)
"""

# =========================
# Imports
# =========================

import json
import os
from config import load_config
from typing import Dict, Optional

# =========================
# Core Index Class
# =========================


class AppDescriptionIndex:
    def __init__(self, path: str):
        self.path = path
        self._data: Dict[str, Dict] = {}
        self.load()

    # ---------- I/O ----------

    def load(self):
        path = os.path.expanduser(self.path)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def save(self):
        path = os.path.expanduser(self.path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ---------- CRUD ----------

    def get(self, app_name: str) -> Optional[Dict]:
        return self._data.get(app_name.lower())

    def get_description(self, app_name: str) -> Optional[str]:
        entry = self.get(app_name)
        if entry:
            return entry.get("description")
        return None

    def add_or_update(
        self,
        app_name: str,
        description: str,
        language: str = "en",
        tags=None,
        last_updated: Optional[str] = None,
    ):
        self._data[app_name.lower()] = {
            "description": description.strip(),
            "language": language,
            "tags": tags or [],
            "last_updated": last_updated,
        }
        self.save()

    def exists(self, app_name: str) -> bool:
        return app_name.lower() in self._data

    def remove(self, app_name: str):
        if self.exists(app_name):
            del self._data[app_name.lower()]
            self.save()


# =========================
# Global Singleton Instance (Recommended)
# =========================


# This instance can be imported and reused across the project
app_desc_index = AppDescriptionIndex(load_config()['APP_DESC_PATH'])


# =========================
# Minimal Demo
# =========================

if __name__ == "__main__":
    index = AppDescriptionIndex("app_descriptions.json")

    index.add_or_update(
        app_name="Baidu Map",
        description="A map and navigation app for driving, walking, and public transport routes.",
        tags=["map", "navigation", "travel"],
        last_updated="2025-01-01",
    )

    print(index.get_description("baidu map"))
