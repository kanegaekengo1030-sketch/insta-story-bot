#!/usr/bin/env python3
"""Instagramストーリー自動投稿（Instagram Graph API / Content Publishing API）

毎回、STORY_IMAGE_URLS に並べた画像を順番にストーリーとして投稿します。
必要な環境変数:
  IG_USER_ID       InstagramビジネスアカウントのID（数字）
  IG_ACCESS_TOKEN  アクセストークン
  STORY_IMAGE_URLS 画像URLをカンマ区切りで（例: https://.../1.jpg,https://.../2.jpg）
任意:
  STORY_MENTIONS_1 / STORY_MENTIONS_2 ... i枚目のメンション（カンマ区切り。@ありなしどちらでも可）
  STORY_MENTIONS   全部の枚に共通のメンション（_1などが無い枚に使われる）
  STORY_MENTION_POS メンションの位置 "x,y"（テスト用・任意）
  GRAPH_VERSION    既定 v25.0
  DRY_RUN          1 にすると投稿せず確認だけ
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = os.environ.get("GRAPH_VERSION", "v25.0")
# Instagramログイン方式のトークン → graph.instagram.com（初期値）
# Facebookログイン方式のトークン → graph.facebook.com に変える
HOST = os.environ.get("GRAPH_HOST", "graph.instagram.com")
BASE = f"https://{HOST}/{VERSION}"


def call(method, path, params):
    url = f"{BASE}/{path}"
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        # トークンが表示されないよう、パラメータは出さない
        raise RuntimeError(f"API error {e.code} on {path}: {body}") from None


def post_story(user_id, token, image_url, mentions=None):
    # 1) コンテナ作成
    params = {
        "media_type": "STORIES",
        "image_url": image_url,
        "access_token": token,
    }
    if mentions:
        # メンション（スタンプなし）。ユーザー名は @ なしで渡す
        tags = []
        for m in mentions:
            parts = m.split(":")  # 例 "name" または "name:0.63:0.22"（名前:x:y）
            tag = {"username": parts[0]}
            if len(parts) == 3:
                tag["x"], tag["y"] = float(parts[1]), float(parts[2])
            tags.append(tag)
        # 任意：位置（x,y）を指定するテスト用。例 "0.5,0.5"（範囲は未確認なので、まず空でテスト）
        pos = os.environ.get("STORY_MENTION_POS", "").strip()
        if pos:
            x, y = (float(v) for v in pos.split(","))
            for t in tags:
                t.setdefault("x", x)
                t.setdefault("y", y)
        params["user_tags"] = json.dumps(tags)
    created = call("POST", f"{user_id}/media", params)
    container_id = created["id"]

    # 2) 処理完了を待つ（最大約60秒）
    for _ in range(20):
        status = call("GET", container_id, {
            "fields": "status_code",
            "access_token": token,
        }).get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {container_id} status={status}")
        time.sleep(3)
    else:
        raise RuntimeError(f"container {container_id} が時間内に完了しませんでした")

    # 3) 公開
    published = call("POST", f"{user_id}/media_publish", {
        "creation_id": container_id,
        "access_token": token,
    })
    return published["id"]


def main():
    user_id = os.environ.get("IG_USER_ID", "").strip()
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    urls = [u.strip() for u in os.environ.get("STORY_IMAGE_URLS", "").split(",") if u.strip()]
    dry = os.environ.get("DRY_RUN") == "1"
    def mentions_for(i):
        # i枚目専用の STORY_MENTIONS_1, _2 … があればそれを使い、なければ STORY_MENTIONS を使う
        raw = os.environ.get(f"STORY_MENTIONS_{i}") or os.environ.get("STORY_MENTIONS", "")
        return [m.strip().lstrip("@") for m in raw.split(",") if m.strip()]

    if not (user_id and token and urls):
        print("IG_USER_ID / IG_ACCESS_TOKEN / STORY_IMAGE_URLS が足りません", file=sys.stderr)
        sys.exit(2)

    failed = []
    for i, url in enumerate(urls, 1):
        if dry:
            print(f"[DRY_RUN] {i}枚目を投稿予定: {url}")
            continue
        # 1枚ごとに最大3回まで試す（一時的な失敗対策。成功済みの枚数は再投稿しない）
        for attempt in range(1, 4):
            try:
                media_id = post_story(user_id, token, url, mentions_for(i))
                print(f"{i}枚目 投稿OK media_id={media_id}")
                break
            except Exception as e:  # noqa: BLE001
                print(f"{i}枚目 失敗({attempt}/3): {e}", file=sys.stderr)
                if attempt < 3:
                    time.sleep(30)
        else:
            failed.append(i)
        time.sleep(5)  # 順番が入れ替わらないよう少し待つ

    if failed:
        # 失敗で終了コード1にする → GitHubが失敗として記録・通知する
        print(f"投稿に失敗した枚数番号: {failed}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
