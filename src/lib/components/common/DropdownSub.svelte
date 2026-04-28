<script lang="ts">
	import { flyAndScale } from '$lib/utils/transitions';
	import { tick } from 'svelte';

	/** CSS classes for the sub-content container */
	export let contentClass =
		'select-none rounded-2xl p-1 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg border border-gray-100 dark:border-gray-800';

	/** Max width in px, enforced at the component level */
	export let maxWidth = 200;

	/** Side offset from the trigger in px (visual gap, bridged by invisible padding) */
	export let sideOffset = 8;
	const viewportPadding = 16;

	const dropdownSubId = `dropdown-sub-${Math.random().toString(36).slice(2)}`;

	let open = false;
	let triggerEl: HTMLDivElement;
	let contentEl: HTMLDivElement;
	let submenuChain = dropdownSubId;

	function updateSubmenuChain() {
		const parentChain =
			triggerEl
				?.closest('[data-dropdown-sub-content-id]')
				?.getAttribute('data-dropdown-sub-chain') ?? '';

		submenuChain = parentChain ? `${parentChain},${dropdownSubId}` : dropdownSubId;
	}

	function isMovingWithinSubmenuTree(target: EventTarget | null) {
		const element = target instanceof Element ? target : null;

		if (!element) {
			return false;
		}

		if (triggerEl?.contains(element) || contentEl?.contains(element)) {
			return true;
		}

		const targetChain = element
			.closest('[data-dropdown-sub-chain]')
			?.getAttribute('data-dropdown-sub-chain');

		return targetChain ? targetChain.split(',').includes(dropdownSubId) : false;
	}

	function positionContent() {
		if (!triggerEl || !contentEl) return;
		const rect = triggerEl.getBoundingClientRect();
		updateSubmenuChain();

		contentEl.style.position = 'fixed';
		contentEl.style.zIndex = '99999';

		// Reset bridge padding
		contentEl.style.paddingLeft = '0';
		contentEl.style.paddingRight = '0';

		// Inherit min-width from parent dropdown container (apply to inner content)
		const innerContent = contentEl.firstElementChild as HTMLElement | null;
		const parentContainer = triggerEl.closest('[class*="rounded"]')?.parentElement;
		const maxViewportWidth = Math.max(0, window.innerWidth - viewportPadding * 2);
		if (parentContainer && innerContent) {
			const parentWidth = parentContainer.offsetWidth;
			if (parentWidth > 0) {
				innerContent.style.minWidth = `${Math.min(parentWidth, maxWidth, maxViewportWidth)}px`;
			}
		}

		if (innerContent) {
			innerContent.style.maxWidth = `${Math.min(maxWidth, maxViewportWidth)}px`;
		}

		// Measure the inner content width for positioning decisions
		const contentWidth = Math.min(innerContent?.offsetWidth || 200, maxViewportWidth);
		const rightSpace = window.innerWidth - rect.right - viewportPadding;
		const leftSpace = rect.left - viewportPadding;
		const maxLeft = Math.max(viewportPadding, window.innerWidth - contentWidth - viewportPadding);

		const setHorizontalPosition = (
			desiredLeft: number,
			direction: 'left' | 'right',
			bridgeGap: boolean
		) => {
			const clampedLeft = Math.min(Math.max(desiredLeft, viewportPadding), maxLeft);

			contentEl.style.left = `${clampedLeft}px`;
			contentEl.style.right = 'auto';

			if (bridgeGap) {
				if (direction === 'right') {
					contentEl.style.paddingLeft = `${sideOffset}px`;
				} else {
					contentEl.style.paddingRight = `${sideOffset}px`;
				}
			}
		};

		if (rightSpace >= contentWidth + sideOffset) {
			setHorizontalPosition(rect.right, 'right', true);
		} else if (leftSpace >= contentWidth + sideOffset) {
			setHorizontalPosition(rect.left - contentWidth - sideOffset, 'left', true);
		} else if (rightSpace >= leftSpace) {
			setHorizontalPosition(Math.min(rect.right, maxLeft), 'right', false);
		} else {
			setHorizontalPosition(Math.max(viewportPadding, rect.left - contentWidth), 'left', false);
		}

		// Vertical positioning with robust bounds clamping (shift method)
		const contentHeight = contentEl.offsetHeight || 0;
		let top = rect.top;

		// If it overflows the bottom edge
		if (top + contentHeight + 16 > window.innerHeight) {
			top = window.innerHeight - contentHeight - 16;
		}

		// If shifting it up causes it to overflow the top edge, cap it at 16px
		if (top < 16) {
			top = 16;
		}

		contentEl.style.top = `${top}px`;
	}

	async function handleMouseEnter() {
		open = true;
		await tick();
		updateSubmenuChain();
		positionContent();
		// Re-position after transition starts rendering real dimensions
		setTimeout(positionContent, 50);
	}

	function handleMouseLeave(event: MouseEvent) {
		// Don't close if moving to the sub-content (including its bridge padding)
		if (isMovingWithinSubmenuTree(event.relatedTarget)) return;
		open = false;
	}

	function handleContentMouseLeave(event: MouseEvent) {
		if (isMovingWithinSubmenuTree(event.relatedTarget)) return;
		open = false;
	}

	function portal(node: HTMLElement) {
		document.body.appendChild(node);
		return {
			destroy() {
				if (node.parentNode) {
					node.parentNode.removeChild(node);
				}
			}
		};
	}
</script>

<svelte:window on:scroll|capture={positionContent} on:resize={positionContent} />

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
	bind:this={triggerEl}
	class="w-full"
	data-dropdown-sub-trigger-id={dropdownSubId}
	on:mouseenter={handleMouseEnter}
	on:mouseleave={handleMouseLeave}
>
	<slot name="trigger" />
</div>

{#if open}
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<!-- Outer wrapper: positioned flush with trigger, invisible padding bridges the gap -->
	<div
		use:portal
		bind:this={contentEl}
		data-dropdown-sub-content-id={dropdownSubId}
		data-dropdown-sub-chain={submenuChain}
		on:mouseleave={handleContentMouseLeave}
	>
		<!-- Inner content: visual styles and transition -->
		<div class={contentClass} style="max-width: {maxWidth}px;" transition:flyAndScale>
			<slot />
		</div>
	</div>
{/if}
