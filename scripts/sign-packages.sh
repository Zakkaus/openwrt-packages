#!/bin/sh
#
# Sign every .apk the SDK just built and verify the signatures.
#
# OpenWrt 25.12.6 packages with apk-tools 3.0.5 (commit b5a31c0). That mkpkg
# has no --sign option, and CONFIG_SIGN_EACH_PACKAGE does not exist in its
# package-pack.mk, so the packages leave the build unsigned. apk adbsign does
# exist: it rewrites each package in place and appends a signature from every
# private key loaded with --sign-key. Reading the still-unsigned package needs
# the global --allow-untrusted; without it adbsign stops before writing. The
# key is the one scripts/setup-signing-key.sh checked against
# keys/public-key.pem.
#
# apk verify then has to accept each package using only that public key. It
# rejects a package with no trusted signature (APKE_SIGNATURE_UNTRUSTED), which
# is also what a device does before public-key.pem is installed in
# /etc/apk/keys/. This workflow only supports .apk packages. An .ipk is opkg
# output and fails the build instead of being published.
#
# Environment:
#   SDK_DIR      the unpacked SDK; its staging_dir/host/bin/apk does the work
#   PACKAGE_DIR  where the packages were written (default: $SDK_DIR/bin/packages)
set -eu

repo_dir="${GITHUB_WORKSPACE:-$(cd "$(dirname "$0")/.." && pwd)}"
private_key="${repo_dir}/keys/private-key.pem"
public_key="${repo_dir}/keys/public-key.pem"

if [ -z "${SDK_DIR:-}" ] || [ ! -d "${SDK_DIR}" ]; then
	echo "::error::SDK_DIR is not set or does not exist, the packages cannot be signed"
	exit 1
fi

package_dir="${PACKAGE_DIR:-${SDK_DIR}/bin/packages}"
apk="${SDK_DIR}/staging_dir/host/bin/apk"

if [ ! -x "${apk}" ]; then
	echo "::error::${apk} does not exist, the packages cannot be signed"
	exit 1
fi
if [ ! -f "${private_key}" ] || [ ! -f "${public_key}" ]; then
	echo "::error::The checked signing key pair is missing from keys/"
	exit 1
fi

if find "${package_dir}" -type f -name '*.ipk' | grep -q .; then
	echo "::error::Found an .ipk package; opkg output is not supported"
	exit 1
fi

packages="$(find "${package_dir}" -type f -name '*.apk' | sort)"
if [ -z "${packages}" ]; then
	echo "::error::The SDK produced no .apk package to sign"
	exit 1
fi

# adbsign returns success even when it loaded no private key and therefore
# wrote nothing. The verify pass below is what makes that failure visible.
printf '%s\n' "${packages}" | while IFS= read -r package; do
	echo "Signing ${package}"
	"${apk}" --allow-untrusted adbsign \
		--sign-key "${private_key}" --reset-signatures "${package}"
done

printf '%s\n' "${packages}" | while IFS= read -r package; do
	echo "Verifying ${package}"
	"${apk}" --keys-dir "${repo_dir}/keys" verify -v "${package}"
done
