<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownSub from '$lib/components/common/DropdownSub.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import Switch from '$lib/components/common/Switch.svelte'; // upstream v0.11.4 autoformat
	import Tooltip from '$lib/components/common/Tooltip.svelte'; // upstream v0.11.4 autoformat
	import Bold from '$lib/components/icons/Bold.svelte'; // upstream v0.11.4 autoformat
	import Download from '$lib/components/icons/Download.svelte';
	import DocumentArrowUp from '$lib/components/icons/DocumentArrowUp.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import CloudArrowUp from '$lib/components/icons/CloudArrowUp.svelte';
	import Pin from '$lib/components/icons/Pin.svelte';
	import PinSlash from '$lib/components/icons/PinSlash.svelte';

	const i18n = getContext<any>('i18n');

	type NoteImportMode = 'replace' | 'append-end' | 'insert-cursor';
	type NoteImportFormat = 'markdown' | 'plain-text';
	type NoteMenuAction = (() => void | Promise<void>) | null;

	export let show = false;
	export const className = 'max-w-[180px]';

	export let onDownload: (type: string) => void = (_type: string) => {};
	export let onDelete: () => void = () => {};
	export let onPin: NoteMenuAction = null;
	export let isPinned = false;

	export let onCopyLink: NoteMenuAction = null;
	export let onCopyToClipboard: NoteMenuAction = null;
	export let onAccess: NoteMenuAction = null;
	export let onUploadFiles: NoteMenuAction = null;
	export let showAutoFormat = false; // upstream v0.11.4 autoformat
	export let autoFormat = true;
	// fork:notes-md-import
	export let onImport: ((format: NoteImportFormat, mode: NoteImportMode) => void) | null = null;
	export let onPasteMarkdown: ((mode: NoteImportMode) => void) | null = null;
	export let onCopyMarkdown: NoteMenuAction = null;

	export let onChange: (state: boolean) => void = () => {};

	const handleAction = (action: NoteMenuAction) => {
		action?.();
		show = false;
	};
</script>

<Dropdown
	bind:show
	align="end"
	sideOffset={6}
	onOpenChange={(state) => {
		onChange(state);
	}}
