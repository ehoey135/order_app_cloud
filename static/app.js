// Since main.py serves this file from the same origin as the API,
// relative URLs like "/companies" and "/orders" just work — no CORS needed.

const form = document.getElementById("order-form");
const companySelect = document.getElementById("companyId");
const waferQtyInput = document.getElementById("waferQuantity");
const chipQtyInput = document.getElementById("chipQuantity");
const waferFieldsEl = document.getElementById("wafer-fields");
const chipFieldsEl = document.getElementById("chip-fields");
const resultEl = document.getElementById("result");
const submitBtn = document.getElementById("submit-btn");

// ---------------------------------------------------------------------------
// Load companies into the dropdown on page load
// ---------------------------------------------------------------------------
async function loadCompanies() {
  try {
    const res = await fetch("/companies");
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    const companies = await res.json();

    companySelect.innerHTML = '<option value="">Select a company…</option>';
    for (const c of companies) {
      const opt = document.createElement("option");
      opt.value = c.company_id;
      opt.textContent = c.company_name;
      companySelect.appendChild(opt);
    }
  } catch (err) {
    companySelect.innerHTML = '<option value="">Failed to load companies</option>';
    console.error("Could not load companies:", err);
  }
}

// ---------------------------------------------------------------------------
// Build one wafer/chip field-group. Returns the wrapper element.
// ---------------------------------------------------------------------------
function buildWaferRecord(index) {
  const wrapper = document.createElement("div");
  wrapper.className = "record";
  wrapper.dataset.index = index;
  wrapper.innerHTML = `
    <div class="record-title">Wafer #${index}</div>
    <div class="grid-2">
      <label>
        Wafer number
        <input type="text" class="wafer-number" required />
      </label>
      <label>
        Wafer name (optional)
        <input type="text" class="wafer-name" />
      </label>
    </div>
    <div class="grid-2">
      <label>
        Wafer number 2 (optional)
        <input type="text" class="wafer-number-2" />
      </label>
      <label>
        Wafer part id (optional)
        <input type="text" class="wafer-part-id" />
      </label>
    </div>
  `;
  return wrapper;
}

function buildChipRecord(index) {
  const wrapper = document.createElement("div");
  wrapper.className = "record";
  wrapper.dataset.index = index;
  wrapper.innerHTML = `
    <div class="record-title">Chip #${index}</div>
    <div class="grid-2">
      <label>
        Chip number
        <input type="text" class="chip-number" required />
      </label>
      <label>
        Chip name (optional)
        <input type="text" class="chip-name" />
      </label>
    </div>
    <div class="grid-2">
      <label>
        Chip number 2 (optional)
        <input type="text" class="chip-number-2" />
      </label>
      <label>
        Chip part id (optional)
        <input type="text" class="chip-part-id" />
      </label>
    </div>
  `;
  return wrapper;
}

// ---------------------------------------------------------------------------
// Resize the wafer/chip field lists to match the quantity inputs, preserving
// values already typed into records that still exist.
// ---------------------------------------------------------------------------
function resizeFieldList(container, quantity, buildFn, emptyMessage) {
  const current = container.querySelectorAll(".record").length;

  if (quantity <= 0) {
    container.innerHTML = `<p class="empty-note">${emptyMessage}</p>`;
    return;
  }

  // Remove the "empty" placeholder if present
  const note = container.querySelector(".empty-note");
  if (note) note.remove();

  if (quantity > current) {
    for (let i = current + 1; i <= quantity; i++) {
      container.appendChild(buildFn(i));
    }
  } else if (quantity < current) {
    const records = container.querySelectorAll(".record");
    for (let i = current; i > quantity; i--) {
      records[i - 1].remove();
    }
  }
}

waferQtyInput.addEventListener("input", () => {
  const qty = Math.max(0, parseInt(waferQtyInput.value, 10) || 0);
  resizeFieldList(
    waferFieldsEl, qty, buildWaferRecord,
    "Set a wafer quantity above to add wafer fields."
  );
});

chipQtyInput.addEventListener("input", () => {
  const qty = Math.max(0, parseInt(chipQtyInput.value, 10) || 0);
  resizeFieldList(
    chipFieldsEl, qty, buildChipRecord,
    "Set a chip quantity above to add chip fields."
  );
});

// ---------------------------------------------------------------------------
// Gather all wafer/chip records currently in the DOM into plain objects
// ---------------------------------------------------------------------------
function collectWafers() {
  return Array.from(waferFieldsEl.querySelectorAll(".record")).map((el) => ({
    wafer_number: el.querySelector(".wafer-number").value.trim(),
    wafer_name: el.querySelector(".wafer-name").value.trim() || null,
    wafer_number_2: el.querySelector(".wafer-number-2").value.trim() || null,
    wafer_part_id: el.querySelector(".wafer-part-id").value.trim() || null,
  }));
}

function collectChips() {
  return Array.from(chipFieldsEl.querySelectorAll(".record")).map((el) => ({
    chip_number: el.querySelector(".chip-number").value.trim(),
    chip_name: el.querySelector(".chip-name").value.trim() || null,
    chip_numb_2: el.querySelector(".chip-number-2").value.trim() || null,
    chip_part_id: el.querySelector(".chip-part-id").value.trim() || null,
  }));
}

// ---------------------------------------------------------------------------
// Result banner helpers
// ---------------------------------------------------------------------------
function showSuccess(data) {
  resultEl.hidden = false;
  resultEl.className = "result success";
  resultEl.innerHTML = `
    <h3>Order created successfully</h3>
    <ul>
      <li>Order ID: ${data.order_id}</li>
      <li>Customer ID: ${data.customer_id}</li>
      <li>Dispatch ID: ${data.dispatch_id}</li>
      <li>Wafer IDs: ${data.wafer_ids.join(", ") || "(none)"}</li>
      <li>Chip IDs: ${data.chip_ids.join(", ") || "(none)"}</li>
    </ul>
  `;
}

function showError(message) {
  resultEl.hidden = false;
  resultEl.className = "result error";
  resultEl.innerHTML = `<h3>Order failed</h3><p>${message}</p>`;
}

// ---------------------------------------------------------------------------
// Submit
// ---------------------------------------------------------------------------
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  resultEl.hidden = true;

  const payload = {
    customer_name: document.getElementById("customerName").value.trim(),
    delivery_date: document.getElementById("deliveryDate").value,
    route: document.getElementById("route").value.trim(),
    cut_location: document.getElementById("cutLocation").value.trim(),
    bag: document.getElementById("bag").value.trim(),
    company_id: parseInt(companySelect.value, 10),
    wafer_quantity: Math.max(0, parseInt(waferQtyInput.value, 10) || 0),
    chip_quantity: Math.max(0, parseInt(chipQtyInput.value, 10) || 0),
    wafers: collectWafers(),
    chips: collectChips(),
  };

  submitBtn.disabled = true;
  submitBtn.textContent = "Creating…";

  try {
    const res = await fetch("/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.detail || "Unknown error");
    } else {
      showSuccess(data);
      form.reset();
      resizeFieldList(waferFieldsEl, 0, buildWaferRecord, "Set a wafer quantity above to add wafer fields.");
      resizeFieldList(chipFieldsEl, 0, buildChipRecord, "Set a chip quantity above to add chip fields.");
      await loadCompanies();
    }
  } catch (err) {
    showError("Could not reach the server. Is it running?");
    console.error(err);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Create order";
  }
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
loadCompanies();