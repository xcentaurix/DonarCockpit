# -*- coding: UTF-8 -*-
"""Cinemeta (Stremio's official movie/series catalog addon) browse/search.

Unlike search_parsers.py (torrent search) and stream_providers.py (stream
resolution for a *known* title's IMDB id), this queries Cinemeta's catalog
resource - the Stremio addon protocol's "browse titles" endpoint, which is
a completely different resource from the "stream" endpoint TorrentioProvider
etc. implement. Cinemeta's "top" catalog supports genre/search/skip extras
(per its manifest.json), so callers can browse by genre the same way the
YTS site itself does, or search by title text, and get back Cinemeta's own
normalized metadata (poster/backdrop/description/imdb id) - no torrent
search or stream resolution involved here at all.
"""
import json
from urllib.parse import quote
from .torrmgr.urlrequest import request_url

# Cache of {(url_prefix, type): [genre, ...]}, keyed so a caller pointed at a
# non-default Cinemeta fork (via url_prefix) doesn't get another fork's list.
# Genre lists are effectively static (they change, if ever, on Cinemeta's own
# release cadence, not per session), so re-fetching the manifest on every
# menu render would just be wasted latency for no benefit.
_GENRE_CACHE = {}


class cinemeta_meta:
    def __init__(self, info):
        self.info = info

    @property
    def imdb_id(self):
        return self.info.get("id", "")

    @property
    def type(self):
        return self.info.get("type", "movie")

    @property
    def title(self):
        return self.info.get("name", "")

    @property
    def year(self):
        return str(self.info.get("year", "") or self.info.get("releaseInfo", ""))

    @property
    def description(self):
        return self.info.get("description", "")

    @property
    def poster(self):
        return self.info.get("poster", "")

    @property
    def background(self):
        return self.info.get("background", "") or self.poster

    @property
    def imdb_rating(self):
        return self.info.get("imdbRating", "")

    @property
    def genres(self):
        return self.info.get("genres", [])


class cinemeta_metas:
    def __init__(self, info=None):
        self.info = info or []
        self.counter = 0

    def __iter__(self):
        self.counter = 0
        return self

    def item(self, index):
        return cinemeta_meta(self.info[index])

    def next(self):
        if self.counter < len(self.info):
            m = self.item(self.counter)
            self.counter += 1
            return m
        raise StopIteration

    __next__ = next

    def __getitem__(self, index):
        return self.item(index)

    def __len__(self):
        return len(self.info)

    def count(self):
        return len(self.info)


class cinemeta_catalog:
    """Browse or search Cinemeta's "top" catalog.

    Leave .query unset and set .genre to browse by category (like YTS's own
    genre filter); set .query instead for a title search. Both can't be
    combined - Cinemeta's "top" catalog treats genre and search as
    alternative filters on the same list, not a joint AND-filter.
    """

    def __init__(self):
        self.url_prefix = "https://v3-cinemeta.strem.io"
        self.rts_type = "movie"        # "movie" or "series"
        self.rts_catalog_id = "top"    # the only catalog Cinemeta currently declares
        self.rts_genre = ""
        self.rts_search_query = ""
        self.rts_skip = 0
        self.metas = cinemeta_metas()

    @property
    def type(self):
        return self.rts_type

    @type.setter
    def type(self, val):
        self.rts_type = val

    @property
    def genre(self):
        return self.rts_genre

    @genre.setter
    def genre(self, val):
        self.rts_genre = val

    @property
    def query(self):
        return self.rts_search_query

    @query.setter
    def query(self, val):
        self.rts_search_query = val

    @property
    def skip(self):
        return self.rts_skip

    @skip.setter
    def skip(self, val):
        self.rts_skip = val

    @property
    def catalog_url(self):
        # Stremio addon catalog extras are packed into ONE path segment as
        # literal "key=value" pairs joined by "&" - not a normal ?query
        # string. Values are percent-encoded individually, but the "&"
        # joiner itself must stay literal: Cinemeta's router splits on raw
        # "&" before decoding the path segment, so a %26 here silently
        # breaks multi-extra requests (verified against the live API).
        extras = []
        if self.rts_genre:
            extras.append("genre=" + quote(self.rts_genre, safe=""))
        if self.rts_search_query:
            extras.append("search=" + quote(self.rts_search_query, safe=""))
        if self.rts_skip:
            extras.append("skip=" + str(int(self.rts_skip)))
        base = f"{self.url_prefix}/catalog/{self.rts_type}/{self.rts_catalog_id}"
        if extras:
            base += "/" + "&".join(extras)
        return base + ".json"

    def browse(self):
        self.metas = cinemeta_metas()
        tmp = request_url(self.catalog_url)
        if tmp["result"]:
            try:
                data = json.loads(tmp["data"])
            except (ValueError, TypeError):
                data = None
            if data:
                self.metas = cinemeta_metas(data.get("metas", []))
        return bool(len(self.metas))

    def genres(self, force=False):
        """Genre list Cinemeta's "top" catalog actually supports for this
        .type, straight from its manifest.json rather than a hardcoded copy
        that could silently drift out of sync with what Cinemeta serves.
        Cached after the first call (per url_prefix/type) - pass force=True
        to bypass the cache and re-fetch. Returns [] on any failure.
        """
        key = (self.url_prefix, self.rts_type)
        if force:
            _GENRE_CACHE.pop(key, None)
        if key in _GENRE_CACHE:
            return _GENRE_CACHE[key]

        result = []
        tmp = request_url(f"{self.url_prefix}/manifest.json")
        if tmp["result"]:
            try:
                manifest = json.loads(tmp["data"])
            except (ValueError, TypeError):
                manifest = None
            if manifest:
                for catalog in manifest.get("catalogs", []):
                    if catalog.get("type") == self.rts_type and catalog.get("id") == self.rts_catalog_id:
                        result = list(catalog.get("genres", []))
                        break
        _GENRE_CACHE[key] = result
        return result
