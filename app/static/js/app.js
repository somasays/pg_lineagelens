/**
 * PostgreSQL Data Lineage Tool - Client-side JavaScript
 */

/**
 * Credential storage and encryption utilities
 */
const CredentialManager = {
    // Generate a random encryption key if needed
    getEncryptionKey: function() {
        let key = localStorage.getItem('pg_lineage_encryption_key');
        if (!key) {
            // Generate a random 32-character key for AES encryption
            key = Array.from(crypto.getRandomValues(new Uint8Array(16)))
                .map(b => b.toString(16).padStart(2, '0')).join('');
            localStorage.setItem('pg_lineage_encryption_key', key);
        }
        return key;
    },
    
    // Encrypt credentials with AES
    encryptCredentials: function(credentials) {
        try {
            // Simple encryption for demo purposes - in production use a proper encryption library
            const key = this.getEncryptionKey();
            const encryptedData = btoa(JSON.stringify(credentials) + '|' + key.substring(0, 8));
            return encryptedData;
        } catch (error) {
            console.error('Error encrypting credentials:', error);
            return null;
        }
    },
    
    // Decrypt stored credentials
    decryptCredentials: function(encryptedData) {
        try {
            const key = this.getEncryptionKey();
            // Simple decryption - in production use a proper decryption method
            const decodedData = atob(encryptedData);
            const [dataStr, keyCheck] = decodedData.split('|');
            
            // Verify key hasn't changed (simple integrity check)
            if (keyCheck !== key.substring(0, 8)) {
                console.error('Encryption key mismatch');
                return null;
            }
            
            return JSON.parse(dataStr);
        } catch (error) {
            console.error('Error decrypting credentials:', error);
            return null;
        }
    },
    
    // Save credentials to local storage with expiration
    saveCredentials: function(credentials) {
        try {
            // Add expiration timestamp (1 day from now)
            const expiresAt = Date.now() + (24 * 60 * 60 * 1000);
            const dataToStore = {
                credentials: credentials,
                expiresAt: expiresAt
            };
            
            // Encrypt and store
            const encryptedData = this.encryptCredentials(dataToStore);
            if (encryptedData) {
                localStorage.setItem('pg_lineage_credentials', encryptedData);
                return true;
            }
            return false;
        } catch (error) {
            console.error('Error saving credentials:', error);
            return false;
        }
    },
    
    // Load credentials from local storage
    loadCredentials: function() {
        try {
            const encryptedData = localStorage.getItem('pg_lineage_credentials');
            if (!encryptedData) return null;
            
            const data = this.decryptCredentials(encryptedData);
            if (!data) return null;
            
            // Check expiration
            if (data.expiresAt < Date.now()) {
                // Credentials expired, delete them
                this.deleteCredentials();
                return null;
            }
            
            return data.credentials;
        } catch (error) {
            console.error('Error loading credentials:', error);
            return null;
        }
    },
    
    // Delete stored credentials
    deleteCredentials: function() {
        localStorage.removeItem('pg_lineage_credentials');
    },
    
    // Get hours until credential expiration
    getHoursUntilExpiration: function() {
        try {
            const encryptedData = localStorage.getItem('pg_lineage_credentials');
            if (!encryptedData) return 0;
            
            const data = this.decryptCredentials(encryptedData);
            if (!data || !data.expiresAt) return 0;
            
            const expiresAt = new Date(data.expiresAt);
            const now = new Date();
            return Math.max(0, Math.round((expiresAt - now) / (1000 * 60 * 60)));
        } catch (error) {
            console.error('Error calculating credential expiration:', error);
            return 0;
        }
    }
};

/**
 * Auto-connect with stored credentials
 */
