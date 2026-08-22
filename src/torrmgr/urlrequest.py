# -*- coding: UTF-8 -*-
# version: 07/12/2021
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from . import ENCODE_UTF8
from ..Debug import logger


def request_url(url, values=None, context=None, timeout=None):
    retval = {"result": False, "data": '', "error": None}
    data = None
    # Without a User-Agent, urllib's default ("Python-urllib/x.y") gets
    # bot-blocked (403) by at least Cinemeta's edge - intermittently, since
    # it depends on which path/cache layer handles the request, so this can
    # look like it "usually works" until a specific query 403s. A normal
    # browser-looking UA avoids the whole class of problem for every caller.
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        if values and isinstance(values, dict):
            data = urlencode(values)
            req = Request(url + '?' + data, headers=headers)
        elif values and isinstance(values, str):
            req = Request(url, values, headers=headers)
        else:
            req = Request(url, headers=headers)
        if context:
            resp = urlopen(req, context=context, timeout=timeout)
        else:
            resp = urlopen(req, timeout=timeout)
        with resp:
            retval["data"] = resp.read()
        retval["data"] = retval["data"].decode()
        retval["result"] = True
    except Exception as err:
        retval["error"] = err
        try:
            logger.debug(ENCODE_UTF8(f"Error request: [{err}] to url: [{url}] with parametrs: [{values}]"))
        except Exception:
            logger.debug("Can't encode error message due request to url: [%s] with parametrs: [%s]", url, values)
    return retval
