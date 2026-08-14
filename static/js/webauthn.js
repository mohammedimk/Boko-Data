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



// Convert Base64URL string to Uint8Array for browser WebAuthn API
function base64urlToUint8Array(base64url) {
    let padding = '='.repeat((4 - base64url.length % 4) % 4);
    let base64 = (base64url + padding).replace(/-/g, '+').replace(/_/g, '/');
    let rawData = window.atob(base64);
    let outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// Convert ArrayBuffer back to Base64URL string for Django response
function arrayBufferToBase64url(buffer) {
    let bytes = new Uint8Array(buffer);
    let string = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        string += String.fromCharCode(bytes[i]);
    }
    return window.btoa(string).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

async function loginWithBiometric(username) {
    try {
        // 1. Fetch WebAuthn authentication options from server
        const response = await fetch(`/webauthn/login/options/?username=${encodeURIComponent(username || '')}`);
        if (!response.ok) {
            throw new Error('Failed to retrieve authentication options from server.');
        }
        
        const options = await response.json();

        // 2. Decode Base64URL strings to Uint8Array so browser can launch prompt
        options.challenge = base64urlToUint8Array(options.challenge);
        
        if (options.allowCredentials) {
            options.allowCredentials.forEach(cred => {
                cred.id = base64urlToUint8Array(cred.id);
            });
        }

        // 3. Trigger Browser Biometric Prompt (Touch ID / Face ID / Windows Hello)
        const credential = await navigator.credentials.get({ publicKey: options });

        if (!credential) {
            throw new Error('Biometric scan cancelled or timed out.');
        }

        // 4. Format client credential response for verification
        const authData = {
            id: credential.id,
            rawId: arrayBufferToBase64url(credential.rawId),
            type: credential.type,
            response: {
                authenticatorData: arrayBufferToBase64url(credential.response.authenticatorData),
                clientDataJSON: arrayBufferToBase64url(credential.response.clientDataJSON),
                signature: arrayBufferToBase64url(credential.response.signature),
                userHandle: credential.response.userHandle ? arrayBufferToBase64url(credential.response.userHandle) : null,
            }
        };

        // 5. Send credential to Django for verification
        const verifyRes = await fetch('/webauthn/login/verify/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(authData)
        });

        const verifyData = await verifyRes.json();

        if (verifyData.success) {
            window.location.href = verifyData.redirect_url || '/dashboard/';
        } else {
            alert(verifyData.message || 'Biometric authentication failed.');
        }

    } catch (err) {
        console.error('WebAuthn Error:', err);
        alert(err.message || 'Biometric login failed.');
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}



async function registerBiometric(nickname = 'My Biometric Key') {
    try {
        // 1. Fetch options from Django server
        const response = await fetch('/webauthn/register/options/');
        if (!response.ok) {
            throw new Error('Failed to retrieve registration options.');
        }

        const options = await response.json();

        // 2. Decode Base64URL strings to Uint8Array for browser API
        options.challenge = base64urlToUint8Array(options.challenge);
        options.user.id = base64urlToUint8Array(options.user.id);

        if (options.excludeCredentials) {
            options.excludeCredentials.forEach(cred => {
                cred.id = base64urlToUint8Array(cred.id);
            });
        }

        // 3. Trigger Browser Prompt (Touch ID / Face ID / Fingerprint Reader)
        const credential = await navigator.credentials.create({ publicKey: options });

        if (!credential) {
            throw new Error('Biometric registration was cancelled.');
        }

        // 4. Format client credential payload
        const regData = {
            id: credential.id,
            rawId: arrayBufferToBase64url(credential.rawId),
            type: credential.type,
            nickname: nickname,
            response: {
                attestationObject: arrayBufferToBase64url(credential.response.attestationObject),
                clientDataJSON: arrayBufferToBase64url(credential.response.clientDataJSON),
            }
        };

        // 5. POST payload to Django backend for DB saving
        const verifyRes = await fetch('/webauthn/register/verify/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(regData)
        });

        const verifyData = await verifyRes.json();

        if (verifyData.success) {
            alert('Fingerprint saved successfully! You can now use it to log in.');
            window.location.reload();
        } else {
            alert('Registration error: ' + verifyData.message);
        }

    } catch (err) {
        console.error('Biometric Registration Error:', err);
        alert(err.message || 'Biometric registration failed.');
    }
}