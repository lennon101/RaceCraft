// theme.js - Dark Mode Support (Light / Dark / Auto)

/**
 * Theme Management System
 * Supports three modes: light, dark, and auto (system-based)
 * Persists user preference in localStorage
 * Defaults to auto mode if no preference is set
 */

const THEME_STORAGE_KEY = 'racecraft_theme_preference';
const THEME_OPTIONS = {
    LIGHT: 'light',
    DARK: 'dark',
    AUTO: 'auto'
};

/**
 * Get the system's preferred color scheme
 * @returns {string} 'dark' or 'light'
 */
function getSystemTheme() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
    }
    return 'light';
}

/**
 * Get the user's theme preference from localStorage
 * @returns {string} 'light', 'dark', or 'auto'
 */
function getThemePreference() {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    // Default to auto if no preference is set
    return stored || THEME_OPTIONS.AUTO;
}

/**
 * Save the user's theme preference to localStorage
 * @param {string} theme - 'light', 'dark', or 'auto'
 */
function saveThemePreference(theme) {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
}

/**
 * Apply the theme to the document
 * @param {string} theme - 'light' or 'dark' (resolved theme, not preference)
 */
function applyTheme(theme) {
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
}

/**
 * Resolve the theme preference to an actual theme
 * If preference is 'auto', resolve to system theme
 * @param {string} preference - 'light', 'dark', or 'auto'
 * @returns {string} 'light' or 'dark'
 */
function resolveTheme(preference) {
    if (preference === THEME_OPTIONS.AUTO) {
        return getSystemTheme();
    }
    return preference;
}

/**
 * Initialize the theme system
 * Should be called as early as possible to avoid flash of wrong theme
 */
function initializeTheme() {
    const preference = getThemePreference();
    const resolvedTheme = resolveTheme(preference);
    applyTheme(resolvedTheme);
    
    console.log(`Theme initialized: preference=${preference}, resolved=${resolvedTheme}`);
}

/**
 * Set the theme preference and apply it
 * @param {string} preference - 'light', 'dark', or 'auto'
 */
function setTheme(preference) {
    if (!Object.values(THEME_OPTIONS).includes(preference)) {
        console.error(`Invalid theme preference: ${preference}`);
        return;
    }
    
    saveThemePreference(preference);
    const resolvedTheme = resolveTheme(preference);
    applyTheme(resolvedTheme);
    
    console.log(`Theme changed: preference=${preference}, resolved=${resolvedTheme}`);
}

/**
 * Setup theme switcher UI
 * Should be called after DOM is ready
 */
function setupThemeSwitcher() {
    const themeRadios = document.querySelectorAll('input[name="theme"]');
    
    // Set the current preference in the UI
    const currentPreference = getThemePreference();
    themeRadios.forEach(radio => {
        if (radio.value === currentPreference) {
            radio.checked = true;
        }
    });
    
    // Listen for theme changes
    themeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                setTheme(this.value);
            }
        });
    });
}

/**
 * Listen for system theme changes when in auto mode
 */
function watchSystemTheme() {
    if (!window.matchMedia) return;
    
    const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Modern browsers support addEventListener
    if (darkModeQuery.addEventListener) {
        darkModeQuery.addEventListener('change', function(e) {
            const preference = getThemePreference();
            // Only apply if user is in auto mode
            if (preference === THEME_OPTIONS.AUTO) {
                const newTheme = e.matches ? 'dark' : 'light';
                applyTheme(newTheme);
                console.log(`System theme changed to ${newTheme} (auto mode active)`);
            }
        });
    } else if (darkModeQuery.addListener) {
        // Fallback for older browsers
        darkModeQuery.addListener(function(e) {
            const preference = getThemePreference();
            if (preference === THEME_OPTIONS.AUTO) {
                const newTheme = e.matches ? 'dark' : 'light';
                applyTheme(newTheme);
                console.log(`System theme changed to ${newTheme} (auto mode active)`);
            }
        });
    }
}

// Initialize theme immediately to avoid flash
initializeTheme();

// Setup theme switcher and system theme watcher when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        setupThemeSwitcher();
        watchSystemTheme();
    });
} else {
    // DOM is already ready
    setupThemeSwitcher();
    watchSystemTheme();
}

// Export for potential use in other scripts
if (typeof window !== 'undefined') {
    window.RaceCraftTheme = {
        getPreference: getThemePreference,
        setTheme: setTheme,
        getSystemTheme: getSystemTheme,
        THEME_OPTIONS: THEME_OPTIONS
    };
}
