// Helper to retrieve Django CSRF token
function getCsrfToken() {
    // First try reading from the rendered {% csrf_token %} input field
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfInput && csrfInput.value) {
        return csrfInput.value;
    }
    // Fallback: extract from browser cookies
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
        
    return cookieValue || '';
}





function bufferDecode(value) {
    return Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));
}
function bufferEncode(value) {
    return btoa(String.fromCharCode(...new Uint8Array(value))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

async function registerBiometric(nickname) {
    const optionsRes = await fetch('/webauthn/register/options/');
    const options = await optionsRes.json();
    options.challenge = bufferDecode(options.challenge);
    options.user.id = bufferDecode(options.user.id);
    if (options.excludeCredentials) {
        options.excludeCredentials.forEach(c => c.id = bufferDecode(c.id));
    }
    const credential = await navigator.credentials.create({ publicKey: options });
    const payload = {
        id: credential.id,
        rawId: bufferEncode(credential.rawId),
        type: credential.type,
        nickname: nickname,
        response: {
            attestationObject: bufferEncode(credential.response.attestationObject),
            clientDataJSON: bufferEncode(credential.response.clientDataJSON),
        },
    };
    const verifyRes = await fetch('/webauthn/register/verify/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify(payload),
    });
    const result = await verifyRes.json();
    showToast(result.message, result.success ? 'success' : 'error');
}

async function loginWithBiometric(username) {
    const optionsRes = await fetch(`/webauthn/login/options/?username=${encodeURIComponent(username || '')}`);
    const options = await optionsRes.json();
    options.challenge = bufferDecode(options.challenge);
    if (options.allowCredentials) {
        options.allowCredentials.forEach(c => c.id = bufferDecode(c.id));
    }
    const credential = await navigator.credentials.get({ publicKey: options });
    const payload = {
        id: credential.id,
        rawId: bufferEncode(credential.rawId),
        type: credential.type,
        response: {
            authenticatorData: bufferEncode(credential.response.authenticatorData),
            clientDataJSON: bufferEncode(credential.response.clientDataJSON),
            signature: bufferEncode(credential.response.signature),
            userHandle: credential.response.userHandle ? bufferEncode(credential.response.userHandle) : null,
        },
    };
    const verifyRes = await fetch('/webauthn/login/verify/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify(payload),
    });
    const result = await verifyRes.json();
    if (result.success) {
        window.location.href = result.redirect;
    } else {
        showToast(result.message, 'error');
    }
}