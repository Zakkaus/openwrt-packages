#!/usr/bin/env python3
"""Write the landing page of the package feed.

Usage: generate.py <site-dir> <base-url> < index-paths

stdin lists the packages.adb files the feed serves, one path per line,
relative to the feed root, so the page covers everything on the mirror and not
only what one run built:
  <series>/packages/<arch>/packages.adb                       e.g. 25.12
  <series>/kmods/<release>/<target>/<subtarget>/packages.adb  e.g. 25.12.6
It writes <lang>/index.html in English, Simplified and Traditional Chinese and copies
assets/ next to them. Only the standard library is used.
"""

import datetime
import html
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GITHUB = 'https://github.com/daeuniverse/openwrt-packages'
SOURCE = GITHUB + '/blob/main/scripts/feed-site/generate.py'
DOCS = {'dae': 'https://github.com/daeuniverse/dae/tree/main/docs', 'honk': 'https://github.com/daeuniverse/honk'}

LANGS = [
	# directory, html lang, name in the language menu
	('en', 'en', 'English'),
	('zh-cn', 'zh-CN', '简体中文'),
	('zh-tw', 'zh-TW', '繁體中文'),
]

# The mirror is hosted by gentoo-zh; the thanks link to its page in the same language
GENTOOZH = {'en': 'https://gentoozh.org/en/', 'zh-cn': 'https://gentoozh.org/', 'zh-tw': 'https://gentoozh.org/zh-tw/'}

