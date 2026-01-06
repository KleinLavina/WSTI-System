
document.addEventListener("DOMContentLoaded", function () {

  /* =====================================================
     GUARD: prevent double-binding
  ===================================================== */
  if (window.__userScriptsLoaded) return;
  window.__userScriptsLoaded = true;

  /* =====================================================
     DROPDOWN FILTER HANDLERS
  ===================================================== */
  function initializeDropdowns() {
    document.querySelectorAll(".wc-filter-dropdown .wc-filter-btn")
      .forEach(button => {
        button.addEventListener("click", e => {
          e.preventDefault();
          e.stopPropagation();

          const dropdown = button.closest(".wc-filter-dropdown");
          const isOpen = dropdown.classList.contains("open");

          document.querySelectorAll(".wc-filter-dropdown")
            .forEach(d => d.classList.remove("open"));

          if (!isOpen) dropdown.classList.add("open");
        });
      });

    document.addEventListener("click", e => {
      if (!e.target.closest(".wc-filter-dropdown")) {
        document.querySelectorAll(".wc-filter-dropdown")
          .forEach(d => d.classList.remove("open"));
      }
    });

    document.addEventListener("keydown", e => {
      if (e.key === "Escape") {
        document.querySelectorAll(".wc-filter-dropdown")
          .forEach(d => d.classList.remove("open"));
      }
    });
  }

  initializeDropdowns();

  /* =====================================================
     CREATE USER SUBMIT (ABSOLUTE HARD GATE)
  ===================================================== */
  const createForm = document.getElementById("createUserForm");
  const createModalEl = document.getElementById("createUserModal");

  if (createForm) {
    createForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const submitBtn = createForm.querySelector('button[type="submit"]');
      if (submitBtn.disabled) return;

      const originalHTML = submitBtn.innerHTML;
      submitBtn.disabled = true;
      submitBtn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';

      // Clear previous errors
      createForm.querySelectorAll(".error-message").forEach(el => el.remove());
      createForm.querySelectorAll(".error").forEach(el =>
        el.classList.remove("error")
      );

      let response;
      try {
        response = await fetch(createForm.action, {
          method: "POST",
          body: new FormData(createForm),
          headers: { "X-Requested-With": "XMLHttpRequest" }
        });
      } catch (networkError) {
        console.error("Network error:", networkError);
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHTML;
        return;
      }

      /* -------------------------------------------------
         SAFE JSON PARSE (NO CRASHES)
      ------------------------------------------------- */
      let data = {};
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        try {
          data = await response.json();
        } catch {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalHTML;
          return;
        }
      } else {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHTML;
        return;
      }

      /* -------------------------------------------------
         ❌ HARD STOP — ANY ERROR BLOCKS ONBOARDING
      ------------------------------------------------- */
      if (!response.ok || data.success !== true) {

        if (data.errors) {
          Object.entries(data.errors).forEach(([field, messages]) => {
            const input = createForm.querySelector(`[name="${field}"]`);
            if (!input) return;

            input.classList.add("error");

            const msg = document.createElement("div");
            msg.className = "error-message";
            msg.textContent = messages[0];

            input.closest(".form-field")?.appendChild(msg);
          });
        }

        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHTML;
        return; // ⛔ NO ONBOARDING
      }

      /* -------------------------------------------------
         ✅ SUCCESS → ONBOARDING
      ------------------------------------------------- */
      bootstrap.Modal.getInstance(createModalEl)?.hide();

      setTimeout(() => {
        loadOnboarding(data.onboard_url);
      }, 400);

      submitBtn.disabled = false;
      submitBtn.innerHTML = originalHTML;
    });
  }

  /* =====================================================
     ONBOARDING LOADER
  ===================================================== */
  window.loadOnboarding = async function (url) {
    const modalEl = document.getElementById("onboardModal");
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    const body = document.getElementById("onboardModalBody");

    body.innerHTML = `
      <div class="text-center p-4">
        <div class="spinner-border text-primary mb-2"></div>
        <p>Loading...</p>
      </div>
    `;

    modal.show();

    try {
      const res = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });
      body.innerHTML = await res.text();
    } catch {
      body.innerHTML =
        `<div class="text-danger text-center p-4">Failed to load onboarding.</div>`;
    }
  };

  /* =====================================================
     ONBOARDING STEP SUBMIT (DELEGATED)
  ===================================================== */
  document.addEventListener("submit", async function (e) {
    const form = e.target.closest(".onboard-form");
    if (!form) return;

    e.preventDefault();

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn.disabled) return;

    const originalHTML = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML =
      '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';

    try {
      const res = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

      const data = await res.json();

      if (data.next) {
        loadOnboarding(data.next);
      } else if (data.completed) {
        bootstrap.Modal.getInstance(
          document.getElementById("onboardModal")
        )?.hide();
        setTimeout(() => window.location.reload(), 400);
      }

    } catch (err) {
      console.error("Onboarding error:", err);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalHTML;
    }
  });

  /* =====================================================
     COMPLETION HANDLER
  ===================================================== */
  window.finishOnboarding = function () {
    bootstrap.Modal.getInstance(
      document.getElementById("onboardModal")
    )?.hide();
    setTimeout(() => window.location.reload(), 400);
  };

});

