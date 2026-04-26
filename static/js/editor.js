// Editor JavaScript with Live Preview

document.addEventListener('DOMContentLoaded', function() {
    const editor = document.getElementById('markdown-content');
    const preview = document.getElementById('preview-content');
    const titleInput = document.getElementById('title');
    const slugInput = document.getElementById('slug');
    const summaryInput = document.getElementById('summary');
    
    if (!editor || !preview) return;
    
    // Live preview update
    let updateTimeout;
    editor.addEventListener('input', function() {
        clearTimeout(updateTimeout);
        updateTimeout = setTimeout(updatePreview, 300);
    });
    
    function updatePreview() {
        const content = editor.value;
        fetch('/api/preview', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content: content})
        })
        .then(r => r.json())
        .then(data => {
            preview.innerHTML = data.html;
        })
        .catch(() => {
            preview.innerHTML = '<p style="color: #999;">Preview will appear here...</p>';
        });
    }
    
    // Auto-generate slug
    if (titleInput && slugInput) {
        titleInput.addEventListener('input', function() {
            if (!slugInput.dataset.edited) {
                slugInput.value = slugify(this.value);
            }
        });
        
        slugInput.addEventListener('input', function() {
            slugInput.dataset.edited = 'true';
        });
    }
    
    // Auto-save to localStorage
    const articleId = document.getElementById('article-id');
    const storageKey = articleId ? `blog-edit-${articleId.value}` : 'blog-new';
    
    // Load saved content
    const savedContent = localStorage.getItem(storageKey + '-content');
    const savedTitle = localStorage.getItem(storageKey + '-title');
    const savedSlug = localStorage.getItem(storageKey + '-slug');
    const savedSummary = localStorage.getItem(storageKey + '-summary');
    
    if (savedContent && !editor.value) editor.value = savedContent;
    if (savedTitle && !titleInput.value) titleInput.value = savedTitle;
    if (savedSlug && !slugInput.value) slugInput.value = savedSlug;
    if (savedSummary && !summaryInput.value) summaryInput.value = savedSummary;
    
    // Auto-save
    function saveToLocal() {
        if (editor.value) localStorage.setItem(storageKey + '-content', editor.value);
        if (titleInput.value) localStorage.setItem(storageKey + '-title', titleInput.value);
        if (slugInput.value) localStorage.setItem(storageKey + '-slug', slugInput.value);
        if (summaryInput) localStorage.setItem(storageKey + '-summary', summaryInput.value);
    }
    
    setInterval(saveToLocal, 5000);
    editor.addEventListener('input', saveToLocal);
    
    // Clear localStorage on save
    const form = document.getElementById('article-form');
    if (form) {
        form.addEventListener('submit', function() {
            localStorage.removeItem(storageKey + '-content');
            localStorage.removeItem(storageKey + '-title');
            localStorage.removeItem(storageKey + '-slug');
            localStorage.removeItem(storageKey + '-summary');
        });
    }
    
    // Toolbar buttons
    window.insertMarkdown = function(type) {
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        const text = editor.value;
        const selected = text.substring(start, end);
        let insertion = '';
        
        switch(type) {
            case 'bold':
                insertion = `**${selected || 'bold text'}**`;
                break;
            case 'italic':
                insertion = `*${selected || 'italic text'}*`;
                break;
            case 'h2':
                insertion = `\n## ${selected || 'Heading'}\n`;
                break;
            case 'h3':
                insertion = `\n### ${selected || 'Heading'}\n`;
                break;
            case 'link':
                insertion = `[${selected || 'link text'}](url)`;
                break;
            case 'code':
                insertion = `\`${selected || 'code'}\``;
                break;
            case 'codeblock':
                insertion = `\n\`\`\`\n${selected || 'code block'}\n\`\`\`\n`;
                break;
            case 'quote':
                insertion = `\n> ${selected || 'quote'}\n`;
                break;
            case 'ul':
                insertion = `\n- ${selected || 'list item'}\n`;
                break;
        }
        
        editor.value = text.substring(0, start) + insertion + text.substring(end);
        editor.focus();
        editor.selectionStart = start + insertion.length;
        editor.selectionEnd = start + insertion.length;
        updatePreview();
    };
    
    updatePreview();
});

function slugify(text) {
    return text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/[\s_-]+/g, '-')
        .replace(/^-+|-+$/g, '');
}
