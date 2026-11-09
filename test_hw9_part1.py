import logging

from inspection_cache import InspectionCache

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

cache = InspectionCache()

# Replace 1 with your actual inspection ID.
inspection_id = 10016

print("=== Testing Counter ===", flush=True)

for i in range(1, 26):
    count = cache.increment_inspection_views(inspection_id)
    print(f"Access #{i}: Total = {count}", flush=True)