# Copyright (C) 2026 by xcentaurix
# License: GNU General Public License v3.0

from Components.config import (
    config, ConfigSubsection, ConfigText, ConfigYesNo, ConfigInteger, ConfigPassword, ConfigSelection,
)

# Defined in its own module (not plugin.py or api.py) so config.plugins.donarcockpit
# exists as soon as anything - plugin.py during Enigma2's plugin scan, or api.py
# imported directly by another plugin - reaches for it. Guarded since Debug.py
# (imported before this module) already creates it with debug_log_level attached;
# recreating it unconditionally here would wipe that out.
if not hasattr(config.plugins, "donarcockpit"):
    config.plugins.donarcockpit = ConfigSubsection()
cfg = config.plugins.donarcockpit
cfg.torrserver_url = ConfigText(default="http://127.0.0.1:8090", fixed_size=False)
cfg.torrserver_login = ConfigText(default="", fixed_size=False)
cfg.torrserver_password = ConfigPassword(default="", fixed_size=False)
cfg.torrserver_timeout = ConfigInteger(default=10, limits=(1, 120))
cfg.install_dir = ConfigText(default="/usr/bin", fixed_size=False)
cfg.binary_name = ConfigText(default="TorrServer", fixed_size=False)
cfg.repo = ConfigText(default="YouROK/TorrServer", fixed_size=False)
cfg.autodownload = ConfigYesNo(default=True)
cfg.autostart = ConfigYesNo(default=True)

# Shared with HydraCockpit (and any other frontend plugin built on this backend) -
# single source of truth so the same TMDB/addon/debrid setup only needs configuring
# once, rather than each frontend keeping its own drifting copy.
cfg.tmdb_api_key = ConfigText(default="7bff10009e7deed9307ad50c67270b6b", fixed_size=False)
cfg.tmdb_language = ConfigSelection(
    default="en-US",
    choices=[
        ("en-US", "English"),
        ("fr-FR", "French"),
        ("es-ES", "Spanish"),
        ("de-DE", "German"),
        ("it-IT", "Italian"),
        ("pt-BR", "Portuguese (Brazil)"),
        ("ar-SA", "Arabic"),
        ("nl-NL", "Dutch"),
        ("ru-RU", "Russian"),
        ("tr-TR", "Turkish"),
        ("ja-JP", "Japanese"),
        ("ko-KR", "Korean"),
        ("zh-CN", "Chinese (Simplified)"),
        ("fa-IR", "Persian"),
    ],
)
cfg.rutor_url_prefix = ConfigText(default="http://rutor.info", fixed_size=False)
cfg.yts_api_base = ConfigText(default="https://movies-api.accel.li/api/v2", fixed_size=False)
cfg.cinemeta_base_url = ConfigText(default="https://v3-cinemeta.strem.io", fixed_size=False)

ADDON_PRESETS = [
    ("https://torrentio.strem.fun", "Torrentio"),
    ("https://mediafusion.elfhosted.com/D-KbFjcL7shV3nF5URsgpERXNhL_XBJ6EGht2NKLbvhYMLLTuwVx8FHavz5BasCyB08p-V9MJANcKlNPclL-8LtdZBPO8CMGPa3J6LlhUpzYz40qfgeazG45o_GTAbMd_7Z8PTgAr9BO7FBlz8XO6k9R4eEMZJ8MicI6vu4uC4aEFFCTbiKArUDobe7TPVYyT5-z6RDm-w80PG-RopSD5-fpJToKkfSdRsUmQQFDrsOHejjaFrcJJzhgc-Tv3rPSJiho4M2PZlwASLofIx5qDBQQ", "MediaFusion"),
    ("https://comet.stremio.ru", "Comet"),
    ("https://stremthru.13377001.xyz/stremio/torz/eyJpbmRleGVycyI6bnVsbCwic3RvcmVzIjpbeyJjIjoidGIiLCJ0IjoiMzhhZWVjYTEtNjNhMC00ODExLWEwMmMtYWZkYjNjOTRjNjVjIn1dLCJjYWNoZWQiOnRydWV9", "StremThru"),
    ("https://stremio.torbox.app/38aeeca1-63a0-4811-a02c-afdb3c94c65c", "TorBox"),
    ("https://aiostreamsfortheweebsstable.midnightignite.me/stremio/9c8a8e08-9269-4beb-b1d4-789a7594dc53/eyJpIjoiLzYwOG5rZ1pweWhPSnJSZ28wcFkrdz09IiwiZSI6ImFCdTBGN3BnM0IydUhnNUR3UlB6alE9PSIsInQiOiJhIn0", "AIOStreams"),
    ("https://easynews.io", "EasyNews"),
]
cfg.addon_base_url = ConfigSelection(default="https://torrentio.strem.fun", choices=ADDON_PRESETS)

cfg.debrid_provider = ConfigSelection(
    default="none",
    choices=[("none", "None"), ("realdebrid", "Real-Debrid"), ("alldebrid", "AllDebrid")],
)
cfg.debrid_token = ConfigPassword(default="", fixed_size=False)
