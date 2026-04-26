(function () {
  const root = document.documentElement;

  function setTheme(newTheme) {
    window.__theme = newTheme;
    root.classList.remove("dark", "light");
    root.classList.add(newTheme);
  }

  var preferredTheme = "system";
  var darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

  function applyTheme() {
    setTheme(
      preferredTheme === "system"
        ? darkQuery.matches
          ? "dark"
          : "light"
        : preferredTheme
    );
  }

  applyTheme();

  if (darkQuery.addEventListener) {
    darkQuery.addEventListener("change", applyTheme);
  } else if (darkQuery.addListener) {
    darkQuery.addListener(applyTheme);
  }
})();

// https://gist.github.com/paulirish/1579671
(function () {
  var lastTime = 0;
  if (!window.requestAnimationFrame) {
    window.requestAnimationFrame = window["webkitRequestAnimationFrame"];
    window.cancelAnimationFrame =
      window["webkitCancelAnimationFrame"] ||
      window["webkitCancelRequestAnimationFrame"];
  }

  if (!window.requestAnimationFrame) {
    window.requestAnimationFrame = function (callback) {
      var currTime = new Date().getTime();
      var timeToCall = Math.max(0, 16 - (currTime - lastTime));
      var id = window.setTimeout(function () {
        callback(currTime + timeToCall);
      }, timeToCall);
      lastTime = currTime + timeToCall;
      return id;
    };
  }

  if (!window.cancelAnimationFrame) {
    window.cancelAnimationFrame = function (id) {
      clearTimeout(id);
    };
  }
})();

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".desc.expandable .expand-button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var desc = btn.closest(".desc.expandable");
      if (desc) desc.classList.toggle("expanded");
    });
  });

  var modal = document.getElementById("registration-modal");
  var form = document.getElementById("registration-modal-form");
  var paymentEl = document.getElementById("registration-payment");
  if (!modal) return;

  var modalScrollLockY = 0;
  var cardInputIds = ["reg-card-number", "reg-card-exp", "reg-card-cvv"];

  function syncTicketPayment() {
    if (!form || !paymentEl) return;
    var selected = form.querySelector('input[name="ticket"]:checked');
    var showCard = !!selected;
    paymentEl.classList.toggle("registration-modal__payment--visible", showCard);
    paymentEl.setAttribute("aria-hidden", showCard ? "false" : "true");
    cardInputIds.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      if (showCard) {
        el.setAttribute("required", "required");
      } else {
        el.removeAttribute("required");
        el.value = "";
      }
    });
  }

  function focusModalStart() {
    if (!form) return;
    var firstRadio = form.querySelector('input[name="ticket"]');
    if (firstRadio && typeof firstRadio.focus === "function") {
      try {
        firstRadio.focus({ preventScroll: true });
      } catch (err) {
        firstRadio.focus();
      }
    }
  }

  function openModal() {
    modalScrollLockY = window.scrollY || window.pageYOffset || document.documentElement.scrollTop || 0;
    document.documentElement.classList.add("registration-modal-active");
    document.body.classList.add("registration-modal-active");
    document.body.style.top = "-" + modalScrollLockY + "px";

    modal.classList.add("registration-modal--open");
    modal.setAttribute("aria-hidden", "false");
    syncTicketPayment();
    focusModalStart();
  }

  function closeModal() {
    modal.classList.remove("registration-modal--open");
    modal.setAttribute("aria-hidden", "true");

    document.documentElement.classList.remove("registration-modal-active");
    document.body.classList.remove("registration-modal-active");
    document.body.style.top = "";
    window.scrollTo(0, modalScrollLockY);

    modalScrollLockY = 0;
  }

  document.querySelectorAll("[data-registration-modal-open]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      openModal();
    });
  });

  modal.querySelectorAll("[data-registration-modal-close]").forEach(function (el) {
    el.addEventListener("click", function () {
      closeModal();
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && modal.classList.contains("registration-modal--open")) {
      closeModal();
    }
  });

  if (form) {
    form.querySelectorAll('input[name="ticket"]').forEach(function (radio) {
      radio.addEventListener("change", function () {
        syncTicketPayment();
      });
      radio.addEventListener("click", function () {
        requestAnimationFrame(syncTicketPayment);
      });
    });
    syncTicketPayment();

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;

      var params = new URLSearchParams(new FormData(form));

      fetch(form.getAttribute("action") || "/", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: params.toString(),
      })
        .then(function (res) {
          if (!res.ok) throw new Error("submit failed");
          closeModal();
          form.reset();
          syncTicketPayment();
          window.alert(
            "Inscrição enviada com sucesso! Em breve você receberá mais informações por e-mail."
          );
        })
        .catch(function () {
          window.alert(
            "Não foi possível enviar o formulário. Verifique sua conexão ou tente novamente em instantes."
          );
        })
        .finally(function () {
          if (submitBtn) submitBtn.disabled = false;
        });
    });
  }
});
