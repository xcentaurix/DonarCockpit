# -*- coding: UTF-8 -*-
"""Debrid-service resolver.

Ported from HydraCockpit's screens.py DebridResolver: given a magnet link,
resolves it through a debrid service (Real-Debrid or AllDebrid) into direct
HTTP download links, so a caller never has to wait on the torrent swarm
itself. Complements stream_providers.py (which finds streams/magnets from a
Stremio addon) and search_parsers.py (which finds magnets from rutor/YTS) -
whichever found the magnet, this resolves it the same way.

Not ported: HydraCockpit's DebridFileAdapter/DebridServiceAdapter/
DebridTorrentAdapter - those are thin shims that make a resolved debrid
link look like a torrsrv torrent object purely for HydraCockpit's own
player/UI code. They're UI glue, not something a shared backend should
own; callers here get the plain (name, size, url) tuples from
add_and_list() and can adapt them however their own UI needs.
"""
import json
import re
import urllib.parse as urllib
import urllib.request as urllib2

from .Debug import logger


class DebridResolver:
    def __init__(self, provider="none", token=""):
        self.provider = (provider or "none").lower()
        self.token = (token or "").strip()

    def enabled(self):
        return self.provider != "none" and bool(self.token)

    def rd_add_magnet(self, magnet):
        try:
            req = urllib2.Request("https://api.real-debrid.com/rest/1.0/torrents/addMagnet",
                                  data=urllib.urlencode({"magnet": magnet}).encode())
            req.add_header("Authorization", f"Bearer {self.token}")
            with urllib2.urlopen(req, timeout=20) as resp:
                data = resp.read()
            j = json.loads(data) if data else {}
            return j.get("id")
        except Exception as e:
            logger.debug("[Debrid] RD addMagnet err: %s", e)
            return None

    def rd_select_all(self, tid):
        try:
            req = urllib2.Request(f"https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{tid}",
                                  data=urllib.urlencode({"files": "all"}).encode())
            req.add_header("Authorization", f"Bearer {self.token}")
            with urllib2.urlopen(req, timeout=20) as resp:
                resp.read()
        except Exception as e:
            logger.debug("[Debrid] RD select err: %s", e)

    def rd_info(self, tid):
        try:
            req = urllib2.Request(f"https://api.real-debrid.com/rest/1.0/torrents/info/{tid}")
            req.add_header("Authorization", f"Bearer {self.token}")
            with urllib2.urlopen(req, timeout=20) as resp:
                data = resp.read()
            return json.loads(data) if data else {}
        except Exception as e:
            logger.debug("[Debrid] RD info err: %s", e)
            return {}

    def rd_unrestrict(self, link):
        try:
            req = urllib2.Request("https://api.real-debrid.com/rest/1.0/unrestrict/link",
                                  data=urllib.urlencode({"link": link}).encode())
            req.add_header("Authorization", f"Bearer {self.token}")
            with urllib2.urlopen(req, timeout=20) as resp:
                data = resp.read()
            j = json.loads(data) if data else {}
            return j.get("download")
        except Exception as e:
            logger.debug("[Debrid] RD unrestrict err: %s", e)
            return None

    def rd_instant_availability(self, hashes):
        """Check whether torrent info hashes are already cached on Real-Debrid,
        without adding them to the account. Real-Debrid has restricted this
        endpoint for third-party use since 2023 and it may just return {} -
        treat a negative result here as "unknown", not "definitely not cached".

        hashes: a single hash string, or a list of them.
        Returns {hash: [...cached file variants...]} - a hash present with
        a non-empty list is cached; missing/empty means not cached (or the
        check itself was blocked).
        """
        try:
            if isinstance(hashes, str):
                hashes = [hashes]
            path = "/".join(h.lower() for h in hashes if h)
            if not path:
                return {}
            req = urllib2.Request(f"https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/{path}")
            req.add_header("Authorization", f"Bearer {self.token}")
            with urllib2.urlopen(req, timeout=20) as resp:
                data = resp.read()
            return json.loads(data) if data else {}
        except Exception as e:
            logger.debug("[Debrid] RD instantAvailability err: %s", e)
            return {}

    def ad_instant_availability(self, magnets):
        """Check whether magnets/hashes are already cached on AllDebrid,
        without uploading them to the account. Unlike Real-Debrid's
        equivalent, this endpoint has stayed reliably available.

        magnets: a single magnet URI or hash string, or a list of them.
        Returns AllDebrid's raw list of {"magnet": ..., "instant": bool, ...}
        entries (one per input, same order), or [] on failure.
        """
        try:
            if isinstance(magnets, str):
                magnets = [magnets]
            magnets = [m for m in magnets if m]
            if not magnets:
                return []
            params = "&".join(f"magnets[]={urllib.quote(m)}" for m in magnets)
            url = f"https://api.alldebrid.com/v4/magnet/instant?agent=donarcockpit&apikey={self.token}&{params}"
            with urllib2.urlopen(url, timeout=20) as resp:
                data = resp.read()
            j = json.loads(data) if data else {}
            if j.get("status") == "success":
                return j.get("data", {}).get("magnets", [])
            return []
        except Exception as e:
            logger.debug("[Debrid] AD instant err: %s", e)
            return []

    def ad_add_magnet(self, magnet):
        try:
            url = f"https://api.alldebrid.com/v4/magnet/upload?agent=donarcockpit&apikey={self.token}&magnets[]={urllib.quote(magnet)}"
            with urllib2.urlopen(url, timeout=20) as resp:
                data = resp.read()
            j = json.loads(data)
            if j.get("status") == "success":
                return j["data"]["magnets"][0]["id"]
            return None
        except Exception as e:
            logger.debug("[Debrid] AD addMagnet err: %s", e)
            return None

    def ad_status(self, tid):
        try:
            url = f"https://api.alldebrid.com/v4/magnet/status?agent=donarcockpit&apikey={self.token}&id={tid}"
            with urllib2.urlopen(url, timeout=20) as resp:
                data = resp.read()
            j = json.loads(data)
            if j.get("status") == "success":
                return j["data"]["magnets"]
            return {}
        except Exception as e:
            logger.debug("[Debrid] AD status err: %s", e)
            return {}

    def ad_unlock(self, link):
        try:
            url = f"https://api.alldebrid.com/v4/link/unlock?agent=donarcockpit&apikey={self.token}&link={urllib.quote(link)}"
            with urllib2.urlopen(url, timeout=20) as resp:
                data = resp.read()
            j = json.loads(data)
            if j.get("status") == "success":
                return j["data"]["link"]
            return None
        except Exception as e:
            logger.debug("[Debrid] AD unlock err: %s", e)
            return None

    def is_cached(self, magnet_or_hash):
        """Check whether a single magnet/hash is already cached on the
        configured debrid provider, without adding it to the account.

        Returns True/False, or None if the provider is unconfigured or the
        check itself failed/was blocked (e.g. Real-Debrid's restricted
        instantAvailability endpoint) - None means "unknown", not "no".
        """
        if self.provider == "realdebrid":
            info_hash = magnet_or_hash
            if magnet_or_hash.lower().startswith("magnet:"):
                m = re.search(r'btih:([a-fA-F0-9]{40}|[a-zA-Z2-7]{32})', magnet_or_hash)
                if not m:
                    return None
                info_hash = m.group(1)
            result = self.rd_instant_availability(info_hash)
            if not result:
                return None
            return bool(result.get(info_hash.lower()))

        if self.provider == "alldebrid":
            result = self.ad_instant_availability(magnet_or_hash)
            if not result:
                return None
            return bool(result[0].get("instant"))

        return None

    def add_and_list(self, magnet):
        """Resolve a magnet through the configured debrid service.

        Returns a list of (name, size_bytes, direct_url) tuples, one per
        file in the torrent, or [] if resolution failed or no provider is
        configured (check enabled() first).
        """
        if self.provider == "realdebrid":
            tid = self.rd_add_magnet(magnet)
            if not tid:
                return []
            self.rd_select_all(tid)
            info = self.rd_info(tid) or {}
            files = info.get("files", []) or []
            links = info.get("links", []) or []
            out = []
            url = links[0] if links else None
            for f in files:
                name = (f.get("path") or "").split("/")[-1]
                size = int(f.get("bytes", 0) or 0)
                link = url
                if link:
                    dl = self.rd_unrestrict(link) or link
                    out.append((name, size, dl))
            return out

        if self.provider == "alldebrid":
            tid = self.ad_add_magnet(magnet)
            if not tid:
                return []
            info = self.ad_status(tid)
            if not info:
                return []

            links = info.get("links") or []
            out = []
            for link_info in links:
                name = link_info.get("filename") or "video"
                size = int(link_info.get("size") or 0)
                raw_link = link_info.get("link")
                if raw_link:
                    dl = self.ad_unlock(raw_link) or raw_link
                    out.append((name, size, dl))
            return out

        return []
