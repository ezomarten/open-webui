// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

type ThemeValue = 'system' | 'oled-dark' | 'light';

type FocusedStyle = {
	backgroundColor: string;
	boxShadow: string;
};

const TRUSTED_HEADER_EMAIL = Cypress.env('trustedHeaderEmail') as string | undefined;

const waitForPaint = (win: Window) => {
	return new Cypress.Promise<void>((resolve) => {
		win.setTimeout(() => resolve(), 220);
	});
};

const installDarkSystemMatchMedia = (win: Window) => {
	Object.defineProperty(win, 'matchMedia', {
		configurable: true,
		writable: true,
		value: (query: string) => ({
			matches: query.includes('prefers-color-scheme') ? true : false,
			media: query,
			onchange: null,
			addListener: () => {},
			removeListener: () => {},
			addEventListener: () => {},
			removeEventListener: () => {},
			dispatchEvent: () => false
		})
	});
};

const visitApp = (path: string, themeValue?: ThemeValue, token?: string) => {
	cy.visit(path, {
		onBeforeLoad: (win) => {
			win.localStorage.setItem('locale', 'en-US');

			if (token) {
				win.localStorage.setItem('token', token);
			}

			if (themeValue === 'system') {
				installDarkSystemMatchMedia(win);
			}
		}
	});

	cy.document().then((doc) => {
		if (doc.getElementById('cypress-disable-motion')) {
			return;
		}

		const style = doc.createElement('style');
		style.id = 'cypress-disable-motion';
		style.textContent = `
			*, *::before, *::after {
				transition: none !important;
				animation: none !important;
				scroll-behavior: auto !important;
			}
		`;
		doc.head.appendChild(style);
	});
};

const signInWithTrustedHeader = () => {
	expect(
		TRUSTED_HEADER_EMAIL,
		'Set Cypress env trustedHeaderEmail to an admin email when auth_trusted_header is enabled'
	).to.be.a('string');

	return cy
		.request({
			method: 'POST',
			url: '/api/v1/auths/signin',
			headers: {
				'Cf-Access-Authenticated-User-Email': TRUSTED_HEADER_EMAIL as string
			},
			body: {
				email: '',
				password: ''
			}
		})
		.then(({ body }) => {
			expect(body?.role).to.eq('admin');
			return body.token as string;
		});
};

const dismissChangelogIfNeeded = () => {
	cy.get('body').then(($body) => {
		if ($body.text().includes("Okay, Let's Go!")) {
			cy.contains('button', "Okay, Let's Go!").click({ force: true });
		}
	});
};

const getUserProfileMenuTrigger = () => {
	return cy
		.get('img[aria-label="Open User Profile Menu"]', { timeout: 15000 })
		.filter(':visible')
		.first();
};

const openAuthenticatedHome = (themeValue: ThemeValue) => {
	cy.request('/api/config').then(({ body }) => {
		if (body?.features?.auth_trusted_header) {
			signInWithTrustedHeader().then((token) => {
				visitApp('/', themeValue, token);
			});
		} else {
			cy.loginAdmin();
			visitApp('/', themeValue);
		}

		getUserProfileMenuTrigger().should('be.visible');
		dismissChangelogIfNeeded();
	});
};

const returnToAuthenticatedHome = (themeValue: ThemeValue) => {
	visitApp('/', themeValue);
	getUserProfileMenuTrigger().should('be.visible');
	dismissChangelogIfNeeded();
};

const openSettingsGeneral = () => {
	getUserProfileMenuTrigger().click({ force: true });
	cy.contains('button', 'Settings', { timeout: 10000 }).click();
	cy.get('button[aria-label="Close settings modal"]', { timeout: 10000 }).should('be.visible');
	cy.contains('button', 'General').click();
	cy.get('#tab-general').should('be.visible');
};

