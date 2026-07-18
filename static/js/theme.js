// theme.js
// Simple light/dark mode toggle using Bootstrap 5's data-bs-theme attribute.
// Preference is remembered in localStorage so it persists across page loads.
(function () {
  const STORAGE_KEY = "sbp-theme";
  const root = document.documentElement;
  const toggleBtn = document.getElementById("theme-toggle");

  function applyTheme(theme) {
    root.setAttribute("data-bs-theme", theme);
  }

  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    applyTheme(saved);
  } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    applyTheme("dark");
  }

  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      const current = root.getAttribute("data-bs-theme") === "dark" ? "dark" : "light";
      const next = current === "dark" ? "light" : "dark";
      applyTheme(next);
      localStorage.setItem(STORAGE_KEY, next);
    });
  }
})();
