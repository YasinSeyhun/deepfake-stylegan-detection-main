import os
import json
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSONL_PATH = os.getenv("INBOX_CACHE", os.path.join(PROJECT_ROOT, "app/inbox_cache.jsonl"))
DAYS_KEEP = int(os.getenv("DAYS_KEEP", 30))

cutoff = datetime.utcnow() - timedelta(days=DAYS_KEEP)
kept = []
removed = 0

if os.path.exists(JSONL_PATH):
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                date_str = obj.get("date")
                if date_str:
                    try:
                        dt = datetime.strptime(date_str[:19], "%a, %d %b %Y %H:%M:%S")
                    except Exception:
                        try:
                            dt = datetime.fromisoformat(date_str)
                        except Exception:
                            dt = None
                    obj["_parsed_date"] = dt
                else:
                    obj["_parsed_date"] = None
                kept.append(obj)
            except Exception:
                kept.append(obj)
    # En güncel 20 maili bırak
    kept = sorted(kept, key=lambda x: x.get("_parsed_date") or datetime.min, reverse=True)[:20]
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for obj in kept:
            obj.pop("_parsed_date", None)
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"[inbox_cache_cleaner] Kept {len(kept)} newest mails.")
else:
    print(f"[inbox_cache_cleaner] No file found: {JSONL_PATH}") 