const openAdminSettingsGeneral = () => {
	getUserProfileMenuTrigger().click({ force: true });
	cy.contains('a', 'Admin Panel', { timeout: 10000 }).click();
	cy.location('pathname', { timeout: 15000 }).should('include', '/admin');
	cy.get('a[href="/admin/settings"]', { timeout: 10000 }).click();
	cy.location('pathname', { timeout: 15000 }).should('include', '/admin/settings');
	cy.get('a[href="/admin/settings/general"]', { timeout: 10000 }).click();
	cy.location('pathname', { timeout: 15000 }).should('include', '/admin/settings/general');
	cy.contains('.ow-settings-row', 'LDAP', { timeout: 15000 }).should('be.visible');
};

const applyThemeFromSettings = (themeValue: ThemeValue) => {
	cy.get('#tab-general select').first().select(themeValue, { force: true });
	cy.wait(150);
};

const parseRgbChannels = (color: string) => {
	const matches = color.match(/\d+(?:\.\d+)?/g) ?? [];
	return matches.slice(0, 3).map((value) => Number(value));
};

const getColorBrightness = (color: string) => {
	return parseRgbChannels(color).reduce((sum, channel) => sum + channel, 0);
};

const normalizeColor = (doc: Document, color: string) => {
	const probe = doc.createElement('div');
	probe.style.color = color;
	probe.style.position = 'fixed';
	probe.style.left = '-9999px';
	probe.style.top = '0';
	doc.body.appendChild(probe);

	const normalizedColor = getComputedStyle(probe).color;
	probe.remove();

	return normalizedColor;
};

const resolveBackgroundColor = (target: HTMLElement, backgroundColor: string) => {
	const doc = target.ownerDocument;
	const host = target.parentElement ?? doc.body;
	const probe = doc.createElement('div');
	probe.style.position = 'fixed';
	probe.style.left = '-9999px';
	probe.style.top = '0';
	probe.style.backgroundColor = backgroundColor;
	host.appendChild(probe);

	const resolvedBackgroundColor = getComputedStyle(probe).backgroundColor;
	probe.remove();

	return resolvedBackgroundColor;
};

const resolveBoxShadow = (target: HTMLElement, boxShadow: string) => {
	const doc = target.ownerDocument;
	const host = target.parentElement ?? doc.body;
	const probe = doc.createElement('div');
	probe.style.position = 'fixed';
	probe.style.left = '-9999px';
	probe.style.top = '0';
	probe.style.boxShadow = boxShadow;
	host.appendChild(probe);

	const resolvedBoxShadow = getComputedStyle(probe).boxShadow;
	probe.remove();

	return resolvedBoxShadow;
};

const getExpectedFocusStyle = (target: HTMLElement): FocusedStyle => {
	const doc = target.ownerDocument;
	const computedStyle = getComputedStyle(target);
	const isDark = doc.documentElement.classList.contains('dark');
	const backgroundVariable = isDark
		? '--ow-settings-focus-bg-dark'
		: '--ow-settings-focus-bg-light';
	const shadowVariable = isDark
		? '--ow-settings-focus-shadow-dark'
		: '--ow-settings-focus-shadow-light';
	const backgroundValue = computedStyle.getPropertyValue(backgroundVariable).trim();
	const shadowValue = computedStyle.getPropertyValue(shadowVariable).trim();

	return {
		backgroundColor: resolveBackgroundColor(target, backgroundValue),
		boxShadow: resolveBoxShadow(target, shadowValue)
	};
};

const getExpectedFocusStyleForSurface = (surfaceClassName = '') => {
	return cy.document().then((doc) => {
		const wrapper = doc.createElement('div');
		wrapper.className = surfaceClassName;
		wrapper.style.position = 'fixed';
		wrapper.style.left = '-9999px';
		wrapper.style.top = '0';
		doc.body.appendChild(wrapper);

		const result = getExpectedFocusStyle(wrapper);
		wrapper.remove();

		return result;
	});
};

const getFocusableElement = (container: HTMLElement) => {
	return container.querySelector(
		'select, button, [role="switch"], input, textarea'
	) as HTMLElement | null;
};

const waitForNextPaint = () => {
	return cy.window().then((win) => waitForPaint(win));
};

