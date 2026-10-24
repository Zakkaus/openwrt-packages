#
# OpenWrt package: vmlinux-btf (https://github.com/QiuSimons/vmlinux-btf)
#
# Unlike the other packages of this feed this one does not build anything: the
# detached BTF blob is produced by the workflow (src/shadow_btf_*.c compiled
# against the kernel headers of the SDK, then pahole) and handed in as a
# prebuilt file:
#
#   VMLINUX_BTF_SRC      path to the blob (the same "vmlinux" the archive holds)
#   VMLINUX_BTF_VERSION  package version, i.e. the kernel version (e.g. 6.12.94)
#   VMLINUX_BTF_KERNEL_RELEASE
#                        kernel release (UTS_RELEASE) of the SDK kernel tree,
#                        used for the vmlinux-<release> symlink; falls back to
#                        the kernel version
#
# The package installs exactly what libbpf and bpftool look for:
# /usr/lib/debug/boot/vmlinux plus the vmlinux-<kernel.release> symlink next to
# it, which is where upstream's package puts it as well.
#
# The built kernel version is also recorded in
# /usr/share/vmlinux-btf/version. The preinst script refuses to install the
# package when the running kernel belongs to a different generation
# (major.minor), and the postinst script adds the vmlinux-<running release>
# symlink for the kernel that is actually running.
#
# This file is free software, licensed under the GNU General Public License v3
# or later.

include $(TOPDIR)/rules.mk

PKG_NAME:=vmlinux-btf
PKG_VERSION:=$(if $(VMLINUX_BTF_VERSION),$(VMLINUX_BTF_VERSION),0.0.0)
PKG_RELEASE:=1

# The types come from the kernel sources, so the blob carries the kernel license
PKG_LICENSE:=GPL-2.0-only

PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)-$(PKG_VERSION)

include $(INCLUDE_DIR)/package.mk

VMLINUX_BTF_KERNEL_RELEASE:=$(if $(VMLINUX_BTF_KERNEL_RELEASE),$(VMLINUX_BTF_KERNEL_RELEASE),$(PKG_VERSION))

# The first two bytes of a BTF blob are the magic (0xeb9f, little endian).
# Evaluated while the Makefile is parsed, i.e. in the invocation that also has
# VMLINUX_BTF_SRC set. It stays empty when the package is only inspected
# (make defconfig), which is fine: only Build/Prepare looks at it.
VMLINUX_BTF_MAGIC:=$(if $(VMLINUX_BTF_SRC),$(shell od -An -tx1 -N2 "$(VMLINUX_BTF_SRC)" 2>/dev/null | tr -d ' \n'))

define Package/vmlinux-btf
  SECTION:=kernel
  CATEGORY:=Kernel
  TITLE:=Detached kernel BTF (vmlinux) for CO-RE eBPF programs
  URL:=https://github.com/QiuSimons/vmlinux-btf
  LICENSE:=GPL-2.0-only
  # Pure data, nothing is needed at runtime
  DEPENDS:=
endef

define Package/vmlinux-btf/description
 Detached BTF blob of this kernel, built from the kernel headers and the
 .config the OpenWrt SDK ships for the target. Install it to make CO-RE eBPF
 programs (dae, honk) work on a kernel whose image carries no BTF.
endef

define Build/Prepare
	@if [ ! -s "$(VMLINUX_BTF_SRC)" ]; then \
		echo "vmlinux-btf: the BTF blob is missing at '$(VMLINUX_BTF_SRC)'"; \
		echo "vmlinux-btf: run 'make package/vmlinux-btf/compile VMLINUX_BTF_SRC=<blob> VMLINUX_BTF_VERSION=<kernel version>'"; \
		exit 1; \
	fi
	@if [ "$(VMLINUX_BTF_MAGIC)" != "9feb" ]; then \
		echo "vmlinux-btf: $(VMLINUX_BTF_SRC) is not a BTF blob (magic '$(VMLINUX_BTF_MAGIC)')"; \
		exit 1; \
	fi
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) "$(VMLINUX_BTF_SRC)" $(PKG_BUILD_DIR)/vmlinux
endef

