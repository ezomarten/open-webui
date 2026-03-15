<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { page } from '$app/stores';

	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	import { chatId, settings, WEBUI_NAME } from '$lib/stores';
	import { createMessagesList } from '$lib/utils';
	import { setTextScale } from '$lib/utils/text-scale';
	import { getPublicShareById } from '$lib/apis/public-shares';

	import Messages from '$lib/components/chat/Messages.svelte';

	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	let loaded = false;
	let unavailable = false;

	let autoScroll = true;
	let processing = '';
	let selectedModels = [''];
	let updatedAt: number | null = null;

	let title = '';
	let messages: any[] = [];
	let history: { messages: Record<string, any>; currentId: string | null } = {
		messages: {},
		currentId: null
	};

	$: messages = createMessagesList(history, history.currentId);

	const toPublicShareFileUrl = (publicShareId: string, file: any) => {
		if (!file?.file_id) {
			return file?.url ?? '';
		}

		const pathname = `/api/v1/public-shares/${publicShareId}/files/${file.file_id}/content`;
		if (typeof window === 'undefined') {
			return pathname;
		}

		return new URL(pathname, window.location.origin).toString();
	};

	const toHistory = (publicShareId: string, items: any[]) => {
		const nextHistory = {
			messages: {},
			currentId: null
		} as { messages: Record<string, any>; currentId: string | null };

		for (let index = 0; index < items.length; index += 1) {
			const current = items[index];
			const previous = items[index - 1] ?? null;
			const next = items[index + 1] ?? null;
			const files = (Array.isArray(current.files) ? current.files : [])
				.map((file: any) => {
					const url = toPublicShareFileUrl(publicShareId, file);
					if (!url) {
						return null;
					}

					return {
						...file,
						type: file?.type ?? 'image',
						url
					};
				})
				.filter(Boolean);

			nextHistory.messages[current.id] = {
				id: current.id,
				role: current.role,
				content: current.content ?? '',
				model: current.model,
				timestamp: current.timestamp,
				done: true,
				parentId: previous?.id ?? null,
				childrenIds: next ? [next.id] : [],
				...(Array.isArray(current.sources) && current.sources.length > 0
					? { sources: current.sources }
					: {}),
				...(files.length > 0 ? { files } : {})
			};
		}

		nextHistory.currentId = items.at(-1)?.id ?? null;
		return nextHistory;
	};

	const loadPublicShare = async () => {
		let localStorageSettings: Record<string, any> = {};

		try {
			localStorageSettings = JSON.parse(localStorage.getItem('settings') ?? '{}');
		} catch (error) {
			console.error('Failed to parse settings from localStorage', error);
		}

		settings.set(localStorageSettings);
		setTextScale(localStorageSettings?.textScale ?? 1);

		const snapshot = await getPublicShareById($page.params.id).catch((error) => {
			console.error(error);
			return null;
		});

		if (!snapshot) {
			unavailable = true;
			return;
		}

		await chatId.set($page.params.id);
		title = snapshot.title;
		updatedAt = snapshot.updated_at ?? null;
		selectedModels = snapshot.models?.length ? snapshot.models : [''];
		history = toHistory(snapshot.id ?? $page.params.id, snapshot.messages ?? []);

		await tick();
		if (messages.length > 0 && messages.at(-1)?.id && messages.at(-1)?.id in history.messages) {
			history.messages[messages.at(-1)?.id].done = true;
		}
	};

	onMount(async () => {
		await loadPublicShare();
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{unavailable
			? `${$i18n.t('Public Share')} • ${$WEBUI_NAME}`
			: title
				? `${title.length > 30 ? `${title.slice(0, 30)}...` : title} • ${$WEBUI_NAME}`
				: `${$WEBUI_NAME}`}
	</title>
	<meta name="robots" content="noindex,nofollow,noarchive" />
</svelte:head>

{#if loaded}
	{#if unavailable}
		<div
			class="h-screen max-h-[100dvh] w-full flex flex-col text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900"
		>
			<div class="m-auto w-full max-w-xl px-6 text-center">
				<h1 class="text-2xl font-medium">{$i18n.t('This public share is unavailable')}</h1>
				<p class="mt-3 text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('It may have been removed or the link may be invalid.')}
				</p>
			</div>
		</div>
	{:else}
		<div
			class="h-screen max-h-[100dvh] w-full flex flex-col text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900"
		>
			<div class="flex flex-col flex-auto justify-center relative">
				<div class="flex flex-col w-full flex-auto overflow-auto h-0" id="messages-container">
					<div
						class="pt-5 px-2 w-full {($settings?.widescreenMode ?? null)
							? 'max-w-full'
							: 'max-w-5xl'} mx-auto"
					>
						<div class="px-3">
							<h1 class="text-2xl font-medium line-clamp-1 m-0">{title}</h1>

							<div class="flex flex-wrap gap-x-4 gap-y-1 text-sm justify-between items-center mt-1">
								<time
									class="text-gray-400"
									datetime={updatedAt ? new Date(updatedAt * 1000).toISOString() : undefined}
								>
									{updatedAt ? dayjs(updatedAt * 1000).format('LLL') : ''}
								</time>

								{#if selectedModels.length > 0 && selectedModels[0] !== ''}
									<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
										{selectedModels.join(', ')}
									</div>
								{/if}
							</div>
						</div>
					</div>

					<div class="h-full w-full flex flex-col py-2" role="main">
						<div class="w-full">
							<Messages
								className="h-full flex pt-4 pb-8 "
								user={null}
								chatId={$chatId}
								readOnly={true}
								{selectedModels}
								{processing}
								bind:history
								bind:messages
								bind:autoScroll
								bottomPadding={false}
								sendMessage={() => {}}
								continueResponse={() => {}}
								regenerateResponse={() => {}}
							/>
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}
{/if}
