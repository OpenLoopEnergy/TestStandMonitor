/**
 * Updates the UI based on the admin flag.
 * It shows/hides elements with the admin only class and toggles
 * the admin mode indicator
 */

function updateAdminUI() {
    const isAdmin = sessionStorage.getItem("isAdmin") === 'true';

    // Update main page admin-only elements
    const clearDatabutton = document.getElementById('clear-data-table-button');
    if (clearDatabutton) {
        clearDatabutton.style.setProperty('display', isAdmin ? 'inline-block' : 'none', 'important');
    }

    // Update all elements that have the "admin-only" class
    document.querySelectorAll('.admin-only').forEach(elem => {
        if (isAdmin) {
            if (elem.tagName === "LI") {
                elem.style.setProperty('display', 'list-item', 'important');
            } else if (elem.tagName === "BUTTON") {
                elem.style.setProperty('display', 'inline-block', 'important');
            } else {
                elem.style.setProperty('display', '', 'important');
            }
        } else {
            elem.style.setProperty('display', 'none','important');
        }
    });

    // Update the Admin Mode indicator (if present)
    const indicator = document.getElementById("admin-indicator");
    if (indicator) {
        indicator.style.setProperty('display', isAdmin ? 'block' : 'none', 'important');
    }
}

function animateLogoBounce(callback) {
    const logo = document.querySelector('.navbar-brand img');
    if (!logo) return;
    logo.classList.add('bounce');
    // Remove the class after the animation duration (1 second)
    setTimeout(() => {
        logo.classList.remove('bounce');
        if (callback && typeof callback === "function") {
            callback();
        }
    }, 1000);
}

function toggleAdminMode() {
    const isAdmin = sessionStorage.getItem("isAdmin") === "true";
    if (isAdmin) {
        // Currently admin, so switch to viewer mode
        sessionStorage.removeItem("isAdmin");
        updateAdminUI();
        alert("You are now in Viewer mode")
    } else {
        sessionStorage.setItem("isAdmin", "true");
        updateAdminUI();
        alert("You are now in Admin mode.")
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Always update admin UI when the page loads
    updateAdminUI();

    // Prevent the logo's parent link from refreshing the page.
    const logoLink = document.querySelector('.navbar-brand');
    if (logoLink) {
        logoLink.addEventListener('click', (e) => {
            e.preventDefault();
        });
    }

    // Set up the admin mode toggle via the logo image clicks
    const logo = document.querySelector('.navbar-brand img');
    let clickCount = 0;
    let firstClickTime = null;

    if (logo) {
        logo.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent any default behavior
            const now = Date.now();
            // Reset the counter if more than 15 seconds have passed since the first click
            if (!firstClickTime || now - firstClickTime > 15000) {
                clickCount = 0;
                firstClickTime = now;
            }
            clickCount++;

            if (clickCount === 10) {
                // Animate the logo rotation then toggle the mode
                animateLogoBounce(() => {
                    toggleAdminMode();
                });
                // Reset click counter
                clickCount = 0;
                firstClickTime = null;
            }
        });
    } else {
        console.warn("Logo image not found. Check your HTML structure.")
    }
});

// === Reboot controller (delegated, robust) ===
;(() => {
  const modalSel = '#rebootModal';
  const timerSel = '#reboot-timer';
  const cancelBtn = '#cancel-reboot';
  const nowBtn   = '#reboot-now';
  const adminKeyWrap  = '#admin-key-wrap';
  const adminKeyInput = '#adminKeyInput';

  let countdown = null;
  let remaining = 10;

  // Toggle true only if your backend requires X-Admin-Key
  const REQUIRES_ADMIN_KEY = false;

  function showToast(id, msg) {
    const $toast = $(id);
    console.log('[toast]', id, msg);
    $toast.find('.toast-body').text(msg);
    try {
      $toast.toast('show');
    } catch (e) {
      // Bootstrap toast may not be initialized – try manual class toggle
      $toast.addClass('show');
      setTimeout(() => $toast.removeClass('show'), 4000);
    }
  }

  function startCountdown() {
    console.log('[reboot] startCountdown');
    remaining = 10;
    $(timerSel).text(remaining);
    if (REQUIRES_ADMIN_KEY) {
      $(adminKeyWrap).show();
      $(adminKeyInput).val('');
    } else {
      $(adminKeyWrap).hide();
    }
    countdown = setInterval(() => {
      remaining--;
      $(timerSel).text(remaining);
      if (remaining <= 0) {
        console.log('[reboot] auto trigger');
        clearInterval(countdown);
        countdown = null;
        $(modalSel).modal('hide');
        triggerReboot(false);
      }
    }, 1000);
  }

  function stopCountdown() {
    if (countdown) {
      console.log('[reboot] stopCountdown');
      clearInterval(countdown);
      countdown = null;
    }
  }

  async function triggerReboot(manual) {
    console.log('[reboot] triggerReboot manual=', manual);
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (REQUIRES_ADMIN_KEY) {
        const keyVal = $(adminKeyInput).val().trim();
        if (!keyVal) {
          showToast('#error-toast', 'Admin key required.');
          return;
        }
        headers['X-Admin-Key'] = keyVal;
      }

      const res = await fetch('/reboot', { method: 'POST', headers });
      const text = await res.text();
      console.log('[reboot] response', res.status, text);
      if (!res.ok) {
        let msg = 'Failed to initiate reboot';
        try {
          const data = JSON.parse(text);
          if (data && data.message) msg = data.message;
        } catch (_) {}
        throw new Error(msg + ` (HTTP ${res.status})`);
      }

      showToast('#success-toast', manual ? 'Reboot initiated.' : 'Auto‑reboot initiated.');
    } catch (err) {
      showToast('#error-toast', `Reboot failed: ${err.message}`);
    }
  }

  // Use delegated handlers so this works even if elements are toggled later
  $(document)
    .on('show.bs.modal', modalSel, startCountdown)
    .on('hide.bs.modal', modalSel, stopCountdown)
    .on('click', cancelBtn, stopCountdown)
    .on('click', nowBtn, function () {
      stopCountdown();
      $(modalSel).modal('hide');
      triggerReboot(true);
    });

  // Helpful: log when the trigger button is clicked and ensure the modal opens
  $(document).on('click', '[data-target="#rebootModal"]', function () {
    console.log('[reboot] trigger button clicked');
    // If needed, you can force the modal open:
    // $(modalSel).modal('show');
  });
})();
