# License: GNU General Public License v3.0
#
# Re-exports the plugin-wide logger so torrmgr's own modules can use the
# same "from .Debug import logger" import as everything else in DonarCockpit.

from ..Debug import logger  # noqa: F401  pylint: disable=unused-import
