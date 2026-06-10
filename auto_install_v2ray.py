"""Deprecated legacy entrypoint.

This branch replaced the historical all-in-one installer with the package-based
implementation under `v2ray_auto/`. Keep this file only to give old commands a
clear failure mode.
"""


def main() -> int:
    raise SystemExit(
        "auto_install_v2ray.py is deprecated on this branch. "
        "Use the refactored API entrypoint: v2ray_auto.api.app"
    )


if __name__ == "__main__":
    main()
