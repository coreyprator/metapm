"""Verify ArtForge requirement insertion into MetaPM."""
import urllib.request
import json

BASE = "https://metapm.rentyourcio.com"

with urllib.request.urlopen(f"{BASE}/api/requirements?project=ArtForge", timeout=30) as resp:
    data = json.loads(resp.read())

reqs = data.get("requirements", [])
af = [r for r in reqs if r.get("code", "").startswith("AF-")]
af_sorted = sorted(af, key=lambda x: x.get("code", ""))

print(f"Total ArtForge requirements: {len(af)}")
print()
for r in af_sorted:
    print(f"  {r['code']}: {r['title']} [{r['status']}, {r['priority']}]")
print()

for code in ["AF-015", "AF-019", "AF-028"]:
    r = next((x for x in af if x["code"] == code), None)
    if r:
        print(f"{code} spot-check:")
        print(f"  title: {r['title']}")
        print(f"  priority: {r['priority']}, status: {r['status']}, type: {r.get('type','?')}")
        print(f"  desc[0:150]: {(r.get('description') or '')[:150]}")
        print()
    else:
        print(f"{code}: NOT FOUND")
        print()
