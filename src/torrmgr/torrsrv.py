import base64
import copy
import json
import os
import platform
import re
import shutil
import sys
import time
from urllib.parse import quote, urlencode
from urllib.request import urlopen, Request

from .Debug import logger
from . import ENCODE_UTF8


def none2str(x):
    return x or ''


def none2list(x):
    return x or []


def base64encodestring(x):
    return base64.encodebytes(x.encode('utf-8')).decode('utf-8').replace('\n', '')


MEDIA_FORMATS = ('.mpg', '.vob', '.m4v', '.mkv', '.avi', '.divx', '.dat', '.flv', '.mp4',
                 '.mov', '.wmv', '.asf', '.3gp', '.3g2', '.mpeg', '.mpe', '.rm',
                 '.rmvb', '.ogm', '.ogv', '.m2ts', '.mts', '.webm', '.pva', '.wtv',
                 '.ts', '.iso', '.img', '.nrg', '.dts', '.mp3', '.wav', '.wave',
                 '.wv', '.oga', '.ogg', '.flac', '.m4a', '.mp2', '.m2a', '.wma',
                 '.ac3', '.mka', '.aac', '.ape', '.alac', '.amr', '.au', '.mid')


def request_url(url, values=None, context=None, timeout=None, login='', password=''):
    retval = {'result': False, 'data': '', 'error': None}
    try:
        if values and isinstance(values, dict):
            data = bytes(urlencode(values), encoding='utf-8')
            req = Request(url + '?' + data)
        elif values and isinstance(values, str):
            req = Request(url, bytes(values, encoding='utf-8'))
            req.add_header('Content-Type', 'application/json')
        else:
            req = Request(url)
        if login:
            base64string = base64encodestring(f'{login}:{password}')
            req.add_header('Authorization', f'Basic {base64string}')
        if context:
            resp = urlopen(req, context=context, timeout=timeout)
        else:
            resp = urlopen(req, timeout=timeout)
        with resp:
            retval['data'] = resp.read()
        retval['data'] = retval['data'].decode()
        retval['result'] = True
    except Exception as err:
        retval['error'] = err
        try:
            logger.debug('Error request: [%s] to url: [%s] with parameters: [%s]', err, url, values)
        except Exception:
            logger.debug("Can't encode error message due request to url: [%s] with parameters: [%s]", url, values)

    return retval


_ARCH_ALIASES = {
    'x86_64': 'amd64', 'amd64': 'amd64',
    'i386': '386', 'i686': '386', 'x86': '386',
    'aarch64': 'arm64', 'arm64': 'arm64', 'armv8l': 'arm64',
    'armv5tel': 'arm5', 'armv5tejl': 'arm5',
    'riscv64': 'riscv64',
}


def detect_os_name():
    """Map sys.platform to the OS tag used in TorrServer release asset names."""
    if sys.platform.startswith('linux'):
        return 'linux'
    if sys.platform == 'darwin':
        return 'darwin'
    if sys.platform in {'win32', 'cygwin'}:
        return 'windows'
    if sys.platform.startswith('freebsd'):
        return 'freebsd'
    return sys.platform


def detect_arch():
    """Map platform.machine() to the arch tag used in TorrServer release asset names."""
    machine = platform.machine().lower()
    if machine in _ARCH_ALIASES:
        return _ARCH_ALIASES[machine]
    if machine.startswith('armv7') or machine.startswith('armv6') or machine == 'arm':
        return 'arm7'
    if machine.startswith('armv5'):
        return 'arm5'
    if machine in {'mips64', 'mips64el'}:
        return 'mips64le' if sys.byteorder == 'little' else 'mips64'
    if machine in {'mips', 'mipsel'}:
        return 'mipsle' if sys.byteorder == 'little' else 'mips'
    return machine


