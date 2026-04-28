// Empire Bot Dashboard — main.js
// Auto-save indicators and helpers

document.addEventListener('DOMContentLoaded', () => {
  // Highlight active nav
  const path = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(a => {
    if (a.getAttribute('href') === path) a.style.color = '#fff';
  });
});
