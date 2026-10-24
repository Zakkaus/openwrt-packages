# vmlinux-bpf-build

Builds a BTF-enabled `vmlinux` for OpenWrt targets and builds the `vmlinux-btf`,
`dae` and `honk` packages for the same architectures, then publishes everything
in a single GitHub Release per kernel version.

The BTF is produced the way the OpenWrt package
[QiuSimons/vmlinux-btf](https://github.com/QiuSimons/vmlinux-btf) does it: a few
small stub sources (`src/shadow_btf_*.c`, vendored from that repository) include
the key kernel headers, the target compiler emits their DWARF, and `pahole`
converts that into the detached BTF blob. Everything comes from the **official
OpenWrt SDK** of each target — its prepared kernel headers and its cross
toolchain — so neither an OpenWrt buildroot nor a kernel configuration or build
is involved, and the types are exactly those of the kernel OpenWrt ships for
that target, patches included.

The packages around it are ordinary OpenWrt packages: the repository root
doubles as an [OpenWrt feed](#repository-layout), with `vmlinux-btf/`, `dae/` and
`honk/` next to the BTF sources, so the released assets are real `.apk` packages
that can be installed with `apk add`.

Everything happens in a single workflow,
[`.github/workflows/build-vmlinux-btf.yml`](.github/workflows/build-vmlinux-btf.yml),
which is documented below. See [Provenance](#provenance) for where each part
comes from.

---

## Repository layout

```
.
├── .github/workflows/build-vmlinux-btf.yml  # the only workflow
├── vmlinux-btf/  # OpenWrt package "vmlinux-btf": Makefile (prebuilt blob)
├── dae/          # OpenWrt package "dae":  Makefile + build.sh + files/ (init, UCI)
├── honk/         # OpenWrt package "honk": Makefile + build.sh + files/ (init, UCI, config)
├── keys/         # public-key.pem: the key the .apk packages are signed with
├── scripts/      # setup-signing-key.sh: restores the signing key from the secret
└── src/          # vendored BTF stubs from QiuSimons/vmlinux-btf
```

The repository root is an OpenWrt feed. The workflow writes
`src-link local <workspace>` into the SDK's `feeds.conf`, installs the packages
from it and builds them with `make package/<name>/compile`, which is what turns
them into `.apk` packages. `vmlinux-btf` is special: the workflow hands the BTF
blob it just produced to the package as `VMLINUX_BTF_SRC`, so the package only
installs it and the archive and the package hold identical bytes.
The upstream sources are checked out into `dae/src` and `honk/src` (they are not
committed), so the directories can also be copied into an OpenWrt buildroot,
or used against a manually unpacked SDK:

```sh
git clone --recurse-submodules --branch v2.1.1 https://github.com/daeuniverse/dae dae/src
git clone --branch v0.1.0-beta.1 https://github.com/daeuniverse/honk honk/src
```

## What it produces

| Asset | Contents | Built from |
|---|---|---|
| `<openwrt_version>-vmlinux-<openwrt_arch>-<kernel_version>.tar.xz` | one file named `vmlinux`: the detached BTF blob (the same file the upstream package installs) | `src/shadow_btf_*.c` compiled against the SDK's prepared kernel headers with the SDK toolchain, then `pahole` |
| `<openwrt_version>-vmlinux-btf-<openwrt_arch>-<kernel_version>.apk` | OpenWrt package `vmlinux-btf` (version = kernel version), installing `/usr/lib/debug/boot/vmlinux`, the `vmlinux-<kernel release>` symlink, `/usr/share/vmlinux-btf/version` and install scripts that enforce the kernel generation | the same blob, packaged with [`vmlinux-btf/Makefile`](vmlinux-btf/Makefile) |
| `<openwrt_version>-dae-2.1.1-<openwrt_arch>.apk` | OpenWrt package `dae` 2.1.1, installing `/usr/bin/dae`, a procd init script and `/etc/config/dae` | [daeuniverse/dae](https://github.com/daeuniverse/dae) tag `v2.1.1`, built by [`dae/Makefile`](dae/Makefile) |
| `<openwrt_version>-honk-0.1.0_beta1-<openwrt_arch>.apk` | OpenWrt package `honk` 0.1.0_beta1, installing `/usr/bin/honk-core` (full feature set with the embedded doona UI), a procd init script and `/etc/config/honk` | [daeuniverse/honk](https://github.com/daeuniverse/honk) tag `v0.1.0-beta.1`, built by [`honk/Makefile`](honk/Makefile) |
| `public-key.pem` | the public key that verifies the signature of every `.apk` asset of the release | [`keys/public-key.pem`](keys/public-key.pem), see [Verifying the packages](#verifying-the-packages) |

Both userspace packages are OpenWrt services: they install
`/etc/init.d/<name>`, `/etc/config/<name>` and a default configuration
(`/etc/dae/config.dae` from the upstream example, `/etc/honk/config.dae` from
[`honk/files/config.dae`](honk/files/config.dae)). The service stays disabled
until `option enabled '1'` is set; see [OpenWrt integration](#openwrt-integration).

Every archive and package is uploaded together with its `.sha256` checksum.
The `dae` and
`honk` packages are built once per OpenWrt architecture and are pinned to an
upstream release, so their name carries that version and not the kernel version;
`x86_64` gets `25.12.5-dae-2.1.1-x86_64.apk` while `aarch64_cortex-a76` gets
`25.12.5-honk-0.1.0_beta1-aarch64_cortex-a76.apk`. OpenWrt 25.x produces
`.apk` packages; for older releases (24.10 and earlier) the same step produces
`.ipk` and the asset keeps that extension.

The version also flows into the binaries: it is passed to the package Makefiles
as `DAE_VERSION` / `HONK_VERSION`, dae's own make receives it as `VERSION`, and
honk derives the string it embeds from `GITHUB_REF`, so a
`refs/tags/v0.1.0-beta.1` ref is exported for its build (the build script then
asserts that the tag, not the git fallback, is what ended up in the binary).
`0.1.0-beta.1` is not a valid apk version — `~` there introduces a commit hash
— so the package spells the beta pre-release as `0.1.0_beta1`, while the sources
and the embedded version come from the upstream tag `v0.1.0-beta.1` itself.

## Usage

1. Go to **Actions → Build vmlinux (BTF) → Run workflow**.
2. Fill in the inputs:

| Input | Default | Meaning |
|---|---|---|
| `openwrt_version` | `25.12.5` | OpenWrt release to build for, e.g. `25.12.5` or `24.10.8`. The kernel version is taken from that release, not entered by hand. |

The kernel version comes from the chosen OpenWrt release, so `openwrt_version`
is the only input (there is no choice between a BTF blob and a full `vmlinux`
ELF any more).

3. The result appears under **Releases**, tagged
   `openwrt-<openwrt_version>-<kernel_version>-<date>` — for example
   `openwrt-25.12.5-6.12.94-20261024`. `<date>` is the UTC date of the run, the
   same for every kernel version it publishes. All architectures of one kernel
   version are collected in that single release; re-running the workflow
   overwrites the existing assets instead of failing, and an existing
   tag/release is reused (a second run on the same UTC day publishes into that
   day's release). The asset names themselves do not carry the date.
   The `dae`/`honk` assets are kernel independent, so every release published by
   a run carries the same set of them (all five architectures), while each
   `vmlinux-btf` package sits in the release of its kernel version.

On a device, the BTF blob is normally installed where libbpf and `bpftool`
expect it, `/usr/lib/debug/boot/vmlinux`. The `vmlinux-btf` package does exactly
that (including the `vmlinux-<kernel release>` symlink the upstream package
creates), so the archive can be skipped entirely:

```sh
# public-key.pem from the same release; the file name on the device does not
# matter, apk matches the key itself rather than the file name
cp public-key.pem /etc/apk/keys/

apk add 25.12.5-vmlinux-btf-aarch64_cortex-a76-6.12.94.apk
# OpenWrt 24.10 and older: opkg install 24.10.8-vmlinux-btf-aarch64_cortex-a76-6.12.94.ipk
```

The package records the kernel version it was built for in
`/usr/share/vmlinux-btf/version`. Its preinst script refuses the installation
when the running kernel belongs to a different generation (`major.minor`, so
`6.12.94` fits `6.12.95` but not `6.13.x`); the postinst script then adds
`/usr/lib/debug/boot/vmlinux-<running release>`, so libbpf also finds the blob on
kernels with a different point release or vendor suffix. Both scripts skip the
check when installing into an offline root (`IPKG_INSTROOT` is set, e.g.
ImageBuilder), where `uname` describes the build host rather than the target.

The `dae` and `honk` assets are OpenWrt packages as well:

```sh
apk add 25.12.5-dae-2.1.1-aarch64_cortex-a76.apk
apk add 25.12.5-honk-0.1.0_beta1-aarch64_cortex-a76.apk
```

The packages are signed, so `apk` accepts them once `public-key.pem` is in
`/etc/apk/keys/`; without the key it needs `--allow-untrusted` (see
[Verifying the packages](#verifying-the-packages)). The
userspace packages install `/usr/bin/dae` and `/usr/bin/honk-core`, a procd init
script, a UCI configuration and a default configuration file. `honk` declares
`libstdcpp` and the kernel modules its datapath needs as dependencies, so `apk`
pulls them in automatically.

## Verifying the packages

The `.apk` assets are signed. `public-key.pem` is the matching public key; it is
committed as [`keys/public-key.pem`](keys/public-key.pem) and attached to every
release, so take it from whichever is convenient:

```sh
# from the newest release, or from the repository at the same tag/commit
curl -LO https://github.com/daeuniverse/vmlinux-bpf-build/releases/latest/download/public-key.pem
curl -LO https://raw.githubusercontent.com/daeuniverse/vmlinux-bpf-build/main/keys/public-key.pem
```

Copy it into the trust store and install as usual - no `--allow-untrusted`
needed:

```sh
cp public-key.pem /etc/apk/keys/
apk add 25.12.5-vmlinux-btf-aarch64_cortex-a76-6.12.94.apk
```

The file name in `/etc/apk/keys/` does not matter: apk identifies a key by its
content rather than by the name, and it tries every key it finds there, so this
one lives next to OpenWrt's own key without replacing it. Without the key apk
rejects the packages as untrusted.

`.ipk` assets (OpenWrt 24.10 and older) are not signed per package - `opkg` has
no such concept, it verifies signed package *lists* - so compare their `.sha256`
checksum instead.

## OpenWrt integration

Both packages are ordinary OpenWrt services and are disabled after installation.
The init scripts are [`dae/files/dae.init`](dae/files/dae.init) and
[`honk/files/honk.init`](honk/files/honk.init); their UCI files are
`/etc/config/dae` and `/etc/config/honk`:

```sh
# /etc/config/dae or /etc/config/honk
config dae 'config'            # config honk 'config'
	option enabled '0'
	option config_file '/etc/dae/config.dae'   # or /etc/honk/config.dae

/etc/init.d/dae enable && /etc/init.d/dae start
/etc/init.d/honk enable && /etc/init.d/honk start
```

The scripts follow the usual procd conventions:

* `start_service` does nothing while `enabled` is `0`.
* `dae` runs `dae validate -c <config_file>` before starting; a configuration
  that fails the rule pipeline (including missing geo assets) is logged and the
  running instance is left untouched.
* `reload` sends `SIGHUP` to the running instance (`procd_send_signal` for dae,
  `honk-core reload` for honk), so established connections survive a
  configuration change. Both services respawn after a crash, and stdout/stderr
  are forwarded to syslog (`logread`), so no log file rotation is needed.
* The honk script mounts `bpffs` on `/sys/fs/bpf` when it is not mounted yet,
  because aya pins its maps there and OpenWrt does not mount it by itself.

Kernel modules are declared as package dependencies:

| Package | Why |
|---|---|
| `kmod-sched-core`, `kmod-sched-bpf`, `kmod-veth`, `kmod-xdp-sockets-diag` | TC-bpf datapath, `dae0` veth pair and the socket/XDP diagnostics used by dae |
| `kmod-veth`, `kmod-sched-core`, `kmod-sched-bpf` | the same TC datapath and `dae0` link pair for honk |
| `kmod-nft-core`, `kmod-nft-queue`, `kmod-nfnetlink-queue`, `kmod-nf-conntrack` | honk's NFQUEUE staging for ambiguous LAN UDP first packets |

BTF is still required by both eBPF engines; install the `vmlinux-btf` package of
the running kernel (or another BTF blob at `/usr/lib/debug/boot/vmlinux`). honk
0.1.0 also reads the external BTF of OpenWrt kernels when sysfs has no
`vmlinux`. honk's real eBPF backend requires Linux 6.12 or newer, so it applies
to the 25.x releases; 24.10 (6.6) is too old for honk, while dae still runs on
both.

### honk's embedded UI

The honk package is built with the full feature set — the crate defaults
(`clash-api`, `mimalloc`, `rprx`) plus `ebpf` and `native-ui` — so the pinned
doona dashboard is embedded in `/usr/bin/honk-core`. Doona is downloaded as a
release archive at build time (SHA-256 verified against honk's
`.github/ci/pins.env`); the frontend is never compiled here.

The shipped `/etc/honk/config.dae` enables it on loopback:

```dae
experimental {
    native_api {
        enabled: true
        listen: '127.0.0.1:9527'
        allow_anonymous_loopback: true
        ui: 'embedded'
    }
}
```

Reach it through SSH port forwarding (`ssh -L 9527:127.0.0.1:9527 root@router`)
and open `http://127.0.0.1:9527/`. Anonymous loopback access is for local setup;
replace it with `secret: '<long random token>'` (and terminate TLS at a reverse
proxy) before exposing the API on any other interface. honk keeps runtime state
in `global.data_dir` (`/var/lib/honk` by default); on OpenWrt `/var` is a tmpfs,
so Selector choices and subscription caches do not survive a reboot — point
`data_dir` at persistent storage if that matters.

## Architectures

One representative target/subtarget per OpenWrt architecture (`arch_packages`):

| OpenWrt arch | target/subtarget | kernel arch |
|---|---|---|
| `x86_64` | `x86/64` | x86_64 |
| `aarch64_generic` | `armsr/armv8` | arm64 |
| `aarch64_cortex-a53` | `mediatek/filogic` | arm64 |
| `aarch64_cortex-a72` | `bcm27xx/bcm2711` | arm64 |
| `aarch64_cortex-a76` | `bcm27xx/bcm2712` | arm64 |

Several targets share the same `arch_packages` (for `aarch64_cortex-a53` also
`qualcommax/ipq807x`, `sunxi/cortexa53`, `mvebu/cortexa53`, …), so the list picks
one each. If a device needs a different kernel `.config`, replace the row with
another target/subtarget that reports the same `arch_packages` — the workflow
verifies `arch_packages` against `profiles.json` and fails fast if it does not
match.

The packages are built for every row of that table, one job per architecture,
using the SDK of that architecture (the same matrix drives the kernel, the BTF
package and the userspace builds). `vmlinux-btf` only wraps the blob that the
`build` job produced for that architecture. `dae` is plain Go, so it only needs
`GOOS=linux` plus the right `GOARCH`/`GOAMD64`/`GOARM64`, and it is tuned per
architecture: `amd64` for `x86_64`, `arm64` with `GOARM64=v8.0` for the generic
and Cortex-A53/A72 targets, and `GOARM64=v8.2,lse` for `aarch64_cortex-a76`
(the A76 implements ARMv8.2 with LSE atomics, which lets Go emit atomic
instructions instead of LL/SC loops). `honk` uses the target's own OpenWrt
toolchain, so each architecture gets a binary built against its own musl and
instruction set. It is compiled with the full feature set and embeds the pinned
doona UI, so the dashboard needs no runtime download or frontend build.

## How it works

```mermaid
flowchart LR
  P["prepare<br/>resolve SDK, kernel version,<br/>arch_packages and build matrix"]
  K["build (x86_64, aarch64_generic, aarch64_cortex-a53/a72/a76)<br/>SDK kernel headers + SDK toolchain<br/>stubs → DWARF → pahole → BTF blob<br/>+ vmlinux-btf package"]
  D["dae 2.1.1 (one per OpenWrt arch)<br/>Go, clang for the eBPF objects"]
  H["honk 0.1.0_beta1 (one per OpenWrt arch)<br/>Rust, full features + embedded doona UI,<br/>eBPF object + BoringSSL via the SDK gcc/g++"]
  R["release<br/>group by kernel version,<br/>one Release per version"]
  P --> K
  P --> D
  P --> H
  K --> R
  D --> R
  H --> R
```

**prepare** — reads
`releases/<version>/targets/<target>/<subtarget>/profiles.json` for
`arch_packages` (validated) and `linux_kernel.version`, and finds the SDK archive
of each target in the download index.

**build** (one job per architecture, does not depend on the other jobs) —
downloads and extracts the SDK, then takes from it:

* the kernel tree OpenWrt already prepared (`build_dir/*/linux-*/linux-*/`, with
  `include/generated/autoconf.h` for that target's `.config`, the generated
  include trees and `Module.symvers`); the `.c` files are stripped from the SDK,
  which does not matter because only headers are included,
* the cross toolchain (`staging_dir/toolchain-*/bin/*-openwrt-linux-musl-gcc`),
  used as an absolute `CROSS_COMPILE` and put on `PATH`,
* `STAGING_DIR` / `STAGING_DIR_HOST`, which the OpenWrt toolchain needs to find
  its sysroot (the values follow OpenWrt's `rules.mk`).

It compiles `src/shadow_btf_core.c` and the two optional units with the upstream
`BTF_CFLAGS` option set (`-nostdinc`, `-isystem` of the compiler's own include
dir, `-D__KERNEL__`, the kernel include trees, `-fshort-wchar`, `-g -gdwarf-4`,
`-fno-eliminate-unused-debug-types`, …), links them with `ld -r` and runs
`pahole --btf_encode_detached` (falling back to `pahole -J` plus
`objcopy --dump-section .BTF` on pahole versions without detached encoding). It
then checks the blob's BTF header (magic `0xeb9f`, non-empty type section) and
that `pahole -C sk_buff` finds the struct, which is the same smoke test the
upstream Makefile runs. Nothing is downloaded from kernel.org and no kernel is
configured or compiled. The same blob is then handed to
[`vmlinux-btf/Makefile`](vmlinux-btf/Makefile) as `VMLINUX_BTF_SRC` and the SDK
packages it, with the kernel version as the package version; the symlink name is
`UTS_RELEASE` from the SDK's `include/generated/utsrelease.h` (the SDK does not
keep `include/config/kernel.release`), so it matches `uname -r` on the device.

**dae** — [`dae/Makefile`](dae/Makefile) is an ordinary OpenWrt package whose
`Build/Compile` calls [`dae/build.sh`](dae/build.sh); the job checks out the
`v2.1.1` tag and only installs the Go toolchain (`actions/setup-go`, using the
version from `dae/src/go.mod`) and clang, which compiles the eBPF objects that
`bpf2go` embeds. The submodules holding the eBPF headers are checked out with
the sources. The build script maps
`arch_packages` to `GOARCH`/`GOAMD64`/`GOARM64` (`amd64` with `v1` for x86_64,
`arm64` with `v8.0`, or `v8.2,lse` on Cortex-A76) and runs dae's own Makefile;
that Makefile unsets the cross-compile variables around `go generate` only, so
the host side still generates the eBPF objects (`GOARM64` needs Go 1.23 or
newer). It then asserts that the result really is a binary for the target and
that it needs no shared library at all.

**honk** — [`honk/Makefile`](honk/Makefile) and [`honk/build.sh`](honk/build.sh)
do the same for honk, whose sources are checked out from the `v0.1.0-beta.1`
tag: the job installs the two toolchains pinned in honk's `rust-toolchain.toml`
files (stable for honk-core, a nightly with `rust-src` for the eBPF object) plus
the pinned `bpf-linker` from `.github/ci/pins.env`, and the SDK's package build
does the rest. The build script writes small `gcc`/`g++`
wrappers that drop the clang-style `--target=` flags CMake injects into
`boring-sys` compile rules (upstream's `ci/zigcc` trick, with the OpenWrt
compiler as the real compiler), downloads and SHA-256 checks the pinned doona
UI archive from its GitHub release (`ci/fetch-doona.sh`), and builds `honk-core`
with the full feature set (`ebpf,native-ui` on top of `clash-api`, `mimalloc`
and `rprx`) and `-C link-self-contained=no -C
target-feature=-crt-static` so it links against the SDK's musl instead of the
musl bundled with Rust (the toolchain has no static unwind library, so
everything is dynamic — the package declares `libstdcpp` as its dependency).
The `ebpf` feature makes honk's `build.rs` build the eBPF object with the pinned
nightly and embed it, and `native-ui` makes it embed the doona assets from
`HONK_DOONA_DIR`, so the build script only has to provide that directory (the
frontend is never compiled). It finally rejects a GLIBC interpreter,
`libsystemd` and any unexpected shared library, and asserts that the version
embedded by honk's build script is the release tag `v0.1.0-beta.1` (the package
itself is versioned `0.1.0_beta1`, which is how apk spells that pre-release)
and that the binary contains the embedded UI.

**release** — collects the artifacts, groups the kernel assets by kernel version,
and for each group checks whether the tag/release already exists
(`gh release view` and `gh api .../git/ref/tags/...`) before creating it, then
uploads all assets with `--clobber`, together with `public-key.pem` so the
signature of the `.apk` packages can be verified without cloning the repository.
The `vmlinux-btf` packages are grouped like the archives; the `dae`/`honk` assets
are added to every group, since they do not belong to one kernel version.
Creating the tag is done with `gh`, pointing it at the commit the workflow ran
on.

**signing** — the signing key is a repository secret and never a file in git.
[`scripts/setup-signing-key.sh`](scripts/setup-signing-key.sh) writes it back to
`keys/private-key.pem` (the path `.gitignore` reserves, so a local build has the
same layout), checks it against [`keys/public-key.pem`](keys/public-key.pem) and
links it where the SDK signs with it; each build job signs its package
(OpenWrt's `CONFIG_SIGN_EACH_PACKAGE`) and verifies the result before the
upload, so a package that does not verify against the published key cannot
reach a release. See [Verifying the packages](#verifying-the-packages) for what
a device needs.

## Provenance

Everything in this repository is derived from other projects; the table below
records where each piece comes from and what was taken from it.

| Source | Taken from it |
|---|---|
| [QiuSimons/vmlinux-btf](https://github.com/QiuSimons/vmlinux-btf) (OpenWrt package, GPL-3.0) | The whole approach and the code behind it: `src/shadow_btf_{core,modules,private}.c` are vendored verbatim (upstream commit `4585b7c`), including the `BTF_KEEP` trick that keeps the interesting structs reachable, and the `BTF_CFLAGS` set and the pahole invocation (detached encode, the `-J` + `objcopy` fallback, the `pahole -C sk_buff` smoke test) follow its `Makefile`. Only the environment differs: upstream runs inside the OpenWrt buildroot or its SDK container, while this workflow rebuilds `$(LINUX_DIR)`, `TARGET_CC_NOCACHE` and `STAGING_DIR` from the SDK tarball. [`vmlinux-btf/Makefile`](vmlinux-btf/Makefile) follows the install layout of its package: `/usr/lib/debug/boot/vmlinux` plus the `vmlinux-<kernel release>` symlink, with `LINUX_VERSION` (here `VMLINUX_BTF_VERSION`) as the version, except that the blob arrives prebuilt instead of being compiled inside the package. |
| [openwrt/openwrt](https://github.com/openwrt/openwrt) (GPL-2.0) | The prebuilt SDKs (toolchain, the prepared kernel header tree, `staging_dir` layout), the `STAGING_DIR` / `STAGING_DIR_HOST` semantics from `rules.mk`, and the target metadata (`profiles.json`: `arch_packages`, `linux_kernel.version`). |
| [daeuniverse/dae](https://github.com/daeuniverse/dae) (AGPL-3.0) | The sources at tag `v2.1.1`, built with its own `Makefile` and its `dae_bpf_headers` submodules. The cross-compile recipe (`CGO_ENABLED=0`, clang for `bpf2go`, `GOOS=linux`) follows its release workflow; the Makefile itself unsets `GOOS`/`GOARCH` around `go generate` so the eBPF generation runs on the host. Its release tags are where the package version (`2.1.1`, the tag without its leading `v`) comes from. |
| [daeuniverse/honk](https://github.com/daeuniverse/honk) (GPL-3.0) | The sources at tag `v0.1.0-beta.1` and the build recipe from its release workflow: pinned toolchains from the `rust-toolchain.toml` files, the eBPF object built by `build.rs` with `-Zbuild-std=core --target bpfel-unknown-none` plus its BTF assertion, `bpf-linker` pinned through `.github/ci/pins.env`, the full feature set (`clash-api`, `mimalloc`, `rprx`, `ebpf`, `native-ui`), the zig wrapper trick from `ci/zigcc`/`ci/zigcxx`/`ci/zig-bindgen-env` and the CMake/bindgen handling it exists for — re-implemented here against the OpenWrt `gcc`/`g++` instead of zig, because the SDK already provides a compiler for the target and its libc. Its release tags are where the version comes from: the binary embeds `v0.1.0-beta.1`, the package is versioned `0.1.0_beta1` because apk reserves `~` for a commit hash. The `native-ui` feature embeds the doona dashboard, fetched by its `ci/fetch-doona.sh` from the release pinned in `.github/ci/pins.env`. |
| [Zakkaus/doona](https://github.com/Zakkaus/doona) (GPL-3.0) | The prebuilt dashboard archive embedded by honk's `native-ui` feature (version and SHA-256 come from honk's `pins.env`); it is downloaded, never built, by this repository. |
| [aya-rs/bpf-linker](https://github.com/aya-rs/bpf-linker) | The prebuilt `bpf-linker` binary (version and SHA256 come from honk's `pins.env`). |
| GitHub Actions | `actions/checkout`, `actions/setup-go`, `actions/upload-artifact`, `actions/download-artifact`, `dtolnay/rust-toolchain`. |

The upstream sources are checked out by the workflow (their commits are in the
job logs), the packages are pinned to the upstream releases above, and the
`dae`/`honk` packages install the upstream license text under
`/usr/share/licenses/<name>/LICENSE`.

## Notes and limitations

* **BTF fidelity.** The stubs are compiled against the kernel tree the SDK ships
  for that target, so the types come from OpenWrt's own kernel sources *with its
  patches applied* and from the target's own `autoconf.h`, i.e. from what the
  device runs. No upstream kernel source is involved, so the earlier caveat
  about patched struct layouts no longer applies.
* **Coverage.** The blob contains the types the stubs reach: the core unit
  (task/socket/skbuff/netdevice/bpf/…), plus netfilter, routing, qdisc, XDP
  socket and a few private structs when the target config and headers allow it.
  A program that needs a type nobody includes will not find it — extend the
  stubs (and keep them in sync with upstream) if that happens.
* **One subtarget per architecture** is built (see above); the prepared kernel
  tree of that subtarget is the one used.
* **`pahole` comes from the runner** (`dwarves` on Ubuntu 24.04). The workflow
  prefers `--btf_encode_detached` and falls back to `-J` + `objcopy` when the
  installed pahole is too old for it.
* **honk** is linked dynamically against the SDK's musl, so the package depends
  on `libstdcpp` and `apk`/`opkg` pull it in. The build fails if the binary asks
  for a GLIBC loader, for `libsystemd` or for any shared library besides libc,
  libgcc_s and libstdc++. If the Rust LTO link ever trips the linker plugin of
  GNU `ld`, set `CARGO_PROFILE_RELEASE_LTO=false` for that build. It is built
  with the **full feature set** (Clash API, native API and the embedded doona
  UI); `native-ui` needs `HONK_DOONA_DIR`, which `build.sh` obtains through
  honk's `ci/fetch-doona.sh` (download plus SHA-256 check, no frontend build).
  The compressed UI adds a few minutes of build time per architecture.
* **The init scripts and their UCI files** are part of the packages and the
  service is disabled by default. dae validates its configuration before
  starting; honk mounts `bpffs` when needed; both reload with SIGHUP and respawn
  after a crash. The kernel modules in the `DEPENDS` list are the datapath
  requirements, not optional extras.
* **`vmlinux-btf` is kernel-generation locked.** The preinst refuses a package
  whose kernel generation differs from `uname -r`, so installing it for a kernel
  that is not running (for example after upgrading the kernel package but before
  rebooting) fails with an explicit error instead of leaving a blob whose CO-RE
  relocations resolve the wrong types. The postinst adds the
  `vmlinux-<uname -r>` symlink, and the installed version is readable from
  `/usr/share/vmlinux-btf/version`.
* **dae** is a static Go binary with no libc dependency at all, one package per
  architecture, version `2.1.1`.
* **The userspace packages are pinned**, so a re-run over the same OpenWrt
  version produces the same asset names: `dae` 2.1.1 and `honk` 0.1.0_beta1 are
  fixed until the versions in the prepare job are bumped. The tag/release they
  are attached to is still the kernel based
  `openwrt-<version>-<kernel_version>-<date>`.
* **The `.apk` packages are signed** with the key that [`keys/public-key.pem`](keys/public-key.pem)
  publishes, and the runs refuse a package whose signature does not verify
  against it, so a device needs only that file in `/etc/apk/keys/` (see
  [Verifying the packages](#verifying-the-packages)). The signature covers the
  package, not the `.tar.xz` archive next to it: those are published with their
  `.sha256` checksum. `.ipk` assets (24.10 and older) are not signed per package
  because `opkg` has no such concept.
* **Time and cost.** Each of the five BTF jobs takes a few minutes, and each dae
  and honk job downloads the ~250 MB SDK plus its language toolchain. They all
  run in parallel, so on plans with a low limit of concurrent jobs the runs will
  queue — trim the target list to what you need.
* **A failing userspace build does not block the release** — the kernel assets
  are published anyway and the missing `dae`/`honk` assets are simply absent
  from that release. `vmlinux-btf` is built in the kernel job itself, so a
  packaging failure fails that architecture's job and the release is not
  published.

## Licensing

This repository contains the workflow, the three OpenWrt packages
(`vmlinux-btf/`, `dae/`, `honk/`), the vendored stubs under `src/` and this
README. The stubs are a verbatim copy of GPL-3.0-or-later code
from [QiuSimons/vmlinux-btf](https://github.com/QiuSimons/vmlinux-btf), and the
rest is derived from the projects below, so adding a `LICENSE` file (GPL-3.0) is
recommended and effectively required for redistribution.

The published artifacts redistribute third-party software, so the licenses of the
sources apply: the BTF describes an OpenWrt (GPL-2.0) kernel and declares
`GPL-2.0-only`, `dae` is **AGPL-3.0** and `honk` is GPL-3.0. The `dae` and
`honk` packages install the upstream license text, which is what GPL/AGPL
redistribution requires; keep that file with the package if you mirror it
elsewhere.
