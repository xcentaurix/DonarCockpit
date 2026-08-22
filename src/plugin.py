# Copyright (C) 2026 by xcentaurix
# License: GNU General Public License v3.0

import threading

from Plugins.Plugin import PluginDescriptor

from .Debug import logger
from .Version import PLUGIN, VERSION
from .ConfigInit import cfg
from . import api
from .setup import SetupScreen
from . import _
from .SkinUtils import loadPluginSkin


loadPluginSkin()


def _boot():
    """Ensure/start TorrServer per config, in the background."""
    try:
        if cfg.autostart.value:
            api.start_torrserver()
        elif cfg.autodownload.value:
            api.ensure_torrserver_binary()
    except Exception as e:
        logger.debug("starting torrserver failed: %s", e)


threading.Thread(target=_boot, name="DonarCockpit-Boot", daemon=True).start()


def setup(session, **_kwargs):
    session.open(SetupScreen)


def autoStart(reason, **kwargs):
    if reason == 0:  # startup
        if "session" in kwargs:
            logger.info("+++ Version: %s starts...", VERSION)
    elif reason == 1:  # shutdown
        logger.info("--- shutdown")


def Plugins(**_kwargs):
    return [
        PluginDescriptor(
            where=[
                PluginDescriptor.WHERE_AUTOSTART,
                PluginDescriptor.WHERE_SESSIONSTART
            ],
            fnc=autoStart
        ),
        PluginDescriptor(
            name=PLUGIN,
            icon="plugin.svg",
            description=_("Shared TorrServer backend"),
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=setup,
        ),
    ]