define Build/Compile
	@echo "vmlinux-btf: packaging $(PKG_BUILD_DIR)/vmlinux"
endef

define Package/vmlinux-btf/preinst
#!/bin/sh
# BTF is specific to one kernel generation: a blob built for another generation
# still loads, but CO-RE relocations resolve the wrong types at runtime. Refuse
# the installation instead of leaving a silently broken package behind.
#
# Package scripts run before the package files are unpacked, so
# /usr/share/vmlinux-btf/version still holds the previously installed version
# (or does not exist yet). Compare against the version baked in at build time,
# which is always the one being installed; the file is only a fallback.
#
# Offline installations into a root directory (ImageBuilder, staging roots) run
# on the build host, whose uname is not the target kernel: skip the check there.
[ -n "$$IPKG_INSTROOT" ] && exit 0

package_version="$(PKG_VERSION)"
if [ -z "$$package_version" ] || [ "$$package_version" = "0.0.0" ]; then
	package_version="$$(cat /usr/share/vmlinux-btf/version 2>/dev/null)"
fi

kernel_generation() {
	printf '%s\n' "$$1" | sed -n 's/^\([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p'
}

running_version="$$(uname -r)"
wanted="$$(kernel_generation "$$package_version")"
running="$$(kernel_generation "$$running_version")"

if [ -z "$$wanted" ] || [ -z "$$running" ]; then
	echo "vmlinux-btf: cannot compare kernel generations (package '$$package_version', running '$$running_version')" >&2
	exit 1
fi
if [ "$$wanted" != "$$running" ]; then
	echo "vmlinux-btf: this package is built for kernel $$package_version (generation $$wanted), but the running kernel is $$running_version (generation $$running)" >&2
	echo "vmlinux-btf: install the package built for $$running, or boot the matching kernel" >&2
	exit 1
fi
exit 0
endef

define Package/vmlinux-btf/postinst
#!/bin/sh
# libbpf and bpftool resolve the BTF of the running kernel through
# /usr/lib/debug/boot/vmlinux-<running release>. The package ships the link for
# the release it was built from, which can differ from the running release on
# the same kernel generation (a point release or a vendor suffix), so add the
# link for the kernel that is actually running.
#
# Only link within the same generation (major.minor): a link for another
# generation would hand libbpf incompatible BTF. preinst already refuses that
# case, so this is the belt-and-braces check.
#
# Same offline-installation caveat as in preinst: the build host's uname is not
# the target kernel.
[ -n "$$IPKG_INSTROOT" ] && exit 0

running="$$(uname -r)"
[ -n "$$running" ] || exit 0

package_version="$$(cat /usr/share/vmlinux-btf/version 2>/dev/null)"
if [ -n "$$package_version" ]; then
	wanted="$$(printf '%s' "$$package_version" | cut -d. -f1,2)"
	current="$$(printf '%s' "$$running" | cut -d. -f1,2)"
	if [ "$$wanted" != "$$current" ]; then
		echo "vmlinux-btf: not creating vmlinux-$$running: the package is for kernel generation $$wanted" >&2
		exit 0
	fi
fi

link="/usr/lib/debug/boot/vmlinux-$$running"
if [ ! -e "$$link" ] && [ ! -L "$$link" ]; then
	ln -s vmlinux "$$link" || exit 1
fi
exit 0
endef

define Package/vmlinux-btf/install
	$(INSTALL_DIR) $(1)/usr/lib/debug/boot
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/vmlinux $(1)/usr/lib/debug/boot/vmlinux
	$(LN) vmlinux $(1)/usr/lib/debug/boot/vmlinux-$(VMLINUX_BTF_KERNEL_RELEASE)
	$(INSTALL_DIR) $(1)/usr/share/vmlinux-btf
	printf '%s\n' "$(PKG_VERSION)" > $(1)/usr/share/vmlinux-btf/version
endef

$(eval $(call BuildPackage,vmlinux-btf))
