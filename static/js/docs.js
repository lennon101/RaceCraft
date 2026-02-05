// docs.js - Handle documentation page specific functionality

document.addEventListener('DOMContentLoaded', function() {
    const sidebarToggle = document.getElementById('docs-sidebar-toggle');
    const sidebarContent = document.getElementById('docs-sidebar-content');

    // Toggle documentation sidebar on mobile
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebarContent.classList.toggle('active');
        });
    }

    // Smooth scroll to anchor links
    document.querySelectorAll('.markdown-content a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add copy button to code blocks
    document.querySelectorAll('.markdown-content pre code').forEach(function(codeBlock) {
        const pre = codeBlock.parentElement;
        const button = document.createElement('button');
        button.className = 'copy-code-btn';
        button.textContent = 'Copy';
        button.onclick = function() {
            navigator.clipboard.writeText(codeBlock.textContent).then(function() {
                button.textContent = 'Copied!';
                setTimeout(function() {
                    button.textContent = 'Copy';
                }, 2000);
            });
        };
        pre.style.position = 'relative';
        pre.appendChild(button);
    });
});
