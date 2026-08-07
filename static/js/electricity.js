// Handles meter number validation for electricity bill payments.
document.addEventListener('DOMContentLoaded', function () {
    const discoSelect = document.querySelector('select[name="disco"]');
    const meterTypeSelect = document.querySelector('select[name="meter_type"]');
    const meterInput = document.getElementById('id_meter_number');
    const validateBtn = document.getElementById('validateMeterBtn');
    const validationResult = document.getElementById('meterValidationResult');

    if (validateBtn) {
        validateBtn.addEventListener('click', async () => {
            const meterNumber = meterInput.value.trim();
            if (!meterNumber) {
                validationResult.innerHTML = '<span class="validation-error">Enter a meter number first.</span>';
                return;
            }
            validationResult.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Validating...';
            try {
                const data = await fetchJSON('/ajax/validate-meter/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `disco=${encodeURIComponent(discoSelect.value)}&meter_number=${encodeURIComponent(meterNumber)}&meter_type=${encodeURIComponent(meterTypeSelect.value)}`,
                });
                if (data.success) {
                    validationResult.innerHTML = `<span class="validation-success"><i class="fa-solid fa-circle-check"></i> ${data.customer_name} - ${data.address}</span>`;
                } else {
                    validationResult.innerHTML = `<span class="validation-error"><i class="fa-solid fa-circle-xmark"></i> ${data.message}</span>`;
                }
            } catch (err) {
                validationResult.innerHTML = '<span class="validation-error">Validation failed. Try again.</span>';
            }
        });
    }
});
