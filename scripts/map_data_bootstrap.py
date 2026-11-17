"""Prepare map assets as soon as the WSGI app imports this module.

Import this module before game services. Those modules load map JSON into
module-level caches, so applying exceptions later in the startup sequence
would not update the data the running app uses.
"""

from scripts.build_map_data import main

MAP_DATA_READY = main()
