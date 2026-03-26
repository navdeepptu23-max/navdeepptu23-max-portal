/* ============================================================
   PORTAL — main.js
   Dynamic interactions: counters, search, AJAX, toast, nav
   ============================================================ */

'use strict';

// ── Flash toast auto‑dismiss ──────────────────────────────────
(function () {
  const toast = document.getElementById('flash-toast');
  if (!toast) return;
  setTimeout(() => {
    toast.style.transition = 'opacity .5s';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 500);
  }, 4500);
  toast.querySelectorAll('.close').forEach(btn => {
    btn.addEventListener('click', () => btn.closest('.alert').remove());
  });
})();

// ── Animated number counter ───────────────────────────────────
function animateCounter(el) {
  const target = parseInt(el.dataset.target || el.textContent.replace(/,/g, ''), 10);
  if (isNaN(target)) return;
  const duration = 1200;
  const start    = performance.now();
  const easeOut  = t => 1 - Math.pow(1 - t, 3);

  function step(ts) {
    const p = Math.min((ts - start) / duration, 1);
    el.textContent = Math.round(easeOut(p) * target).toLocaleString();
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// Trigger counters when they scroll into view
(function () {
  const counters = document.querySelectorAll('[data-counter]');
  if (!counters.length) return;

  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        animateCounter(e.target);
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(el => io.observe(el));
})();

// ── Scroll‑in animations ──────────────────────────────────────
(function () {
  const els = document.querySelectorAll('.fade-in-up');
  if (!els.length) return;

  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.animationPlayState = 'running';
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });

  els.forEach(el => {
    el.style.animationPlayState = 'paused';
    io.observe(el);
  });
})();

// ── Mobile nav toggle ─────────────────────────────────────────
(function () {
  const btn = document.getElementById('nav-hamburger');
  const menu = document.getElementById('nav-mobile');
  if (!btn || !menu) return;
  btn.addEventListener('click', () => {
    menu.classList.toggle('open');
    btn.setAttribute('aria-expanded', menu.classList.contains('open'));
  });
})();

// ── Dashboard sidebar toggle (mobile) ────────────────────────
(function () {
  const btn = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('dash-sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (!btn || !sidebar) return;

  function open() {
    sidebar.classList.add('open');
    if (overlay) overlay.style.display = 'block';
  }
  function close() {
    sidebar.classList.remove('open');
    if (overlay) overlay.style.display = 'none';
  }

  btn.addEventListener('click', () => sidebar.classList.contains('open') ? close() : open());
  if (overlay) overlay.addEventListener('click', close);
})();

// ── Live table search ─────────────────────────────────────────
(function () {
  document.querySelectorAll('[data-search-table]').forEach(input => {
    const tableId = input.dataset.searchTable;
    const table   = document.getElementById(tableId);
    if (!table) return;

    input.addEventListener('input', () => {
      const q = input.value.toLowerCase().trim();
      table.querySelectorAll('tbody tr').forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
      // empty‑state row
      const visible = table.querySelectorAll('tbody tr:not([style*="none"])').length;
      let noResult  = table.querySelector('.no-result-row');
      if (!visible) {
        if (!noResult) {
          noResult = table.insertRow(-1);
          noResult.className = 'no-result-row';
          const td = noResult.insertCell(0);
          td.colSpan = 100;
          td.style.cssText = 'text-align:center;padding:2rem;color:#718096;';
          td.textContent   = 'No matching records found.';
        }
      } else if (noResult) {
        noResult.remove();
      }
    });
  });
})();

// ── Sortable table ────────────────────────────────────────────
(function () {
  document.querySelectorAll('th.sortable').forEach(th => {
    th.addEventListener('click', () => {
      const table = th.closest('table');
      const idx   = Array.from(th.parentElement.children).indexOf(th);
      const asc   = th.dataset.sort !== 'asc';
      th.dataset.sort = asc ? 'asc' : 'desc';

      // Reset other headers
      th.parentElement.querySelectorAll('th').forEach(t => { if (t !== th) delete t.dataset.sort; });

      const rows = Array.from(table.querySelectorAll('tbody tr'));
      rows.sort((a, b) => {
        const va = a.cells[idx]?.textContent.trim() || '';
        const vb = b.cells[idx]?.textContent.trim() || '';
        const na = parseFloat(va.replace(/,/g, ''));
        const nb = parseFloat(vb.replace(/,/g, ''));
        if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
        return asc ? va.localeCompare(vb) : vb.localeCompare(va);
      });

      const tbody = table.querySelector('tbody');
      rows.forEach(r => tbody.appendChild(r));
    });
  });
})();

// ── Like button (AJAX) ────────────────────────────────────────
(function () {
  document.querySelectorAll('.like-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const postId = btn.dataset.postId;
      if (!postId) return;
      try {
        const res  = await fetch(`/post/${postId}/like`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          btn.querySelector('.like-count').textContent = data.likes;
          btn.classList.add('liked');
          btn.querySelector('i').style.transform = 'scale(1.3)';
          setTimeout(() => btn.querySelector('i').style.transform = '', 200);
        }
      } catch (_) {}
    });
  });
})();

// ── Password show/hide ────────────────────────────────────────
window.togglePassword = function (fieldId, iconEl) {
  const field = document.getElementById(fieldId);
  if (!field) return;
  if (field.type === 'password') {
    field.type = 'text';
    if (iconEl) iconEl.innerHTML = '🙈';
  } else {
    field.type = 'password';
    if (iconEl) iconEl.innerHTML = '&#128065;';
  }
};

// ── Password strength meter ───────────────────────────────────
(function () {
  const pw  = document.getElementById('password');
  const bar = document.getElementById('pw-strength-bar');
  const lbl = document.getElementById('pw-strength-label');
  if (!pw || !bar) return;

  pw.addEventListener('input', () => {
    const v = pw.value;
    let score = 0;
    if (v.length >= 8)               score++;
    if (/[A-Z]/.test(v))             score++;
    if (/[0-9]/.test(v))             score++;
    if (/[^A-Za-z0-9]/.test(v))      score++;

    const levels = [
      { w: '0%',   bg: '#e2e8f0', t: '' },
      { w: '25%',  bg: '#fc8181', t: 'Weak' },
      { w: '50%',  bg: '#f6ad55', t: 'Fair' },
      { w: '75%',  bg: '#63b3ed', t: 'Good' },
      { w: '100%', bg: '#48bb78', t: 'Strong' },
    ];
    const l = levels[score];
    bar.style.width      = l.w;
    bar.style.background = l.bg;
    if (lbl) lbl.textContent = l.t;
  });
})();

// ── Confirm delete ────────────────────────────────────────────
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', e => {
    if (!confirm(el.dataset.confirm)) e.preventDefault();
  });
});

// ── Auto‑resize textareas ─────────────────────────────────────
document.querySelectorAll('textarea.auto-resize').forEach(ta => {
  ta.addEventListener('input', () => {
    ta.style.height = 'auto';
    ta.style.height = ta.scrollHeight + 'px';
  });
});

// ── Char counter ──────────────────────────────────────────────
document.querySelectorAll('[data-maxlength]').forEach(el => {
  const max  = parseInt(el.dataset.maxlength, 10);
  const hint = document.getElementById(el.id + '-count');
  if (!hint) return;
  el.addEventListener('input', () => {
    const left = max - el.value.length;
    hint.textContent = `${left} characters remaining`;
    hint.style.color = left < 20 ? '#e53e3e' : '#718096';
  });
  hint.textContent = `${max} characters remaining`;
});
