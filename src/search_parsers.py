# Copyright (C) 2026 by xcentaurix
# License: GNU General Public License v3.0

import json
import re
from urllib.parse import quote, unquote, urlencode
from .torrmgr.urlrequest import request_url


def get_text_between(txt, s_delim, e_delim, s_position=0):
    res = {"text": "", "position": -1}
    first = txt.find(s_delim, s_position)
    if first >= 0:
        first += len(s_delim)
        end = txt.find(e_delim, first)
        if end:
            res["text"] = txt[first:(end if end >= 0 else None)]
            res["position"] = end + len(e_delim)
    return res


def pretty_name(txt):
    retval = re.sub('(<.*?>)', " ", txt)
    retval = retval.replace("&quot;", "'").replace('&nbsp;', " ")
    return retval.strip(" :")


class v_link:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    @property
    def platform(self):
        return self.key

    @property
    def link(self):
        return self.value


class v_links:
    def __init__(self, links):
        self.links = links
        self.counter = 0

    def __iter__(self):
        self.counter = 0
        return self

    def item(self, index):
        return v_link(self.links.keys()[index], self.links.values()[index])

    def next(self):
        if self.counter < len(self.links):
            vl = self.item(self.counter)
            self.counter += 1
            return vl
        raise StopIteration

    __next__ = next

    def __getitem__(self, index):
        return self.item(index)

    def __len__(self):
        return len(self.links)

    def count(self):
        return len(self.links)

    def link_by_name(self, key):
        return v_link(key, self.links[key])


class t_info:
    def __init__(self, info, search_obj=None):
        self.info = info  # {"url":"", "date":'', "name":"", "size":"", "seeders":"", "leechers":"", "magnet":'', "file_url":""}
        self.detail_info = {"description": "", "year": "", "genres": "", "duration": "", "video": "", "quality": "", "imdb_id": ""}
        self.search_obj = search_obj

    @property
    def detail_url(self):
        # link to the URL with detailed description
        return self.info.get("url", "")

    @property
    def date(self):
        # torrent publication date
        return self.info.get("date", "")

    @property
    def name(self):
        # torrent title/name
        return self.info.get("name", "")

    @property
    def size(self):
        # torrent size - GB/MB string
        return self.info.get("size", "")

    @property
    def magnet(self):
        # magnet link to the torrent
        return self.info.get("magnet", "")

    @property
    def file_url(self):
        # link for downloading the .torrent file
        return self.info.get("file_url", "")

    @property
    def seeders(self):
        # number of seeders - notoriously unreliable
        return self.info.get("seeders", "")

    @property
    def leechers(self):
        # number of leechers
        return self.info.get("leechers", "")
    # detail information
    # detailed torrent information, available after calling load_detail_info()

    @property
    def description(self):
        # torrent description
        return self.detail_info.get("description", "")

    @property
    def poster_url(self):
        # poster image URL, not always available!
        return self.detail_info.get("poster_url", "")

    @property
    def year(self):
        # movie release year
        return self.detail_info.get("year", "")

    @property
    def genres(self):
        # movie genres - list of strings
        return self.detail_info.get("genres", [])

    @property
    def duration(self):
        # movie duration - string
        return self.detail_info.get("duration", "")

    @property
    def video(self):
        # video parameters
        return self.detail_info.get("video", "")

    @property
    def quality(self):
        # video quality info, not always available!
        return self.detail_info.get("quality", "")

    @property
    def imdb_id(self):
        # "tt1234567" - only populated by parsers that get it for free from
        # their own API response (currently just yts, via movie["imdb_code"]);
        # rutor has no IMDB linkage at all, so this stays "" for it.
        return self.detail_info.get("imdb_id", "")

    def load_detail_info(self):
        return (self.search_obj.load_detail_info(self) if self.search_obj else False)

    def load_poster(self, fname):
        retval = False
        if self.poster_url:
            tmp = request_url(self.poster_url)
            if tmp["result"]:
                with open(fname, "wb") as fo:
                    fo.write(tmp["data"])
                    retval = True
        return retval


