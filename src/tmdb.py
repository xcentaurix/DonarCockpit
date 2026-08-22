# -*- coding: UTF-8 -*-
# Copyright (C) 2026 by xcentaurix
# License: GNU General Public License v3.0
# version: 21/02/2022
# author: zmej74
# version: 07/05/2022
# author: Vasiliks
import json
import re
from difflib import SequenceMatcher
from time import gmtime
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from .torrmgr import ENCODE_UTF8, DECODE_UTF8
from .torrmgr.urlrequest import request_url
from .Debug import logger

TMDB_PICTURES_URL = 'https://image.tmdb.org/t/p/w300%s'


def tmdb_title(x):
    return x.get("title", x.get("name", ""))


def tmdb_release_date(x):
    return x.get('release_date', x.get('first_air_date', ''))


def tmdb_poster_url(x):
    return (TMDB_PICTURES_URL % x.get("poster_path")) if x.get("poster_path", "") else ""


def tmdb_backdrop_url(x):
    return (TMDB_PICTURES_URL % x.get("backdrop_path")) if x.get("backdrop_path", "") else ""


class constants:
    every_word = 0  # matches if any of the words occurs
    full_string = 1  # matches if the whole string occurs
    sort_nosort = 0
    sort_fullin = 1
    sort_ratio = 2


class tmdb_topic:
    def __init__(self, t_dict):
        self.info = t_dict

    @property
    def title(self):
        return tmdb_title(self.info)

    @property
    def original_title(self):
        return self.info.get("original_title", "")

    @property
    def name(self):
        return self.info.get("name", "")

    @property
    def original_name(self):
        return self.info.get("original_name", "")

    @property
    def description(self):
        return self.info.get("overview", "")

    @property
    def release_date(self):
        return tmdb_release_date(self.info)

    @property
    def poster_url(self):
        return tmdb_poster_url(self.info)

    @property
    def poster(self):
        return tmdb_poster_url(self.info)

    @property
    def background_url(self):
        return tmdb_backdrop_url(self.info)

    @property
    def poster_path(self):
        return self.info.get("poster_path", "")

    @property
    def background_path(self):
        return self.info.get("background_path", "")

    @property
    def vote_average(self):
        return self.info.get("vote_average", 0)

    @property
    def vote_count(self):
        return self.info.get("vote_count", 0)

    @property
    def id(self):
        return self.info.get("id", 0)

    @property
    def media_type(self):
        return self.info.get("media_type", "")


class tmdb_topics:

    def __init__(self, lst):
        self.info = lst
        self.counter = 0

    def __iter__(self):
        self.counter = 0
        return self

    def item(self, index):
        return tmdb_topic(self.info[index])

    def next(self):
        if self.counter < len(self.info):
            tmdbt = self.item(self.counter)
            self.counter += 1
            return tmdbt
        raise StopIteration

    __next__ = next

    def __getitem__(self, index):
        return self.item(self.counter)

    def __len__(self):
        return len(self.info)

    def count(self):
        return len(self.info)

    def __add__(self, lst):
        return tmdb_topics(self.info + lst)

    def clear(self):
        self.info = []

    def sort_by_entry(self):
        def in_title(title, search):
            prc = 99
            delims = r'   |  | '
            words = re.split(delims, search)
            cnt = len(words)
            found = 0
            for one in words:
                if one in title:
                    found += 1
            return float(found) / cnt * 100 > prc
        results = self.info
        search_str = self.info

        def get_title(x):
            return ENCODE_UTF8(x.get("title", x.get("name", "")))

        def sort_func(x):
            return len(DECODE_UTF8(get_title(x))) * (1 if in_title(get_title(x), search_str) else 1000)
        results.sort(key=sort_func)

    def sort_by_ratio(self, query):
        results = self.info

        def get_title(x):
            return ENCODE_UTF8(x.get("title", x.get("name", "")))
        for item in results:
            query_str = DECODE_UTF8(query)
            info_str = DECODE_UTF8(get_title(item))
            item["sm_ratio"] = SequenceMatcher(None, query_str.lower(), info_str.lower()).ratio()

        def sort_func(x):
            return x["sm_ratio"]
        results.sort(key=sort_func, reverse=True)


