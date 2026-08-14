import threading

from Plugins.Plugin import PluginDescriptor

from .Debug import logger
from .Version import PLUGIN
from .ConfigInit import cfg
from . import api
from .setup import DonarSetup


def _boot():
    """Ensure/start TorrServer per config, in the background.

    Same rationale as HydraCockpit: this runs during Enigma2's plugin-scan
    import pass, and ensure/start do a blocking network download and/or spawn
    a subprocess, so this must not run synchronously at import time - that
    would stall the whole plugin scan if the network isn't up yet at boot.
    """
    try:
        if cfg.autostart.value:
            api.start_torrserver()
        elif cfg.autodownload.value:
            api.ensure_torrserver_binary()
    except Exception as err:  # pragma: no cover - defensive, boot thread must not crash
        logger.debug("[%s] boot failed: %s", PLUGIN, err)


threading.Thread(target=_boot, name="DonarCockpit-Boot", daemon=True).start()


def main(session, **_kwargs):
    session.open(DonarSetup)


def Plugins(**_kwargs):
    return [
        PluginDescriptor(
            name=PLUGIN,
            icon="plugin.png",
            description="Shared TorrServer backend",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main,
        ),
    ]
