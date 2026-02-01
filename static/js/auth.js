// Authentication Module for RaceCraft
// Handles Supabase authentication and session management

class AuthManager {
    constructor() {
        this.supabase = null;
        this.currentUser = null;
        this.anonymousId = null;
        this.supabaseEnabled = false;
        
        // Initialize anonymous ID
        this.anonymousId = this.getOrCreateAnonymousId();
    }

    async initialize() {
        try {
            // Check if Supabase is configured
            const response = await fetch('/api/auth/check');
            const data = await response.json();
            
            if (data.supabase_enabled && data.supabase_url && data.supabase_anon_key) {
                // Initialize Supabase client
                this.supabase = window.supabase.createClient(
                    data.supabase_url,
                    data.supabase_anon_key
                );
                this.supabaseEnabled = true;
                
                // Check for existing session
                const { data: { session } } = await this.supabase.auth.getSession();
                if (session) {
                    this.currentUser = session.user;
                    await this.handleAuthStateChange();
                }
                
                // Listen for auth changes
                this.supabase.auth.onAuthStateChange((event, session) => {
                    this.currentUser = session?.user || null;
                    this.handleAuthStateChange();
                });
                
                console.log('✓ Supabase authentication initialized');
            } else {
                console.log('ℹ Supabase not configured - running in legacy mode');
            }
        } catch (error) {
            console.error('Failed to initialize auth:', error);
        }
        
        // Render UI regardless
        this.renderAuthUI();
    }

    async getSupabaseAnonKey() {
        // This method is no longer needed as we get the key from the /api/auth/check endpoint
        // Kept for backward compatibility
        return null;
    }

    getOrCreateAnonymousId() {
        let id = localStorage.getItem('racecraft_anonymous_id');
        if (!id) {
            id = 'anon_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('racecraft_anonymous_id', id);
        }
        return id;
    }

    async handleAuthStateChange() {
        if (this.currentUser) {
            // User logged in - migrate anonymous data if exists
            const anonymousId = localStorage.getItem('racecraft_anonymous_id');
            if (anonymousId) {
                await this.migrateAnonymousData(anonymousId);
            }
        }
        this.renderAuthUI();
    }

    async migrateAnonymousData(anonymousId) {
        try {
            const session = await this.supabase.auth.getSession();
            if (!session?.data?.session?.access_token) return;

            const response = await fetch('/api/auth/migrate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session.data.session.access_token}`
                },
                body: JSON.stringify({ anonymous_id: anonymousId })
            });