# Translated text, as HTML. {app}, {conf} and {docs} follow the chosen service.
TEXT = {
	'en': {
		'title': 'OpenWrt package feed',
		'subtitle': 'apk packages of dae, honk and their LuCI apps for OpenWrt 25.12 and later.',
		'nav_guide': 'Guide',
		'nav_files': 'Files',
		'language': 'Language',
		'theme': 'Light or dark',
		'outline': 'On this page',
		'copy': 'Copy',
		'copied': 'Copied',
		'system': 'System',
		'service': 'Service',
		'install': 'Install',
		'key': 'Import the signing key',
		'repos': 'Add the repositories',
		'repos_note': 'With the <code>@daeuniverse</code> tag, a package the system also has is only taken from this feed when it is named with the tag, so system packages of the same name stay in place.',
		'add': 'Install the packages',
		'add_note': 'Without LuCI, leave out the <code>luci-</code> packages.',
		'start': 'Enable the service',
		'start_note': 'In LuCI under <kbd>Services</kbd> → <kbd>{app}</kbd>, or from the shell:',
		'config_note': 'Configuration: <code>{conf}</code>, syntax in the {docs}.',
		'docs': 'documentation',
		'versions': 'Supported versions',
		'th_series': 'Version',
		'th_status': 'Status',
		'version_rows': [
			('25.12', 'Supported on OpenWrt and ImmortalWrt.'),
			('24.10', 'Not supported. It installs packages with opkg, which has no tags, so this feed would replace packages of the same name; ImmortalWrt 24.10 ships its own dae.'),
			('23.05 and older', 'Not supported. The kernel is older than 5.17, the minimum dae needs.'),
		],
		'builds_note': 'Official OpenWrt kernels have no BTF, so dae and honk need <code>vmlinux-btf</code>, which is built for the targets and releases below only; official OpenWrt on other targets is not supported.',
		'no_arches': '32-bit ARM and MIPS have no packages and are not supported on OpenWrt or ImmortalWrt.',
		'check': 'Check the release and target of the router:',
		'th_target': 'Target',
		'th_releases': 'Releases',
		'arches': 'Architectures of the {series} packages (ImmortalWrt needs only these to match): ',
		'no_builds': 'Nothing has been published yet.',
		'errors': 'Common errors',
		'th_error': 'Message',
		'th_cause': 'Cause',
		'error_items': [
			('UNTRUSTED signature', 'The signing key is not imported.'),
			('vmlinux-btf (no such package)', 'No vmlinux-btf for this release and target, or the kmods repository is missing.'),
			('vmlinux-btf breaks: kernel', 'The firmware runs a self-built or snapshot kernel, not the release kernel.'),
		],
		'edit': 'Edit this page',
		'updated': 'Updated {date}',
		'all_files': 'All files',
		'source': 'Source',
		'thanks': 'Mirror hosted by <a href="{gentoozh}">gentoo-zh</a>',
	},
	'zh-cn': {
		'title': 'OpenWrt 软件源',
		'subtitle': 'dae、honk 及其 LuCI 界面的 apk 软件包，适用于 OpenWrt 25.12 及以上版本。',
		'nav_guide': '说明',
		'nav_files': '文件',
		'language': '语言',
		'theme': '浅色或深色',
		'outline': '本页目录',
		'copy': '复制',
		'copied': '已复制',
		'system': '系统',
		'service': '服务',
		'install': '安装',
		'key': '导入签名公钥',
		'repos': '添加软件源',
		'repos_note': '<code>@daeuniverse</code>标签使系统也有的软件包只在带标签指名时才从本源安装，不会取代系统的同名软件包。',
		'add': '安装软件包',
		'add_note': '不使用 LuCI 时，省略<code>luci-</code>开头的软件包。',
		'start': '启用服务',
		'start_note': '在 LuCI 的<kbd>服务</kbd> → <kbd>{app}</kbd> 中启用，或在命令行执行：',
		'config_note': '配置文件：<code>{conf}</code>，语法见 {docs}。',
		'docs': '文档',
		'versions': '支持的版本',
		'th_series': '版本',
		'th_status': '状态',
		'version_rows': [
			('25.12', '支持 OpenWrt 和 ImmortalWrt。'),
			('24.10', '不支持。它用 opkg 安装软件包，opkg 没有标签，本源会取代同名软件包；ImmortalWrt 24.10 已自带 dae。'),
			('23.05 及更早', '不支持。内核低于 dae 要求的 5.17。'),
		],
		'builds_note': '官方 OpenWrt 内核不含 BTF，dae 和 honk 需要<code>vmlinux-btf</code>，它只为下表的 target 和版本提供；其他 target 的官方 OpenWrt 不支持。',
		'no_arches': '32 位 ARM 和 MIPS 没有软件包，OpenWrt 和 ImmortalWrt 都不支持。',
		'check': '查询路由器的版本和 target：',
		'th_target': 'Target',
		'th_releases': '版本',
		'arches': '{series} 软件包的架构（ImmortalWrt 只需架构相符）：',
		'no_builds': '尚未发布。',
		'errors': '常见错误',
		'th_error': '错误信息',
		'th_cause': '原因',
		'error_items': [
			('UNTRUSTED signature', '未导入签名公钥。'),
			('vmlinux-btf (no such package)', '此版本或 target 没有 vmlinux-btf，或缺少 kmods 软件源。'),
			('vmlinux-btf breaks: kernel', '固件使用自编译或快照版内核，不是正式版内核。'),
		],
		'edit': '编辑此页',
		'updated': '更新于 {date}',
		'all_files': '全部文件',
		'source': '源代码',
		'thanks': '镜像服务器由 <a href="{gentoozh}">gentoo-zh</a> 提供',
	},
	'zh-tw': {
		'title': 'OpenWrt 軟體源',
		'subtitle': 'dae、honk 及其 LuCI 介面的 apk 套件，適用於 OpenWrt 25.12 以上版本。',
		'nav_guide': '說明',
		'nav_files': '檔案',
		'language': '語言',
		'theme': '淺色或深色',
		'outline': '本頁目錄',
		'copy': '複製',
		'copied': '已複製',
		'system': '系統',
		'service': '服務',
		'install': '安裝',
		'key': '匯入簽章公鑰',
		'repos': '加入軟體源',
		'repos_note': '<code>@daeuniverse</code>標籤使系統也有的套件只在帶標籤指名時才從本源安裝，不會取代系統的同名套件。',
		'add': '安裝套件',
		'add_note': '不使用 LuCI 時，省略<code>luci-</code>開頭的套件。',
		'start': '啟用服務',
		'start_note': '在 LuCI 的<kbd>服務</kbd> → <kbd>{app}</kbd> 中啟用，或在命令列執行：',
		'config_note': '設定檔：<code>{conf}</code>，語法見 {docs}。',
		'docs': '文件',
		'versions': '支援的版本',
		'th_series': '版本',
		'th_status': '狀態',
		'version_rows': [
			('25.12', '支援 OpenWrt 和 ImmortalWrt。'),
			('24.10', '不支援。它用 opkg 安裝套件，opkg 沒有標籤，本源會取代同名套件；ImmortalWrt 24.10 已內建 dae。'),
			('23.05 及更早', '不支援。核心低於 dae 要求的 5.17。'),
		],
		'builds_note': '官方 OpenWrt 核心不含 BTF，dae 和 honk 需要<code>vmlinux-btf</code>，它只為下表的 target 和版本提供；其他 target 的官方 OpenWrt 不支援。',
		'no_arches': '32 位 ARM 和 MIPS 沒有套件，OpenWrt 和 ImmortalWrt 都不支援。',
		'check': '查詢路由器的版本和 target：',
		'th_target': 'Target',
		'th_releases': '版本',
		'arches': '{series} 套件的架構（ImmortalWrt 只需架構相符）：',
		'no_builds': '尚未發布。',
		'errors': '常見錯誤',
		'th_error': '錯誤訊息',
		'th_cause': '原因',
		'error_items': [
			('UNTRUSTED signature', '未匯入簽章公鑰。'),
			('vmlinux-btf (no such package)', '此版本或 target 沒有 vmlinux-btf，或缺少 kmods 軟體源。'),
			('vmlinux-btf breaks: kernel', '韌體使用自行編譯或快照版核心，不是正式版核心。'),
		],
		'edit': '編輯此頁',
		'updated': '更新於 {date}',
		'all_files': '全部檔案',
		'source': '原始碼',
		'thanks': '鏡像伺服器由 <a href="{gentoozh}">gentoo-zh</a> 提供',
	},
}

