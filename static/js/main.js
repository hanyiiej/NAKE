// Main JavaScript for Blog

document.addEventListener('DOMContentLoaded', function() {
    // Auto-generate slug from title
    const titleInput = document.getElementById('title');
    const slugInput = document.getElementById('slug');
    
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
    
    // Delete confirmation
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this article?')) {
                e.preventDefault();
            }
        });
    });
    
    // Copy slug on click
    const slugField = document.querySelector('.slug-display');
    if (slugField) {
        slugField.addEventListener('click', function() {
            navigator.clipboard.writeText(this.textContent);
            this.style.color = 'var(--accent-yellow)';
            setTimeout(() => {
                this.style.color = '';
            }, 1000);
        });
    }
});

function slugify(text) {
    return text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/[\s_-]+/g, '-')
        .replace(/^-+|-+$/g, '');
}
