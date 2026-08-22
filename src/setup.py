# Copyright (C) 2026 by xcentaurix
# License: GNU General Public License v3.0

from Screens.Setup import Setup
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Sources.StaticText import StaticText
from twisted.internet.threads import deferToThread

from .Debug import logger, log_levels, setLogLevel
from .Version import PLUGIN, VERSION
from .ConfigInit import cfg
from . import api
from . import _


class SetupScreen(Setup):
    """Standard Setup-driven config screen for DonarCockpit, extended with a
    TorrServer version-check display and an "Update Server" action."""

    def __init__(self, session):
        Setup.__init__(self, session, setup=PLUGIN.lower(), plugin=f"Extensions/{PLUGIN}", PluginLanguageDomain=PLUGIN)
        self.skinName = "SetupDonarCockpit"
        self.setTitle(PLUGIN + " - " + _("Setup") + f" - {VERSION}")

        self["installed_version"] = StaticText(_("Installed version: checking..."))
        self["latest_version"] = StaticText(_("Latest version: checking..."))

        # screenpart_CockpitButtonBar binds its buttons via name="key_*" to a
        # Button component (matching the rest of the Cockpit family), not the
        # source="key_*" render="Label" StaticText pairing ConfigListScreen/Setup
        # set up by default - override those here to match.
        self["key_red"] = Button(_("Cancel"))
        self["key_green"] = Button(_("Save"))
        self["key_yellow"] = Button(_("Update Server"))
        self["yellowAction"] = ActionMap(["ColorActions"], {
            "yellow": self.updateServer,
        }, -1)

        self._installed_version = None
        self._latest_version = None
        self._pending_checks = 2
        self._updating = False
        self._checkVersions()

    # keySave/keyCancel wrap Setup's own (ConfigListScreen's, saving/canceling
    # each entry then closing the screen) just to block closing the screen
    # while an update download/install is in progress.

    def keyCancel(self):
        if self._updating:
            return
        Setup.keyCancel(self)

    def keySave(self):
        if self._updating:
            return
        setLogLevel(log_levels[cfg.debug_log_level.value])
        Setup.keySave(self)

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
