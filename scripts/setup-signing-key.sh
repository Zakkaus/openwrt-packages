#!/bin/sh
#
# Materialise the package signing key of an SDK build.
#
# The private key is a repository secret (PRIVATE_KEY) and never a file in git.
# This script writes it to keys/private-key.pem - the path .gitignore reserves,
# so a local build and CI use the same layout - checks that it belongs to the
# public key that is committed here and published with every release, and links
# it where the SDK looks for its signing key (BUILD_KEY_APK_SEC, which OpenWrt
# defaults to $(TOPDIR)/private-key.pem).
#
# Environment:
#   PRIVATE_KEY  the secret; when empty the packages are left unsigned
#   SDK_DIR      the unpacked SDK that builds the packages; when empty the key
#                is only materialised in keys/, which is useful to check a
#                secret by hand
#   OPENWRT_VERSION  only used in the messages
#   GITHUB_ENV   when set, PACKAGE_SIGNING=1 is handed to the following steps
set -eu

repo_dir="${GITHUB_WORKSPACE:-$(cd "$(dirname "$0")/.." && pwd)}"
keys_dir="${repo_dir}/keys"
private_key="${keys_dir}/private-key.pem"
public_key="${keys_dir}/public-key.pem"

if [ -z "${PRIVATE_KEY:-}" ]; then
	echo "::warning::PRIVATE_KEY is not set, the packages will be published unsigned"
	exit 0
fi

if [ ! -f "${public_key}" ]; then
	echo "::error::${public_key} is missing, the secret cannot be checked against it"
	exit 1
fi

# umask 077 so the file is created with mode 0600 instead of being chmod'ed
# afterwards
mkdir -p "${keys_dir}"
(umask 077; printf '%s\n' "${PRIVATE_KEY}" > "${private_key}")

# The secret has to belong to the published key: otherwise every package would
# be rejected by a device, and the run would only find out after compiling
if ! openssl ec -in "${private_key}" -pubout 2>/dev/null \
	| diff -q "${public_key}" - > /dev/null; then
	echo "::error::PRIVATE_KEY does not match keys/public-key.pem"
	rm -f "${private_key}"
	exit 1
fi
echo "Signing key: keys/private-key.pem (matches keys/public-key.pem)"

if [ -z "${SDK_DIR:-}" ]; then
	echo "SDK_DIR is not set, the key is only materialised in keys/"
	exit 0
fi

# Only apk signs individual packages. opkg (24.10 and older) verifies signed
# package lists, and these are single files, so there is nothing to sign there.
if ! grep -q 'CONFIG_SIGN_EACH_PACKAGE' "${SDK_DIR}/include/package-pack.mk"; then
	echo "${OPENWRT_VERSION:-This OpenWrt version} builds .ipk packages, which carry no per-package signature"
	rm -f "${private_key}"
	exit 0
fi

# BUILD_KEY_APK_SEC of that tree; the symlink keeps the only copy in keys/
ln -sf "${private_key}" "${SDK_DIR}/private-key.pem"

if [ -n "${GITHUB_ENV:-}" ]; then
	echo "PACKAGE_SIGNING=1" >> "${GITHUB_ENV}"
fi
