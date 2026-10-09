#!/usr/bin/env python3
"""NovaNic: synchronise une playlist SoundCloud, GitHub Pages, annonces et Blogger.

Dépendance : yt-dlp. Aucune donnée secrète n'est inscrite dans les pages publiques.
"""
import hashlib
import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from yt_dlp import YoutubeDL

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "chansons"
ANNOUNCES = ROOT / "annonces"
PLAYLIST = "https://soundcloud.com/novanic/sets/novanic-de-lombre-aux-toiles"
BLOG = "https://novanic-officiel.blogspot.com/"
YOUTUBE = "https://www.youtube.com/playlist?list=PL8GEGyzX4bDi9mzJu77-WxpfRmNRtx4Aa"
FACEBOOK = "https://www.facebook.com/NovaNic.officiel/"
GENERIC = {"", "Nouvelle chanson NovaNic", "NA", "None"}

def esc(value):
    return html.escape(str(value or ""), quote=True)

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def safe_url(value, hosts=None):
    try:
        u = urlparse(str(value or ""))
        if u.scheme != "https" or not u.hostname or u.username or u.password:
            return ""
        if hosts and u.hostname.lower() not in hosts:
            return ""
        return u.geturl()
    except (ValueError, TypeError):
        return ""

def slug_title(url):
    slug = urlparse(url).path.strip("/").split("/")[-1]
    words = re.sub(r"[-_]+", " ", slug).strip()
    return words[:180].title() or "Chanson NovaNic"

def filename(track_id):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", str(track_id))[:100]

def get_tracks():
    with YoutubeDL({"extract_flat": "in_playlist", "quiet": True, "no_warnings": True,
                    "skip_download": True, "socket_timeout": 35, "retries": 2}) as ydl:
        playlist = ydl.extract_info(PLAYLIST, download=False)
    result = []
    for item in (playlist or {}).get("entries") or []:
        if not item:
            continue
        url = str(item.get("webpage_url") or item.get("url") or "")
        if url.startswith("/"):
            url = "https://soundcloud.com" + url
        url = safe_url(url, {"soundcloud.com", "www.soundcloud.com"})
        if not url or len(urlparse(url).path.strip("/").split("/")) < 2:
            continue
        url = url.split("?")[0].split("#")[0]
        ident = str(item.get("id") or hashlib.sha256(url.encode()).hexdigest()[:20])
        title = str(item.get("title") or "").strip()
        if title in GENERIC or title.lower() in {"unknown", "untitled"}:
            title = slug_title(url)
        cover = safe_url(item.get("thumbnail") or item.get("artwork_url"))
        result.append({"id": ident, "title": title[:200], "url": url,
                       "cover": cover, "description": str(item.get("description") or "")[:500]})
    if not result:
        raise RuntimeError("Playlist SoundCloud inaccessible ou vide : aucune donnée écrasée.")
    return list({t["id"]: t for t in result}.values())

def iframe(url):
    return ('<iframe title="Écouter sur SoundCloud" loading="lazy" '
            'src="https://w.soundcloud.com/player/?url=' + quote(url, safe="") +
            '" width="100%" height="166" style="border:0;border-radius:12px" allow="autoplay"></iframe>')

def cover_html(t):
    url = safe_url(t.get("cover"))
    return ('<img src="' + esc(url) + '" alt="Pochette de ' + esc(t["title"]) +
            '" loading="lazy" style="width:100%;max-height:310px;object-fit:cover;border-radius:14px">') if url else ""

def marker(t):
    return "novanic-soundcloud-id:" + str(t["id"])

