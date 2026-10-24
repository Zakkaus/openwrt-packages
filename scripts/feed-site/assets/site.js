// Enhancements of the feed landing page; it works without them.
//   - copy buttons on the code blocks
//   - a light/dark switch next to the system setting
//   - the system and app choices are remembered
//   - the outline marks the section in view
'use strict';

(() => {
	const root = document.documentElement;
	root.classList.add('js');

	const load = key => { try { return localStorage.getItem(key); } catch (e) { return null; } };
	const save = (key, value) => { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } };

	const theme = load('feed-theme');
	if (theme === 'light' || theme === 'dark')
		root.dataset.theme = theme;

	document.addEventListener('DOMContentLoaded', () => {
		const toggle = document.querySelector('.theme-toggle');
		toggle?.addEventListener('click', () => {
			const dark = root.dataset.theme
				? root.dataset.theme === 'dark'
				: matchMedia('(prefers-color-scheme: dark)').matches;
			root.dataset.theme = dark ? 'light' : 'dark';
			save('feed-theme', root.dataset.theme);
		});

		// Close the language menu on a click elsewhere, like a native menu
		document.addEventListener('click', event => {
			for (const menu of document.querySelectorAll('details[open]'))
				if (!menu.contains(event.target))
					menu.open = false;
		});

		for (const button of document.querySelectorAll('.copy')) {
			button.addEventListener('click', () => {
				const text = button.closest('.code').querySelector('pre').innerText.replace(/\n$/, '');
				navigator.clipboard.writeText(text).then(() => {
					button.classList.add('done');
					button.setAttribute('aria-label', button.dataset.done);
					setTimeout(() => {
						button.classList.remove('done');
						button.setAttribute('aria-label', button.dataset.copy);
					}, 1500);
				});
			});
		}

		for (const name of [ 'os', 'app' ]) {
			const input = document.getElementById(`${name}-${load('feed-' + name)}`);
			if (input)
				input.checked = true;
			for (const radio of document.querySelectorAll(`input[name="${name}"]`))
				radio.addEventListener('change', () => save('feed-' + name, radio.value));
		}

		const links = new Map([ ...document.querySelectorAll('.outline a') ]
			.map(a => [ a.hash.slice(1), a ]));
		const observer = new IntersectionObserver(entries => {
			for (const entry of entries) {
				if (!entry.isIntersecting)
					continue;
				for (const a of links.values())
					a.removeAttribute('aria-current');
				links.get(entry.target.id)?.setAttribute('aria-current', 'true');
			}
		}, { rootMargin: '-72px 0px -70% 0px' });
		for (const id of links.keys()) {
			const section = document.getElementById(id);
			if (section)
				observer.observe(section);
		}
	});
})();
