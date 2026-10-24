#!/bin/sh
#
# Materialise the package signing key of an SDK build.
#
# The private key is a repository secret (PRIVATE_KEY) and never a file in git.
# This script writes it to keys/private-key.pem - the path .gitignore reserves,
# so a local build and CI use the same layout - and checks that it belongs to
# the public key that is committed here and published with every release.
# scripts/sign-packages.sh signs the built .apk files with it afterwards: the
# OpenWrt 25.12 SDK packages with apk-tools 3.0.5, whose "apk mkpkg" cannot
# sign, so the SDK is not asked to sign during the build.
#
# Environment:
#   PRIVATE_KEY  the secret; required, a missing key fails the build
#   GITHUB_ENV   when set, PACKAGE_SIGNING=1 is handed to the following steps
set -eu

repo_dir="${GITHUB_WORKSPACE:-$(cd "$(dirname "$0")/.." && pwd)}"
keys_dir="${repo_dir}/keys"
private_key="${keys_dir}/private-key.pem"
public_key="${keys_dir}/public-key.pem"

if [ -z "${PRIVATE_KEY:-}" ]; then
	echo "::error::PRIVATE_KEY is not set, refusing to build packages that cannot be signed"
	exit 1
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

if [ -n "${GITHUB_ENV:-}" ]; then
	echo "PACKAGE_SIGNING=1" >> "${GITHUB_ENV}"
fi
