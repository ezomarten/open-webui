import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { toast } from 'svelte-sonner';

import { createNewNote } from '$lib/apis/notes';

const MARKDOWN_FILE_EXTENSION_REGEX = /\.(md|markdown|mdown|mkd|mkdn)$/i;
const MARKDOWN_MIME_TYPES = new Set(['text/markdown', 'text/x-markdown']);
const PLAIN_TEXT_FILE_EXTENSION_REGEX = /\.txt$/i;
const PLAIN_TEXT_MIME_TYPES = new Set(['text/plain']);

const noteMarkdownRenderer = new marked.Renderer() as any;

noteMarkdownRenderer.list = (body, ordered, start) => {
	const isTaskList = body.includes('data-checked=');

	if (isTaskList) {
		return `<ul data-type="taskList">${body}</ul>`;
	}

	const type = ordered ? 'ol' : 'ul';
	const startatt = ordered && start !== 1 ? ` start="${start}"` : '';
	return `<${type}${startatt}>${body}</${type}>`;
};

noteMarkdownRenderer.listitem = (text, task, checked) => {
	if (task) {
		const checkedAttr = checked ? 'true' : 'false';
		return `<li data-type="taskItem" data-checked="${checkedAttr}">${text}</li>`;
	}

	return `<li>${text}</li>`;
};

// fork:notes-md-import
export const isMarkdownFile = (file: File) => {
	const mimeType = (file.type ?? '').toLowerCase();
	return MARKDOWN_MIME_TYPES.has(mimeType) || MARKDOWN_FILE_EXTENSION_REGEX.test(file.name);
};

export const isPlainTextFile = (file: File) => {
	const mimeType = (file.type ?? '').toLowerCase();
	return PLAIN_TEXT_MIME_TYPES.has(mimeType) || PLAIN_TEXT_FILE_EXTENSION_REGEX.test(file.name);
};

export const getMarkdownTitleFromFileName = (fileName: string) => {
	if (!fileName) {
		return '';
	}

	return fileName.replace(MARKDOWN_FILE_EXTENSION_REGEX, '');
};

export const getPlainTextTitleFromFileName = (fileName: string) => {
	if (!fileName) {
		return '';
	}

	return fileName.replace(PLAIN_TEXT_FILE_EXTENSION_REGEX, '');
};

export const readTextFile = (file: File) =>
	new Promise<string>((resolve, reject) => {
		const reader = new FileReader();

		reader.onload = (event) => {
			const content = event.target?.result;

			if (typeof content !== 'string') {
				reject(new Error('Invalid file content'));
				return;
			}

			resolve(content);
		};

		reader.onerror = () => {
			reject(new Error('Failed to read file'));
		};

		reader.readAsText(file);
	});

export const parseMarkdownToNoteHtml = (markdown: string) => {
	return marked.parse(markdown ?? '', {
		async: false,
		breaks: true,
		gfm: true,
		renderer: noteMarkdownRenderer
	}) as string;
};

const escapeHtml = (text: string) =>
	text
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#39;');

const preservePlainTextSpacing = (text: string) =>
	escapeHtml(text)
		.replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;')
		.replace(/ {2,}/g, (match) => '&nbsp;'.repeat(match.length - 1) + ' ');

export const parsePlainTextToNoteHtml = (text: string) => {
	const normalizedText = (text ?? '').replace(/\r\n/g, '\n');

	if (!normalizedText) {
		return '';
	}

	return normalizedText
		.split('\n')
		.map((line) => (line === '' ? '<p></p>' : `<p>${preservePlainTextSpacing(line)}</p>`))
		.join('');
};

export const createNoteContentFromMarkdown = (markdown: string) => ({
	json: null,
	html: parseMarkdownToNoteHtml(markdown),
	md: markdown
});

export const createNoteContentFromPlainText = (text: string) => ({
	json: null,
	html: parsePlainTextToNoteHtml(text),
	md: text
});

// fork:notes-md-import
export const readMarkdownFile = async (file: File) => {
	if (!isMarkdownFile(file)) {
		throw new Error('Only markdown files are allowed');
	}

	const markdown = await readTextFile(file);

	return {
		title: getMarkdownTitleFromFileName(file.name),
		markdown,
		content: createNoteContentFromMarkdown(markdown)
	};
};

