<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar__brand">
        <div class="sidebar__mark">PB</div>
        <div class="sidebar__brand-text">
          <span class="sidebar__name">PhoneBook</span>
          <span class="sidebar__sub">Analytics</span>
        </div>
      </div>

      <nav class="sidebar__nav">
        <RouterLink to="/" class="sidebar__link">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="2" y="2" width="7" height="7" rx="1.5"/>
            <rect x="11" y="2" width="7" height="7" rx="1.5"/>
            <rect x="2" y="11" width="7" height="7" rx="1.5"/>
            <rect x="11" y="11" width="7" height="7" rx="1.5"/>
          </svg>
          <span class="sidebar__link-label">Dashboard</span>
        </RouterLink>

        <RouterLink to="/contacts" class="sidebar__link">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="10" cy="7" r="3.5"/>
            <path d="M2.5 17.5c0-3.314 3.358-6 7.5-6s7.5 2.686 7.5 6"/>
          </svg>
          <span class="sidebar__link-label">Contacts</span>
        </RouterLink>

        <RouterLink to="/calls" class="sidebar__link">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M3.5 4.5a1 1 0 0 1 1-1h2l1.5 3.5-1.5 1a9.5 9.5 0 0 0 5 5l1-1.5 3.5 1.5v2a1 1 0 0 1-1 1C7.5 16.5 3.5 12 3.5 4.5z"/>
          </svg>
          <span class="sidebar__link-label">Call History</span>
        </RouterLink>

        <RouterLink to="/favourites" class="sidebar__link">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M10 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4L10 14.4l-4.8 2.5.9-5.4L2.2 7.7l5.4-.8z"/>
          </svg>
          <span class="sidebar__link-label">Favourites</span>
        </RouterLink>

        <RouterLink to="/manage" class="sidebar__link">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M10 13V3m0 10-3-3m3 3 3-3"/>
            <path d="M3 14v1.5A1.5 1.5 0 0 0 4.5 17h11a1.5 1.5 0 0 0 1.5-1.5V14"/>
          </svg>
          <span class="sidebar__link-label">Manage Contacts</span>
        </RouterLink>
      </nav>

      <div class="sidebar__footer">v1.0 · 2026</div>
    </aside>

    <div class="main">
      <RouterView />
    </div>
  </div>
</template>

<script setup></script>
