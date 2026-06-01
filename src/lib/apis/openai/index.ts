import { OPENAI_API_BASE_URL, WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

export const getOpenAIConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type OpenAIConfig = {
	ENABLE_OPENAI_API: boolean;
	OPENAI_API_BASE_URLS: string[];
	OPENAI_API_KEYS: string[];
	OPENAI_API_CONFIGS: object;
};

export const updateOpenAIConfig = async (token: string = '', config: OpenAIConfig) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			...config
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// fork:openrouter-zdr — OpenRouter ZDR helpers
const isOpenRouterUrl = (url: string) => {
	try {
		return new URL(url).hostname.endsWith('openrouter.ai');
	} catch {
		return url.toLowerCase().includes('openrouter.ai');
	}
};

const isOpenRouterZdrEnabled = (url: string, config: object = {}) => {
	return isOpenRouterUrl(url) && !!(config as any)?.openrouter_zdr_only;
};

const getOpenAIModelsListUrl = (url: string, config: object = {}) => {
	return isOpenRouterZdrEnabled(url, config) ? `${url}/endpoints/zdr` : `${url}/models`;
};

const normalizeOpenRouterZdrModelsResponse = (response: any) => {
	const endpointData = Array.isArray(response?.data) ? response.data : [];
	const modelsById: Record<string, any> = {};

	for (const endpoint of endpointData) {
		if (!endpoint || typeof endpoint !== 'object') {
			continue;
		}

		const modelId = endpoint.model_id;
		if (!modelId) {
			continue;
		}

		const model =
			modelsById[modelId] ??
			(modelsById[modelId] = {
				id: modelId,
				name: endpoint.model_name ?? endpoint.name ?? modelId,
				owned_by: 'openai',
				openai: { id: modelId },
				providers: [] as string[],
				provider_tags: [] as string[],
				zdr_only: true
			});

		if (endpoint.provider_name && !model.providers.includes(endpoint.provider_name)) {
			model.providers.push(endpoint.provider_name);
		}

		if (endpoint.tag && !model.provider_tags.includes(endpoint.tag)) {
			model.provider_tags.push(endpoint.tag);
		}

		if (!model.context_length && endpoint.context_length) {
			model.context_length = endpoint.context_length;
		}
	}

	return {
		object: 'list',
		data: Object.values(modelsById)
	};
};

const normalizeOpenAIModelsResponse = (url: string, config: object = {}, response: any) => {
	if (!response) {
		return response;
	}

	return isOpenRouterZdrEnabled(url, config)
		? normalizeOpenRouterZdrModelsResponse(response)
		: response;
};

const applyOpenRouterZdrPreferences = (url: string, config: object = {}, body: object = {}) => {
	if (!isOpenRouterZdrEnabled(url, config) || typeof body !== 'object' || body === null) {
		return body;
	}

	const provider = (body as any)?.provider;

	return {
		...body,
		provider: {
			...(provider && typeof provider === 'object' && !Array.isArray(provider) ? provider : {}),
			zdr: true
		}
	};
};

export const getOpenAIModelsDirect = async (url: string, key: string, config: object = {}) => {  // fork:openrouter-zdr
	let error = null;

	const res = await fetch(getOpenAIModelsListUrl(url, config), {  // fork:openrouter-zdr
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(key && { authorization: `Bearer ${key}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return normalizeOpenAIModelsResponse(url, config, res);  // fork:openrouter-zdr
};

export const getOpenAIModels = async (token: string, urlIdx?: number) => {
	let error = null;

	const res = await fetch(
		`${OPENAI_API_BASE_URL}/models${typeof urlIdx === 'number' ? `/${urlIdx}` : ''}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const verifyOpenAIConnection = async (
	token: string = '',
	connection: dict = {},
	direct: boolean = false
) => {
	const { url, key, config } = connection;
	if (!url) {
		throw 'OpenAI: URL is required';
	}

	let error = null;
	let res = null;

	if (direct) {
		// fork:openrouter-zdr — use getOpenAIModelsDirect which handles ZDR model list URL
		res = await getOpenAIModelsDirect(url, key, config).catch((err) => {
			error = err;
			return [];
		});

		if (error) {
			throw error;
		}
	} else {
		res = await fetch(`${OPENAI_API_BASE_URL}/verify`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				url,
				key,
				config
			})
		})
			.then(async (res) => {
				if (!res.ok) throw await res.json();
				return res.json();
			})
			.catch((err) => {
				error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
				return [];
			});

		if (error) {
			throw error;
		}
	}

	return res;
};

export const chatCompletion = async (
	token: string = '',
	body: object,
	url: string = `${WEBUI_BASE_URL}/api`,
	config: object = {}  // fork:openrouter-zdr
): Promise<[Response | null, AbortController]> => {
	const controller = new AbortController();
	let error = null;
	const payload = applyOpenRouterZdrPreferences(url, config, body);  // fork:openrouter-zdr

	const res = await fetch(`${url}/chat/completions`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			...(token && { Authorization: `Bearer ${token}` }),
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(payload)  // fork:openrouter-zdr
	}).catch((err) => {
		console.error(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return [res, controller];
};

export const generateOpenAIChatCompletion = async (
	token: string = '',
	body: object,
	url: string = `${WEBUI_BASE_URL}/api`
) => {
	let error = null;

	const res = await fetch(`${url}/chat/completions`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		credentials: 'include',
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const synthesizeOpenAISpeech = async (
	token: string = '',
	speaker: string = 'alloy',
	text: string = '',
	model: string = 'tts-1'
) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/audio/speech`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			model: model,
			input: text,
			voice: speaker
		})
	}).catch((err) => {
		console.error(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};