// fork:notes-md-import
export const readPlainTextFile = async (file: File) => {
	if (!isPlainTextFile(file)) {
		throw new Error('Only plain text files are allowed');
	}

	const text = await readTextFile(file);

	return {
		title: getPlainTextTitleFromFileName(file.name),
		text,
		content: createNoteContentFromPlainText(text)
	};
};

export const downloadPdf = async (note) => {
	const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
		import('jspdf'),
		import('html2canvas-pro')
	]);

	// Define a fixed virtual screen size
	const virtualWidth = 1024; // Fixed width (adjust as needed)
	const virtualHeight = 1400; // Fixed height (adjust as needed)

	// STEP 1. Get a DOM node to render
	const html = DOMPurify.sanitize(note.data?.content?.html ?? '');
	const isDarkMode = document.documentElement.classList.contains('dark');

	let node;
	if (html instanceof HTMLElement) {
		node = html;
	} else {
		const virtualWidth = 800; // px, fixed width for cloned element

		// Clone and style
		node = document.createElement('div');

		// title node
		const titleNode = document.createElement('div');
		titleNode.textContent = note.title;
		titleNode.style.fontSize = '24px';
		titleNode.style.fontWeight = 'medium';
		titleNode.style.paddingBottom = '20px';
		titleNode.style.color = isDarkMode ? 'white' : 'black';
		node.appendChild(titleNode);

		const contentNode = document.createElement('div');

		contentNode.innerHTML = html;

		node.appendChild(contentNode);

		node.classList.add('text-black');
		node.classList.add('dark:text-white');
		node.style.width = `${virtualWidth}px`;
		node.style.position = 'absolute';
		node.style.left = '-9999px';
		node.style.height = 'auto';
		node.style.padding = '40px 40px';

		console.log(node);
		document.body.appendChild(node);
	}

	// Render to canvas with predefined width
	const canvas = await html2canvas(node, {
		useCORS: true,
		backgroundColor: isDarkMode ? '#000' : '#fff',
		scale: 2, // Keep at 1x to avoid unexpected enlargements
		width: virtualWidth, // Set fixed virtual screen width
		windowWidth: virtualWidth, // Ensure consistent rendering
		windowHeight: virtualHeight
	});

	// Remove hidden node if needed
	if (!(html instanceof HTMLElement)) {
		document.body.removeChild(node);
	}

	const imgData = canvas.toDataURL('image/jpeg', 0.7);

	// A4 page settings
	const pdf = new jsPDF('p', 'mm', 'a4');
	const imgWidth = 210; // A4 width in mm
	const pageWidthMM = 210; // A4 width in mm
	const pageHeight = 297; // A4 height in mm
	const pageHeightMM = 297; // A4 height in mm

	if (isDarkMode) {
		pdf.setFillColor(0, 0, 0);
		pdf.rect(0, 0, pageWidthMM, pageHeightMM, 'F'); // black bg
	}

	// Maintain aspect ratio
	const imgHeight = (canvas.height * imgWidth) / canvas.width;
	let heightLeft = imgHeight;
	let position = 0;

	pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
	heightLeft -= pageHeight;

	// Handle additional pages
	while (heightLeft > 0) {
		position -= pageHeight;
		pdf.addPage();

		if (isDarkMode) {
			pdf.setFillColor(0, 0, 0);
			pdf.rect(0, 0, pageWidthMM, pageHeightMM, 'F'); // black bg
		}

		pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
		heightLeft -= pageHeight;
	}

	pdf.save(`${note.title}.pdf`);
};

export const createNoteHandler = async (title: string, md?: string, html?: string) => {
	//  $i18n.t('New Note'),
	const markdownContent = md ?? '';
	const htmlContent = html ?? (markdownContent ? parseMarkdownToNoteHtml(markdownContent) : '');

	const res = await createNewNote(localStorage.token, {
		// YYYY-MM-DD
		title: title,
		data: {
			content: {
				json: null,
				html: htmlContent,
				md: markdownContent
			}
		},
		meta: null,
		access_grants: []
	}).catch((error) => {
		toast.error(`${error}`);
		return null;
	});

	if (res) {
		return res;
	}
};