const assertSettingsRowMatchesProbe = (label: string, surfaceClassName = '') => {
	cy.contains('.ow-settings-row', label).then(($row) => {
		const row = $row[0] as HTMLElement;
		const focusableElement = getFocusableElement(row);
		const doc = row.ownerDocument;
		const isDark = doc.documentElement.classList.contains('dark');
		const beforeBackgroundColor = normalizeColor(doc, getComputedStyle(row).backgroundColor);

		expect(focusableElement, `${label} focus target`).to.not.eq(null);
		focusableElement?.focus();

		waitForNextPaint().then(() => {
			const style = getComputedStyle(row);
			const expectedStyle = getExpectedFocusStyle(row);
			const focusedBackgroundColor = normalizeColor(doc, style.backgroundColor);
			expect(row.matches(':focus-within')).to.eq(true);
			expect(focusedBackgroundColor).to.not.eq(beforeBackgroundColor);

			if (!isDark) {
				expect(focusedBackgroundColor).to.eq(expectedStyle.backgroundColor);
			}

			expect(style.boxShadow).to.eq(expectedStyle.boxShadow);
		});
	});
};

const openChatControls = () => {
	cy.get('button[aria-label="Controls"]').click();
	cy.contains('button', 'Advanced Params', { timeout: 10000 }).should('be.visible');
};

const assertControlHeaderMatchesProbe = (label: string) => {
	cy.contains('button', label).then(($header) => {
		const header = $header[0] as HTMLButtonElement;
		const doc = header.ownerDocument;
		const isDark = doc.documentElement.classList.contains('dark');
		const beforeBackgroundColor = normalizeColor(doc, getComputedStyle(header).backgroundColor);
		header.focus();

		waitForNextPaint().then(() => {
			const style = getComputedStyle(header);
			const expectedStyle = getExpectedFocusStyle(header);
			const focusedBackgroundColor = normalizeColor(doc, style.backgroundColor);
			expect(header.matches(':focus-visible')).to.eq(true);
			expect(focusedBackgroundColor).to.not.eq(beforeBackgroundColor);

			if (!isDark) {
				expect(focusedBackgroundColor).to.eq(expectedStyle.backgroundColor);
			}

			expect(style.boxShadow).to.eq(expectedStyle.boxShadow);
		});
	});
};

const assertModalLightProbeIsStrongerThanAdmin = () => {
	getExpectedFocusStyleForSurface('ow-settings-surface-modal').then((modalStyle) => {
		getExpectedFocusStyleForSurface('ow-settings-surface-admin').then((adminStyle) => {
			expect(getColorBrightness(modalStyle.backgroundColor)).to.be.lessThan(
				getColorBrightness(adminStyle.backgroundColor)
			);
		});
	});
};

const verifyThemeScenario = (themeValue: ThemeValue) => {
	openSettingsGeneral();

	applyThemeFromSettings(themeValue);
	assertSettingsRowMatchesProbe('Notifications', 'ow-settings-surface-modal');
	assertSettingsRowMatchesProbe('Advanced Parameters', 'ow-settings-surface-modal');

	if (themeValue === 'light') {
		assertModalLightProbeIsStrongerThanAdmin();
	}

	returnToAuthenticatedHome(themeValue);
	openChatControls();
	assertControlHeaderMatchesProbe('Advanced Params');

	openAdminSettingsGeneral();
	assertSettingsRowMatchesProbe('LDAP', 'ow-settings-surface-admin');
};

describe('Theme Hover Consistency', () => {
	const requestedTheme = Cypress.env('theme') as 'system' | 'oled-dark' | 'light' | undefined;
	const themes: ThemeValue[] = requestedTheme ? [requestedTheme] : ['system', 'oled-dark', 'light'];

	themes.forEach((themeValue) => {
		beforeEach(() => {
			openAuthenticatedHome(themeValue);
		});

		it(`matches the surface-aware emphasis in settings and controls for ${themeValue}`, () => {
			verifyThemeScenario(themeValue);
		});
	});
});
