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

define Package/vmlinux-btf/install
	$(INSTALL_DIR) $(1)/usr/lib/debug/boot
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/vmlinux $(1)/usr/lib/debug/boot/vmlinux
	$(LN) vmlinux $(1)/usr/lib/debug/boot/vmlinux-$(VMLINUX_BTF_KERNEL_RELEASE)
endef

$(eval $(call BuildPackage,vmlinux-btf))
