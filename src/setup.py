from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.config import getConfigListEntry
from twisted.internet.threads import deferToThread

from .ConfigInit import cfg
from .Debug import logger
from .Version import VERSION
from . import api
from . import _


class DonarSetup(Screen, ConfigListScreen):
    """Settings screen for DonarCockpit's shared TorrServer/TMDB/search config."""

    skin = """
    <screen name="DonarSetup" position="center,center" size="820,570" title="DonarCockpit Settings">
        <widget name="config" position="10,10" size="800,380" scrollbarMode="showOnDemand" />
        <widget source="installed_version" render="Label" position="10,398" size="800,25" font="Regular;18" halign="left" valign="center" transparent="1" zPosition="2" />
        <widget source="latest_version" render="Label" position="10,423" size="800,25" font="Regular;18" halign="left" valign="center" transparent="1" zPosition="2" />
        <ePixmap position="0,510" size="140,40" pixmap="skin_default/buttons/red.png" alphatest="blend" zPosition="1" />
        <ePixmap position="150,510" size="140,40" pixmap="skin_default/buttons/green.png" alphatest="blend" zPosition="1" />
        <ePixmap position="300,510" size="140,40" pixmap="skin_default/buttons/yellow.png" alphatest="blend" zPosition="1" />
        <widget source="key_red" render="Label" position="0,510" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" zPosition="2" />
        <widget source="key_green" render="Label" position="150,510" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" zPosition="2" />
        <widget source="key_yellow" render="Label" position="300,510" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" zPosition="2" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(_("DonarCockpit Settings") + f" - {VERSION}")
        ConfigListScreen.__init__(self, [
            getConfigListEntry(_("TorrServer URL"), cfg.torrserver_url),
            getConfigListEntry(_("TorrServer login (optional)"), cfg.torrserver_login),
            getConfigListEntry(_("TorrServer password (optional)"), cfg.torrserver_password),
            getConfigListEntry(_("TorrServer request timeout (s)"), cfg.torrserver_timeout),
            getConfigListEntry(_("Install directory"), cfg.install_dir),
            getConfigListEntry(_("Binary name"), cfg.binary_name),
            getConfigListEntry(_("GitHub repo (owner/name)"), cfg.repo),
            getConfigListEntry(_("Auto-download binary if missing"), cfg.autodownload),
            getConfigListEntry(_("Auto-start TorrServer at boot"), cfg.autostart),
            getConfigListEntry(_("TMDB API key"), cfg.tmdb_api_key),
            getConfigListEntry(_("TMDB language"), cfg.tmdb_language),
            getConfigListEntry(_("Rutor mirror URL"), cfg.rutor_url_prefix),
            getConfigListEntry(_("YTS API base URL"), cfg.yts_api_base),
            getConfigListEntry(_("Cinemeta base URL"), cfg.cinemeta_base_url),
            getConfigListEntry(_("Stremio addon URL"), cfg.addon_base_url),
            getConfigListEntry(_("Debrid provider"), cfg.debrid_provider),
            getConfigListEntry(_("Debrid API token"), cfg.debrid_token),
        ], session=session)

        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Save"))
        self["key_yellow"] = StaticText(_("Update Server"))
        self["installed_version"] = StaticText(_("Installed version: checking..."))
        self["latest_version"] = StaticText(_("Latest version: checking..."))
        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "cancel": self.keyCancel,
            "red": self.keyCancel,
            "save": self.keySave,
            "green": self.keySave,
            "yellow": self.updateServer,
        }, -1)

        self._installed_version = None
        self._latest_version = None
        self._pending_checks = 2
        self._updating = False
        self._checkVersions()

    # keySave/keyCancel below wrap ConfigListScreen's own (which iterate
    # self["config"].list, calling .save()/.cancel() on each entry, then
    # close the screen) just to block closing the screen while an update
    # download/install is in progress.

    def keyCancel(self):
        if self._updating:
            return
        ConfigListScreen.keyCancel(self)

    def keySave(self):
        if self._updating:
            return
        ConfigListScreen.keySave(self)

    def _checkVersions(self):
        deferToThread(api.get_torrserver_version).addCallback(self._installedVersionChecked).addErrback(self._installedVersionCheckFailed)
        deferToThread(api.get_latest_torrserver_version).addCallback(self._latestVersionChecked).addErrback(self._latestVersionCheckFailed)

    def _installedVersionChecked(self, version):
        self._installed_version = version
        self._pending_checks -= 1
        self["installed_version"].setText(_("Installed version: %s") % (version or _("not running")))

    def _installedVersionCheckFailed(self, failure):
        self._installed_version = None
        self._pending_checks -= 1
        self["installed_version"].setText(_("Installed version: unknown"))
        logger.debug("Failed to check installed TorrServer version: %s", failure)

    def _latestVersionChecked(self, version):
        self._latest_version = version
        self._pending_checks -= 1
        self["latest_version"].setText(_("Latest version: %s") % (version or _("unknown")))

    def _latestVersionCheckFailed(self, failure):
        self._latest_version = None
        self._pending_checks -= 1
        self["latest_version"].setText(_("Latest version: unknown"))
        logger.debug("Failed to check latest TorrServer version: %s", failure)

    @staticmethod
    def _normalizedVersion(version):
        return version.strip().lstrip("vV") if version else version

    def updateServer(self):
        if self._updating:
            return
        if self._pending_checks:
            self.session.open(MessageBox, _("Still checking versions, please wait..."), MessageBox.TYPE_INFO, timeout=3)
            return
        if self._latest_version is None:
            self.session.open(MessageBox, _("Could not determine the latest TorrServer version."), MessageBox.TYPE_ERROR, timeout=5)
            return
        if self._normalizedVersion(self._installed_version) == self._normalizedVersion(self._latest_version):
            self.session.open(MessageBox, _("TorrServer is already up to date."), MessageBox.TYPE_INFO, timeout=3)
            return

        self._updating = True
        self["key_yellow"].setText(_("Updating..."))
        deferToThread(api.update_torrserver_binary).addCallback(self._updateServerDone).addErrback(self._updateServerFailed)

    def _updateServerDone(self, path):
        self._updating = False
        self["key_yellow"].setText(_("Update Server"))
        if path:
            self._installed_version = self._latest_version
            self["installed_version"].setText(_("Installed version: %s") % (self._latest_version or ""))
            self.session.open(MessageBox, _("TorrServer updated successfully."), MessageBox.TYPE_INFO, timeout=3)
        else:
            self.session.open(MessageBox, _("TorrServer update failed - see the debug log for details."), MessageBox.TYPE_ERROR, timeout=5)

    def _updateServerFailed(self, failure):
        self._updating = False
        self["key_yellow"].setText(_("Update Server"))
        logger.debug("TorrServer update failed: %s", failure)
        self.session.open(MessageBox, _("TorrServer update failed - see the debug log for details."), MessageBox.TYPE_ERROR, timeout=5)
