<script lang="ts">
	import { getContext } from 'svelte';
	import { models, config, user } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import {
		deleteSharedChatById,
		getChatById,
		shareChatById,
		getChatAccessGrants,
		updateChatAccessGrants
	} from '$lib/apis/chats';
	import {
		deletePublicShareByChatId,
		getPublicShareByChatId,
		upsertPublicShareByChatId
	} from '$lib/apis/public-shares';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';

	export let chatId;
	export let show = false;

	let chat = null;
	let shareUrl = null;
	let publicShare = null;
	let publicShareUrl = null;
	let publicShareLoading = false;
	let accessGrants: any[] = [];
	const i18n = getContext('i18n');
	const publicShareErrorMessage = (error) => $i18n.t(error?.detail ?? `${error}`);

	const shareLocalChat = async () => {
		const sharedChat = await shareChatById(localStorage.token, chatId);
		shareUrl = `${window.location.origin}/s/${sharedChat.share_id ?? sharedChat.id}`;
		chat = await getChatById(localStorage.token, chatId);

		return shareUrl;
	};

	const shareChat = async () => {
		const _chat = chat.chat;

		toast.success($i18n.t('Redirecting you to Open WebUI Community'));
		const url = 'https://openwebui.com';

		const tab = await window.open(`${url}/chats/upload`, '_blank');
		window.addEventListener(
			'message',
			(event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(
						JSON.stringify({
							chat: _chat,
							models: $models.filter((m) => _chat.models.includes(m.id))
						}),
						'*'
					);
				}
			},
			false
		);
	};

	const loadPublicShare = async () => {
		if (!$config?.features?.enable_public_chat_sharing || !chatId) {
			publicShare = null;
			publicShareUrl = null;
			return;
		}

		publicShare = await getPublicShareByChatId(localStorage.token, chatId).catch(() => null);
		publicShareUrl = publicShare?.url ?? null;
	};

	const syncPublicShare = async () => {
		publicShareLoading = true;

		const syncedPublicShare = await upsertPublicShareByChatId(localStorage.token, chatId).catch(
			(error) => {
				toast.error(publicShareErrorMessage(error));
				return null;
			}
		);

		publicShareLoading = false;

		if (syncedPublicShare) {
			publicShare = syncedPublicShare;
			publicShareUrl = syncedPublicShare.url;
			chat = await getChatById(localStorage.token, chatId);
		}

		return syncedPublicShare;
	};

	const copyPublicShare = async () => {
		if (!publicShare || publicShare.is_stale) {
			const syncedPublicShare = await syncPublicShare();
			if (!syncedPublicShare) {
				return;
			}

			copyToClipboard(syncedPublicShare.url);
			toast.success($i18n.t('Copied public link to clipboard!'));
			return;
		}

		copyToClipboard(publicShare.url);
		toast.success($i18n.t('Copied public link to clipboard!'));
	};

	const stopPublicShare = async () => {
		const res = await deletePublicShareByChatId(localStorage.token, chatId).catch((error) => {
			toast.error(publicShareErrorMessage(error));
			return null;
		});

		if (res) {
			publicShare = null;
			publicShareUrl = null;
			toast.success($i18n.t('Public link stopped.'));
		}
	};

	const loadAccessGrants = async () => {
		if (!chatId) {
			accessGrants = [];
			return;
		}

		try {
			accessGrants = (await getChatAccessGrants(localStorage.token, chatId)) ?? [];
		} catch (e) {
			console.error('Failed to load access grants', e);
			accessGrants = [];
		}
	};

	const saveAccessGrants = async () => {
		try {
			await updateChatAccessGrants(localStorage.token, chatId, accessGrants);
			toast.success($i18n.t('Access updated'));
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const isDifferentChat = (_chat) => {
		if (!chat) {
			return true;
		}
		if (!_chat) {
			return false;
		}
		return chat.id !== _chat.id || chat.share_id !== _chat.share_id;
	};

	$: if (show) {
		(async () => {
			if (chatId) {
				const _chat = await getChatById(localStorage.token, chatId);
				if (isDifferentChat(_chat)) {
					chat = _chat;
				}

				await loadPublicShare();
				await loadAccessGrants();
			} else {
				chat = null;
				publicShare = null;
				publicShareUrl = null;
				accessGrants = [];
			}
		})();
	}
</script>

<Modal bind:show size="md">
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-0.5">
			<div class="text-lg font-medium self-center">{$i18n.t('Share Chat')}</div>
			<button
				class="self-center"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		{#if chat}
			<div class="px-5 pt-4 pb-5 w-full flex flex-col">
				<div class="text-sm dark:text-gray-300 mb-1">
					{#if chat.share_id}
						<a href="/s/{chat.share_id}" target="_blank"
							>{$i18n.t('You have shared this chat')}
							<span class="underline">{$i18n.t('before')}</span>.</a
						>
						{$i18n.t('Click here to')}
						<button
							class="underline"
							on:click={async () => {
								const res = await deleteSharedChatById(localStorage.token, chatId);

								if (res) {
									chat = await getChatById(localStorage.token, chatId);
								}
							}}
						>
							{$i18n.t('delete this link')}
						</button>
						{$i18n.t('and create a new shared link.')}
					{:else}
						{$i18n.t(
							"Messages you send after creating your link won't be shared. Users with the URL will be able to view the shared chat."
						)}
					{/if}
				</div>

				{#if chat.share_id}
					<div class="mt-3">
						<AccessControl
							bind:accessGrants
							accessRoles={['read']}
							sharePublic={$user?.permissions?.sharing?.public_chats || $user?.role === 'admin'}
							shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) ||
								$user?.role === 'admin'}
							onChange={saveAccessGrants}
						/>
					</div>
				{/if}

				<div class="flex justify-end">
					<div class="flex flex-col items-end space-x-1 mt-3">
						<div class="flex gap-1 flex-wrap justify-end">
							{#if $config?.features.enable_community_sharing}
								<button
									class="self-center flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-800 transition rounded-full"
									type="button"
									on:click={() => {
										shareChat();
										show = false;
									}}
								>
									{$i18n.t('Share to Open WebUI Community')}
								</button>
							{/if}

							<button
								class="self-center flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
								type="button"
								id="copy-and-share-chat-button"
								on:click={async () => {
									const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

									if (isSafari) {
										const getUrlPromise = async () => {
											const url = await shareLocalChat();
											return new Blob([url], { type: 'text/plain' });
										};

										navigator.clipboard
											.write([
												new ClipboardItem({
													'text/plain': getUrlPromise()
												})
											])
											.catch((error) => {
												console.error('Async: Could not copy text: ', error);
											});
									} else {
										copyToClipboard(await shareLocalChat());
									}

									toast.success($i18n.t('Copied shared chat URL to clipboard!'));
									show = false;
								}}
							>
								<Link />

								{#if chat.share_id}
									{$i18n.t('Update and Copy Link')}
								{:else}
									{$i18n.t('Copy Link')}
								{/if}
							</button>
						</div>
					</div>
				</div>

				{#if $config?.features?.enable_public_chat_sharing}
					<div class="mt-5 pt-4 border-t border-gray-100 dark:border-gray-850">
						<div class="text-sm font-medium dark:text-gray-200">{$i18n.t('Public Link')}</div>
						<div class="text-sm dark:text-gray-300 mt-1">
							{$i18n.t(
								'Creates an anonymous read-only public page. Image attachments and public web citations are included. Other files and private citations are omitted.'
							)}
						</div>

						{#if publicShare?.is_stale}
							<div class="text-xs text-amber-600 dark:text-amber-400 mt-2">
								{$i18n.t('This public snapshot is older than the current chat.')}
							</div>
						{/if}

						<div class="flex justify-end mt-3">
							<div class="flex flex-wrap gap-1 justify-end">
								{#if publicShareUrl}
									<a
										href={publicShareUrl}
										target="_blank"
										class="self-center flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-800 transition rounded-full"
									>
										{$i18n.t('Open Public Page')}
									</a>
								{/if}

								<button
									class="self-center flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full disabled:opacity-60"
									type="button"
									disabled={publicShareLoading}
									on:click={async () => {
										if (!publicShare) {
											const syncedPublicShare = await syncPublicShare();
											if (syncedPublicShare) {
												copyToClipboard(syncedPublicShare.url);
												toast.success($i18n.t('Copied public link to clipboard!'));
											}
											return;
										}

										await copyPublicShare();
									}}
								>
									<Link />

									{#if !publicShare}
										{$i18n.t('Create Public Link')}
									{:else if publicShare.is_stale}
										{$i18n.t('Update and Copy Public Link')}
									{:else}
										{$i18n.t('Copy Public Link')}
									{/if}
								</button>

								{#if publicShare}
									<button
										class="self-center flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-800 transition rounded-full"
										type="button"
										on:click={stopPublicShare}
									>
										{$i18n.t('Stop Public Link')}
									</button>
								{/if}
							</div>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</Modal>