class t_infos:
    def __init__(self, info=None, search_obj=None):
        self.info = []
        self.search_obj = search_obj
        if info:
            self.info = info
        self.counter = 0

    def __iter__(self):
        self.counter = 0
        return self

    def item(self, index):
        return t_info(self.info[index], self.search_obj)

    def next(self):
        if self.counter < len(self.info):
            ti = self.item(self.counter)
            self.counter += 1
            return ti
        raise StopIteration

    __next__ = next

    def __getitem__(self, index):
        return self.item(index)

    def __len__(self):
        return len(self.info)

    def count(self):
        return len(self.info)

    def append(self, info):
        self.info.append(info)


class rts_mode:
    full_phrase = 0
    all_words = 1
    any_words = 2
    bool_expression = 3


class rts_category:
    all = 0


class rts_area:
    titles = 0
    titles_descriptions = 1


class rts_sort:
    date = 0
    seeders = 2
    leechers = 4
    name = 6
    size = 8
    relevance = 10


class rts_order:
    ascending = 1
    descending = 0


class rutor:
    def __init__(self):
        self.rts_search_url = '/search/{page}/{category}/{mode}{area}0/{sort}/{item}'
        self.url_prefix = 'http://rutor.info'
        """ search string parameters:
            page - search page (0), starts at 0, then from the result - 1 (second page), 2 (third, etc.)
            category - movie category, default 0 - all categories
            mode - search mode: 0 - exact phrase, 1 - all words, 2 - any of the words, 3 - logical expression
            area - search area: 0 - in titles, 1 - in titles and descriptions
            sort - result sorting: 0 - date added, descending (1-ascending),
                                            2 - by seeders, descending (3-ascending),
                                            4 - by leechers, descending (5-ascending),
                                            6 - by title, descending (7-ascending),
                                            8 - by size, descending (9-ascending),
                                            10 - by relevance, descending (11-ascending)
            item - search text
            """
        self.rts_search_page = 0
        self.rts_category = rts_category.all
        self.rts_mode = rts_mode.full_phrase
        self.rts_area = rts_area.titles
        self.rts_sortmode = rts_sort.date
        self.rts_sortorder = rts_order.descending
        self.t_info_dict = {"url": "", "date": '', "name": "", "size": "", "seeders": "", "leechers": "", "magnet": '', "file_url": ""}
        self.rts_infos = None
        self.srv_latest_url = 'https://releases.yourok.ru/torr/server_release.json'
        self.rts_search_query = ""

    @property
    def search_url(self):
        return (self.url_prefix + self.rts_search_url).format(page=self.rts_search_page, category=self.rts_category, mode=self.rts_mode,
                                                              area=self.rts_area,
                                                              sort=(self.rts_sortmode + self.rts_sortorder), item=self.rts_search_query)

    @property
    def query(self):
        return unquote(self.rts_search_query)

    @query.setter
    def query(self, val):
        self.rts_search_query = quote(val)

    def parse_next_urls(self, html):
        retval = []
        start = '<div id="index"><b>Страницы:'
        end = '</b>'
        tmp = get_text_between(html, start, end)
        if tmp["text"]:
            retval = [self.url_prefix + one for one in re.findall('(?:<a href=")(.*?)(?:">)', tmp["text"], flags=re.DOTALL)]
        return retval

    def parse_torrs_info(self, html):
        retval = False
        start = '''<table width="100%"><tr class="backgr"><td width="10px">Добавлен</td><td colspan="2">Название</td><td width="1px">Размер</td><td width="1px">Пиры</td></tr>'''
        end = '</table>'
        tmp = get_text_between(html, start, end)
        # tstrs = re.findall('(?:<tr class="tum|gai">)(?:.*?)(?:</tr>)', tmp["text"], flags=re.DOTALL)
        if tmp["text"]:
            tstrs = re.findall('<tr class="(?:gai|tum)">(.*?)</tr>', tmp["text"], flags=re.DOTALL)
            for one in tstrs:
                info = self.t_info_dict.copy()
                istrs = re.findall('<td(.*?)</td>', one, flags=re.DOTALL)
                # date
                info["date"] = re.sub('&nbsp;', ' ', istrs[0].strip("<>"))
                hrefs = re.findall('href="(.*?)">', istrs[1], flags=re.DOTALL)
                # download link
                info["file_url"] = hrefs[0]
                # magnet
                info["magnet"] = hrefs[1]
                # torrent's page url
                info["url"] = self.url_prefix + hrefs[2]
                # name
                info["name"] = re.findall('(?:href="/torrent.*?>)(.*?)</a>', re.sub('&#039;', "'", istrs[1]), flags=re.DOTALL)[0]
                # info["name"] =
                # size
                info["size"] = re.sub('align="right">|&nbsp;', " ", istrs[-2]).strip()
                traf = re.findall('(?:>&nbsp;)(.*?)</span>', istrs[-1], flags=re.DOTALL)
                info["seeders"] = int(traf[0])
                info["leechers"] = int(traf[1])
                self.rts_infos.append(info)
            retval = bool(len(self.rts_infos))
        return retval

    def parse_detail_info(self, html):
        def from_list(x, y, z=""):
            return x[y] if len(x) > 0 else z

        info = {}
        # description
        # desc = re.findall(r'<b>О фильме:[\s]*</b>(<.*?>)*(.*?)<br />', html, flags=re.DOTALL)
        desc = re.findall(r'(Описание|О фильме)[\s|:]*</b>(<.*?>)*(.*?)<br />', html, flags=re.DOTALL)
        if desc and isinstance(desc[0], tuple) and len(desc[0]) == 3:
            info["description"] = pretty_name(desc[0][2])
        else:
            info["description"] = ''
        # poster
        tmp = re.findall('></td><td><br /><img src="(.*?)"', html, flags=re.DOTALL)
        info["poster_url"] = from_list(tmp, 0, "")
        # year
        # tmp = re.findall(r'<b>Год выхода:[\s]*</b>(.*?)<br />', html, flags=re.DOTALL)
        tmp = re.findall(r'<b>Год.*?[\s]*</b>:*?(.*?)<br />', html, flags=re.DOTALL)
        info["year"] = pretty_name(from_list(tmp, 0, ""))
        # genre
        # tmp = re.findall(r'<b>Жанр:[\s]*</b>[\s]*(.*?)<br />', html, flags=re.DOTALL)
        tmp = re.findall(r'<b>Жанр.*?[\s]*</b>[\s]*:*?[\s]*(.*?)<br />', html, flags=re.DOTALL)
        info["genres"] = re.findall('target="_blank">(.*?)</a>', from_list(tmp, 0, ""), flags=re.DOTALL)
        # duration
        # tmp = re.findall(r'<b>Продолжительность:[\s]*</b>(.*?)<br />', html, flags=re.DOTALL)
        tmp = re.findall(r'<b>Продолжительность.*?[\s]*</b>:*?(.*?)<br />', html, flags=re.DOTALL)
        info["duration"] = pretty_name(from_list(tmp, 0, ""))
        # quality
        tmp = re.findall(r'<b>Качество:[\s]*</b>(.*?)<br />', html, flags=re.DOTALL)
        info["quality"] = from_list(tmp, 0, "")
        # video
        # tmp = re.findall(r'<b>Видео:[\s]*</b>(.*?)<br />', html, flags=re.DOTALL)
        tmp = re.findall(r'<b>Видео.*?[\s]*</b>:*?(.*?)<br />', html, flags=re.DOTALL)
        info["video"] = pretty_name(from_list(tmp, 0, ""))
        return info

    def search(self):
        self.rts_infos = t_infos(info=None, search_obj=self)
        # print self.search_url
        tmp = request_url(self.search_url)
        if tmp["result"]:
            nexts = self.parse_next_urls(tmp["data"])
            if self.parse_torrs_info(tmp["data"]):
                for oneurl in nexts:
                    del tmp
                    tmp = request_url(oneurl)
                    if tmp["result"]:
                        self.parse_torrs_info(tmp["data"])
        return bool(len(self.rts_infos))

    def load_detail_info(self, tinfo_obj):
        retval = False
        tmp = request_url(tinfo_obj.detail_url)
        if tmp["result"]:
            s_info = self.parse_detail_info(tmp["data"])
            if s_info:
                tinfo_obj.detail_info = s_info
                retval = True
        return retval


