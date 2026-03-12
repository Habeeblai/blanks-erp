/* Blanks ERP — main.js */

// Auto-dismiss flash messages after 4 seconds
document.querySelectorAll('.alert').forEach(el => {
  setTimeout(() => {
    const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
    bsAlert.close();
  }, 4000);
});

// ─── Grid inventory inline editing ────────────────────────────────────────
document.querySelectorAll('.grid-qty-input').forEach(input => {
  let timer;

  input.addEventListener('change', function () {
    const variantId = this.dataset.variantId;
    const qty = parseInt(this.value, 10);
    if (isNaN(qty) || qty < 0) return;

    this.classList.add('saving');
    this.classList.remove('saved');

    clearTimeout(timer);
    timer = setTimeout(() => {
      fetch('/inventory/grid/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variant_id: variantId, quantity: qty }),
      })
      .then(r => r.json())
      .then(data => {
        this.classList.remove('saving');
        if (data.success) {
          this.classList.add('saved');
          setTimeout(() => this.classList.remove('saved'), 1500);
        }
      })
      .catch(() => this.classList.remove('saving'));
    }, 500);
  });
});

// ─── Dynamic sale form — add/remove rows ──────────────────────────────────
const addItemBtn = document.getElementById('add-sale-item');
if (addItemBtn) {
  addItemBtn.addEventListener('click', () => {
    const container = document.getElementById('sale-items');
    const row = container.querySelector('.sale-row').cloneNode(true);
    // Reset values
    row.querySelectorAll('select, input').forEach(el => el.value = '');
    row.querySelector('.item-info')?.remove();
    container.appendChild(row);
  });

  document.getElementById('sale-items').addEventListener('click', e => {
    if (e.target.closest('.remove-row')) {
      const rows = document.querySelectorAll('.sale-row');
      if (rows.length > 1) e.target.closest('.sale-row').remove();
    }
  });

  // Show variant info on selection
  document.getElementById('sale-items').addEventListener('change', e => {
    if (e.target.classList.contains('variant-select')) {
      const vid = e.target.value;
      const row = e.target.closest('.sale-row');
      if (!vid) return;
      fetch(`/sales/api/variant_info/${vid}`)
        .then(r => r.json())
        .then(d => {
          let info = row.querySelector('.item-info');
          if (!info) {
            info = document.createElement('div');
            info.className = 'item-info';
            row.appendChild(info);
          }
          info.innerHTML = `
            <small style="color:var(--text-muted); font-family: var(--font-mono);">
              Price: <span style="color:var(--accent)">₦${d.selling_price.toFixed(2)}</span>
              &nbsp;|&nbsp; Stock: <span style="color:var(--success)">${d.stock}</span>
            </small>`;
        });
    }
  });
}