class tmdb_query:

    @staticmethod
    def clear_name(topic, regex_str=""):
        """
        Attempt to leave only the leading keywords in the title, without symbols
        """
        if not topic:
            return ""
        if not regex_str:
            regex_str = (r'[0-9]+\+|'
                         r'([\(\[]).*?([\)\]])|'
                         r'\d{1,3}\-я|'
                         r'(с|С)ерия|'
                         r'\d{1,3}\s(с|C)\-н|'
                         r'\d{1,3}\sс\?(\.|\,|\ )|'
                         r'(с|С)езон\s\d{1,3}|'
                         r'Премьера\.\s|'
                         r'(х|Х|м|М|т|Т|д|Д)/ф\s|'
                         r'(х|Х|м|М|т|Т|д|Д)/с\s|'
                         r'\s(с|С)(езон|ерия|-н|-я)\s.+|'
                         r'(ч|Ч)асть|'
                         r'\s\d{1,3}\s(ч|ч\.|с\.|с)\s.+|'
                         r'\.\s\d{1,3}\s(ч|ч\.|с\.|с)\s.+|'
                         r'\s(ч|ч\.|с\.|с)\s\d{1,3}.+|'
                         r'(\s\-(.*?).*)|'
                         r'[\\/\(_]|'
                         r'\s\d{1,3}\-\d{1,3}\s')
        regex = re.compile(regex_str, re.DOTALL)
        # remove everything after / , \ , |, *
        toxic_symbols = r'/|\||\*|\\|\(|\['
        topic = re.split(toxic_symbols, topic)[0]
        topic = regex.sub('', topic).strip()
        topic = topic.replace(".", " ").strip()
        # topic = re.sub(" +", " ", topic)
        topic = re.sub(" +|:", " ", topic)
        toxic_phrase = 'SATR|WEBR|BDR|WEB-|HDTV|AVC'
        topic = re.split(toxic_phrase, topic)[0]
        topic = re.sub("    |   |  ", " ", topic)
        return topic

    @staticmethod
    def get_year(topic):
        try:
            yr = [_y for _y in re.findall(r'\d{4}', topic) if '1930' <= _y <= f"{gmtime().tm_year}"]
            return yr[-1] if yr else ''
        except Exception:
            return ''

    @staticmethod
    def get_url(url, values=None, context=None, timeout=None):
        return request_url(url, values=values or {}, context=context, timeout=timeout)

    @staticmethod
    def get_url_(url, values=None, context=None, timeout=None):
        retval = {"result": False, "data": '', "error": None}
        try:
            if values and isinstance(values, dict):
                data = urlencode(values)
                req = Request(url + '?' + data)
            elif values and isinstance(values, str):
                req = Request(url, values)
            else:
                req = Request(url)
            if context:
                resp = urlopen(req, context=context, timeout=timeout)
            else:
                resp = urlopen(req, timeout=timeout)
            with resp:
                retval["data"] = resp.read()
            retval["result"] = True
        except Exception as err:
            retval["error"] = err
            try:
                logger.debug(ENCODE_UTF8(f"Error request: [{err}] to url: [{url}] with parametrs: [{values}]"))
            except Exception:
                logger.debug("Can't encode error message due request to url: [%s] with parametrs: [%s]", url, values)
        return retval

    def __init__(self):
        self.base_url = "https://api.themoviedb.org/3/search/multi"
        self.search_page = 0    # 0 - all pages
        self.source_str = ""
        self.search_year = ""
        self.search_params = {'api_key': "", 'query': "", 'region': '', 'language': '', 'include_adult': 1, "page": 1}
        self.to_clear = False
        self.search_mode = constants.every_word
        self.regexp_pattern = ""
        self.sort_mode = constants.sort_ratio
        self.found_topics = []
        # self.error_request = None

    @property
    def query(self):
        return self.search_params["query"]

    @query.setter
    def query(self, value):
        self.source_str = value
        if self.cleaning:
            self.search_params["query"] = self.clear_name(value, self.regexp_pattern)
            self.search_year = self.get_year(value)
        else:
            self.search_params["query"] = value
        self.search_params["query"] = re.sub("    |   |  ", " ", self.search_params["query"])

    @property
    def pattern(self):
        return self.regexp_pattern

    @pattern.setter
    def pattern(self, value):
        self.regexp_pattern = value
        if self.source_str:
            self.query = self.source_str

    @property
    def cleaning(self):
        return self.to_clear

    @cleaning.setter
    def cleaning(self, value):
        self.to_clear = value
        if self.source_str:
            self.query = self.source_str

    @property
    def year(self):
        return self.search_year

    @year.setter
    def year(self, value):
        self.search_year = str(value)

    @property
    def page(self):
        return self.search_page

    @page.setter
    def page(self, value):
        self.search_page = value
        self.search_params["page"] = value if value > 0 else 1

    @property
    def api_key(self):
        return self.search_params["api_key"]

    @api_key.setter
    def api_key(self, value):
        self.search_params["api_key"] = value

    @property
    def language(self):
        return self.search_params["language"]

    @language.setter
    def language(self, value):
        self.search_params["language"] = value

    @property
    def region(self):
        return self.search_params["region"]

    @region.setter
    def region(self, value):
        self.search_params["region"] = value

    @property
    def adult(self):
        return self.search_params["include_adult"] == 1

    @adult.setter
    def adult(self, value):
        if isinstance(value, bool):
            self.search_params["include_adult"] = 1 if value else 0
        else:
            self.search_params["include_adult"] = value

    def do_search(self):
        self.found_topics = tmdb_topics([])
        # self.search_params["page"] = self.page
        retval = False

        def found(x, y):
            return x["result"] and x["data"] and y.get("total_results", 0) > 0
        # self.fill_params()
        res = self.get_url(self.base_url, self.search_params)
        try:
            info = json.loads(res["data"])
        except Exception:
            info = None
        # print res
        if found(res, info):
            try:
                pages = info["total_pages"]
                self.found_topics += info["results"]
                if self.search_page == 0 and pages > 1:
                    params = self.search_params.copy()
                    for one in range(1, pages + 1):
                        params["page"] = one
                        res = self.get_url(self.base_url, params)
                        try:
                            info = json.loads(res["data"])
                        except Exception:
                            info = None
                        if found(res, info):
                            self.found_topics += info["results"]
                retval = True
            except Exception as err:
                logger.debug("Error [%s] due request to server", err)
        return retval

    def select_tmdb_info(self):
        self.do_search()
        if self.sort_mode == constants.sort_fullin:
            self.found_topics.sort_by_entry()
        elif self.sort_mode == constants.sort_ratio:
            self.found_topics.sort_by_ratio(self.query)
        else:
            pass
        return self.found_topics

    def select_one_tmdb_info(self):
        self.do_search()
        if self.sort_mode == constants.sort_fullin:
            self.found_topics.sort_by_entry()
        elif self.sort_mode == constants.sort_ratio:
            self.found_topics.sort_by_ratio(self.query)
        else:
            pass
        retval = None
        for item in self.found_topics:
            if item.media_type in {'movie', 'tv'}:
                release_date = self.get_year(item.release_date)
                if release_date and self.search_year == release_date:
                    retval = item
                    break
        else:
            try:
                retval = self.found_topics[0]
            except Exception:
                pass

        return retval