def get_latest_release_tag(repo='YouROK/TorrServer', timeout=30):
    """Return the tag_name of the latest GitHub release for repo, or None on failure.

    Only queries the GitHub API - unlike download_latest_torrent_binary, it
    does not download anything, so it's cheap to call just to check for updates.
    """
    try:
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'HydraCockpit'}
        req = Request(f'https://api.github.com/repos/{repo}/releases/latest', headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            release = json.load(resp)
        return release.get('tag_name') or None
    except Exception:
        return None


def download_latest_torrent_binary(destination_dir, binary_name='torrserver', repo='YouROK/TorrServer', timeout=30, os_name=None, arch=None):
    """Download the latest release asset matching this host's OS/architecture into the given directory."""
    retval = {'result': False, 'path': '', 'error': None, 'url': None, 'version': None}
    try:
        if not destination_dir:
            raise ValueError('destination_dir is required')
        os.makedirs(destination_dir, exist_ok=True)

        os_name = os_name or detect_os_name()
        arch = arch or detect_arch()
        suffix = f'-{os_name}-{arch}'

        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'HydraCockpit'}
        req = Request(f'https://api.github.com/repos/{repo}/releases/latest', headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            release = json.load(resp)

        tag_name = release.get('tag_name') or ''
        assets = release.get('assets') or []

        def matches(name):
            name = name.lower()
            if 'gst-' in name:
                return False
            base = name[:-4] if name.endswith('.exe') else name
            return base.endswith(suffix)

        asset = next((candidate for candidate in assets if matches(candidate.get('name') or '')), None)
        if not asset:
            raise RuntimeError(f'No release asset found for {repo} matching {suffix}')

        download_url = asset.get('browser_download_url')
        if not download_url:
            raise RuntimeError('Release asset does not provide a download URL')

        target_path = os.path.join(destination_dir, binary_name)
        req = Request(download_url, headers=headers)
        try:
            with urlopen(req, timeout=timeout) as resp, open(target_path, 'wb') as handle:
                shutil.copyfileobj(resp, handle)
        except Exception:
            if os.path.isfile(target_path):
                os.remove(target_path)
            raise

        if os.name != 'nt':
            os.chmod(target_path, 0o755)

        if not os.path.isfile(target_path):
            raise RuntimeError(f'Downloaded file is missing at {target_path}')
        retval['result'] = True
        retval['path'] = target_path
        retval['url'] = download_url
        retval['version'] = tag_name
    except Exception as err:
        retval['error'] = err

    return retval


def get_text_between(txt, s_delim, e_delim, s_position=0):
    res = {'text': '', 'position': -1}
    first = txt.find(s_delim, s_position)
    if first >= 0:
        first += len(s_delim)
        end = txt.find(e_delim, first)
        if end:
            res['text'] = txt[first:end if end >= 0 else None]
            res['position'] = end + len(e_delim)
    return res


def hash_from_magnet(magnet):
    """Returns the hash string from a magnet link"""
    return get_text_between(magnet, ':btih:', '&')['text']


def is_magnet(magnet):
    return magnet.startswith('magnet:?xt=urn:btih:')


class torrent:
    """
    Class describing torrents read from TorrServer.
    Reading video file data requires calling an additional method.
    """

    def __init__(self, title=None, poster=None, data=None, link=None, torrsrv=None):
        self.info = {'title': title, 'poster': poster, 'data': data, 'timestamp': None, 'name': None, 'stat': None,
                     'stat_string': None, 'torrent_size': 0, 'total_peers': None, 'pending_peers': None,
                     'active_peers': None, 'connected_seeders': None, 'bytes_written': None,
                     'bytes_read': None, 'file_stats': None,
                     'hash': None, 'save_to_db': True, 'link': link, 'extradata': t_data(data)}
        self.torrsrv = torrsrv

    @property
    def title(self):
        return self.info.get('title', None)

    @title.setter
    def title(self, val):
        self.info['title'] = val

    @property
    def poster(self):
        return self.info.get('poster', None)

    @poster.setter
    def poster(self, val):
        self.info['poster'] = val

    @property
    def data(self):
        return self.info.get('extradata', None)

    @data.setter
    def data(self, val):
        if isinstance(val, t_data):
            self.info['extradata'] = val
        else:
            self.info['extradata'] = t_data(val)

    @property
    def save_to_db(self):
        return self.info.get('save_to_db', True)

    @save_to_db.setter
    def save_to_db(self, val):
        self.info['save_to_db'] = val

    @property
    def hash(self):
        return self.info.get('hash', None)

    @property
    def status(self):
        return self.info.get('stat', None)

    @property
    def status_string(self):
        return self.info.get('stat_string', None)

    @property
    def torrent_size(self):
        return self.info.get('torrent_size', 0)

    @property
    def total_peers(self):
        return self.info.get('total_peers', None)

    @property
    def pending_peers(self):
        return self.info.get('pending_peers', None)

    @property
    def active_peers(self):
        return self.info.get('active_peers', None)

    @property
    def connected_seeders(self):
        return self.info.get('connected_seeders', None)

    @property
    def bytes_written(self):
        return self.info.get('bytes_written', None)

    @property
    def bytes_read(self):
        return self.info.get('bytes_read', None)

    @property
    def timestamp(self):
        return self.info.get('timestamp', None)

    @property
    def files(self):
        return t_files(none2list(self.info.get('file_stats', [])))

    @property
    def link(self):
        return self.info.get('link', None)

    @link.setter
    def link(self, val):
        self.info['link'] = val

    def get_torrent(self):
        if self.torrsrv:
            return self.torrsrv.get_torrent(self)
        return None


class t_file:
    """
    Class describing a video file contained in a torrent
    """

    def __init__(self, file_id=None, path=None, length=None):
        self.info = {'id': file_id, 'path': path, 'length': length}

    @property
    def id(self):
        return self.info.get('id', None)

    @property
    def path(self):
        return self.info.get('path', '')

    @property
    def length(self):
        return self.info.get('length', 0)


class t_files:
    """
    List of t_file objects belonging to a torrent
    """

    def __iter__(self):
        self.counter = 0
        return self

    def __init__(self, file_stats):
        self.files = file_stats
        self.counter = 0

    def next(self):
        if self.counter < len(self.files):
            f_s = t_file(file_id=self.files[self.counter]['id'], path=self.files[self.counter].get('path', ''), length=self.files[self.counter].get('length', 0))
            self.counter += 1
            return f_s
        raise StopIteration

    __next__ = next

    def __getitem__(self, index):
        return t_file(file_id=self.files[index]['id'], path=self.files[index].get('path', ''), length=self.files[index].get('length', 0))

    def __len__(self):
        return len(self.files)

    def count(self):
        return len(self.files)

    def file_by_id(self, file_id):
        """
        Returns a t_file object by its id
        """
        for idx, val in enumerate(self.files):
            if val['id'] == file_id:
                retval = self[idx]
                break
        else:
            retval = None

        return retval


class t_data:
    """
    Extra data stored in the data field
    """
    keynode = 'E2TorrPlayer'

    def __init__(self, input_json=''):
        self.data_dict = {t_data.keynode: {}}
        self.load_json(input_json)

    def load_json(self, input_json):
        if not input_json:
            input_json = ''
        start = '{"%s' % t_data.keynode
        if input_json.startswith(start):
            self.data_dict = json.loads(input_json)
        elif input_json.startswith('{'):
            try:
                self.data_dict = {t_data.keynode: {'extradata': json.loads(input_json)}}
            except Exception:
                pass

        else:
            self.data_dict = {t_data.keynode: {'description': input_json}}

    @property
    def json(self):
        return json.dumps(self.data_dict)

    @json.setter
    def json(self, val):
        self.load_json(val)

    @property
    def description(self):
        return self.data_dict[t_data.keynode].get('description', '')

    @description.setter
    def description(self, val):
        self.data_dict[t_data.keynode]['description'] = val

    @property
    def name(self):
        return self.data_dict[t_data.keynode].get('name', '')

    @name.setter
    def name(self, val):
        self.data_dict[t_data.keynode]['name'] = val

    @property
    def original_title(self):
        return self.data_dict[t_data.keynode].get('original_title', '')

    @original_title.setter
    def original_title(self, val):
        self.data_dict[t_data.keynode]['original_title'] = val

    @property
    def title(self):
        return self.data_dict[t_data.keynode].get('title', '')

    @title.setter
    def title(self, val):
        self.data_dict[t_data.keynode]['title'] = val

    @property
    def vote_average(self):
        return self.data_dict[t_data.keynode].get('vote_average', 0)

    @vote_average.setter
    def vote_average(self, val):
        self.data_dict[t_data.keynode]['vote_average'] = val

    @property
    def vote_count(self):
        return self.data_dict[t_data.keynode].get('vote_count', 0)

    @vote_count.setter
    def vote_count(self, val):
        self.data_dict[t_data.keynode]['vote_count'] = val

    @property
    def extrajson(self):
        return json.dumps(self.data_dict[t_data.keynode].get('extradata', {}))

    @extrajson.setter
    def extrajson(self, val):
        self.data_dict[t_data.keynode]['extradata'] = json.loads(val) if val else {}

    @property
    def extradata(self):
        return self.data_dict[t_data.keynode].get('extradata', {})

    @extradata.setter
    def extradata(self, val):
        self.data_dict[t_data.keynode]['extradata'] = val


class torrents:
    """
    List of torrent objects read from the server
    """

    def __iter__(self):
        self.counter = 0
        return self

    def __init__(self, trnts_info=None, torrsrv=None):
        self.torrents_info = []
        self.torrsrv = torrsrv
        for one in trnts_info or ():
            trnt = torrent(torrsrv=torrsrv)
            for key, val in one.items():
                trnt.info[key] = val

            trnt.data = t_data(trnt.info.get('data', ''))
            self.torrents_info.append(trnt)

        self.counter = 0

    def set_item(self, old_tinfo, new_tinfo):
        pass

    def next(self):
        if self.counter < len(self.torrents_info):
            trnt = self.torrents_info[self.counter]
            self.counter += 1
            return trnt
        raise StopIteration

    __next__ = next

    def __getitem__(self, index):
        if isinstance(index, str):
            retval = self.torrent_by_hash(index)
            if retval is None:
                raise IndexError('list index out of range')
        else:
            retval = self.torrents_info[index]
        return retval

    def __setitem__(self, index, trnt):
        self.torrents_info[index] = trnt

    def __len__(self):
        return len(self.torrents_info)

    def count(self):
        return len(self.torrents_info)

    def append(self, trnt):
        self.torrents_info.append(trnt)

    def insert(self, index, trnt):
        self.torrents_info.insert(index, trnt)

    def index(self, val):
        if isinstance(val, str):
            newval = self.torrent_by_hash(val)
            if newval is None:
                raise ValueError(f'{val} is not in list')
        else:
            newval = val
        return self.torrents_info.index(newval)

    def torrent_by_hash(self, torrent_hash):
        """
        Returns a torrent object from the list by its hash
        """
        trnt = None
        for one in self.torrents_info:
            if one.hash == torrent_hash:
                trnt = one
                break

        return trnt


class torrsettings:
    """
    Class describing TorrServer settings
    """

    def __init__(self, sets=None):
        self.sets = sets if sets is not None else {}
        self.init_sets = copy.deepcopy(self.sets)

    def get_changed(self):
        flag = False
        for key, val in self.sets.items():
            if key in self.init_sets.keys() and self.init_sets[key] != val:
                flag = True

        if flag:
            return self.sets
        return {}

    @property
    def CacheSize(self):
        return self.sets.get('CacheSize', None)

    @CacheSize.setter
    def CacheSize(self, val):
        self.sets['CacheSize'] = val

    @property
    def PreloadBuffer(self):
        return self.sets.get('PreloadBuffer', None)

    @PreloadBuffer.setter
    def PreloadBuffer(self, val):
        if self.sets.get('PreloadBuffer', None):
            self.sets['PreloadBuffer'] = val

    @property
    def PreloadCache(self):
        return self.sets.get('PreloadCache', None)

    @PreloadCache.setter
    def PreloadCache(self, val):
        if self.sets.get('PreloadCache', None):
            self.sets['PreloadCache'] = val

    @property
    def ReaderReadAHead(self):
        return self.sets.get('ReaderReadAHead', None)

    @ReaderReadAHead.setter
    def ReaderReadAHead(self, val):
        self.sets['ReaderReadAHead'] = val

    @property
    def UseDisk(self):
        return self.sets.get('UseDisk', None)

    @UseDisk.setter
    def UseDisk(self, val):
        self.sets['UseDisk'] = val

    @property
    def TorrentsSavePath(self):
        return self.sets.get('TorrentsSavePath', None)

    @TorrentsSavePath.setter
    def TorrentsSavePath(self, val):
        self.sets['TorrentsSavePath'] = val

    @property
    def RemoveCacheOnDrop(self):
        return self.sets.get('RemoveCacheOnDrop', None)

    @RemoveCacheOnDrop.setter
    def RemoveCacheOnDrop(self, val):
        self.sets['RemoveCacheOnDrop'] = val

    @property
    def ForceEncrypt(self):
        return self.sets.get('ForceEncrypt', None)

    @ForceEncrypt.setter
    def ForceEncrypt(self, val):
        self.sets['ForceEncrypt'] = val

    @property
    def RetrackersMode(self):
        return self.sets.get('RetrackersMode', None)

    @RetrackersMode.setter
    def RetrackersMode(self, val):
        self.sets['RetrackersMode'] = val

    @property
    def TorrentDisconnectTimeout(self):
        return self.sets.get('TorrentDisconnectTimeout')

    @TorrentDisconnectTimeout.setter
    def TorrentDisconnectTimeout(self, val):
        self.sets['TorrentDisconnectTimeout'] = val

    @property
    def EnableDebug(self):
        return self.sets.get('EnableDebug', None)

    @EnableDebug.setter
    def EnableDebug(self, val):
        self.sets['EnableDebug'] = val

    @property
    def EnableIPv6(self):
        return self.sets.get('EnableIPv6', None)

    @EnableIPv6.setter
    def EnableIPv6(self, val):
        self.sets['EnableIPv6'] = val

    @property
    def DisableTCP(self):
        return self.sets.get('DisableTCP', None)

    @DisableTCP.setter
    def DisableTCP(self, val):
        self.sets['DisableTCP'] = val

    @property
    def DisableUTP(self):
        return self.sets.get('DisableUTP', None)

    @DisableUTP.setter
    def DisableUTP(self, val):
        self.sets['DisableUTP'] = val

    @property
    def DisableUPNP(self):
        return self.sets.get('DisableUPNP', None)

    @DisableUPNP.setter
    def DisableUPNP(self, val):
        self.sets['DisableUPNP'] = val

    @property
    def DisableDHT(self):
        return self.sets.get('DisableDHT', None)

    @DisableDHT.setter
    def DisableDHT(self, val):
        self.sets['DisableDHT'] = val

    @property
    def DisablePEX(self):
        return self.sets.get('DisablePEX', None)

    @DisablePEX.setter
    def DisablePEX(self, val):
        self.sets['DisablePEX'] = val

    @property
    def DisableUpload(self):
        return self.sets.get('DisableUpload', None)

    @DisableUpload.setter
    def DisableUpload(self, val):
        self.sets['DisableUpload'] = val

    @property
    def DownloadRateLimit(self):
        return self.sets.get('DownloadRateLimit', None)

    @DownloadRateLimit.setter
    def DownloadRateLimit(self, val):
        self.sets['DownloadRateLimit'] = val

    @property
    def UploadRateLimit(self):
        return self.sets.get('UploadRateLimit', None)

    @UploadRateLimit.setter
    def UploadRateLimit(self, val):
        self.sets['UploadRateLimit'] = val

    @property
    def ConnectionsLimit(self):
        return self.sets.get('ConnectionsLimit', None)

    @ConnectionsLimit.setter
    def ConnectionsLimit(self, val):
        self.sets['ConnectionsLimit'] = val

    @property
    def DhtConnectionLimit(self):
        return self.sets.get('DhtConnectionLimit', None)

    @DhtConnectionLimit.setter
    def DhtConnectionLimit(self, val):
        self.sets['DhtConnectionLimit'] = val

    @property
    def PeersListenPort(self):
        return self.sets.get('PeersListenPort', None)

    @PeersListenPort.setter
    def PeersListenPort(self, val):
        self.sets['PeersListenPort'] = val

    @property
    def Strategy(self):
        return self.sets.get('Strategy', None)

    @Strategy.setter
    def Strategy(self, val):
        self.sets['Strategy'] = val


class torrserver:
    """
    Class for working with TorrServer.
    Implements the http API interface commands.
    """

    def __init__(self):
        self.srv_protocol = 'http'
        self.srv_host = '127.0.0.1'
        self.srv_port = 8090
        self.srv_torrents = torrents({}, self)
        self.srv_settings = torrsettings()
        self.srv_timeout = None
        self.srv_login = None
        self.srv_password = None
        self.waiting = 2
        self.attempts_count = 3
        self.filter_ext = MEDIA_FORMATS

    @property
    def url(self):
        return f'{self.srv_protocol}://{self.srv_host}:{self.srv_port}'

    @url.setter
    def url(self, val):
        try:
            tmp = re.split('://|:|/', val)
            self.srv_protocol = tmp[0]
            self.srv_host = tmp[1]
            self.srv_port = int(tmp[2])
        except Exception:
            pass

    @property
    def torr_version(self):
        retval = None
        cmd = self.url + '/echo'
        tmp = request_url(cmd, timeout=self.srv_timeout, login=self.srv_login, password=self.srv_password)
        if tmp['result']:
            retval = tmp['data']
        return retval

    @property
    def settings(self):
        return self.srv_settings

    @property
    def attempts(self):
        return self.attempts_count

    @attempts.setter
    def attempts(self, val):
        self.attempts_count = val if val < 1 else 1

    def request(self, url, values=None, context=None, timeout=None, login='', password='', key_check=''):
        sensitivity = 2
        res = None

        def check(x, k):
            return k in x if k else True
        timeout = self.srv_timeout if self.srv_timeout else 10
        for _ in range(self.attempts):
            t1 = time.time()
            res = request_url(url, values, context, timeout, login, password)
            t2 = time.time()
            if res['data'] and check(res['data'], key_check):
                break
            if t2 - t1 < float(timeout / sensitivity) and self.attempts > 1:
                time.sleep(self.waiting)
                self.test_connection()
            else:
                break

        return res

    def read_torrents(self):
        """ read info about all torrents (dosn't fill file_stats info)"""
        retval = False
        cmd = self.url + '/torrents'
        params = {'action': 'list'}
        tmp = self.request(cmd, json.dumps(params), timeout=self.srv_timeout, login=self.srv_login, password=self.srv_password, key_check='"hash"')
        if tmp['result']:
            tors = json.loads(tmp['data'])
            self.srv_torrents = torrents(tors, self)
            retval = True
        return retval

    def get_torrent(self, trnt):
        """ read extended info about one torrent"""
        if isinstance(trnt, torrent):
            torrent_hash = trnt.hash
            stat_tor = trnt
        else:
            torrent_hash = hash_from_magnet(trnt) if is_magnet(trnt) else trnt
            stat_tor = torrent()
        retval = None
        cmd = f'{self.url}/stream/fname?link={torrent_hash}&stat'
        tmp = self.request(cmd, {}, timeout=self.srv_timeout, login=self.srv_login, password=self.srv_password, key_check='"file_stats"')
        if tmp['result']:
            tor = json.loads(tmp['data'])
            for key, val in tor.items():
                stat_tor.info[key] = val

            def get_fext(x):
                return os.path.splitext(x)[1]
            tmp = list(filter((lambda lone: not self.filter_ext or self.filter_ext and get_fext(lone.get('path', '')) in self.filter_ext), stat_tor.info.get('file_stats', [])))
            if stat_tor.info.get('file_stats', None):
                stat_tor.info['file_stats'] = tmp
            retval = stat_tor
        return retval

    def add_torrent(self, trnt):
        """ add torrent to server's list"""
        cmd = self.url + '/torrents'
        retval = False
        params = {'action': 'add',
                  'link': none2str(trnt.link),
                  'title': none2str(trnt.title),
                  'poster': none2str(trnt.poster),
                  'save_to_db': trnt.save_to_db}
        tmp = request_url(cmd, json.dumps(params), timeout=self.srv_timeout, login=self.srv_login, password=self.srv_password)
        if tmp['result']:
            tor = json.loads(tmp['data'])
            if isinstance(trnt, torrent):
                for key, val in tor.items():
                    trnt.info[key] = val

            retval = True
        return retval

    def remove_torrent(self, trnt):
        """ delete torennt from TorServer
            parameters: trnt - torrent object or hash"""
        if isinstance(trnt, torrent):
            torrent_hash = trnt.hash
            save = trnt.save_to_db
        else:
            torrent_hash = trnt
            save = True
        cmd = self.url + '/torrents'
        retval = False
        params = {'action': 'rem', 'hash': torrent_hash, 'save_to_db': save}
        tmp = request_url(cmd, json.dumps(params), timeout=self.srv_timeout, login=self.srv_login, password=self.srv_password)
        if tmp['result']:
            retval = True
        return retval

    def update_torrent(self, trnt):
        """ change torent info
            parameters: trnt - torrent object"""
        cmd = self.url + '/torrents'
        retval = False
        params = {'action': 'set', 'hash': trnt.hash, 'title': trnt.title, 'poster': trnt.poster, 'data': trnt.data.json, 'save_to_db': trnt.save_to_db}
        tmp = request_url(cmd, json.dumps(params), timeout=self.srv_timeout, login=self.srv_login, password=self.srv_password)
        if tmp['data']:
            tor = json.loads(tmp['data'])
            for key, val in tor.items():
                trnt.info[key] = val

            retval = True
        return retval

    def get_stream_url(self, trnt, file_id):
        """return stream dictionary: (name, path, stream) """
        f_obj = trnt.files.file_by_id(file_id) if isinstance(file_id, int) else file_id
        file_path = quote(ENCODE_UTF8(f_obj.path))
        retval = {'name': trnt.title, 'file': f_obj.path,
                  'stream': f'{self.url}/stream/{file_path}?link={trnt.hash}&index={f_obj.id}&play'}
        return retval

    def get_onlyplay_url(self, trnt, file_id=1):
        """ Returns the URL for streaming the torrent without adding it to TorrServer. """
        link = trnt.link if isinstance(trnt, torrent) else trnt
        if not isinstance(link, str):
            link = str(link)
        return f'{self.url}/stream/fname?link={quote(link)}&index={file_id}&play'

    def preload_torrent(self, trnt, file_id, wait_time=25):
        """preload torrent an returns stream url"""
        f_obj = trnt.files.file_by_id(file_id) if isinstance(file_id, int) else file_id
        file_path = quote(ENCODE_UTF8(f_obj.path))
        cmd = f'{self.url}/stream/{file_path}?link={trnt.hash}&index={f_obj.id}&preload'
        tmp = request_url(cmd, timeout=self.srv_timeout, login=self.srv_login, password=self.srv_password)
        retval = self.get_stream_url(trnt, file_id)['stream'] if tmp['result'] else ''
        time.sleep(wait_time)
        return retval

    def torrent_by_hash(self, torrent_hash):
        trnt = None
        for one in self.srv_torrents:
            if one.info['hash'] == torrent_hash:
                trnt = torrent()
                trnt.info = copy.deepcopy(one.info)
                break

        return trnt

    def read_torr_settings(self):
        retval = False
        cmd = self.url + '/settings'
        params = {'action': 'get'}
        tmp = request_url(cmd, json.dumps(params), timeout=self.srv_timeout, login=self.srv_login, password=self.srv_password)
        if tmp['result']:
            self.srv_settings = torrsettings(json.loads(tmp['data']))
            retval = True
        return retval

    def save_torr_settings(self, reread=True):
        retval = False
        cmd = self.url + '/settings'
        changed = self.srv_settings.get_changed()
        if changed:
            params = {'action': 'set', 'sets': changed}
            tmp = request_url(cmd, json.dumps(params), timeout=self.srv_timeout, login=self.srv_login, password=self.srv_password)
            if tmp['result']:
                retval = True
                if reread:
                    self.read_torr_settings()
        else:
            retval = True
        return retval

    def test_connection(self):
        return self.torr_version is not None

    def stop_server(self):
        retval = False
        cmd = self.url + '/shutdown'
        tmp = request_url(cmd, timeout=self.srv_timeout, login=self.srv_login, password=self.srv_password)
        if tmp['result']:
            retval = True
            time.sleep(self.waiting)
        return retval


if __name__ == '__main__':
    pass
