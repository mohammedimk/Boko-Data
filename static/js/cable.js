// Handles smart card validation and dynamic bouquet loading for cable subscriptions.
document.addEventListener('DOMContentLoaded', function () {
    const providerSelect = document.getElementById('id_provider');
    const smartcardInput = document.getElementById('id_smartcard');
    const validateBtn = document.getElementById('validateCardBtn');
    const validationResult = document.getElementById('cardValidationResult');
    const bouquetsGrid = document.getElementById('bouquetsGrid');
    const bouquetIdInput = document.getElementById('id_bouquet_id');

    function renderBouquets(bouquets) {
        bouquetsGrid.innerHTML = '';
        if (!bouquets || bouquets.length === 0) {
            bouquetsGrid.innerHTML = '<div class="text-muted small py-3 text-center w-100">No bouquets available.</div>';
            return;
        }
        bouquets.forEach(bq => {
            const el = document.createElement('div');
            el.className = 'plan-item';
            el.dataset.bouquetId = bq.bouquet_id;
            el.innerHTML = `
                <div class="plan-size" style="font-size:0.85rem;">${bq.name}</div>
                <div class="plan-price">₦${Number(bq.price).toFixed(2)}</div>
            `;
            el.addEventListener('click', () => {
                document.querySelectorAll('#bouquetsGrid .plan-item').forEach(p => p.classList.remove('selected'));
                el.classList.add('selected');
                bouquetIdInput.value = bq.bouquet_id;
            });
            bouquetsGrid.appendChild(el);
        });
    }

    async function loadBouquets(provider) {
        bouquetsGrid.innerHTML = '<div class="text-muted small py-3 text-center w-100"><i class="fa-solid fa-spinner fa-spin"></i> Loading bouquets...</div>';
        bouquetIdInput.value = '';
        try {
            const data = await fetchJSON(`/ajax/cable-bouquets/?provider=${encodeURIComponent(provider)}`);
            if (data.success) {
                renderBouquets(data.bouquets);
            } else {
                bouquetsGrid.innerHTML = `<div class="text-danger small py-3 text-center w-100">${data.message || 'Could not load bouquets.'}</div>`;
            }
        } catch (err) {
            bouquetsGrid.innerHTML = '<div class="text-danger small py-3 text-center w-100">Network error while loading bouquets.</div>';
        }
    }

    if (providerSelect) {
        loadBouquets(providerSelect.value);
        providerSelect.addEventListener('change', () => loadBouquets(providerSelect.value));
    }

    if (validateBtn) {
        validateBtn.addEventListener('click', async () => {
            const smartcard = smartcardInput.value.trim();
            if (!smartcard) {
                validationResult.innerHTML = '<span class="validation-error">Enter a smart card number first.</span>';
                return;
            }
            validationResult.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Validating...';
            try {
                const data = await fetchJSON('/ajax/validate-decoder/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `provider=${encodeURIComponent(providerSelect.value)}&smartcard_number=${encodeURIComponent(smartcard)}`,
                });
                if (data.success) {
                    validationResult.innerHTML = `<span class="validation-success"><i class="fa-solid fa-circle-check"></i> ${data.customer_name}</span>`;
                } else {
                    validationResult.innerHTML = `<span class="validation-error"><i class="fa-solid fa-circle-xmark"></i> ${data.message}</span>`;
                }
            } catch (err) {
                validationResult.innerHTML = '<span class="validation-error">Validation failed. Try again.</span>';
            }
        });
    }
});