def article(t):
    return ('<article style="background:#1e122e;color:#fff;padding:26px;border-radius:20px;font:16px/1.7 Arial">'
            '<!-- ' + esc(marker(t)) + ' -->'
            '<p style="color:#ffd37f">✦ NovaNic — De l’ombre aux étoiles</p>'
            '<h1 style="color:#ffd37f">' + esc(t["title"]) + '</h1>' + cover_html(t) +
            '<p>Découvrez ce morceau de NovaNic, disponible dans la playlist officielle.</p>' +
            iframe(t["url"]) +
            '<p><a style="color:#ffd37f" href="' + esc(t["url"]) +
            '" target="_blank" rel="noopener noreferrer">🎵 Écouter sur SoundCloud</a></p>'
            '<p><a style="color:#ffd37f" href="' + esc(YOUTUBE) +
            '" target="_blank" rel="noopener noreferrer">▶ Playlist YouTube</a></p>'
            '<p>« Pas un empire. Une maison. » 💜</p></article>')

def request_json(url, headers=None, data=None, method=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = Request(url, data=body, method=method or ("POST" if body else "GET"),
                  headers={"Accept": "application/json",
                           **({"Content-Type": "application/json"} if body else {}),
                           **(headers or {})})
    try:
        with urlopen(req, timeout=35) as response:
            return json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError("Blogger HTTP " + str(error.code)) from error

def blogger_token():
    keys = ("BLOGGER_CLIENT_ID", "BLOGGER_CLIENT_SECRET", "BLOGGER_REFRESH_TOKEN")
    if not all(os.getenv(key) for key in keys):
        return None
    form = urlencode({"client_id": os.environ[keys[0]], "client_secret": os.environ[keys[1]],
                      "refresh_token": os.environ[keys[2]], "grant_type": "refresh_token"}).encode()
    req = Request("https://oauth2.googleapis.com/token", data=form,
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urlopen(req, timeout=35) as response:
        return json.loads(response.read())["access_token"]

def blog_id(token):
    if os.getenv("BLOGGER_BLOG_ID"):
        return os.environ["BLOGGER_BLOG_ID"]
    return str(request_json("https://www.googleapis.com/blogger/v3/blogs/byurl?" +
                            urlencode({"url": BLOG}),
                            {"Authorization": "Bearer " + token})["id"])

def find_existing_blogger_post(track, token, blog):
    """Vérifie les articles existants avant tout POST pour limiter les doublons."""
    headers = {"Authorization": "Bearer " + token}
    base = "https://www.googleapis.com/blogger/v3/blogs/" + quote(str(blog), safe="") + "/posts"
    for status in ("live", "draft"):
        page = ""
        for _ in range(20):
            params = {"fetchBodies": "true", "maxResults": "500", "status": status}
            if page:
                params["pageToken"] = page
            result = request_json(base + "?" + urlencode(params), headers)
            for post in result.get("items", []):
                if marker(track) in str(post.get("content") or ""):
                    return post
            page = result.get("nextPageToken", "")
            if not page:
                break
        else:
            raise RuntimeError("Recherche Blogger incomplète : publication reportée.")
    return None

def post_blogger(track, token, blog):
    previous = find_existing_blogger_post(track, token, blog)
    if previous:
        return previous, True
    draft = os.getenv("BLOGGER_AS_DRAFT", "true").lower() != "false"
    endpoint = ("https://www.googleapis.com/blogger/v3/blogs/" +
                quote(str(blog), safe="") + "/posts?isDraft=" + str(draft).lower())
    response = request_json(endpoint, {"Authorization": "Bearer " + token},
                            {"kind": "blogger#post", "title": "🎵 " + track["title"] + " — NovaNic",
                             "content": article(track),
                             "labels": ["NovaNic", "Chanson", "SoundCloud"]})
    return response, False

def announcement(t):
    return ("# 🎵 " + t["title"] + " — NovaNic\n\n"
            "Une nouvelle chanson rejoint l'univers NovaNic ! 💜✨\n\n"
            "🎧 Écouter sur SoundCloud : " + t["url"] + "\n\n"
            "🌟 Retrouvez toutes les chansons : https://zlormann.github.io/novanic-studio/chansons/\n\n"
            "« Pas un empire. Une maison. »\n"
            "« Personne devant, personne laissé derrière soi. »\n\n"
            "#NovaNic #NovaTeam #NouvelleChanson\n")

def css():
    return """<style>*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top right,#422654,transparent 42%),#10091b;color:#f7efff;font:16px/1.7 Arial,sans-serif}main{max-width:1150px;margin:auto;padding:35px 20px}h1{color:#ffd37f;font-size:clamp(30px,5vw,50px)}h2{color:#e0b8ff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:20px}.card{background:#211431;border:1px solid #76559b;padding:22px;border-radius:18px}a{color:#ffd37f}.muted{color:#c9b8da}.cover{width:100%;height:220px;object-fit:cover;border-radius:12px}footer{padding:30px 0;color:#cebce1}code{overflow-wrap:anywhere}</style>"""

def page(title, body):
    return ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + esc(title) + ' — NovaNic</title>' + css() +
            '</head><body><main>' + body +
            '<footer>« Pas un empire. Une maison. » 💜 · '
            '<a href="https://novanic-officiel.blogspot.com/">Blog officiel</a> · '
            '<a href="../">NovaNic Studio</a></footer></main></body></html>')

def write_pages(tracks, state):
    BASE.mkdir(parents=True, exist_ok=True)
    ANNOUNCES.mkdir(parents=True, exist_ok=True)
    cards, announcements = [], []
    for t in tracks:
        file_id = filename(t["id"])
        image = ('<img class="cover" src="' + esc(t["cover"]) + '" alt="Pochette ' +
                 esc(t["title"]) + '" loading="lazy">') if t.get("cover") else ""
        cards.append('<article class="card">' + image + '<h2>' + esc(t["title"]) +
                     '</h2><p class="muted">NovaNic • SoundCloud</p>' + iframe(t["url"]) +
                     '<p><a href="' + file_id + '.html">Découvrir la chanson →</a></p></article>')
        (BASE / (file_id + ".html")).write_text(page(t["title"],
            '<p>✦ DE L’OMBRE AUX ÉTOILES</p><h1>' + esc(t["title"]) + '</h1>' +
            '<div class="card">' + cover_html(t) + '<p>Une chanson de NovaNic, '
            'à découvrir dans la playlist officielle.</p>' + iframe(t["url"]) +
            '<p><a href="' + esc(t["url"]) + '" target="_blank" rel="noopener noreferrer">'
            'Écouter sur SoundCloud ↗</a></p></div><p><a href="./">← Toutes les chansons</a></p>'),
            encoding="utf-8")
        # Les annonces des morceaux initiaux restent accessibles, mais sont
        # identifiées comme archives pour éviter de les annoncer comme nouveautés.
        if state["tracks"].get(t["id"], {}).get("baseline"):
            continue
        (ANNOUNCES / (file_id + ".md")).write_text(announcement(t), encoding="utf-8")
        announcements.append('<article class="card"><h2>' + esc(t["title"]) +
                             '</h2><p><a href="' + file_id +
                             '.md">Copier le texte de l’annonce ↗</a></p></article>')
    (BASE / "index.html").write_text(page("Toutes les chansons",
        '<p>✦ NOVANIC — DE L’OMBRE AUX ÉTOILES</p><h1>🎵 Toutes les chansons</h1>'
        '<p>Catalogue synchronisé avec la playlist SoundCloud officielle.</p>'
        '<p><a href="../annonces/">Annonces NovaTeam</a> · '
        '<a href="../journal/">Journal de synchronisation</a></p>'
        '<div class="grid">' + "\n".join(cards) + '</div>'), encoding="utf-8")
    (ANNOUNCES / "index.html").write_text(page("Annonces NovaTeam",
        '<p>✦ NOVATEAM</p><h1>📣 Annonces prêtes à partager</h1>'
        '<p>Ces textes ne sont pas publiés automatiquement sur Facebook.</p>'
        '<div class="grid">' + ("\n".join(announcements) or
                               '<p>Aucune nouvelle chanson depuis l’activation.</p>') + '</div>'),
        encoding="utf-8")

def log_event(log, kind, detail):
    log.append({"at": now(), "type": kind, "detail": str(detail)[:220]})
    del log[:-100]

def write_journal(events, state, count):
    folder = ROOT / "journal"
    folder.mkdir(exist_ok=True)
    (folder / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    rows = "".join('<tr><td>' + esc(e["at"]) + '</td><td>' + esc(e["type"]) +
                   '</td><td>' + esc(e["detail"]) + '</td></tr>' for e in reversed(events))
    statuses = {}
    for t in state["tracks"].values():
        s = t.get("blogger_status", "archive" if t.get("baseline") else "en attente")
        statuses[s] = statuses.get(s, 0) + 1
    summary = " • ".join(esc(k) + " : " + str(v) for k, v in statuses.items())
    body = ('<p>✦ NOVANIC — AUTOMATISATION</p><h1>📋 Journal de synchronisation</h1>'
            '<p>Chansons détectées : ' + str(count) + '</p><p>' + summary + '</p>'
            '<p class="muted">Les erreurs techniques ne contiennent ni jetons ni secrets.</p>'
            '<div class="card" style="overflow-x:auto"><table style="width:100%;text-align:left">'
            '<thead><tr><th>Date UTC</th><th>Événement</th><th>Détail</th></tr></thead><tbody>' +
            rows + '</tbody></table></div>')
    (folder / "index.html").write_text(page("Journal de synchronisation", body), encoding="utf-8")

def main():
    BASE.mkdir(parents=True, exist_ok=True)
    state_path = BASE / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {
        "version": 2, "tracks": {}}
    first = not state_path.exists()
    state["version"] = 2
    known = state.setdefault("tracks", {})
    log_path = ROOT / "journal" / "events.json"
    events = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    tracks = get_tracks()  # Si SoundCloud échoue, ne pas toucher aux fichiers ni à l'état.
    new_count = 0
    for t in tracks:
        old = known.get(t["id"])
        if old is None:
            new_count += 1
            known[t["id"]] = {**t, "baseline": first, "blogger_done": first,
                              "blogger_status": "archive" if first else "en attente",
                              "detected_at": now()}
            if not first:
                log_event(events, "nouvelle chanson", t["title"])
        else:
            old["url"] = t["url"]
            if old.get("title") in GENERIC or (t["title"] not in GENERIC and
                                                t["title"] != slug_title(t["url"])):
                old["title"] = t["title"]
            old["cover"] = t.get("cover") or old.get("cover", "")
            old["description"] = t.get("description") or old.get("description", "")
            # Ancienne version : les morceaux initiaux ont déjà blogger_done=True.
            if old.get("baseline") and old.get("blogger_done"):
                old.setdefault("blogger_status", "archive")
    log_event(events, "synchronisation", str(len(tracks)) + " chanson(s), " +
              str(new_count if not first else 0) + " nouveauté(s)")
    token = None
    try:
        token = blogger_token()
        if token:
            blog = blog_id(token)
            for t in known.values():
                if t.get("blogger_done"):
                    continue
                try:
                    post, existed = post_blogger(t, token, blog)
                    t["blogger_done"] = True
                    t["blogger_status"] = "déjà présent" if existed else (
                        "brouillon" if os.getenv("BLOGGER_AS_DRAFT", "true").lower() != "false"
                        else "publié")
                    t["blogger_url"] = post.get("url", "")
                    log_event(events, "Blogger", t["title"] + " : " + t["blogger_status"])
                except Exception as error:
                    t["blogger_status"] = "échec"
                    log_event(events, "erreur Blogger", t["title"] + " (" +
                              type(error).__name__ + ")")
                    print("Blogger : échec pour", t["id"], type(error).__name__)
        else:
            print("Blogger non connecté : secrets OAuth requis.")
    except Exception as error:
        log_event(events, "connexion Blogger", "indisponible (" +
                  type(error).__name__ + ")")
        print("Blogger non connecté :", type(error).__name__)
    visible = [known[t["id"]] for t in tracks]
    write_pages(visible, state)
    write_journal(events, state, len(tracks))
    (BASE / "data.json").write_text(json.dumps(visible, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print("Terminé :", len(tracks), "chansons, catalogue, annonces, journal.")

if __name__ == "__main__":
    main()