# Lucide icons (ISC license), drawn with the stroke style of style.css
ICONS = {
	'copy': '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
	'check': '<path d="M20 6 9 17l-5-5"/>',
	'languages': '<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/>',
	'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
	'moon': '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
	'pen': '<path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z"/>',
	'github': '<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/>',
}

# Chinese text puts a space between a character and inline code, none next to
# punctuation; the strings are written without it and spaced here.
CJK_CODE = re.compile(r'(?<=[\u4e00-\u9fff])(?=<code>)|(?<=</code>)(?=[\u4e00-\u9fff])')

INDEX = re.compile(r'^(\d+\.\d+)/(?:packages/([^/]+)|kmods/(\d+\.\d+\.\d+)/([^/]+/[^/]+))/packages\.adb$')
esc = html.escape


def icon(name, cls=''):
	return f'<svg class="icon {cls}" viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


def version_key(version):
	return tuple(int(part) for part in version.split('.'))


def read_builds(lines):
	"""{series: {'packages': {arch}, 'kmods': {release: {target/subtarget}}}}, newest first."""
	builds = {}
	for line in lines:
		m = INDEX.match(line.strip().removeprefix('./'))
		if not m:
			continue
		entry = builds.setdefault(m[1], {'packages': set(), 'kmods': {}})
		if m[2]:
			entry['packages'].add(m[2])
		else:
			entry['kmods'].setdefault(m[3], set()).add(m[4])
	return dict(sorted(builds.items(), key=lambda kv: version_key(kv[0]), reverse=True))


SH_TOKEN = re.compile(r'(\$\{[^}]*\}|\$\w+)|("[^"]*"|\'[^\']*\')|(<<-?\'?\w+\'?|[|&;>\\])')


