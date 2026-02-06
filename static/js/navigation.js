// navigation.js - Handle side navigation menu

document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menu-toggle');
    const sideNav = document.getElementById('side-nav');
    const navOverlay = document.getElementById('nav-overlay');
    const navClose = document.getElementById('nav-close');

    // Open menu
    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            sideNav.classList.add('active');
            navOverlay.classList.add('active');
        });
    }

    // Close menu
    if (navClose) {
        navClose.addEventListener('click', function() {
            sideNav.classList.remove('active');
            navOverlay.classList.remove('active');
        });
    }

    // Close menu when clicking overlay
    if (navOverlay) {
        navOverlay.addEventListener('click', function() {
            sideNav.classList.remove('active');
            navOverlay.classList.remove('active');
        });
    }

    // Close menu on ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sideNav.classList.contains('active')) {
            sideNav.classList.remove('active');
            navOverlay.classList.remove('active');
        }
    });
});
