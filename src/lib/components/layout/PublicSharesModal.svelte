<script lang="ts">
	import type { Writable } from 'svelte/store';
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import { deletePublicShareByChatId, getPublicShareList } from '$lib/apis/public-shares';

	import ChatsModal from './ChatsModal.svelte';

	const i18n: Writable<any> = getContext('i18n');

	export let show = false;
	export let onUpdate = () => {};

	let chatList: any[] | null = null;
	let page = 1;
	let total = 0;

	let query = '';
	let orderBy = 'updated_at';
	let direction = 'desc';

	let allChatsLoaded = false;
	let chatListLoading = false;
	let searchDebounceTimeout: any;

	let filter: any = {};
	$: filter = {
		...(query ? { query } : {}),
		...(orderBy ? { order_by: orderBy } : {}),
		...(direction ? { direction } : {})
	};

	$: if (filter !== null) {
		searchHandler();
	}

	const applyResponse = (response, append = false) => {
		const items = response?.items ?? [];
		total = response?.total ?? items.length;
		chatList = append ? [...(chatList || []), ...items] : items;
		allChatsLoaded = (chatList?.length ?? 0) >= total || items.length === 0;
	};

	const loadPublicShares = async (_page = 1) => {
		return getPublicShareList(localStorage.token, _page, filter).catch((error) => {
			toast.error(`${error?.detail ?? error}`);
			return null;
		});
	};

	const searchHandler = async () => {
		if (!show) {
			return;
		}

		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		page = 1;
		chatList = null;

		const load = async () => {
			const response = await loadPublicShares(page);
			applyResponse(response);
		};

		if (query === '') {
			await load();
		} else {
			searchDebounceTimeout = setTimeout(load, 500);
		}
	};

	const loadMoreChats = async () => {
		chatListLoading = true;
		page += 1;

		const response = await loadPublicShares(page);
		applyResponse(response, true);

		chatListLoading = false;
	};

	const stopPublicShareHandler = async (chat: any) => {
		const res = await deletePublicShareByChatId(localStorage.token, chat.chat_id).catch((error) => {
			toast.error(`${error?.detail ?? error}`);
			return null;
		});

		if (res === true) {
			toast.success($i18n.t('Public link stopped successfully.'));
			onUpdate();
			init();
		} else if (res === false) {
			toast.error($i18n.t('Failed to stop public link.'));
		}
	};

	const init = async () => {
		page = 1;
		const response = await loadPublicShares(page);
		applyResponse(response);
	};

	const publicShareHref = (chat: any) => chat.url;
	const publicShareCopyHref = (chat: any) => chat.url;

	$: if (show) {
		init();
	}
</script>

<ChatsModal
	bind:show
	bind:query
	bind:orderBy
	bind:direction
	title={$i18n.t('Public Shares')}
	emptyPlaceholder={$i18n.t('You have no public shares.')}
	shareUrl={false}
	itemHref={publicShareHref}
	copyHref={publicShareCopyHref}
	copyTooltip={$i18n.t('Copy Public Link')}
	copySuccessMessage={$i18n.t('Public link copied to clipboard.')}
	unshareTooltip={$i18n.t('Stop Public Link')}
	{chatList}
	{allChatsLoaded}
	{chatListLoading}
	onUpdate={() => {
		onUpdate();
		init();
	}}
	loadHandler={loadMoreChats}
	unshareHandler={stopPublicShareHandler}
/>