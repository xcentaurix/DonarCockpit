# Copyright (C) 2026 by xcentaurix
# License: GNU General Public License v3.0

"""Public API for DonarCockpit.

Other Enigma2 plugins should use this module rather than reaching into
DonarCockpit's internals directly:

    from Plugins.Extensions.DonarCockpit import api as donar

    ts = donar.get_torrserver()
    ts.read_torrents()

    donar.start_torrserver()

    q = donar.new_tmdb_query()
    q.query = "Interstellar"
    results = q.select_tmdb_info()

    search = donar.new_rutor_search()
    search.query = "Interstellar"

    search = donar.new_yts_search()
    search.query = "Interstellar"

    browse = donar.new_yts_search()  # no query -> browse by category instead of title search
    browse.genres()  # -> fixed list, hardcoded (YTS has no genre-listing endpoint)
    browse.genre = "Action"
    browse.quality = "2160p"
    browse.rts_sortmode = "rating"
    browse.search()
    for t in browse.rts_infos:
        print(t.name, t.magnet)

    cinemeta_browse = donar.new_cinemeta_browse("movie")  # metadata, not torrents
    cinemeta_browse.genres()  # -> fetched live from Cinemeta's manifest.json, cached after first call
    cinemeta_browse.genre = "Horror"
    cinemeta_browse.browse()
    for m in cinemeta_browse.metas:
        print(m.title, m.imdb_id, m.poster)

    streams = donar.get_streams("tt0816692")  # Interstellar's IMDB id

    resolver = donar.new_debrid_resolver()
    if resolver.enabled():
        files = resolver.add_and_list(magnet_uri)

    cached = donar.is_cached_on_debrid(magnet_uri)  # True/False/None (unknown)

All settings used above (TorrServer URL/credentials, install dir, TMDB key,
rutor mirror, YTS API base, Cinemeta base URL, Stremio addon URL, debrid
provider/token, ...)
live in config.plugins.donarcockpit and are edited via DonarCockpit's own
"DonarCockpit Settings" menu entry - callers don't need to know about them.

Lower-level access is also available directly, e.g.:

    from Plugins.Extensions.DonarCockpit.torrmgr import torrsrv
    from Plugins.Extensions.DonarCockpit.tmdb import tmdb_query
    from Plugins.Extensions.DonarCockpit.search_parsers import rutor, yts
    from Plugins.Extensions.DonarCockpit.cinemeta import cinemeta_catalog
    from Plugins.Extensions.DonarCockpit.stream_providers import get_provider
    from Plugins.Extensions.DonarCockpit.debrid_resolver import DebridResolver
"""
import json
import os
import socket
import subprocess
import time

from .Debug import logger
from .ConfigInit import cfg as _cfg
from .torrmgr import torrsrv
from .torrmgr.urlrequest import request_url
from .tmdb import tmdb_query
from .search_parsers import rutor, yts
from .cinemeta import cinemeta_catalog
from .stream_providers import get_provider
from .debrid_resolver import DebridResolver

__all__ = [
    "torrserver_path",
    "get_torrserver",
    "is_torrserver_running",
    "get_torrserver_version",
    "get_latest_torrserver_version",
    "ensure_torrserver_binary",
    "update_torrserver_binary",
    "start_torrserver",
    "stop_torrserver",
    "new_tmdb_query",
    "new_rutor_search",
    "new_yts_search",
    "new_cinemeta_browse",
    "new_stream_provider",
    "get_streams",
    "new_debrid_resolver",
    "is_cached_on_debrid",
]


def torrserver_path():
    """Absolute path to the configured TorrServer binary."""
    c = _cfg
    return os.path.join(c.install_dir.value, c.binary_name.value)


def get_torrserver():
    """Return a torrsrv.torrserver client configured from DonarCockpit's settings."""
    c = _cfg
    ts = torrsrv.torrserver()
    ts.url = c.torrserver_url.value
    ts.srv_login = c.torrserver_login.value or None
    ts.srv_password = c.torrserver_password.value or None
    ts.srv_timeout = c.torrserver_timeout.value
    return ts


def is_torrserver_running(timeout=0.3):
    """Check, via a raw socket connect, whether TorrServer is already listening."""
    ts = get_torrserver()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((ts.srv_host, ts.srv_port)) == 0
    finally:
        sock.close()


def get_torrserver_version():
    """Return the running TorrServer's version string, or None if it can't be reached."""
    return get_torrserver().torr_version


def get_latest_torrserver_version():
    """Return the tag_name of the latest available TorrServer release on GitHub, or None on failure."""
    return torrsrv.get_latest_release_tag(repo=_cfg.repo.value)


def ensure_torrserver_binary():
    """Download the TorrServer binary if it isn't already installed.

    Returns the binary path on success, or None if it's missing and either
    couldn't be downloaded or auto-download is disabled in settings.
    """
    c = _cfg
    path = torrserver_path()
    if os.path.isfile(path):
        return path
    if not c.autodownload.value:
        return None
    result = torrsrv.download_latest_torrent_binary(
        c.install_dir.value, binary_name=c.binary_name.value, repo=c.repo.value,
    )
    if result.get("result") and os.path.isfile(result.get("path", "")):
        return result["path"]
    logger.debug("TorrServer install failed: %s", result.get("error"))
    return None


