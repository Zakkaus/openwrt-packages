#!/bin/sh
#
# Download and unpack the OpenWrt SDK of one target.
#
# The SDK comes from the host the prepare job picked (SDK_URL, the official
# downloads server when it serves the release) and, when prepare found one, from
# the next mirror that does (SDK_FALLBACK_URL): they serve the same release
# tree, so the mirror covers the official host being unreachable or slow, and
# releases the official tree has already rotated into archive.openwrt.org.
#
# Every download is verified against the sha256sums published in the same
# directory, so a truncated or corrupted transfer is retried on the next mirror
# instead of failing later, halfway through compiling with the SDK.
#
# Environment:
#   SDK_URL           the SDK tarball to fetch first
#   SDK_FALLBACK_URL  the same tarball on the mirror; may be empty
#   SDK_NAME          file name of the tarball; derived from SDK_URL when empty
#   RUNNER_TEMP       where the SDK is unpacked; defaults to a fresh temp dir
#   GITHUB_ENV        when set, SDK_DIR is handed to the following steps
set -eu

sdk_url="${SDK_URL:?SDK_URL is not set}"
sdk_name="${SDK_NAME:-${sdk_url##*/}}"
sdk_fallback_url="${SDK_FALLBACK_URL:-}"
work_dir="${RUNNER_TEMP:-$(mktemp -d)}"
download_dir="${work_dir}/sdk-dl"
sdk_root="${work_dir}/sdk"

echo "SDK: ${sdk_name}"
echo "Download: ${sdk_url}"
echo "Fallback: ${sdk_fallback_url:-none}"

# The checksum the publisher of that directory lists for the tarball, so a
# broken transfer is caught before the build. Empty when the directory does not
# publish sha256sums at all, which only earns a warning below.
expected_sha256() {
	curl -fsSL --http1.1 --retry 2 --retry-delay 3 --connect-timeout 20 --max-time 60 \
		"$1/sha256sums" 2>/dev/null \
		| awk -v name="${sdk_name}" '($2 == name || $2 == "*" name) { print $1; exit }'
}

try_download() {
	url="$1"
	echo "Downloading ${url}"
	echo "Checksum: ${url%/*}/sha256sums"
	rm -f "${download_dir}/${sdk_name}"
	# No --retry-all-errors on purpose: a 404 means this host does not have the
	# tarball and the next mirror should be tried at once, while timeouts,
	# connection refusals and 5xx responses are still retried here. A transfer
	# that stalls below 1 KiB/s for a minute counts as a failure too.
	if ! curl -fL --http1.1 --retry 5 --retry-delay 5 --retry-connrefused \
		--connect-timeout 20 --speed-limit 1024 --speed-time 60 \
		-o "${download_dir}/${sdk_name}" "${url}"; then
		echo "::warning::Download of ${sdk_name} from ${url} failed"
		return 1
	fi

	expected="$(expected_sha256 "${url%/*}")"
	if [ -z "${expected}" ]; then
		echo "::warning::${url%/*}/sha256sums does not list ${sdk_name}, the download is unverified"
		return 0
	fi
	actual="$(sha256sum "${download_dir}/${sdk_name}" | cut -d' ' -f1)"
	if [ "${actual}" != "${expected}" ]; then
		echo "::warning::SHA256 of ${sdk_name} from ${url} is ${actual}, expected ${expected}"
		return 1
	fi
	echo "SHA256 of ${sdk_name} matches ${url%/*}/sha256sums"
}

mkdir -p "${download_dir}" "${sdk_root}"

sdk_source=""
if try_download "${sdk_url}"; then
	sdk_source="${sdk_url}"
elif [ -n "${sdk_fallback_url}" ] && [ "${sdk_fallback_url}" != "${sdk_url}" ] \
	&& try_download "${sdk_fallback_url}"; then
	sdk_source="${sdk_fallback_url}"
else
	echo "::error::Could not download ${sdk_name} from ${sdk_url}${sdk_fallback_url:+ or ${sdk_fallback_url}}"
	exit 1
fi
echo "SDK source: ${sdk_source}"

case "${sdk_name}" in
	*.tar.zst) tar_opts=--zstd ;;
	*.tar.xz)  tar_opts=-J ;;
	*)         tar_opts= ;;
esac
# shellcheck disable=SC2086 # tar_opts is one flag or empty on purpose
tar ${tar_opts} -C "${sdk_root}" -xf "${download_dir}/${sdk_name}"
rm -rf "${download_dir}"

sdk_dir="$(find "${sdk_root}" -mindepth 1 -maxdepth 1 -type d -name 'openwrt-sdk-*' | head -n1)"
if [ -z "${sdk_dir}" ]; then
	echo "::error::Unexpected SDK layout, no openwrt-sdk-* directory found"
	exit 1
fi
echo "SDK directory: ${sdk_dir}"

if [ -n "${GITHUB_ENV:-}" ]; then
	echo "SDK_DIR=${sdk_dir}" >> "${GITHUB_ENV}"
fi
