#!/usr/bin/env python3
"""Sync public SoundCloud set to GitHub Pages and optionally Blogger."""
import html
import json
import os
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from yt_dlp import YoutubeDL

BASE = Path(__file__).resolve().parents[1] / "chansons"
PLAYLIST = "https://soundcloud.com/novanic/sets/novanic-de-lombre-aux-toiles"
BLOG = "https://novanic-officiel.blogspot.com/"
YOUTUBE = "https://www.youtube.com/playlist?list=PL8GEGyzX4bDi9mzJu77-WxpfRmNRtx4Aa"

def esc(s):
    return html.escape(str(s), quote=True)

def valid(url):
    try:
        u = urlparse(str(url))
        return u.scheme == "https" and u.hostname in ("soundcloud.com", "www.soundcloud.com") and len(u.path.strip("/")) > 0
    except ValueError:
        return False

def get_tracks():
    with YoutubeDL({"extract_flat":"in_playlist","quiet":True,"no_warnings":True,
                    "skip_download":True,"socket_timeout":35,"retries":2}) as ydl:
        result = ydl.extract_info(PLAYLIST, download=False)
    tracks = []
    for entry in (result or {}).get("entries") or []:
        if not entry:
            continue
        url = entry.get("webpage_url") or entry.get("url") or ""
        if url.startswith("/"):
            url = "https://soundcloud.com" + url
        if not valid(url):
            print("URL ignorée :", entry.get("title"), url)
            continue
        url = url.split("?")[0].split("#")[0]
        import hashlib
        ident = str(entry.get("id") or hashlib.sha256(url.encode()).hexdigest()[:20])
        tracks.append({"id":ident,"title":str(entry.get("title") or "Nouvelle chanson NovaNic")[:200],"url":url})
    if not tracks:
        raise RuntimeError("Aucun morceau accessible : état inchangé. Vérifier SoundCloud / yt-dlp.")
    return list({t["id"]:t for t in tracks}.values())

def iframe(url):
    return '<iframe title="Écouter sur SoundCloud" src="https://w.soundcloud.com/player/?url='+quote(url,safe="")+'" width="100%" height="166" style="border:0;border-radius:10px" loading="lazy" allow="autoplay"></iframe>'

def article(t):
    return ('<article style="background:#1e122e;color:#fff;padding:26px;border-radius:20px;font:16px/1.7 Arial">'
        '<p style="color:#ffd37f">✦ NovaNic — De l’ombre aux étoiles</p>'
        '<h1 style="color:#ffd37f">'+esc(t["title"])+'</h1>'
        '<p>Découvrez ce morceau de NovaNic, disponible dans la playlist officielle.</p>'
        +iframe(t["url"])+'<p><a style="color:#ffd37f" href="'+esc(t["url"])+'">🎵 Écouter sur SoundCloud</a></p>'
        '<p><a style="color:#ffd37f" href="'+esc(YOUTUBE)+'">▶ Playlist YouTube</a></p>'
        '<p>« Pas un empire. Une maison. » 💜</p></article>')

def request_json(url, headers=None, data=None):
    body=json.dumps(data).encode() if data is not None else None
    req=Request(url,data=body,headers={"Accept":"application/json",**({"Content-Type":"application/json"} if body else {}),**(headers or {})},method="POST" if body else "GET")
    try:
        with urlopen(req,timeout=40) as response:
            return json.loads(response.read())
    except HTTPError as err:
        raise RuntimeError("HTTP "+str(err.code)+": "+err.read().decode(errors="replace")[:350]) from err

def blogger_token():
    keys=["BLOGGER_CLIENT_ID","BLOGGER_CLIENT_SECRET","BLOGGER_REFRESH_TOKEN"]
    if not all(os.getenv(k) for k in keys):
        return None
    form=urlencode({"client_id":os.environ[keys[0]],"client_secret":os.environ[keys[1]],
                    "refresh_token":os.environ[keys[2]],"grant_type":"refresh_token"}).encode()
    req=Request("https://oauth2.googleapis.com/token",data=form,
                headers={"Content-Type":"application/x-www-form-urlencoded"})
    with urlopen(req,timeout=35) as response:
        return json.loads(response.read())["access_token"]

