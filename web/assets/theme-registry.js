/* PAS 全站统一 14 套风格注册与同步引擎（严格对齐 web-ui-design/references/style-presets.md） */
(() => {
  'use strict';

  const STORAGE_KEY = 'pas_se_theme';
  const LEGACY_KEY = 'se_theme';

  const GROUPS = [
    {
      id: 'light',
      label: { 'zh-CN': '浅色与护眼', 'en-US': 'Light & Eye-Care', 'ru-RU': 'Светлые темы' },
      items: [
        { id: 'minimalist-light', dark: false, label: { 'zh-CN': '极简明亮', 'en-US': 'Minimalist Light', 'ru-RU': 'Светлый минимализм' } },
        { id: 'arctic-frost', dark: false, label: { 'zh-CN': '极地冰蓝', 'en-US': 'Arctic Frost', 'ru-RU': 'Арктический лед' } },
        { id: 'warm-paper', dark: false, label: { 'zh-CN': '护眼暖纸', 'en-US': 'Warm Paper', 'ru-RU': 'Теплая бумага' } },
        { id: 'slate-daylight', dark: false, label: { 'zh-CN': '冷灰工程', 'en-US': 'Slate Daylight', 'ru-RU': 'Инженерный серый' } },
        { id: 'bento-grid', dark: false, label: { 'zh-CN': '便当盒网格', 'en-US': 'Bento Grid', 'ru-RU': 'Сетка Бенто' } },
        { id: 'editorial', dark: false, label: { 'zh-CN': '编辑杂志', 'en-US': 'Editorial', 'ru-RU': 'Журнальный' } },
      ],
    },
    {
      id: 'dark',
      label: { 'zh-CN': '暗色工程', 'en-US': 'Dark Engineering', 'ru-RU': 'Темные инженерные' },
      items: [
        { id: 'precision-dark', dark: true, label: { 'zh-CN': '精密暗黑', 'en-US': 'Precision Dark', 'ru-RU': 'Точный темный' } },
        { id: 'ocean-slate', dark: true, label: { 'zh-CN': '深海工业蓝', 'en-US': 'Ocean Slate', 'ru-RU': 'Глубокий океан' } },
        { id: 'nord-dark', dark: true, label: { 'zh-CN': '北欧极夜', 'en-US': 'Nord Dark', 'ru-RU': 'Северная ночь' } },
        { id: 'industrial-amber', dark: true, label: { 'zh-CN': '碳黑琥珀', 'en-US': 'Industrial Amber', 'ru-RU': 'Янтарь и карбон' } },
        { id: 'glassmorphism', dark: true, label: { 'zh-CN': '毛玻璃拟态', 'en-US': 'Glassmorphism', 'ru-RU': 'Стекломорфизм' } },
      ],
    },
    {
      id: 'scifi',
      label: { 'zh-CN': '科幻战情室', 'en-US': 'Sci-Fi Console', 'ru-RU': 'Sci-Fi пульт' },
      items: [
        { id: 'sci-fi-cyan', dark: true, label: { 'zh-CN': '科幻 · 电光青', 'en-US': 'Sci-Fi Cyan', 'ru-RU': 'Неон циан' } },
        { id: 'sci-fi-purple', dark: true, label: { 'zh-CN': '科幻 · 赛博紫', 'en-US': 'Sci-Fi Purple', 'ru-RU': 'Кибер фиолетовый' } },
        { id: 'sci-fi-matrix', dark: true, label: { 'zh-CN': '科幻 · 矩阵绿', 'en-US': 'Sci-Fi Matrix', 'ru-RU': 'Матрица зеленый' } },
      ],
    },
  ];

  const ALL_ITEMS = GROUPS.flatMap((g) => g.items);
  const VALID_IDS = ALL_ITEMS.map((x) => x.id);

  function getLang() {
    const l = localStorage.getItem('pas_se_lang') || localStorage.getItem('se_lang') || document.documentElement.lang || 'zh-CN';
    return ['zh-CN', 'en-US', 'ru-RU'].includes(l) ? l : 'zh-CN';
  }

  function resolveTheme(candidate) {
    const raw = candidate || localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_KEY) || 'minimalist-light';
    return VALID_IDS.includes(raw) ? raw : 'minimalist-light';
  }

  function populateSelect(sel, lang) {
    if (!sel) return;
    const curLang = lang || getLang();
    const curVal = resolveTheme(document.documentElement.getAttribute('data-theme') || sel.value);
    sel.innerHTML = '';
    for (const grp of GROUPS) {
      const og = document.createElement('optgroup');
      og.label = grp.label[curLang] || grp.label['zh-CN'];
      for (const item of grp.items) {
        const opt = document.createElement('option');
        opt.value = item.id;
        opt.textContent = item.label[curLang] || item.label['zh-CN'];
        og.appendChild(opt);
      }
      sel.appendChild(og);
    }
    sel.value = curVal;
  }

  function applyTheme(next) {
    const valid = resolveTheme(next);
    document.documentElement.setAttribute('data-theme', valid);
    try {
      localStorage.setItem(STORAGE_KEY, valid);
      localStorage.setItem(LEGACY_KEY, valid);
    } catch {
      /* ignore */
    }
    document.querySelectorAll('#theme-select').forEach((sel) => {
      if (sel.value !== valid) sel.value = valid;
    });
    window.dispatchEvent(new CustomEvent('pas:theme-change', { detail: { theme: valid } }));
    return valid;
  }

  // 立即应用已持久化的主题，避免页面首屏白闪
  applyTheme();

  function initSelects() {
    const lang = getLang();
    document.querySelectorAll('#theme-select').forEach((sel) => {
      populateSelect(sel, lang);
      if (!sel.dataset.pasThemeBound) {
        sel.dataset.pasThemeBound = '1';
        sel.addEventListener('change', (e) => applyTheme(e.target.value));
      }
    });
    const langSel = document.getElementById('lang-select');
    if (langSel && !langSel.dataset.pasThemeLangBound) {
      langSel.dataset.pasThemeLangBound = '1';
      langSel.addEventListener('change', () => {
        const nextLang = langSel.value || getLang();
        document.querySelectorAll('#theme-select').forEach((sel) => populateSelect(sel, nextLang));
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSelects);
  } else {
    initSelects();
  }

  window.addEventListener('storage', (e) => {
    if (e.key === STORAGE_KEY || e.key === LEGACY_KEY) applyTheme(e.newValue);
  });

  window.PAS_THEMES = VALID_IDS;
  window.PAS_THEME_GROUPS = GROUPS;
  window.PAS_APPLY_THEME = applyTheme;
  window.PAS_POPULATE_THEME_SELECT = populateSelect;
})();