>
	<slot />

	<div slot="content">
		<div
			class="w-[180px] max-w-[calc(100vw-32px)] text-sm rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
		>
			{#if showAutoFormat}
				<Tooltip
					className="w-full"
					content={$i18n.t(
						'Format Markdown as you type and paste. Turn off to keep Markdown characters and paste plain text. Existing formatting is preserved.'
					)}
				>
					<div
						class="select-none flex h-[1.6875rem] items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-50/60 dark:hover:bg-gray-800/60"
					>
						<Bold className="size-3.5 shrink-0" strokeWidth="2" />
						<span class="flex-1">{$i18n.t('Formatting')}</span>
						<Switch bind:state={autoFormat} ariaLabel={$i18n.t('Formatting')} />
					</div>
				</Tooltip>
				<hr />
			{/if}
			{#if onImport}
				<DropdownSub>
					<button
						slot="trigger"
						class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					>
						<DocumentArrowUp strokeWidth="2" />
						<div class="flex items-center">{$i18n.t('Import')}</div>
					</button>

					<DropdownSub>
						<button
							slot="trigger"
							class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
						>
							<div class="flex items-center line-clamp-1">{$i18n.t('Markdown')} (.md)</div>
						</button>

						<button
							class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							on:click={() => {
								handleAction(() => onImport('markdown', 'replace'));
							}}
						>
							<div class="flex items-center line-clamp-1">{$i18n.t('Replace current content')}</div>
						</button>

						<button
							class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							on:click={() => {
								handleAction(() => onImport('markdown', 'append-end'));
							}}
						>
							<div class="flex items-center line-clamp-1">{$i18n.t('Append to end')}</div>
						</button>

						<button
							class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							on:click={() => {
								handleAction(() => onImport('markdown', 'insert-cursor'));
							}}
						>
							<div class="flex items-center line-clamp-1">{$i18n.t('Insert at cursor')}</div>
						</button>
					</DropdownSub>

					<DropdownSub>
						<button
							slot="trigger"
							class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
						>
							<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.txt)')}</div>
						</button>

						<button
							class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							on:click={() => {
								handleAction(() => onImport('plain-text', 'replace'));
							}}
						>
							<div class="flex items-center line-clamp-1">{$i18n.t('Replace current content')}</div>
						</button>

						<button
							class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							on:click={() => {
								handleAction(() => onImport('plain-text', 'append-end'));
							}}
						>
							<div class="flex items-center line-clamp-1">{$i18n.t('Append to end')}</div>
						</button>

						<button
							class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							on:click={() => {
								handleAction(() => onImport('plain-text', 'insert-cursor'));
							}}
						>
							<div class="flex items-center line-clamp-1">{$i18n.t('Insert at cursor')}</div>
						</button>
					</DropdownSub>
				</DropdownSub>
			{/if}

			<DropdownSub>
				<button
					slot="trigger"
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
				>
					<Download strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Download')}</div>
				</button>

				<button
					class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					on:click={() => {
						onDownload('txt');
					}}
				>
					<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.txt)')}</div>
				</button>

				<button
					class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					on:click={() => {
						onDownload('md');
					}}
				>
					<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.md)')}</div>
				</button>

				<button
					class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					on:click={() => {
						onDownload('pdf');
					}}
				>
					<div class="flex items-center line-clamp-1">{$i18n.t('PDF document (.pdf)')}</div>
				</button>
			</DropdownSub>

			{#if onAccess}
				<button
					class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					on:click={() => {
						handleAction(onAccess);
					}}
				>
					<LockClosed strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Access')}</div>
				</button>
			{/if}

			{#if onUploadFiles}
				<button
					class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					on:click={() => {
						handleAction(onUploadFiles);
					}}
				>
					<CloudArrowUp strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Upload files')}</div>
				</button>
			{/if}

			{#if onCopyLink || onCopyToClipboard}
				<DropdownSub>
					<button
						slot="trigger"
						class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					>
						<Share strokeWidth="2" />
						<div class="flex items-center">{$i18n.t('Share')}</div>
					</button>

					{#if onCopyLink}
						<button
							class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							on:click={() => {
								onCopyLink();
							}}
						>
							<Link />
							<div class="flex items-center">{$i18n.t('Copy link')}</div>
						</button>
					{/if}

					{#if onCopyToClipboard}
						<button
							class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							on:click={() => {
								onCopyToClipboard();
							}}
						>
							<DocumentDuplicate strokeWidth="2" />
							<div class="flex items-center">{$i18n.t('Copy to clipboard')}</div>
						</button>
					{/if}
				</DropdownSub>
			{/if}

			{#if onPasteMarkdown || onCopyMarkdown}
				<DropdownSub>
					<button
						slot="trigger"
						class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					>
						<Clipboard strokeWidth="2" />
						<div class="flex items-center">{$i18n.t('Clipboard')}</div>
					</button>

					{#if onPasteMarkdown}
						<DropdownSub>
							<button
								slot="trigger"
								class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							>
								<div class="flex items-center line-clamp-1">{$i18n.t('Paste as Markdown')}</div>
							</button>

							<button
								class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
								on:click={() => {
									handleAction(() => onPasteMarkdown('replace'));
								}}
							>
								<div class="flex items-center line-clamp-1">
									{$i18n.t('Replace current content')}
								</div>
							</button>

							<button
								class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
								on:click={() => {
									handleAction(() => onPasteMarkdown('append-end'));
								}}
							>
								<div class="flex items-center line-clamp-1">{$i18n.t('Append to end')}</div>
							</button>

							<button
								class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
								on:click={() => {
									handleAction(() => onPasteMarkdown('insert-cursor'));
								}}
							>
								<div class="flex items-center line-clamp-1">{$i18n.t('Insert at cursor')}</div>
							</button>
						</DropdownSub>
					{/if}

					{#if onCopyMarkdown}
						<button
							class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
							on:click={() => {
								handleAction(onCopyMarkdown);
							}}
						>
							<DocumentDuplicate strokeWidth="2" />
							<div class="flex items-center">{$i18n.t('Copy as Markdown')}</div>
						</button>
					{/if}
				</DropdownSub>
			{/if}

			{#if onPin}
				<button
					class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
					on:click={() => {
						onPin();
						show = false;
					}}
				>
					{#if isPinned}
						<PinSlash />
						<div class="flex items-center">{$i18n.t('Unpin')}</div>
					{:else}
						<Pin />
						<div class="flex items-center">{$i18n.t('Pin to Sidebar')}</div>
					{/if}
				</button>
			{/if}

			<button
				class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
				on:click={() => {
					onDelete();
				}}
			>
				<GarbageBin />
				<div class="flex items-center">{$i18n.t('Delete')}</div>
			</button>
		</div>
	</div>
</Dropdown>