def highlight_sh(text):
	"""Shell colouring as Shiki's github themes do it: commands, variables,
	strings, operators; the lines of a here-document are data."""
	out, heredoc, continued = [], None, False
	for line in text.split('\n'):
		if heredoc:
			cls = 'o' if line == heredoc else 's'
			heredoc = None if line == heredoc else heredoc
			out.append(f'<span class="tok-{cls}">{esc(line)}</span>')
			continue
		if line.lstrip().startswith('#'):
			out.append(f'<span class="tok-c">{esc(line)}</span>')
			continue
		html_line, command = '', not continued
		continued = line.endswith('\\')
		for m in re.finditer(r'\S+|\s+', line):
			word = m[0]
			if word.isspace():
				html_line += word
				continue
			if command and not word.startswith(('$', '"', "'")) and '=' not in word:
				html_line += f'<span class="tok-f">{esc(word)}</span>'
				command = False
				continue
			command = command and '=' in word
			last = 0
			for t in SH_TOKEN.finditer(word):
				if t.start() > last:
					html_line += f'<span class="tok-s">{esc(word[last:t.start()])}</span>'
				cls = 'v' if t[1] else 's' if t[2] else 'o'
				html_line += f'<span class="tok-{cls}">{esc(t[0])}</span>'
				if t[3] and t[3].startswith('<<'):
					heredoc = t[3].lstrip('<-').strip("'")
				if t[3] in ('|', '&', ';'):
					command = True
				last = t.end()
			if last < len(word):
				html_line += f'<span class="tok-s">{esc(word[last:])}</span>'
		out.append(html_line)
	return '\n'.join(out)


def code(text, T, attrs=''):
	return (f'<div class="code"{attrs}><div class="code-title"><span>sh</span>'
	        f'<button class="button square copy" type="button" aria-label="{T["copy"]}" '
	        f'data-copy="{T["copy"]}" data-done="{T["copied"]}">'
	        f'{icon("copy", "icon-copy")}{icon("check", "icon-done")}</button></div>'
	        f'<pre><code>{highlight_sh(text)}</code></pre></div>')


def variants(key, **values):
	"""One inline span per variant; CSS shows the one that is chosen."""
	return ''.join(f'<span data-{key}="{v}">{text}</span>' for v, text in values.items())


def tabs(name, legend, options):
	"""A radio group drawn as tabs; style.css hides the variants not chosen."""
	radios = ''.join(
		f'<input type="radio" name="{name}" id="{name}-{value}" value="{value}"' + (' checked' if i == 0 else '') + '>'
		f'<label for="{name}-{value}">{label}</label>'
		for i, (value, label) in enumerate(options))
	return f'<fieldset class="choice"><legend>{legend}</legend><div class="tabs">{radios}</div></fieldset>'


