# Copyright (C) 2026 by xcentaurix
# License: GNU General Public License v3.0

import re


class Provider:
    def __init__(self):
        self.base_url = ""
        self.name = "Unknown"

    def get_stream_url(self, _typ, _imdb, _season=None, _episode=None):
        return ""

    def parse_streams(self, _data, _title, _year, _season=None, _episode=None):
        return []

    def _format_size(self, size):
        try:
            size = float(size)
            for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
                if size < 1024:
                    return f"{size:.2f} {unit}"
                size /= 1024
            return f"{size:.2f} PB"
        except Exception:
            return "0 B"


class TorrentioProvider(Provider):
    def __init__(self):
        super().__init__()
        self.name = "Torrentio"
        self.base_url = "https://torrentio.strem.fun"

    def get_stream_url(self, typ, imdb, season=None, episode=None):
        base = self.base_url.rstrip("/")
        if typ == "movie":
            return f"{base}/stream/movie/{imdb}.json"
        if typ == "series":
            return f"{base}/stream/series/{imdb}:{season}:{episode}.json"
        return ""

    def parse_streams(self, data, _title, _year, _season=None, _episode=None):
        return data.get("streams", [])  # Torrentio format is native Stremio format


class CometProvider(Provider):
    def __init__(self):
        super().__init__()
        self.name = "Comet"
        self.base_url = "https://comet.stremio.ru"

    def get_stream_url(self, typ, imdb, season=None, episode=None):
        base = self.base_url.rstrip("/")
        if typ == "movie":
            return f"{base}/stream/movie/{imdb}.json"
        if typ == "series":
            return f"{base}/stream/series/{imdb}:{season}:{episode}.json"
        return ""

    def parse_streams(self, data, _title, _year, _season=None, _episode=None):
        streams = data.get("streams", [])
        for s in streams:
            bh = s.get("behaviorHints", {})
            if "bingeGroup" in bh and "infoHash" not in s:
                s["infoHash"] = bh["bingeGroup"].replace("comet|", "")
            if "filename" in bh and "title" not in s:
                s["title"] = bh["filename"]
        return streams


class MediaFusionProvider(Provider):
    def __init__(self):
        super().__init__()
        self.name = "MediaFusion"
        self.base_url = "https://mediafusion.elfhosted.com"

    def get_stream_url(self, typ, imdb, season=None, episode=None):
        base = self.base_url.rstrip("/")
        if typ == "movie":
            return f"{base}/stream/movie/{imdb}.json"
        if typ == "series":
            return f"{base}/stream/series/{imdb}:{season}:{episode}.json"
        return ""

    def parse_streams(self, data, _title, _year, _season=None, _episode=None):
        streams = data.get("streams", [])
        for s in streams:
            url = s.get("url", "")
            if "/playback/" in url and "infoHash" not in s:
                m = re.search(r'/playback/([^/]+)', url)
                if m:
                    s["infoHash"] = m.group(1)
        return streams


class StremThruProvider(Provider):
    def __init__(self):
        super().__init__()
        self.name = "StremThru"
        self.base_url = "https://stremthru.13377001.xyz"

    def get_stream_url(self, typ, imdb, season=None, episode=None):
        base = self.base_url.rstrip("/")
        if typ == "movie":
            return f"{base}/stream/movie/{imdb}.json"
        if typ == "series":
            return f"{base}/stream/series/{imdb}:{season}:{episode}.json"
        return ""

    def parse_streams(self, data, _title, _year, _season=None, _episode=None):
        return data.get("streams", [])


class TorBoxProvider(Provider):
    def __init__(self):
        super().__init__()
        self.name = "TorBox"
        self.base_url = "https://stremio.torbox.app"

    def get_stream_url(self, typ, imdb, season=None, episode=None):
        base = self.base_url.rstrip("/")
        if typ == "movie":
            return f"{base}/stream/movie/{imdb}.json"
        if typ == "series":
            return f"{base}/stream/series/{imdb}:{season}:{episode}.json"
        return ""

    def parse_streams(self, data, _title, _year, _season=None, _episode=None):
        return data.get("streams", [])


class AIOStreamsProvider(Provider):
    def __init__(self):
        super().__init__()
        self.name = "AIOStreams"
        self.base_url = "https://aiostreamsfortheweebsstable.midnightignite.me"

    def get_stream_url(self, typ, imdb, season=None, episode=None):
        base = self.base_url.rstrip("/")
        if typ == "movie":
            return f"{base}/stream/movie/{imdb}.json"
        if typ == "series":
            return f"{base}/stream/series/{imdb}:{season}:{episode}.json"
        return ""

    def parse_streams(self, data, _title, _year, _season=None, _episode=None):
        return data.get("streams", [])


class EasyNewsProvider(Provider):
    def __init__(self):
        super().__init__()
        self.name = "EasyNews"
        self.base_url = "https://easynews.io"  # Placeholder if needed

    def get_stream_url(self, typ, imdb, season=None, episode=None):
        base = self.base_url.rstrip("/")
        if typ == "movie":
            return f"{base}/stream/movie/{imdb}.json"
        if typ == "series":
            return f"{base}/stream/series/{imdb}:{season}:{episode}.json"
        return ""

    def parse_streams(self, data, _title, _year, _season=None, _episode=None):
        return data.get("streams", [])


def get_provider(url):
    """Return the Provider matching this addon base URL's quirks, pointed
    at that exact URL. Falls back to TorrentioProvider (native format,
    the most common case) when the URL doesn't match any known addon."""
    u = (url or "").lower()
    if "comet" in u:
        provider = CometProvider()
    elif "mediafusion" in u:
        provider = MediaFusionProvider()
    elif "stremthru" in u:
        provider = StremThruProvider()
    elif "torbox" in u:
        provider = TorBoxProvider()
    elif "aiostreams" in u:
        provider = AIOStreamsProvider()
    elif "easynews" in u:
        provider = EasyNewsProvider()
    else:
        provider = TorrentioProvider()
    if url:
        provider.base_url = url
    return provider
