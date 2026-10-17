"""Instagramの長期トークンを60日延ばし、新しいトークンだけを標準出力に出す。
(トークンはログに出さない。ログ用の情報は標準エラー出力に出す)"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

token = os.environ.get("IG_ACCESS_TOKEN", "")
if not token:
    print("ERROR: IG_ACCESS_TOKEN is empty", file=sys.stderr)
    sys.exit(1)

url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "ig_refresh_token", "access_token": token}
)
try:
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", "replace")
    body = body.replace(token, "***")
    print(f"ERROR: HTTP {e.code}: {body}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {type(e).__name__}", file=sys.stderr)
    sys.exit(1)

new = data.get("access_token")
if not new:
    print("ERROR: no access_token in response", file=sys.stderr)
    sys.exit(1)
days = int(data.get("expires_in", 0)) // 86400
print(f"OK: refreshed, valid for about {days} days", file=sys.stderr)
print(new)

