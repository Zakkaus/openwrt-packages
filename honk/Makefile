#
# OpenWrt package: honk (https://github.com/daeuniverse/honk)
#
# The sources are expected next to this Makefile in ./src, which is what the
# GitHub workflow checks out:
#
#   git clone https://github.com/daeuniverse/honk src
#
# Nothing is downloaded while building. build.sh builds the eBPF object with the
# nightly toolchain pinned in crates/honk-ebpf/rust-toolchain.toml, compiles
# honk-core with the crate's own pinned stable toolchain, and uses the OpenWrt
# cross gcc/g++ of the SDK (TARGET_CROSS) for BoringSSL, SQLite and the final
# link. The version reported by the binary is HONK_VERSION (debug-<date>).
#
# This file is free software, licensed under the GNU General Public License v3
# or later.

# $(CURDIR) points at the buildroot root, and $(MAKEFILE_LIST) grows with every
# included file, so the package directory has to be resolved before the first
# include. abspath keeps it valid when a recipe runs from another directory.
PKG_DIR:=$(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))

include $(TOPDIR)/rules.mk

PKG_NAME:=honk
PKG_VERSION:=$(if $(HONK_VERSION),$(HONK_VERSION),debug)
PKG_RELEASE:=1

PKG_LICENSE:=GPL-3.0-only
PKG_LICENSE_FILES:=LICENSE
PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)-$(PKG_VERSION)

include $(INCLUDE_DIR)/package.mk

HONK_SRC:=$(PKG_DIR)/src

define Package/honk
  SECTION:=net
  CATEGORY:=Network
  SUBMENU:=Web Servers/Proxies
  TITLE:=eBPF transparent proxy engine (honk-core)
  URL:=https://github.com/daeuniverse/honk
  LICENSE:=GPL-3.0-only
  # honk-core is linked against the musl and the C++ runtime of OpenWrt
  DEPENDS:=+libstdcpp
endef

define Package/honk/description
 honk is an eBPF transparent proxy engine. honk-core embeds its eBPF object and
 needs kernel BTF for CO-RE relocations; install vmlinux-btf for that.
endef

define Build/Prepare
	@if [ ! -d "$(HONK_SRC)" ]; then \
		echo "honk: the source tree is missing at $(HONK_SRC)"; \
		echo "honk: run 'git clone https://github.com/daeuniverse/honk src' in $(PKG_DIR)"; \
		exit 1; \
	fi
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) $(HONK_SRC)/. $(PKG_BUILD_DIR)/
endef

define Build/Compile
	HONK_SRC="$(PKG_BUILD_DIR)" \
	HONK_VERSION="$(PKG_VERSION)" \
	HONK_ARCH_PACKAGES="$(ARCH_PACKAGES)" \
	OPENWRT_CC="$(TARGET_CROSS)gcc" \
	OPENWRT_CXX="$(TARGET_CROSS)g++" \
	sh "$(PKG_DIR)/build.sh"
endef

define Package/honk/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/honk-core $(1)/usr/bin/honk-core
	$(INSTALL_DIR) $(1)/usr/share/licenses/honk
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/LICENSE $(1)/usr/share/licenses/honk/LICENSE
endef

$(eval $(call BuildPackage,honk))