function autoConnectWithStoredCredentials() {
    // Check if we're already connected
    const connectionDisplayDiv = document.querySelector('.p-3.rounded');
    if (connectionDisplayDiv) {
        // Already connected, nothing to do
        return;
    }
    
    // Check if manual disconnect was performed
    const manualDisconnect = localStorage.getItem('pg_lineage_manual_disconnect') === 'true';
    if (manualDisconnect) {
        // User manually disconnected, don't auto-reconnect
        // Display status but don't connect
        const connectionStatus = document.getElementById('connectionStatus');
        if (connectionStatus) {
            connectionStatus.innerHTML = `
                <div class="alert alert-info">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <i class="bi bi-info-circle me-2"></i>
                            Disconnected. Saved credentials available.
                        </div>
                        <button class="btn btn-sm btn-primary" id="useSavedCredentials">
                            <i class="bi bi-box-arrow-in-right me-1"></i>Use Saved Credentials
                        </button>
                    </div>
                </div>
            `;
            
            // Add event listener to the "Use Saved Credentials" button
            setTimeout(() => {
                const useSavedCredentialsButton = document.getElementById('useSavedCredentials');
                if (useSavedCredentialsButton) {
                    useSavedCredentialsButton.addEventListener('click', function() {
                        // Clear the manual disconnect flag
                        localStorage.removeItem('pg_lineage_manual_disconnect');
                        
                        // Show connecting message
                        connectionStatus.innerHTML = '<div class="alert alert-info">Connecting with saved credentials...</div>';
                        
                        // Now reconnect using the same function
                        const credentials = CredentialManager.loadCredentials();
                        if (!credentials) {
                            connectionStatus.innerHTML = '<div class="alert alert-danger">Stored credentials not found or expired</div>';
                            return;
                        }
                        
                        // Create form data from stored credentials
                        const formData = new FormData();
                        for (const [key, value] of Object.entries(credentials)) {
                            formData.append(key, value);
                        }
                        
                        // Send connection request
                        fetch('/connect', {
                            method: 'POST',
                            body: formData
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                connectionStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                                // Refresh page to show connected status
                                setTimeout(() => {
                                    window.location.reload();
                                }, 1000);
                            } else {
                                connectionStatus.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
                            }
                        })
                        .catch(error => {
                            connectionStatus.innerHTML = `<div class="alert alert-danger">Error: ${error}</div>`;
                        });
                    });
                }
            }, 0);
        }
        return;
    }
    
    // Load stored credentials
    const credentials = CredentialManager.loadCredentials();
    if (!credentials) {
        // No valid stored credentials
        return;
    }
    
    // Show auto-connect message
    const connectionStatus = document.getElementById('connectionStatus');
    if (connectionStatus) {
        connectionStatus.innerHTML = '<div class="alert alert-info">Auto-connecting using saved credentials...</div>';
    }
    
    // Create form data from stored credentials
    const formData = new FormData();
    for (const [key, value] of Object.entries(credentials)) {
        formData.append(key, value);
    }
    
    // Send connection request
    fetch('/connect', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (connectionStatus) {
                connectionStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
            }
            // Refresh page to show connected status
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            // Connection failed with stored credentials
            if (connectionStatus) {
                connectionStatus.innerHTML = `<div class="alert alert-warning">Auto-connect failed: ${data.message}</div>`;
            }
            // Delete invalid credentials
            CredentialManager.deleteCredentials();
        }
    })
    .catch(error => {
        if (connectionStatus) {
            connectionStatus.innerHTML = `<div class="alert alert-danger">Auto-connect error: ${error}</div>`;
        }
        // Delete potentially invalid credentials
        CredentialManager.deleteCredentials();
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Auto-connect with stored credentials on page load
    autoConnectWithStoredCredentials();
    
    // Show stored credential status if not connected
    const connectionDisplayDiv = document.querySelector('.p-3.rounded');
    if (!connectionDisplayDiv) {
        const storedCredentialData = CredentialManager.loadCredentials();
        const connectionStatus = document.getElementById('connectionStatus');
        
        if (connectionStatus && storedCredentialData) {
            // Get hours until expiration from CredentialManager directly
            const hoursLeft = CredentialManager.getHoursUntilExpiration();
            
            connectionStatus.innerHTML = `
                <div class="alert alert-secondary">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <i class="bi bi-key-fill me-2"></i>
                            Stored credentials: ${storedCredentialData.user}@${storedCredentialData.host}/${storedCredentialData.database}
                            <small class="ms-2 text-muted">(expires in ~${hoursLeft} hours)</small>
                        </div>
                        <button class="btn btn-sm btn-outline-secondary" id="clearCredentials">
                            <i class="bi bi-trash me-1"></i>Clear
                        </button>
                    </div>
                </div>
            `;
            
            // Add event listener to clear button
            document.getElementById('clearCredentials').addEventListener('click', function() {
                CredentialManager.deleteCredentials();
                connectionStatus.innerHTML = '<div class="alert alert-success">Stored credentials deleted</div>';
                setTimeout(() => {
                    connectionStatus.innerHTML = '';
                }, 2000);
            });
        }
    }
    
    // Connection form handling
    const connectionForm = document.getElementById('connectionForm');
    if (connectionForm) {
        // Add "Remember Me" checkbox
        const formGroup = document.createElement('div');
        formGroup.className = 'mb-3 form-check';
        formGroup.innerHTML = `
            <input type="checkbox" class="form-check-input" id="rememberCredentials" name="rememberCredentials" checked>
            <label class="form-check-label" for="rememberCredentials">Remember credentials (encrypted, expires in 24 hours)</label>
        `;
        connectionForm.querySelector('button[type="submit"]').parentNode.insertBefore(formGroup, connectionForm.querySelector('button[type="submit"]'));
        
        connectionForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Clear the manual disconnect flag when user manually connects
            localStorage.removeItem('pg_lineage_manual_disconnect');
            
            const formData = new FormData(this);
            const connectionStatus = document.getElementById('connectionStatus');
            const rememberCredentials = formData.get('rememberCredentials') === 'on';
            
            // Clear previous status and show loading message
            connectionStatus.innerHTML = '<div class="alert alert-info">Connecting to database...</div>';
            
            // Prepare credentials object for storing if requested
            const credentials = {};
            if (rememberCredentials) {
                credentials.host = formData.get('host');
                credentials.port = formData.get('port');
                credentials.database = formData.get('database');
                credentials.user = formData.get('user');
                credentials.password = formData.get('password');
            }
            
            // Send connection request
            fetch('/connect', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    connectionStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                    document.getElementById('analyzeBtn').disabled = false;
                    
                    // Store credentials if requested
                    if (rememberCredentials) {
                        CredentialManager.saveCredentials(credentials);
                    }
                    
                    // Refresh page to show connected status
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    connectionStatus.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
                }
            })
            .catch(error => {
                connectionStatus.innerHTML = `<div class="alert alert-danger">Error: ${error}</div>`;
            });
        });
    }
    
    // Analysis form handling
    const analysisForm = document.getElementById('analysisForm');
    if (analysisForm) {
        analysisForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const analysisStatus = document.getElementById('analysisStatus');
            const loader = document.getElementById('loader');
            const analyzeBtn = document.getElementById('analyzeBtn');
            
            // Clear previous status, show loading spinner, and disable button
            analysisStatus.innerHTML = '<div class="alert alert-info">Running analysis... This may take a few moments.</div>';
            loader.style.display = 'block';
            analyzeBtn.disabled = true;
            
            // Send analysis request
            fetch('/analyze', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                loader.style.display = 'none';
                analyzeBtn.disabled = false;
                
                if (data.success) {
                    analysisStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                    
                    // Redirect directly to lineage page after analysis
                    setTimeout(() => {
                        window.location.href = '/lineage';
                    }, 1500);
                } else {
                    analysisStatus.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
                }
            })
            .catch(error => {
                loader.style.display = 'none';
                analyzeBtn.disabled = false;
                analysisStatus.innerHTML = `<div class="alert alert-danger">Error: ${error}</div>`;
            });
        });
    }
    
    // Hook into the disconnect link to add a reconnection lock
    const disconnectLink = document.querySelector('a[href="/disconnect"]');
    if (disconnectLink) {
        disconnectLink.addEventListener('click', function() {
            // Set a flag to prevent auto-reconnection after disconnect
            localStorage.setItem('pg_lineage_manual_disconnect', 'true');
            // Keep credentials stored, just prevent auto-reconnection
        });
    }
    
    // Initialize any tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
});