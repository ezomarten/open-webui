import { WEBUI_API_BASE_URL } from '$lib/constants';

const normalizeError = async (res: Response) => {
	let error = null;

	const body = await res.json().catch(() => null);
	if (!res.ok) {
		error = body ?? { detail: res.statusText, status: res.status };
		throw error;
	}

	return body;
};

export const getPublicShareList = async (token: string, page: number = 1, filter?: object) => {
	let error = null;
	const searchParams = new URLSearchParams();
	searchParams.append('page', `${page}`);

	if (filter) {
		Object.entries(filter).forEach(([key, value]) => {
			if (value !== undefined && value !== null) {
				searchParams.append(key, value.toString());
			}
		});
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/public-shares/list?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(normalizeError)
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPublicShareByChatId = async (token: string, chatId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/public-shares/chats/${chatId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(normalizeError)
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const upsertPublicShareByChatId = async (token: string, chatId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/public-shares/chats/${chatId}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(normalizeError)
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deletePublicShareByChatId = async (token: string, chatId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/public-shares/chats/${chatId}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(normalizeError)
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPublicShareById = async (publicShareId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/public-shares/${publicShareId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		}
	})
		.then(normalizeError)
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};