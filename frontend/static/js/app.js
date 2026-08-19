const root = document.documentElement;
const savedTheme = localStorage.getItem("coffee-theme");
if (savedTheme) root.dataset.theme = savedTheme;

const menuButton = document.querySelector(".menu-button");
const navigation = document.querySelector(".main-nav");
menuButton?.addEventListener("click", () => {
  const open = navigation.classList.toggle("open");
  menuButton.setAttribute("aria-expanded", String(open));
});

const themeButton = document.querySelector(".theme-toggle");
function syncThemeIcon() {
  if (themeButton)
    themeButton.setAttribute(
      "aria-label",
      root.dataset.theme === "dark"
        ? "Ativar tema claro"
        : "Ativar tema escuro",
    );
}
syncThemeIcon();
themeButton?.addEventListener("click", () => {
  root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("coffee-theme", root.dataset.theme);
  syncThemeIcon();
});

function dismissToast(toast) {
  toast.classList.add("toast-out");
  setTimeout(() => toast.remove(), 220);
}
function wireToast(toast) {
  toast
    .querySelector("button")
    ?.addEventListener("click", () => dismissToast(toast));
  setTimeout(() => dismissToast(toast), 3200);
}
document.querySelectorAll(".toast").forEach(wireToast);
function showToast(message, type = "success") {
  const region = document.querySelector(".toast-region");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.setAttribute("role", "status");
  const text = document.createElement("span");
  text.textContent = message;
  const close = document.createElement("button");
  close.type = "button";
  close.ariaLabel = "Fechar notificação";
  close.textContent = "×";
  toast.append(text, close, document.createElement("i"));
  region.append(toast);
  wireToast(toast);
}

document.addEventListener("click", (event) => {
  const step = event.target.closest("[data-step]");
  if (!step) return;
  const input = step.closest(".quantity-picker")?.querySelector("input");
  if (!input) return;
  const next = Math.min(
    Number(input.max) || 99,
    Math.max(
      Number(input.min) || 1,
      Number(input.value || 1) + Number(step.dataset.step),
    ),
  );
  input.value = next;
});

document.querySelectorAll("[data-phone-mask]").forEach((input) => {
  function formatPhone() {
    const digits = input.value.replace(/\D/g, "").slice(0, 11);
    let formatted = digits;
    if (digits.length > 2)
      formatted = `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
    else if (digits.length) formatted = `(${digits}`;
    if (digits.length > 7)
      formatted = `${formatted.slice(0, 10)}-${digits.slice(7)}`;
    input.value = formatted;
  }
  input.addEventListener("input", formatPhone);
  input.addEventListener("paste", () => setTimeout(formatPhone));
});

document.querySelectorAll("[data-cep-mask]").forEach((input) => {
  function formatCep() {
    const digits = input.value.replace(/\D/g, "").slice(0, 8);
    input.value =
      digits.length > 5 ? `${digits.slice(0, 5)}-${digits.slice(5)}` : digits;
  }
  input.addEventListener("input", formatCep);
  input.addEventListener("paste", () => setTimeout(formatCep));
});

document.addEventListener("submit", (event) => {
  const form = event.target.closest("[data-confirm]");
  if (form && !window.confirm(form.dataset.confirm)) event.preventDefault();
});

document.addEventListener("submit", async (event) => {
  const form = event.target.closest(".js-add-cart");
  if (!form) return;
  event.preventDefault();
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;
  try {
    const response = await fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message);
    document
      .querySelectorAll("[data-cart-count]")
      .forEach((badge) => (badge.textContent = data.count));
    showToast(data.message);
  } catch (error) {
    showToast(error.message || "Não foi possível adicionar o item.", "error");
  } finally {
    button.disabled = false;
  }
});

const liveFilter = document.querySelector("[data-live-filter]");
if (liveFilter) {
  const searchInput = liveFilter.querySelector('input[type="search"]');
  const categorySelect = liveFilter.querySelector("select");
  let filterTimer;
  async function updateCatalog() {
    const url = new URL(
      liveFilter.action || window.location.href,
      window.location.origin,
    );
    const params = new URLSearchParams(new FormData(liveFilter));
    url.search = params.toString();
    liveFilter.classList.add("is-loading");
    try {
      const response = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) throw new Error();
      const documentCopy = new DOMParser().parseFromString(
        await response.text(),
        "text/html",
      );
      const nextGrid = documentCopy.querySelector(".product-grid");
      if (nextGrid)
        document.querySelector(".product-grid").replaceWith(nextGrid);
      history.replaceState({}, "", `${url.pathname}${url.search}#cardapio`);
    } finally {
      liveFilter.classList.remove("is-loading");
    }
  }
  searchInput?.addEventListener("input", () => {
    clearTimeout(filterTimer);
    filterTimer = setTimeout(updateCatalog, 280);
  });
  searchInput?.addEventListener("search", updateCatalog);
  categorySelect?.addEventListener("change", updateCatalog);
}

const scrollTopButton = document.querySelector(".scroll-top");
function syncScrollTop() {
  scrollTopButton?.classList.toggle("visible", window.scrollY > 550);
}
window.addEventListener("scroll", syncScrollTop, { passive: true });
scrollTopButton?.addEventListener("click", () =>
  window.scrollTo({ top: 0, behavior: "smooth" }),
);
syncScrollTop();

document.addEventListener("click", (event) => {
  const toggle = event.target.closest(".password-toggle");
  if (!toggle) return;
  const input = toggle.closest(".password-field")?.querySelector("input");
  if (!input) return;
  const willShow = input.type === "password";
  input.type = willShow ? "text" : "password";
  toggle.setAttribute("aria-pressed", String(willShow));
  toggle.setAttribute(
    "aria-label",
    willShow ? "Ocultar senha" : "Mostrar senha",
  );
});
