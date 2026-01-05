document.addEventListener("DOMContentLoaded", function () {

  /* =====================================================
     GUARD: prevent double-binding (CRITICAL FIX)
  ===================================================== */
  if (window.__userScriptsLoaded) return;
  window.__userScriptsLoaded = true;

  /* =====================================================
     DROPDOWN FILTER HANDLERS (FIXED)
  ===================================================== */
  function initializeDropdowns() {
    const dropdownButtons = document.querySelectorAll(
      '.wc-filter-dropdown .wc-filter-btn'
    );

    console.log(
      'Initializing dropdowns. Found:',
      dropdownButtons.length,
      'buttons'
    );

    dropdownButtons.forEach((button, index) => {
      console.log(`Setting up dropdown ${index}:`, button);

      button.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();

        const dropdown = this.closest('.wc-filter-dropdown');
        const isOpen = dropdown.classList.contains('open');

        console.log('Dropdown clicked. Was open:', isOpen);

        // Close all dropdowns first
        document
          .querySelectorAll('.wc-filter-dropdown')
          .forEach(d => d.classList.remove('open'));

        // Open current if it was closed
        if (!isOpen) {
          dropdown.classList.add('open');
          console.log('Dropdown opened');

          // Position dropdown menu if near viewport edge
          const menu = dropdown.querySelector('.wc-filter-menu');
          if (menu) {
            menu.style.top = '';
            menu.style.bottom = '';

            setTimeout(() => {
              const rect = menu.getBoundingClientRect();
              const spaceBelow = window.innerHeight - rect.bottom;

              if (spaceBelow < 0) {
                menu.style.top = 'auto';
                menu.style.bottom = 'calc(100% + 8px)';
                console.log('Dropdown repositioned above');
              }
            }, 10);
          }
        }
      });
    });

    /* ---- Close dropdowns on outside click ---- */
    const outsideClickHandler = function (e) {
      if (!e.target.closest('.wc-filter-dropdown')) {
        document
          .querySelectorAll('.wc-filter-dropdown.open')
          .forEach(d => d.classList.remove('open'));
      }
    };

    document.removeEventListener('click', window.__dropdownOutsideClick);
    window.__dropdownOutsideClick = outsideClickHandler;
    document.addEventListener('click', outsideClickHandler);

    /* ---- Prevent menu clicks from closing dropdown ---- */
    document.querySelectorAll('.wc-filter-menu').forEach(menu => {
      menu.addEventListener('click', function (e) {
        if (e.target.tagName === 'A') return; // allow navigation
        e.stopPropagation();
      });
    });

    /* ---- Close dropdowns on ESC ---- */
    const escapeHandler = function (e) {
      if (e.key === 'Escape') {
        document
          .querySelectorAll('.wc-filter-dropdown')
          .forEach(d => d.classList.remove('open'));
      }
    };

    document.removeEventListener('keydown', window.__dropdownEscapeHandler);
    window.__dropdownEscapeHandler = escapeHandler;
    document.addEventListener('keydown', escapeHandler);
  }

  console.log('Script loaded, initializing dropdowns...');
  initializeDropdowns();

  /* =====================================================
     CREATE USER SUBMIT
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

      createForm.querySelectorAll(".error-message").forEach(el => el.remove());
      createForm.querySelectorAll(".error").forEach(el => el.classList.remove("error"));

      try {
        const response = await fetch(createForm.action, {
          method: "POST",
          body: new FormData(createForm),
          headers: { "X-Requested-With": "XMLHttpRequest" }
        });

        const data = await response.json();

        if (!response.ok) {
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
          throw new Error("Validation failed");
        }

        const modal = bootstrap.Modal.getInstance(createModalEl);
        modal.hide();

        setTimeout(() => {
          loadOnboarding(data.onboard_url);
        }, 400);

      } catch (err) {
        console.error(err);
        alert("Unable to process request. Please check inputs.");
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHTML;
      }
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
      <div class="loading-spinner">
        <div class="spinner"></div>
        <p>Loading...</p>
      </div>
    `;

    modal.show();

    try {
      const response = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

      const html = await response.text();
      body.innerHTML = html;

    } catch (err) {
      console.error(err);
      body.innerHTML = `
        <div class="loading-spinner">
          <p style="color:#dc2626;">Failed to load onboarding.</p>
        </div>
      `;
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
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

      const data = await response.json();

      if (data.next) {
        loadOnboarding(data.next);
      } else if (data.completed) {
        bootstrap.Modal.getInstance(
          document.getElementById("onboardModal")
        ).hide();
        setTimeout(() => window.location.reload(), 400);
      }

    } catch (err) {
      console.error(err);
      alert("Onboarding failed. Please retry.");
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
