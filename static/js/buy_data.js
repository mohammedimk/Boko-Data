// Dynamically loads CheapDataHub data plans based on the selected network.
document.addEventListener('DOMContentLoaded', function () {
    const networkSelect = document.getElementById('id_network');
    const plansGrid = document.getElementById('plansGrid');
    const planIdInput = document.getElementById('id_plan_id');
    const selectedSummary = document.getElementById('selectedSummary');
    const selectedPlanName = document.getElementById('selectedPlanName');
    const selectedPlanPrice = document.getElementById('selectedPlanPrice');
    const form = document.getElementById('dataForm');
    const planError = document.getElementById('planError');

    function renderPlans(plans) {
        plansGrid.innerHTML = '';
        if (!plans || plans.length === 0) {
            plansGrid.innerHTML = '<div class="text-muted small py-3 text-center w-100">No plans available for this network.</div>';
            return;
        }
        plans.forEach(plan => {
            const el = document.createElement('div');
            el.className = 'plan-item';
            el.dataset.planId = plan.plan_id;
            el.dataset.planName = plan.name;
            el.dataset.planPrice = plan.price;
            el.innerHTML = `
                <div class="plan-size">${plan.data_size}</div>
                <div class="plan-validity">${plan.validity}</div>
                <div class="plan-price">₦${Number(plan.price).toFixed(2)}</div>
            `;
            el.addEventListener('click', () => selectPlan(el));
            plansGrid.appendChild(el);
        });
    }

    function selectPlan(el) {
        document.querySelectorAll('.plan-item').forEach(p => p.classList.remove('selected'));
        el.classList.add('selected');
        planIdInput.value = el.dataset.planId;
        selectedPlanName.textContent = `${el.dataset.planName}`;
        selectedPlanPrice.textContent = Number(el.dataset.planPrice).toFixed(2);
        selectedSummary.classList.remove('d-none');
        planError.classList.add('d-none');
    }

    async function loadPlans(network) {
        plansGrid.innerHTML = '<div class="text-muted small py-3 text-center w-100"><i class="fa-solid fa-spinner fa-spin"></i> Loading plans...</div>';
        selectedSummary.classList.add('d-none');
        planIdInput.value = '';
        try {
            const data = await fetchJSON(`/ajax/data-plans/?network=${encodeURIComponent(network)}`);
            if (data.success) {
                renderPlans(data.plans);
            } else {
                plansGrid.innerHTML = `<div class="text-danger small py-3 text-center w-100">${data.message || 'Could not load plans.'}</div>`;
            }
        } catch (err) {
            plansGrid.innerHTML = '<div class="text-danger small py-3 text-center w-100">Network error while loading plans.</div>';
        }
    }

    if (networkSelect) {
        loadPlans(networkSelect.value);
        networkSelect.addEventListener('change', () => loadPlans(networkSelect.value));
    }

    if (form) {
        form.addEventListener('submit', function (e) {
            if (!planIdInput.value) {
                e.preventDefault();
                planError.classList.remove('d-none');
                showToast('Please select a data plan before continuing.', 'error');
            }
        });
    }
});