def update_torrserver_binary():
    """Install the latest TorrServer release if it's newer than what's running.

    Compares the running instance's reported version (via get_torrserver_version,
    which requires TorrServer to currently be running - if it isn't, the current
    version is unknown and an update is downloaded unconditionally) against the
    latest GitHub release tag. If TorrServer is running, it's stopped before the
    binary is replaced and restarted afterward.

    Returns the new binary path if an update was installed, None if already
    up to date (or the version check/download failed).
    """
    c = _cfg
    latest_version = get_latest_torrserver_version()
    if not latest_version:
        logger.debug("Could not determine latest TorrServer version.")
        return None

    current_version = get_torrserver_version()
    if current_version and current_version.strip().lstrip("vV") == latest_version.strip().lstrip("vV"):
        return None

    was_running = is_torrserver_running()
    if was_running:
        stop_torrserver()

    result = torrsrv.download_latest_torrent_binary(
        c.install_dir.value, binary_name=c.binary_name.value, repo=c.repo.value,
    )

    if was_running:
        start_torrserver()

    if result.get("result") and os.path.isfile(result.get("path", "")):
        return result["path"]
    logger.debug("TorrServer update failed: %s", result.get("error"))
    return None


def start_torrserver():
    """Ensure the binary is present and launch it if it isn't already running.

    Returns True if TorrServer ends up running (whether it already was, or
    this call just started it), False otherwise.
    """
    if is_torrserver_running():
        return True
    path = ensure_torrserver_binary()
    if not path:
        return False
    ts = get_torrserver()
    with open(os.devnull, "wb") as devnull:
        # Intentionally not using 'with' on Popen: this launches TorrServer as
        # a detached background process, and 'with Popen(...)' would block
        # here waiting for it to exit.
        subprocess.Popen(  # pylint: disable=consider-using-with
            [path, "--port", str(ts.srv_port), "--path", "/etc/enigma2"],
            stdout=devnull, stderr=devnull,
        )
    for _ in range(15):  # give it up to ~3s to bind its port
        if is_torrserver_running():
            break
        time.sleep(0.2)
    return is_torrserver_running()


def stop_torrserver():
    """Ask the running TorrServer instance to shut down over its HTTP API."""
    return get_torrserver().stop_server()


def new_tmdb_query():
    """Return a tmdb_query pre-configured with DonarCockpit's TMDB settings."""
    q = tmdb_query()
    q.api_key = _cfg.tmdb_api_key.value
    q.language = _cfg.tmdb_language.value
    return q


def new_rutor_search():
    """Return a rutor torrent-search helper pre-configured with DonarCockpit's settings."""
    search = rutor()
    search.url_prefix = _cfg.rutor_url_prefix.value
    return search


def new_yts_search():
    """Return a yts torrent-search helper pre-configured with DonarCockpit's settings.

    Set .query for a title search, same as new_rutor_search(). Leave .query
    unset and use .genre/.quality/.minimum_rating instead to browse by
    category (YTS's own list_movies.json filters) rather than search by title.
    """
    search = yts()
    search.url_prefix = _cfg.yts_api_base.value
    return search


def new_cinemeta_browse(typ="movie"):
    """Return a cinemeta_catalog helper pre-configured with DonarCockpit's settings.

    Unlike new_rutor_search()/new_yts_search() (torrent search) or
    get_streams() (stream resolution for a known IMDB id), this browses
    Cinemeta's own movie/series catalog - the same metadata source Stremio's
    official app uses for its home screen. Set .genre to browse by category,
    or .query for a title search; then call .browse() and iterate .metas.
    """
    catalog = cinemeta_catalog()
    catalog.url_prefix = _cfg.cinemeta_base_url.value
    catalog.type = typ
    return catalog


def new_stream_provider(addon_url=None):
    """Return the stream Provider matching the given (or configured default)
    Stremio-addon base URL, e.g. TorrentioProvider for torrentio.strem.fun.
    """
    return get_provider(addon_url or _cfg.addon_base_url.value)


def get_streams(imdb, typ="movie", season=None, episode=None, addon_url=None):
    """Fetch and parse streams for a known title's IMDB id from the
    configured (or given) Stremio-addon server.

    Unlike new_rutor_search()/new_yts_search() (search by query text), this
    resolves a *known* title (by IMDB id, plus season/episode for a series)
    to whatever streams that addon currently has for it. Returns a list of
    native-format Stremio stream dicts (each typically has a title/name and
    either an infoHash or a direct url), or [] on any failure.
    """
    provider = new_stream_provider(addon_url)
    stream_url = provider.get_stream_url(typ, imdb, season, episode)
    if not stream_url:
        return []
    tmp = request_url(stream_url)
    if not tmp["result"]:
        return []
    try:
        data = json.loads(tmp["data"])
    except (ValueError, TypeError):
        return []
    return provider.parse_streams(data, "", "", season, episode)


def new_debrid_resolver():
    """Return a DebridResolver pre-configured with DonarCockpit's settings.

    Check resolver.enabled() before use - it's False (and add_and_list()
    always returns []) until a debrid provider and token are configured.
    """
    return DebridResolver(provider=_cfg.debrid_provider.value, token=_cfg.debrid_token.value)


def is_cached_on_debrid(magnet_or_hash):
    """Check whether a magnet/hash is already cached on the configured
    debrid provider, without committing to a full add_and_list() resolve.

    Returns True/False, or None if no provider is configured, or if the
    check is unknown/blocked (notably Real-Debrid's restricted
    instantAvailability endpoint - see new_debrid_resolver()'s docstring).
    """
    resolver = new_debrid_resolver()
    if not resolver.enabled():
        return None
    return resolver.is_cached(magnet_or_hash)