def render(lang, html_lang, t, builds, base):
	fill = {
		'gentoozh': GENTOOZH[lang],
		'date': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d'),
		'app': variants('app', dae='dae', honk='honk'),
		'conf': variants('app', dae='/etc/dae/config.dae', honk='/etc/honk/config.dae'),
		'docs': variants('app', **{app: f'<a href="{url}">{app} {t["docs"]}</a>' for app, url in DOCS.items()}),
		'series': '{series}',  # filled per series below
	}
	T = {k: v.format(**fill) if isinstance(v, str) else v for k, v in t.items()}
	if lang.startswith('zh'):
		T = {k: CJK_CODE.sub(' ', v) if isinstance(v, str) else v for k, v in T.items()}

	# The packages are shared by a release series (25.12), vmlinux-btf belongs
	# to one release (25.12.6) and target
	repo = lambda kmods: (
		'. /etc/openwrt_release\n'
		f'FEED={base}/${{DISTRIB_RELEASE%.*}}\n'
		'cat > /etc/apk/repositories.d/daeuniverse.list <<EOF\n'
		'@daeuniverse $FEED/packages/$DISTRIB_ARCH/packages.adb\n'
		+ ('@daeuniverse $FEED/kmods/$DISTRIB_RELEASE/$DISTRIB_TARGET/packages.adb\n' if kmods else '')
		+ 'EOF\n'
		'apk update')
	i18n = {'zh-cn': ' \\\n    luci-i18n-daeuniverse-zh-cn@daeuniverse', 'zh-tw': ' \\\n    luci-i18n-daeuniverse-zh-tw@daeuniverse'}.get(lang, '')
	per_app = lambda make: ''.join(code(make(app), T, f' data-app="{app}"') for app in DOCS)
	per_os_app = lambda make: ''.join(code(make(os, app), T, f' data-os="{os}" data-app="{app}"')
	                                  for os in ('openwrt', 'immortalwrt') for app in DOCS)
	# A dependency the system also has comes from the system unless it is
	# named with the tag, so the service is named as well: ImmortalWrt has a
	# dae of its own, which would be picked otherwise.
	# Official OpenWrt needs the BTF of vmlinux-btf; dae would pull it in
	# through kmod-xdp-sockets-diag, honk would not, so it is named for both.
	btf = {'openwrt': ' vmlinux-btf@daeuniverse', 'immortalwrt': ''}

	if builds:
		# One row per target with the releases that have vmlinux-btf for it,
		# then the architectures of each series, which is all ImmortalWrt needs
		releases = {}
		for series, entry in builds.items():
			for release, targets in entry['kmods'].items():
				for target in targets:
					releases.setdefault(target, []).append((series, release))
		link = lambda path, text: f'<a href="../{esc(path)}/">{esc(text)}</a>'
		rows = ''.join(
			f'<tr><td class="mono">{esc(target)}</td><td class="mono">'
			+ ' '.join(link(f'{s}/kmods/{r}/{target}', r) for s, r in sorted(found, key=lambda sr: version_key(sr[1]), reverse=True))
			+ '</td></tr>'
			for target, found in sorted(releases.items()))
		table = (f'<div class="table"><table><thead><tr><th>{T["th_target"]}</th><th>{T["th_releases"]}</th></tr></thead>'
		         f'<tbody>{rows}</tbody></table></div>' if rows else '')
		table += ''.join(
			f'<p>{T["arches"].format(series=esc(series))}<span class="mono">'
			+ ' '.join(link(f'{series}/packages/{arch}', arch) for arch in sorted(entry['packages']))
			+ '</span></p>'
			for series, entry in builds.items() if entry['packages'])
	else:
		table = f'<p>{T["no_builds"]}</p>'

	errors = ''.join(f'<tr><td class="mono">{esc(e)}</td><td>{c}</td></tr>' for e, c in T['error_items'])
	versions = ''.join(f'<tr><td>{esc(v)}</td><td>{status}</td></tr>' for v, status in T['version_rows'])
	sections = [('versions', T['versions']), ('install', T['install']), ('errors', T['errors'])]
	h2 = {key: f'<h2 id="{key}">{title}<a class="anchor" href="#{key}" aria-hidden="true">#</a></h2>' for key, title in sections}
	outline = ''.join(f'<li><a href="#{key}">{title}</a></li>' for key, title in sections)
	languages = ''.join(
		f'<li><a href="../{d}/" hreflang="{h}" lang="{h}"' + (' aria-current="true"' if d == lang else '') + f'>{esc(n)}</a></li>'
		for d, h, n in LANGS)
	alternates = '\n'.join(f'<link rel="alternate" hreflang="{h}" href="{base}/{d}/">' for d, h, _ in LANGS)

	return f'''<!doctype html>
<html lang="{html_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{T["title"]} · daeuniverse</title>
<meta name="description" content="{T["subtitle"]}">
<link rel="icon" href="../assets/daeuniverse.png">
<link rel="stylesheet" href="../assets/style.css">
<script src="../assets/site.js"></script>
{alternates}
</head>
<body>
<header class="topbar">
<a class="brand" href="./"><img src="../assets/daeuniverse.png" alt="" width="28" height="28">daeuniverse</a>
<nav class="topbar-nav"><a class="button" href="./" aria-current="page">{T["nav_guide"]}</a><a class="button" href="../files/">{T["nav_files"]}</a></nav>
<div class="topbar-actions">
<details class="lang"><summary class="button square" aria-label="{T["language"]}" title="{T["language"]}">{icon("languages")}</summary><ul>{languages}</ul></details>
<button class="button square theme-toggle" type="button" aria-label="{T["theme"]}" title="{T["theme"]}">{icon("moon", "icon-dark")}{icon("sun", "icon-light")}</button>
<a class="button square" href="{GITHUB}" aria-label="GitHub" title="GitHub">{icon("github")}</a>
</div>
</header>
<div class="page">
<main class="article">
<h1>{T["title"]}</h1>
<p class="subtitle">{T["subtitle"]}</p>

{h2["versions"]}
<div class="table"><table class="stack"><thead><tr><th>{T["th_series"]}</th><th>{T["th_status"]}</th></tr></thead><tbody>{versions}</tbody></table></div>
<p>{T["check"]}</p>
{code(". /etc/openwrt_release\necho $DISTRIB_RELEASE $DISTRIB_ARCH $DISTRIB_TARGET", T)}
<p>{T["builds_note"]}</p>
{table}
<p>{T["no_arches"]}</p>

{h2["install"]}
<div class="choices">
{tabs("os", T["system"], [("openwrt", "OpenWrt"), ("immortalwrt", "ImmortalWrt")])}
{tabs("app", T["service"], [("dae", "dae"), ("honk", "honk")])}
</div>
<ol class="steps">
<li><h3>{T["key"]}</h3>
{code(f"wget -O /etc/apk/keys/daeuniverse.pem \\\n    {base}/public-key.pem", T)}</li>
<li><h3>{T["repos"]}</h3>
{code(repo(True), T, ' data-os="openwrt"')}
{code(repo(False), T, ' data-os="immortalwrt"')}
<p>{T["repos_note"]}</p>
</li>
<li><h3>{T["add"]}</h3>
{per_os_app(lambda os, app: f"apk add {app}@daeuniverse luci-app-{app}@daeuniverse{btf[os]}{i18n}")}
<p>{T["add_note"]}</p></li>
<li><h3>{T["start"]}</h3>
<p>{T["start_note"]}</p>
{per_app(lambda app: f"uci set {app}.config.enabled=1\nuci commit {app}\n/etc/init.d/{app} enable\n/etc/init.d/{app} start")}
<p>{T["config_note"]}</p></li>
</ol>

{h2["errors"]}
<div class="table"><table class="stack"><thead><tr><th>{T["th_error"]}</th><th>{T["th_cause"]}</th></tr></thead><tbody>{errors}</tbody></table></div>

<p class="edit"><a class="button" href="{SOURCE}">{icon("pen")}{T["edit"]}</a></p>
</main>
<nav class="outline" aria-label="{T["outline"]}"><ul>{outline}</ul></nav>
</div>
<footer class="footer">
<span>{T["updated"]}</span>
<span>{T["thanks"]}</span>
<nav><a href="../files/">{T["all_files"]}</a><a href="../public-key.pem">public-key.pem</a><a href="{GITHUB}">{T["source"]}</a></nav>
</footer>
</body>
</html>
'''


def main():
	site, base = Path(sys.argv[1]), sys.argv[2].rstrip('/')
	builds = read_builds(sys.stdin)
	for lang, html_lang, _ in LANGS:
		(site / lang).mkdir(parents=True, exist_ok=True)
		(site / lang / 'index.html').write_text(render(lang, html_lang, TEXT[lang], builds, base), encoding='utf-8')
	shutil.copytree(HERE / 'assets', site / 'assets', dirs_exist_ok=True)


if __name__ == '__main__':
	main()
