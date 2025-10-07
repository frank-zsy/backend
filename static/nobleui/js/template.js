;(function () {
  "use strict";

  const ready = (callback) => {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, { once: true });
      return;
    }
    callback();
  };

  const applyLucideIcons = () => {
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  };

  const toggleClass = (element, className) => {
    if (!element) {
      return;
    }
    element.classList.toggle(className);
  };

  const initializeLayout = () => {
    const sidebarToggles = document.querySelectorAll("[data-toggle='sidebar']");
    const pageBody = document.querySelector("body");

    sidebarToggles.forEach((toggle) => {
      toggle.addEventListener("click", () => {
        toggleClass(pageBody, "sidebar-open");
      });
    });

    const themeSwitchers = document.querySelectorAll("[data-theme]");
    themeSwitchers.forEach((switcher) => {
      switcher.addEventListener("click", (event) => {
        const theme = event.currentTarget.getAttribute("data-theme");
        if (!theme) {
          return;
        }
        document.documentElement.setAttribute("data-bs-theme", theme);
        localStorage.setItem("preferred-theme", theme);
        applyLucideIcons();
      });
    });

    const storedTheme = localStorage.getItem("preferred-theme");
    if (storedTheme) {
      document.documentElement.setAttribute("data-bs-theme", storedTheme);
    }

    const autoYear = document.querySelectorAll("[data-current-year]");
    autoYear.forEach((node) => {
      node.textContent = String(new Date().getFullYear());
    });

    applyLucideIcons();
  };

  ready(initializeLayout);
  window.addEventListener("resize", applyLucideIcons);
})();