class yts:
    """YTS (yts.mx-compatible) movie torrent search, following the same
    query/search_url/search/load_detail_info contract as rutor above, so
    callers can use either parser interchangeably.

    Unlike rutor, YTS returns clean JSON rather than HTML to scrape, and a
    single search response already carries every field rutor needs a second
    detail-page fetch for (poster, genres, year, ...). Each movie can also
    list several torrents (qualities/types); this yields one t_info per
    torrent, matching rutor's one-row-per-upload semantics, rather than
    collapsing a movie's options down to a single "best" pick.
    """

    # Public trackers commonly bundled with YTS-sourced torrents, needed to
    # build a usable magnet link since the API only provides an info hash.
    DEFAULT_TRACKERS = [
        "udp://open.demonii.com:1337/announce",
        "udp://tracker.openbittorrent.com:80",
        "udp://tracker.coppersurfer.tk:6969",
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://p4p.arenabg.com:1337",
        "udp://tracker.leechers-paradise.org:6969",
    ]

    # Unlike Cinemeta (see cinemeta.py's genres(), which fetches this list
    # live from its manifest.json), YTS's API has no genre-listing endpoint -
    # this fixed set is only ever documented on the website's own filter UI,
    # so it can't be fetched, only hardcoded. Not verified against the live
    # site as of this writing (yts.mx was unreachable/DNS-blocked from the
    # dev environment this was written in) - treat as best-effort and
    # sanity-check against yts.mx's own filters if titles seem to go missing.
    GENRES = [
        "Action", "Adventure", "Animation", "Biography", "Comedy", "Crime",
        "Documentary", "Drama", "Family", "Fantasy", "Film-Noir", "Game-Show",
        "History", "Horror", "Music", "Musical", "Mystery", "News",
        "Reality-TV", "Romance", "Sci-Fi", "Sport", "Talk-Show", "Thriller",
        "War", "Western",
    ]

    def __init__(self):
        self.url_prefix = "https://yts.mx/api/v2"
        self.rts_search_page = 1
        self.rts_sortmode = "date_added"
        self.rts_sortorder = "desc"
        self.rts_limit = 20
        self.rts_search_query = ""
        # Browse-by-category filters (YTS list_movies.json params) - all
        # optional and omitted from search_url when unset, so leaving them
        # alone preserves the previous query-only search behavior. Setting
        # these with no query lets callers browse (e.g. "Action, 2160p,
        # sorted by rating") the same way the YTS site itself does, rather
        # than only ever searching by title text.
        self.rts_genre = ""
        self.rts_quality = ""
        self.rts_minimum_rating = 0
        self.t_info_dict = {"url": "", "date": '', "name": "", "size": "", "seeders": "", "leechers": "", "magnet": '', "file_url": ""}
        self.rts_infos = None
        self.trackers = list(self.DEFAULT_TRACKERS)

    @property
    def search_url(self):
        params = {
            "page": self.rts_search_page,
            "sort_by": self.rts_sortmode,
            "order_by": self.rts_sortorder,
            "limit": self.rts_limit,
        }
        if self.rts_search_query:
            params["query_term"] = self.rts_search_query
        if self.rts_genre:
            params["genre"] = self.rts_genre
        if self.rts_quality:
            params["quality"] = self.rts_quality
        if self.rts_minimum_rating:
            params["minimum_rating"] = self.rts_minimum_rating
        return f"{self.url_prefix}/list_movies.json?{urlencode(params)}"

    @property
    def query(self):
        return self.rts_search_query

    @query.setter
    def query(self, val):
        self.rts_search_query = val

    @property
    def genre(self):
        # e.g. "Action", "Comedy", "Horror", ... (see yts.mx/api#list_movies)
        return self.rts_genre

    @genre.setter
    def genre(self, val):
        self.rts_genre = val

    @property
    def quality(self):
        # "720p", "1080p", "2160p", "3D", or "" for all qualities
        return self.rts_quality

    @quality.setter
    def quality(self, val):
        self.rts_quality = val

    @property
    def minimum_rating(self):
        # 0-9, IMDB rating floor; 0 means unfiltered
        return self.rts_minimum_rating

    @minimum_rating.setter
    def minimum_rating(self, val):
        self.rts_minimum_rating = val

    def build_magnet(self, torrent_hash, display_name):
        trackers = "".join(f"&tr={quote(t)}" for t in self.trackers)
        return f"magnet:?xt=urn:btih:{torrent_hash}&dn={quote(display_name)}{trackers}"

    def parse_movies(self, movies):
        retval = False
        for movie in movies:
            movie_name = movie.get("title_long") or movie.get("title", "")
            detail = {
                "description": movie.get("description_full") or movie.get("synopsis", ""),
                "poster_url": movie.get("large_cover_image", ""),
                "year": str(movie.get("year", "")),
                "genres": movie.get("genres", []),
                "duration": (f"{movie['runtime']} min" if movie.get("runtime") else ""),
                "imdb_id": movie.get("imdb_code", ""),
            }
            for torrent in movie.get("torrents", []):
                info = self.t_info_dict.copy()
                info["url"] = movie.get("url", "")
                info["date"] = torrent.get("date_uploaded", "")
                info["name"] = f"{movie_name} [{torrent.get('quality', '')} {torrent.get('type', '')}]".strip()
                info["size"] = torrent.get("size", "")
                info["seeders"] = torrent.get("seeds", 0)
                info["leechers"] = torrent.get("peers", 0)
                info["file_url"] = torrent.get("url", "")
                info["magnet"] = self.build_magnet(torrent.get("hash", ""), movie_name)
                # Detail info is already fully known from this same response -
                # load_detail_info() below just hands it back, no HTTP call.
                info["_detail"] = dict(
                    detail,
                    video=f"{torrent.get('video_codec', '')} {torrent.get('bit_depth', '')}bit {torrent.get('audio_channels', '')}".strip(),
                    quality=torrent.get("quality", ""),
                )
                self.rts_infos.append(info)
                retval = True
        return retval

    def search(self):
        self.rts_infos = t_infos(info=None, search_obj=self)
        tmp = request_url(self.search_url)
        if tmp["result"]:
            try:
                data = json.loads(tmp["data"])
            except (ValueError, TypeError):
                data = None
            if data:
                movies = data.get("data", {}).get("movies", [])
                self.parse_movies(movies)
        return bool(len(self.rts_infos))

    def load_detail_info(self, tinfo_obj):
        detail = tinfo_obj.info.get("_detail")
        if not detail:
            return False
        tinfo_obj.detail_info = detail
        return True

    def genres(self):
        """The fixed GENRES list above - a method (not just the bare class
        constant) so callers can use yts_search.genres() the same way they'd
        call cinemeta_catalog.genres(), without caring which provider theirs
        happens to be a live fetch and which is a hardcoded list.
        """
        return list(self.GENRES)