            if (response.ok) {
                const data = await response.json();
                console.log(`✓ Migrated ${data.migrated_plans} plans to your account`);
                
                // Clear anonymous ID after migration
                localStorage.removeItem('racecraft_anonymous_id');
                this.anonymousId = null;
                
                // Show success message
                this.showNotification(`Welcome! ${data.migrated_plans} plan(s) have been saved to your account.`, 'success');
            }
        } catch (error) {
            console.error('Migration error:', error);
        }
    }

    renderAuthUI() {
        const container = document.getElementById('auth-container');
        if (!container) return;

        if (this.currentUser) {
            // Show user info and logout button
            container.innerHTML = `
                <div class="auth-user-info">
                    <span class="mdi mdi-account-circle"></span>
                    <span class="auth-user-email">${this.currentUser.email}</span>
                </div>
                <button class="auth-btn" onclick="authManager.logout()">
                    <span class="mdi mdi-logout"></span> Sign Out
                </button>
            `;
        } else if (this.supabaseEnabled) {
            // Show sign in button
            container.innerHTML = `
                <button class="auth-btn" onclick="authManager.showAuthModal()">
                    <span class="mdi mdi-login"></span> Sign In
                </button>
                <div class="anonymous-notice" style="display: none;">
                    You're using RaceCraft anonymously. <a onclick="authManager.showAuthModal()">Create an account</a> to save your plans across devices.
                </div>
            `;
            
            // Show anonymous notice if user has created plans
            if (localStorage.getItem('has_saved_plans')) {
                const notice = container.querySelector('.anonymous-notice');
                if (notice) notice.style.display = 'block';
            }
        } else {
            // Supabase not configured
            container.innerHTML = '';
        }
    }

    showAuthModal() {
        const modal = document.getElementById('auth-modal');
        if (modal) {
            modal.style.display = 'flex';
            // Reset forms
            this.switchAuthTab('signin');
            this.clearAuthForms();
        }
    }

    hideAuthModal() {
        const modal = document.getElementById('auth-modal');
        if (modal) {
            modal.style.display = 'none';
            this.clearAuthForms();
        }
    }

    switchAuthTab(tab) {
        // Update tabs
        document.querySelectorAll('.auth-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        
        // Update forms
        document.querySelectorAll('.auth-form').forEach(f => {
            f.classList.toggle('active', f.id === `${tab}-form`);
        });
        
        // Update modal title
        const titles = {
            'signin': 'Sign In',
            'signup': 'Create Account',
            'magic': 'Magic Link Sign In'
        };
        document.getElementById('auth-modal-title').textContent = titles[tab] || 'Sign In';
    }

    clearAuthForms() {
        // Clear all inputs and messages
        document.querySelectorAll('.auth-form input').forEach(input => input.value = '');
        document.querySelectorAll('.error-message').forEach(msg => msg.style.display = 'none');
        document.querySelectorAll('.success-message').forEach(msg => msg.style.display = 'none');
    }

    async signIn(email, password) {
        const errorDiv = document.getElementById('signin-error');
        errorDiv.style.display = 'none';

        try {
            const { data, error } = await this.supabase.auth.signInWithPassword({
                email,
                password
            });

            if (error) throw error;

            this.hideAuthModal();
            this.showNotification('Successfully signed in!', 'success');
        } catch (error) {
            errorDiv.textContent = error.message || 'Failed to sign in';
            errorDiv.style.display = 'block';
        }
    }

    async signUp(email, password, passwordConfirm) {
        const errorDiv = document.getElementById('signup-error');
        const successDiv = document.getElementById('signup-success');
        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';

        // Validate passwords match
        if (password !== passwordConfirm) {
            errorDiv.textContent = 'Passwords do not match';
            errorDiv.style.display = 'block';
            return;
        }

        // Validate password length
        if (password.length < 6) {
            errorDiv.textContent = 'Password must be at least 6 characters';
            errorDiv.style.display = 'block';
            return;
        }

        try {
            const { data, error } = await this.supabase.auth.signUp({
                email,
                password
            });

            if (error) throw error;

            successDiv.style.display = 'block';
            
            // Auto close modal after 2 seconds
            setTimeout(() => {
                this.hideAuthModal();
            }, 2000);
        } catch (error) {
            errorDiv.textContent = error.message || 'Failed to create account';
            errorDiv.style.display = 'block';
        }
    }

    async sendMagicLink(email) {
        const errorDiv = document.getElementById('magic-error');
        const successDiv = document.getElementById('magic-success');
        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';

        try {
            const { data, error } = await this.supabase.auth.signInWithOtp({
                email,
                options: {
                    emailRedirectTo: window.location.origin
                }
            });

            if (error) throw error;

            successDiv.style.display = 'block';
        } catch (error) {
            errorDiv.textContent = error.message || 'Failed to send magic link';
            errorDiv.style.display = 'block';
        }
    }

    async logout() {
        if (!this.supabase) return;

        try {
            await this.supabase.auth.signOut();
            this.showNotification('Successfully signed out', 'success');
            
            // Recreate anonymous ID
            this.anonymousId = this.getOrCreateAnonymousId();
        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    // Get auth headers for API requests
    async getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };

        if (this.supabase && this.currentUser) {
            const session = await this.supabase.auth.getSession();
            if (session?.data?.session?.access_token) {
                headers['Authorization'] = `Bearer ${session.data.session.access_token}`;
            }
        } else if (this.anonymousId) {
            headers['X-Anonymous-ID'] = this.anonymousId;
        }

        return headers;
    }

    showNotification(message, type = 'info') {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'success' ? 'var(--success-color)' : 'var(--danger-color)'};
            color: white;
            border-radius: 8px;
            box-shadow: var(--shadow-lg);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Global auth manager instance
const authManager = new AuthManager();

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await authManager.initialize();
    
    // Set up auth modal event listeners
    setupAuthModalListeners();
});

function setupAuthModalListeners() {
    // Tab switching
    document.querySelectorAll('.auth-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            authManager.switchAuthTab(tab.dataset.tab);
        });
    });

    // Sign in
    document.getElementById('signin-btn')?.addEventListener('click', async () => {
        const email = document.getElementById('signin-email').value;
        const password = document.getElementById('signin-password').value;
        await authManager.signIn(email, password);
    });

    // Sign up
    document.getElementById('signup-btn')?.addEventListener('click', async () => {
        const email = document.getElementById('signup-email').value;
        const password = document.getElementById('signup-password').value;
        const passwordConfirm = document.getElementById('signup-password-confirm').value;
        await authManager.signUp(email, password, passwordConfirm);
    });

    // Magic link
    document.getElementById('magic-btn')?.addEventListener('click', async () => {
        const email = document.getElementById('magic-email').value;
        await authManager.sendMagicLink(email);
    });

    // Cancel buttons
    document.querySelectorAll('[id^="auth-cancel-btn"]').forEach(btn => {
        btn.addEventListener('click', () => authManager.hideAuthModal());
    });

    // Close modal on outside click
    document.getElementById('auth-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'auth-modal') {
            authManager.hideAuthModal();
        }
    });

    // Enter key support
    ['signin', 'signup', 'magic'].forEach(formType => {
        document.getElementById(`${formType}-form`)?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById(`${formType}-btn`)?.click();
            }
        });
    });
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
