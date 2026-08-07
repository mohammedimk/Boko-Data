// Sidebar toggle for mobile
document.addEventListener('DOMContentLoaded', function () {
    const toggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (toggle && sidebar) {
        toggle.addEventListener('click', () => sidebar.classList.toggle('show'));
    }

    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll('.app-alert').forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Reads the CSRF token from the cookie (Django default cookie name: csrftoken)
function getCsrfToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + '=')) {
            return decodeURIComponent(cookie.substring(name.length + 1));
        }
    }
    return '';
}

// Lightweight Bootstrap toast helper
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const bg = { success: 'text-bg-success', error: 'text-bg-danger', info: 'text-bg-primary', warning: 'text-bg-warning' }[type] || 'text-bg-primary';
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center ${bg} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;
    container.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

// Simple GET/POST spinner-aware fetch wrapper used by service pages
async function fetchJSON(url, options = {}) {
    const response = await fetch(url, options);
    return response.json();
}
