"""Apply Bordle's map-specific exceptions during deployment builds.

This uses the generated GeoJSON files committed with the app; the original
Natural Earth shapefile is intentionally not required at deploy time.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(ROOT))
    from scripts.add_french_guiana import main as add_french_guiana
    from scripts.assign_crimea_to_ukraine import main as assign_crimea_to_ukraine

    assign_crimea_to_ukraine()
    add_french_guiana()
    return True


if __name__ == "__main__":
    main()
