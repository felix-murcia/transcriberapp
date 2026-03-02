/**
 * Módulo principal - Inicialización y orquestación
 * Coordina todos los módulos y configura event listeners
 */

import { elements, validateElements } from "./modules/domElements.js";
import {
    handleSendAudio,
    setupBeforeUnloadHandler,
    setupChatHandlers,
    setupCollapsibleHandlers,
    setupFileHandlers,
    setupFormHandlers,
    setupHistoryHandlers,
    setupModalHandlers,
    setupPrintHandler,
    setupRecordingHandlers
} from "./modules/eventHandlers.js";
import { updateRecordingButtonsState } from "./modules/ui.js";

/**
 * Estado de autenticación
 */
let isAuthenticated = false;
let currentUser = null;

/**
 * Verifica el estado de autenticación con el servidor
 */
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/check');
        const data = await response.json();

        isAuthenticated = data.logged_in;
        currentUser = data.user || null;

        updateAuthUI();
        return isAuthenticated;
    } catch (error) {
        console.error('Error verificando autenticación:', error);
        return false;
    }
}

/**
 * Actualiza la UI según el estado de autenticación
 */
function updateAuthUI() {
    const overlay = document.getElementById('loginOverlay');
    const sessionLabel = document.getElementById('sessionLabel');

    if (isAuthenticated) {
        // Ocultar overlay
        if (overlay) overlay.style.display = 'none';

        // Actualizar label de sesión
        if (sessionLabel) {
            sessionLabel.textContent = currentUser?.username || 'Conectado';
            sessionLabel.classList.add('authenticated');
        }

        // Habilitar funcionalidades
        enableAppFeatures();
    } else {
        // Mostrar overlay
        if (overlay) overlay.style.display = 'flex';

        // Actualizar label de sesión
        if (sessionLabel) {
            sessionLabel.textContent = 'Sin sesión';
            sessionLabel.classList.remove('authenticated');
        }

        // Deshabilitar funcionalidades
        disableAppFeatures();
    }
}

/**
 * Habilita las funcionalidades de la app
 */
function enableAppFeatures() {
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
        mainContent.style.pointerEvents = 'auto';
        mainContent.style.opacity = '1';
    }
}

/**
 * Deshabilita las funcionalidades de la app
 */
function disableAppFeatures() {
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
        mainContent.style.pointerEvents = 'none';
        mainContent.style.opacity = '0.5';
    }
}

/**
 * Realiza el login
 */
async function login(email, password) {
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (data.success) {
            isAuthenticated = true;
            currentUser = data.user;
            updateAuthUI();
            return { success: true };
        } else {
            return { success: false, error: data.error || 'Credenciales inválidas' };
        }
    } catch (error) {
        console.error('Error en login:', error);
        return { success: false, error: 'Error de conexión' };
    }
}

/**
 * Realiza el logout
 */
async function logout() {
    try {
        await fetch('/api/auth/logout', {
            method: 'POST'
        });

        isAuthenticated = false;
        currentUser = null;
        updateAuthUI();
    } catch (error) {
        console.error('Error en logout:', error);
    }
}

/**
 * Configura los event listeners de autenticación
 */
function setupAuthHandlers() {
    // Login desde overlay
    const overlayBtn = document.getElementById('loginOverlayBtn');
    if (overlayBtn) {
        overlayBtn.addEventListener('click', () => {
            const modal = document.getElementById('loginModal');
            if (modal) modal.style.display = 'block';
        });
    }

    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            const errorDiv = document.getElementById('loginError');

            const result = await login(email, password);

            if (result.success) {
                // Cerrar modal
                const modal = document.getElementById('loginModal');
                if (modal) modal.style.display = 'none';

                // Limpiar formulario
                loginForm.reset();
                if (errorDiv) errorDiv.hidden = true;
            } else {
                if (errorDiv) {
                    errorDiv.textContent = result.error;
                    errorDiv.hidden = false;
                }
            }
        });
    }

    // Close modal
    const closeModal = document.querySelector('.close-modal');
    if (closeModal) {
        closeModal.addEventListener('click', () => {
            const modal = document.getElementById('loginModal');
            if (modal) modal.style.display = 'none';
        });
    }

    // Click outside modal
    window.addEventListener('click', (e) => {
        const modal = document.getElementById('loginModal');
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

/**
 * Inicializa toda la aplicación
 */
async function init() {
    validateElements();

    if (elements.nameWarning) elements.nameWarning.hidden = false;
    if (elements.chatToggle) elements.chatToggle.disabled = true;

    // Initializar estado de botones de grabación (sin audio al inicio)
    updateRecordingButtonsState(false);

    // Verificar autenticación primero
    await checkAuthStatus();

    // Configurar handlers de autenticación
    setupAuthHandlers();

    // Configurar todos los event listeners
    setupFormHandlers();
    setupRecordingHandlers();
    setupFileHandlers();
    setupChatHandlers();
    setupHistoryHandlers();
    setupPrintHandler();
    setupBeforeUnloadHandler();
    setupModalHandlers();
    setupCollapsibleHandlers();

    // Asignar manejador principal de envío de audio
    if (elements.sendBtn) {
        elements.sendBtn.onclick = handleSendAudio;
    }

    console.log("✅ Aplicación iniciada correctamente");
}

// Esperar a que el DOM esté listo
document.addEventListener("DOMContentLoaded", init);