def post_blogger(t,token):
    headers={"Authorization":"Bearer "+token}
    blog_id=os.getenv("BLOGGER_BLOG_ID") or request_json(
        "https://www.googleapis.com/blogger/v3/blogs/byurl?"+urlencode({"url":BLOG}),headers)["id"]
    draft=os.getenv("BLOGGER_AS_DRAFT","false").lower()=="true"
    url="https://www.googleapis.com/blogger/v3/blogs/"+quote(str(blog_id),safe="")+"/posts?isDraft="+str(draft).lower()
    return request_json(url,headers,{"kind":"blogger#post","title":"🎵 "+t["title"]+" — NovaNic",
                  "content":article(t),"labels":["NovaNic","Chanson","SoundCloud"]})

def catalogue(tracks):
    cards=[]
    for t in tracks:
        cards.append('<article class="card"><h2>'+esc(t["title"])+'</h2>'+iframe(t["url"])+
            '<p><a href="'+esc(t["url"])+'" target="_blank" rel="noopener noreferrer">♫ Écouter sur SoundCloud ↗</a></p></article>')
    return ('''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Les chansons — NovaNic</title><style>*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top right,#3c2554,transparent 40%),#10091b;color:#f7efff;font:16px/1.7 Arial,sans-serif}main{max-width:1100px;margin:auto;padding:35px 20px}h1{color:#ffd37f;font-size:clamp(32px,6vw,52px)}h2{color:#e0b8ff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:20px}.card{background:#211431;border:1px solid #76559b;padding:22px;border-radius:18px}a{color:#ffd37f}footer{padding:30px 0;color:#cebce1}</style></head>
<body><main><p>✦ NOVANIC — DE L’OMBRE AUX ÉTOILES</p><h1>🎵 Toutes les chansons</h1><p>Les morceaux de la playlist SoundCloud officielle.</p><div class="grid">'''
        +"\n".join(cards)+'''</div><footer>« Pas un empire. Une maison. » 💜 <a href="https://novanic-officiel.blogspot.com/">Blog officiel</a> · <a href="../">NovaNic Studio</a></footer></main></body></html>''')

def main():
    tracks=get_tracks()
    BASE.mkdir(parents=True,exist_ok=True)
    state_path=BASE/"state.json"
    if not state_path.exists():
        state={"version":1,"tracks":{t["id"]:{**t,"blogger_done":True,"baseline":True} for t in tracks}}
        print("Premier passage : chansons existantes enregistrées sans publication Blogger.")
    else:
        state=json.loads(state_path.read_text(encoding="utf-8"))
        known=state.setdefault("tracks",{})
        for t in tracks:
            if t["id"] not in known:
                known[t["id"]]={**t,"blogger_done":False,"baseline":False}
                print("Nouvelle chanson :",t["title"])
            else:
                known[t["id"]].update(t)
    token=None
    try:
        token=blogger_token()
    except Exception as exc:
        print("Connexion Blogger non disponible :",exc)
    if token:
        for t in state["tracks"].values():
            if t.get("blogger_done"):
                continue
            try:
                response=post_blogger(t,token)
                t["blogger_done"]=True
                t["blogger_url"]=response.get("url","")
                print("Article Blogger créé :",t["title"])
            except Exception as exc:
                print("Blogger : échec, une nouvelle tentative aura lieu :",t["title"],exc)
    else:
        print("Blogger en attente : configurer les secrets OAuth.")
    (BASE/"data.json").write_text(json.dumps(tracks,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (BASE/"index.html").write_text(catalogue(tracks),encoding="utf-8")
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Catalogue mis à jour :",len(tracks),"chansons")

if __name__=="__main__":
    main()
