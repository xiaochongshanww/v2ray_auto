"""CLI entrypoint placeholder.

The refactor keeps command-line execution separate from the HTTP API. The full
CLI will be added after the core API stabilizes.
"""


def main() -> int:
    print("Use v2ray_auto.api.app for the refactored service entrypoint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
