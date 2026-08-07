# DonarCockpit

Enigma2 plugin providing a shared TorrServer / TMDB / torrent-search backend
for other Cockpit-family plugins (HydraCockpit, TheraphosaCockpit, ...).

It has no significant UI of its own beyond a settings screen
("DonarCockpit Settings" in the plugin menu): its job is to own the
TorrServer binary, its lifecycle, and TMDB/torrent-search configuration once,
so other plugins don't each need their own copy.

## Configuration

All settings live under `config.plugins.donarcockpit` and are editable from
the "DonarCockpit Settings" plugin menu entry:

- `torrserver_url`, `torrserver_login`, `torrserver_password`, `torrserver_timeout`
- `install_dir`, `binary_name`, `repo` (GitHub `owner/name` to fetch releases from)
- `autodownload`, `autostart`
- `tmdb_api_key`, `tmdb_language`
- `rutor_url_prefix`

## Using DonarCockpit from another plugin

```python
from Plugins.Extensions.DonarCockpit import api as donar

donar.start_torrserver()
ts = donar.get_torrserver()
ts.read_torrents()

q = donar.new_tmdb_query()
q.query = "Interstellar"
results = q.select_tmdb_info()

search = donar.new_rutor_search()
search.query = "Interstellar"
```

Lower-level access to the underlying `torrmgr` package (`torrsrv`, `tmdb`,
`search_parsers`, `urlrequest`) is also available directly:

```python
from Plugins.Extensions.DonarCockpit.torrmgr import torrsrv
```

## Attribution

`torrmgr` is carried over from HydraCockpit (itself based on the work of
Ostende and others).
