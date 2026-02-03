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
                // Wait for Supabase library to load
                if (typeof window.supabase === 'undefined') {
                    console.error('❌ Supabase library not loaded from CDN');
                    console.log('ℹ Running in legacy mode - Supabase authentication disabled');
                    this.renderAuthUI();
                    return;
                }
                
                // Initialize Supabase client - the CDN version exports createClient directly
                const { createClient } = window.supabase;
                this.supabase = createClient(
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
            id = 'anon_' + Date.now() + '_' + Math.random().toString(36).substring(2, 11);
            localStorage.setItem('racecraft_anonymous_id', id);
        }
        return id;
    }

    async handleAuthStateChange() {
        // Removed automatic local plans migration popup - users can manually import via Load Plan button
        this.renderAuthUI();
    }

    async checkForLocalPlans() {
        try {
            // Fetch local plans from disk
            const response = await fetch('/api/auth/list-local-plans');

            if (!response.ok) {
                console.error('Failed to fetch local plans');
                return;
            }

            const data = await response.json();
            
            if (!data.plans || data.plans.length === 0) {
                // No local plans to migrate
                return;
            }

            // Store local plans for migration
            this.localPlans = data.plans;
            
            // Show migration modal
            this.renderLocalMigrationModal();
        } catch (error) {
            console.error('Error checking for local plans:', error);
        }
    }

    async showMigrationModal(anonymousId) {
        // This method is kept for backward compatibility but is no longer used
        // Migration now happens from local disk plans, not anonymous Supabase plans
        console.log('showMigrationModal called - this is deprecated, use checkForLocalPlans instead');
    }

    renderMigrationModal() {
        // Legacy method for anonymous Supabase plans migration
        // Kept for backward compatibility but not actively used
        const modal = document.getElementById('migration-modal');
        const plansList = document.getElementById('migration-plans-list');
        
        if (!modal || !plansList || !this.anonymousPlans) return;

        // Clear previous content
        plansList.innerHTML = '';

        // Add select all checkbox
        const selectAllDiv = document.createElement('div');
        selectAllDiv.className = 'migration-select-all';
        selectAllDiv.innerHTML = `
            <input type="checkbox" id="migration-select-all" checked />
            <label for="migration-select-all">Select All</label>
        `;
        plansList.appendChild(selectAllDiv);

        // Add plan items
        this.anonymousPlans.forEach(plan => {
            const planDiv = document.createElement('div');
            planDiv.className = 'migration-plan-item';
            planDiv.innerHTML = `
                <input type="checkbox" class="migration-plan-checkbox" data-plan-id="${plan.id}" checked />
                <div class="migration-plan-info">
                    <div class="migration-plan-name">${plan.name}</div>
                    <div class="migration-plan-date">Last updated: ${plan.updated_at}</div>
                </div>
            `;
            plansList.appendChild(planDiv);
        });

        // Set up select all functionality
        const selectAllCheckbox = document.getElementById('migration-select-all');
        const planCheckboxes = document.querySelectorAll('.migration-plan-checkbox');
        
        selectAllCheckbox.addEventListener('change', (e) => {
            planCheckboxes.forEach(cb => cb.checked = e.target.checked);
        });

        // Update select all when individual checkboxes change
        planCheckboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                const allChecked = Array.from(planCheckboxes).every(checkbox => checkbox.checked);
                selectAllCheckbox.checked = allChecked;
            });
        });

        // Show modal
        modal.style.display = 'flex';
    }

    renderLocalMigrationModal() {
        const modal = document.getElementById('migration-modal');
        const plansList = document.getElementById('migration-plans-list');
        
        if (!modal || !plansList || !this.localPlans) return;

        // Update modal title and description
        const title = modal.querySelector('h2');
        const description = modal.querySelector('.info-text');
        if (title) title.textContent = 'Import Local Plans to Your Account';
        if (description) description.textContent = 'You have some race plans saved locally. Would you like to import them into your account?';

        // Clear previous content
        plansList.innerHTML = '';

        // Add select all checkbox
        const selectAllDiv = document.createElement('div');
        selectAllDiv.className = 'migration-select-all';
        selectAllDiv.innerHTML = `
            <input type="checkbox" id="migration-select-all" checked />
            <label for="migration-select-all">Select All</label>
        `;
        plansList.appendChild(selectAllDiv);

        // Add plan items (use filename as id for local plans)
        this.localPlans.forEach(plan => {
            const planDiv = document.createElement('div');
            planDiv.className = 'migration-plan-item';
            planDiv.innerHTML = `
                <input type="checkbox" class="migration-plan-checkbox" data-filename="${plan.id}" checked />
                <div class="migration-plan-info">
                    <div class="migration-plan-name">${plan.name}</div>
                    <div class="migration-plan-date">Last updated: ${plan.updated_at}</div>
                </div>
            `;
            plansList.appendChild(planDiv);
        });

        // Set up select all functionality
        const selectAllCheckbox = document.getElementById('migration-select-all');
        const planCheckboxes = document.querySelectorAll('.migration-plan-checkbox');
        
        selectAllCheckbox.addEventListener('change', (e) => {
            planCheckboxes.forEach(cb => cb.checked = e.target.checked);
        });

        // Update select all when individual checkboxes change
        planCheckboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                const allChecked = Array.from(planCheckboxes).every(checkbox => checkbox.checked);
                selectAllCheckbox.checked = allChecked;
            });
        });

        // Show modal
        modal.style.display = 'flex';
    }

    async migrateAnonymousData(anonymousId) {
        // This method is no longer used for automatic migration
        // Kept for backward compatibility
        console.log('Automatic migration disabled - use showMigrationModal instead');
    }

    async performMigration() {
        const selectedCheckboxes = document.querySelectorAll('.migration-plan-checkbox:checked');
        
        // Check if we're migrating local plans (by filename) or anonymous plans (by plan ID)
        const hasFilename = selectedCheckboxes.length > 0 && selectedCheckboxes[0].dataset.filename;
        
        if (hasFilename) {
            // Migrating local disk plans
            await this.performLocalMigration(selectedCheckboxes);
        } else {
            // Migrating anonymous Supabase plans (legacy)
            await this.performAnonymousMigration(selectedCheckboxes);
        }
    }

    async performLocalMigration(selectedCheckboxes) {
        const selectedFilenames = Array.from(selectedCheckboxes).map(cb => cb.dataset.filename);

        if (selectedFilenames.length === 0) {
            document.getElementById('migration-modal').style.display = 'none';
            return;
        }

        try {
            const session = await this.supabase.auth.getSession();
            if (!session?.data?.session?.access_token) {
                this.showNotification('Please sign in to migrate plans', 'error');
                return;
            }

            let successCount = 0;
            let errorCount = 0;

            // Migrate each selected plan
            for (const filename of selectedFilenames) {
                try {
                    const response = await fetch('/api/auth/migrate-local-plan', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${session.data.session.access_token}`
                        },
                        body: JSON.stringify({ filename })
                    });

                    if (response.ok) {
                        successCount++;
                    } else {
                        errorCount++;
                        const data = await response.json();
                        console.error(`Failed to migrate ${filename}:`, data.error);
                    }
                } catch (error) {
                    errorCount++;
                    console.error(`Error migrating ${filename}:`, error);
                }
            }

            // Clear local plans reference
            this.localPlans = null;

            // Hide modal
            const modal = document.getElementById('migration-modal');
            if (modal) modal.style.display = 'none';

            // Show result message
            if (successCount > 0) {
                this.showNotification(
                    `Successfully imported ${successCount} plan(s) to your account!`, 
                    'success'
                );
            }

            if (errorCount > 0) {
                this.showNotification(
                    `Failed to import ${errorCount} plan(s). Please try again.`, 
                    'error'
                );
            }
        } catch (error) {
            console.error('Migration error:', error);
            this.showNotification('Failed to import plans. Please try again.', 'error');
        }
    }

    async performAnonymousMigration(selectedCheckboxes) {
        const selectedPlanIds = Array.from(selectedCheckboxes).map(cb => cb.dataset.planId);

        try {
            const session = await this.supabase.auth.getSession();
            if (!session?.data?.session?.access_token) return;

            const response = await fetch('/api/auth/migrate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session.data.session.access_token}`
                },
                body: JSON.stringify({ 
                    anonymous_id: this.pendingAnonymousId,
                    plan_ids: selectedPlanIds 
                })
            });

            if (response.ok) {
                const data = await response.json();
                console.log(`✓ Migrated ${data.migrated_plans} plans to your account`);
                
                // Clear anonymous ID after migration (or skip)
                localStorage.removeItem('racecraft_anonymous_id');
                this.anonymousId = null;
                this.pendingAnonymousId = null;
                this.anonymousPlans = null;
                
                // Hide modal
                const modal = document.getElementById('migration-modal');
                if (modal) modal.style.display = 'none';
                
                // Show success message
                if (data.migrated_plans > 0) {
                    this.showNotification(`Welcome! ${data.migrated_plans} plan(s) have been imported to your account.`, 'success');
                } else {
                    this.showNotification('Welcome to RaceCraft!', 'success');
                }
            }
        } catch (error) {
            console.error('Migration error:', error);
            this.showNotification('Failed to import plans. Please try again.', 'error');
        }
    }

    skipMigration() {
        // Clear migration data without migrating
        localStorage.removeItem('racecraft_anonymous_id');
        this.anonymousId = null;
        this.pendingAnonymousId = null;
        this.anonymousPlans = null;
        this.localPlans = null;
        
        // Hide modal
        const modal = document.getElementById('migration-modal');
        if (modal) modal.style.display = 'none';
        
        this.showNotification('Welcome to RaceCraft!', 'success');
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
            
            // Clear all form inputs and state when signing out
            // This ensures no data persists from the signed-in user to the next session
            if (typeof clearAllInputs === 'function') {
                clearAllInputs();
            }
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

    // Migration modal buttons
    document.getElementById('migration-import-btn')?.addEventListener('click', async () => {
        await authManager.performMigration();
    });

    document.getElementById('migration-skip-btn')?.addEventListener('click', () => {
        authManager.skipMigration();
    });

    // Close migration modal on outside click
    document.getElementById('migration-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'migration-modal') {
            authManager.skipMigration();
        }
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
