#!/usr/bin/env bash
# Download the python-build-standalone runtime for the current platform into
# desktop/runtime/python3.13 (same layout as the local dev runtime).
#
# Overridable env:
#   PYBUILD_STANDALONE_RELEASE  release tag (default 20260807)
#   PYBUILD_STANDALONE_VERSION  CPython version   (default 3.13.15)

set -euo pipefail

RELEASE="${PYBUILD_STANDALONE_RELEASE:-20260807}"
CPYTHON="${PYBUILD_STANDALONE_VERSION:-3.13.15}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)/runtime"
TARGET_DIR="${RUNTIME_DIR}/python3.13"

OS="$(uname -s)"
ARCH="$(uname -m)"

case "${OS}" in
  Darwin)
    case "${ARCH}" in
      arm64|aarch64) TARGET="aarch64-apple-darwin" ;;
      x86_64)        TARGET="x86_64-apple-darwin" ;;
      *) echo "unsupported darwin arch: ${ARCH}" >&2; exit 1 ;;
    esac ;;
  Linux)
    case "${ARCH}" in
      aarch64|arm64) TARGET="aarch64-unknown-linux-gnu" ;;
      x86_64)        TARGET="x86_64-unknown-linux-gnu" ;;
      *) echo "unsupported linux arch: ${ARCH}" >&2; exit 1 ;;
    esac ;;
  MINGW*|MSYS*|CYGWIN*)
    TARGET="x86_64-pc-windows-msvc" ;;
  *)
    echo "unsupported OS: ${OS}" >&2; exit 1 ;;
esac

URL="https://github.com/astral-sh/python-build-standalone/releases/download/${RELEASE}/cpython-${CPYTHON}%2B${RELEASE}-${TARGET}-install_only.tar.gz"

echo "runtime target: ${TARGET}"
echo "fetching: ${URL}"
mkdir -p "${RUNTIME_DIR}"
curl -fL --retry 3 -o /tmp/pbs.tar.gz "${URL}"

rm -rf "${TARGET_DIR}" "${RUNTIME_DIR}/.tmp"
mkdir -p "${RUNTIME_DIR}/.tmp"
tar -xzf /tmp/pbs.tar.gz -C "${RUNTIME_DIR}/.tmp"
rm -f /tmp/pbs.tar.gz

SRC_DIR="$(find "${RUNTIME_DIR}/.tmp" -maxdepth 3 -type d \( -name 'python' -o -name 'python3.13' \) | head -1)"
if [ -z "${SRC_DIR}" ]; then
  echo "unexpected archive layout:" >&2
  find "${RUNTIME_DIR}/.tmp" -maxdepth 3 -type d | head -20 >&2
  exit 1
fi

mv "${SRC_DIR}" "${TARGET_DIR}"
rm -rf "${RUNTIME_DIR}/.tmp"

BIN_PATH="${TARGET_DIR}/bin/python3"
[ -x "${BIN_PATH}" ] || BIN_PATH="${TARGET_DIR}/python.exe"
echo "runtime installed: ${TARGET_DIR}"
"${BIN_PATH}" --version
