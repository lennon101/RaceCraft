// Hamburger Menu JavaScript

document.addEventListener('DOMContentLoaded', () => {
    const hamburgerBtn = document.getElementById('hamburger-btn');
    const sideMenu = document.getElementById('side-menu');
    const closeMenuBtn = document.getElementById('close-menu-btn');
    const menuOverlay = document.getElementById('menu-overlay');

    // Open menu
    function openMenu() {
        sideMenu.classList.add('open');
        menuOverlay.classList.add('active');
        hamburgerBtn.classList.add('active');
        document.body.style.overflow = 'hidden'; // Prevent scrolling when menu is open
    }

    // Close menu
    function closeMenu() {
        sideMenu.classList.remove('open');
        menuOverlay.classList.remove('active');
        hamburgerBtn.classList.remove('active');
        document.body.style.overflow = ''; // Restore scrolling
    }

    // Toggle menu
    function toggleMenu() {
        if (sideMenu.classList.contains('open')) {
            closeMenu();
        } else {
            openMenu();
        }
    }

    // Event listeners
    if (hamburgerBtn) {
        hamburgerBtn.addEventListener('click', toggleMenu);
    }

    if (closeMenuBtn) {
        closeMenuBtn.addEventListener('click', closeMenu);
    }

    if (menuOverlay) {
        menuOverlay.addEventListener('click', closeMenu);
    }

    // Close menu on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sideMenu.classList.contains('open')) {
            closeMenu();
        }
    });

    // Close menu when clicking a navigation link
    const sideMenuLinks = document.querySelectorAll('.side-menu-link');
    sideMenuLinks.forEach(link => {
        link.addEventListener('click', () => {
            closeMenu();
        });
    });
});
