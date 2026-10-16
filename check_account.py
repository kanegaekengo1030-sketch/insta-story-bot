#!/usr/bin/env python3
"""トークンが使えるか確認し、アカウントのIDとユーザー名を表示する（トークン自体は表示しない）。"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HOST = os.environ.get("GRAPH_HOST", "graph.instagram.com")
VERSION = os.environ.get("GRAPH_VERSION", "v25.0")
token = os.environ.get("IG_ACCESS_TOKEN", "").strip()

if not token:
    print("IG_ACCESS_TOKEN が登録されていません", file=sys.stderr)
    sys.exit(2)

query = urllib.parse.urlencode({"fields": "user_id,username", "access_token": token})
url = f"https://{HOST}/{VERSION}/me?{query}"
try:
    with urllib.request.urlopen(url, timeout=30) as res:
        data = json.loads(res.read().decode())
except urllib.error.HTTPError as e:
    print(f"API error {e.code}: {e.read().decode(errors='replace')}", file=sys.stderr)
    sys.exit(1)

print("確認OK")
print("user_id  :", data.get("user_id") or data.get("id"))
print("username :", data.get("username"))
