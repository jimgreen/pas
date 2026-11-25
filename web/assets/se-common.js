/* 状态估计子页面共享工具：双主题、中/英/俄三语、API 请求、模态确认与设备字典 */
(() => {
  'use strict';

  const BASE_I18N = {
    'zh-CN': {
      'brand.sub': '在线分析平台',
      'nav.overview': '总览',
      'nav.analysis': '分析功能',
      'nav.se_root': '状态估计 SE',
      'nav.se_main': '主画面',
      'nav.se_flow': '潮流图',
      'nav.se_curves': '历史曲线',
      'nav.se_devices': '设备对比',
      'nav.se_measurements': '有效实测明细',
      'nav.se_params': '算法参数',
      'nav.se_prefilter': '预过滤量测管理',
      'nav.se_pseudo': '伪量测管理',
      'nav.se_bad': '坏量测管理',
      'nav.se_logs': '运行日志',
      'nav.se_detail': '状态估计明细',
      'nav.lf': '潮流分析 LF',
      'nav.ca': '静态安全 CA',
      'nav.management': '运行管理',
      'nav.runs': '运行历史',
      'nav.measurements': '设备量测',
      'nav.limits': '安全限值',
      'nav.workspace': '工作目录',
      'nav.settings': '系统设置',
      'service.checking': '服务检查中',
      'service.ok': '服务运行中',
      'service.degraded': '服务降级',
      'action.run_se': '立即执行 SE',
      'action.refresh': '刷新',
      'action.add': '新增',
      'action.edit': '编辑',
      'action.delete': '删除',
      'action.save': '保存',
      'action.cancel': '取消',
      'action.confirm': '确认',
      'action.export_csv': '导出 CSV',
      'theme.light': '极简明亮',
      'theme.dark': '精密暗黑',
      'theme.bento': '便当盒网格',
      'theme.glass': '毛玻璃拟态',
      'theme.editorial': '编辑杂志',
      'theme.cyan': '科幻 · 电光青',
      'theme.purple': '科幻 · 赛博紫',
      'theme.matrix': '科幻 · 矩阵绿',
      'common.all': '全部',
      'common.enabled': '启用',
      'common.disabled': '停用',
      'common.empty': '—',
      'common.prev': '上一页',
      'common.next': '下一页',
      'ui.split_v': '拖动调整宽度 / 双击复位',
      'ui.split_h': '拖动调整高度 / 双击复位',
      'ui.sidebar_resize': '拖动调整宽度 / 双击隐藏或展开',
      'ui.sidebar_hide': '隐藏左侧目录树',
      'ui.sidebar_show': '展开左侧目录树',
      'status.succeeded': '成功',
      'status.failed': '失败',
      'status.running': '运行中',
      'status.queued': '排队中',
      'msg.se_submitted': 'SE 计算已提交，正在刷新…',
      'msg.se_done': 'SE 计算完成',
      'devtype.ACNode': '交流节点',
      'devtype.DCNode': '直流节点',
      'devtype.ACGenerator': '交流机组',
      'devtype.DCGenerator': '直流机组',
      'devtype.ACLoad': '交流负荷',
      'devtype.DCLoad': '直流负荷',
      'devtype.ACBranch': '交流支路',
      'devtype.DCBranch': '直流支路',
      'devtype.ACZeroBranch': '交流零阻抗支路',
      'devtype.DCDCConverter': 'DC/DC 换流器',
      'devtype.DCACConverter': 'DC/AC 换流器',
      'devtype.ACBreak': '交流断路器',
      'devtype.DCBreak': '直流断路器',
      'devtype.ACPowerBalance': '交流功率平衡',
      'devtype.DCPowerBalance': '直流功率平衡',
    },
    'en-US': {
      'brand.sub': 'Online Analysis',
      'nav.overview': 'Overview',
      'nav.analysis': 'Analysis',
      'nav.se_root': 'State Estimation SE',
      'nav.se_main': 'Home',
      'nav.se_flow': 'Power Flow Map',
      'nav.se_curves': 'History Curves',
      'nav.se_devices': 'Device Compare',
      'nav.se_measurements': 'Valid Measurements',
      'nav.se_params': 'SE Parameters',
      'nav.se_prefilter': 'Prefilter Meas',
      'nav.se_pseudo': 'Pseudo Meas',
      'nav.se_bad': 'Bad Data',
      'nav.se_logs': 'Run Logs',
      'nav.se_detail': 'SE Details',
      'nav.lf': 'Load Flow LF',
      'nav.ca': 'Contingency CA',
      'nav.management': 'Management',
      'nav.runs': 'Run History',
      'nav.measurements': 'Measurements',
      'nav.limits': 'Limits',
      'nav.workspace': 'Workspace',
      'nav.settings': 'Settings',
      'service.checking': 'Checking…',
      'service.ok': 'Service Online',
      'service.degraded': 'Degraded',
      'action.run_se': 'Run SE Now',
      'action.refresh': 'Refresh',
      'action.add': 'Add',
      'action.edit': 'Edit',
      'action.delete': 'Delete',
      'action.save': 'Save',
      'action.cancel': 'Cancel',
      'action.confirm': 'Confirm',
      'action.export_csv': 'Export CSV',
      'theme.light': 'Minimalist Light',
      'theme.dark': 'Precision Dark',
      'theme.bento': 'Bento Grid',
      'theme.glass': 'Glassmorphism',
      'theme.editorial': 'Editorial',
      'theme.cyan': 'Sci-Fi Cyan',
      'theme.purple': 'Sci-Fi Purple',
      'theme.matrix': 'Sci-Fi Matrix',
      'common.all': 'All',
      'common.enabled': 'On',
      'common.disabled': 'Off',
      'common.empty': '—',
      'common.prev': 'Prev',
      'common.next': 'Next',
      'ui.split_v': 'Drag to resize / Double-click to reset',
      'ui.split_h': 'Drag to resize / Double-click to reset',
      'ui.sidebar_resize': 'Drag to resize / Double-click to toggle',
      'ui.sidebar_hide': 'Hide sidebar',
      'ui.sidebar_show': 'Show sidebar',
      'status.succeeded': 'Succeeded',
      'status.failed': 'Failed',
      'status.running': 'Running',
      'status.queued': 'Queued',
      'msg.se_submitted': 'SE job submitted, refreshing…',
      'msg.se_done': 'SE calculation finished',
      'devtype.ACNode': 'AC Bus',
      'devtype.DCNode': 'DC Bus',
      'devtype.ACGenerator': 'AC Gen',
      'devtype.DCGenerator': 'DC Gen',
      'devtype.ACLoad': 'AC Load',
      'devtype.DCLoad': 'DC Load',
      'devtype.ACBranch': 'AC Branch',
      'devtype.DCBranch': 'DC Branch',
      'devtype.ACZeroBranch': 'AC Zero-Z',
      'devtype.DCDCConverter': 'DC/DC Conv',
      'devtype.DCACConverter': 'DC/AC Conv',
      'devtype.ACBreak': 'AC Breaker',
      'devtype.DCBreak': 'DC Breaker',
      'devtype.ACPowerBalance': 'AC Balance',
      'devtype.DCPowerBalance': 'DC Balance',
    },
    'ru-RU': {
      'brand.sub': 'Онлайн-анализ',
      'nav.overview': 'Обзор',
      'nav.analysis': 'Анализ',
      'nav.se_root': 'Оценка сост. SE',
      'nav.se_main': 'Главная',
      'nav.se_flow': 'Схема потоков',
      'nav.se_curves': 'Графики истории',
      'nav.se_devices': 'Сравнение оборуд.',
      'nav.se_measurements': 'Достоверные изм.',
      'nav.se_params': 'Параметры SE',
      'nav.se_prefilter': 'Предфильтр',
      'nav.se_pseudo': 'Псевдоизмерения',
      'nav.se_bad': 'Плохие данные',
      'nav.se_logs': 'Журнал работы',
      'nav.se_detail': 'Детали SE',
      'nav.lf': 'Потоки LF',
      'nav.ca': 'Надёжность CA',
      'nav.management': 'Управление',
      'nav.runs': 'История',
      'nav.measurements': 'Измерения',
      'nav.limits': 'Пределы',
      'nav.workspace': 'Каталог',
      'nav.settings': 'Настройки',
      'service.checking': 'Проверка…',
      'service.ok': 'Сервис активен',
      'service.degraded': 'Ограничен',
      'action.run_se': 'Запуск SE',
      'action.refresh': 'Обновить',
      'action.add': 'Добавить',
      'action.edit': 'Изменить',
      'action.delete': 'Удалить',
      'action.save': 'Сохранить',
      'action.cancel': 'Отмена',
      'action.confirm': 'Подтвердить',
      'action.export_csv': 'Экспорт CSV',
      'theme.light': 'Светлая',
      'theme.dark': 'Тёмная',
      'theme.bento': 'Бенто-сетка',
      'theme.glass': 'Стекло',
      'theme.editorial': 'Журнальный',
      'theme.cyan': 'Кибер-циан',
      'theme.purple': 'Кибер-фиолет',
      'theme.matrix': 'Матрица',
      'common.all': 'Все',
      'common.enabled': 'Вкл',
      'common.disabled': 'Выкл',
      'common.empty': '—',
      'common.prev': 'Назад',
      'common.next': 'Далее',
      'ui.split_v': 'Перетащите ширину / Двойной клик для сброса',
      'ui.split_h': 'Перетащите высоту / Двойной клик для сброса',
      'ui.sidebar_resize': 'Перетащите ширину / Двойной клик скрыть',
      'ui.sidebar_hide': 'Скрыть меню',
      'ui.sidebar_show': 'Показать меню',
      'status.succeeded': 'Успешно',
      'status.failed': 'Ошибка',
      'status.running': 'Выполняется',
      'status.queued': 'В очереди',
      'msg.se_submitted': 'Расчёт SE запущен…',
      'msg.se_done': 'Расчёт SE завершён',
      'devtype.ACNode': 'Узел AC',
      'devtype.DCNode': 'Узел DC',
      'devtype.ACGenerator': 'Ген. AC',
      'devtype.DCGenerator': 'Ген. DC',
      'devtype.ACLoad': 'Нагр. AC',
      'devtype.DCLoad': 'Нагр. DC',
      'devtype.ACBranch': 'Ветвь AC',
      'devtype.DCBranch': 'Ветвь DC',
      'devtype.ACZeroBranch': 'Нул. ветвь AC',
      'devtype.DCDCConverter': 'DC/DC преобр.',
      'devtype.DCACConverter': 'DC/AC преобр.',
      'devtype.ACBreak': 'Выкл. AC',
      'devtype.DCBreak': 'Выкл. DC',
      'devtype.ACPowerBalance': 'Баланс AC',
      'devtype.DCPowerBalance': 'Баланс DC',
    },
  };

  const VALID_THEMES = [
    'minimalist-light',
    'precision-dark',
    'bento-grid',
    'glassmorphism',
    'editorial',
    'sci-fi-cyan',
    'sci-fi-purple',
    'sci-fi-matrix',
  ];

  function createSECommon(pageDict, onLangChange) {
    let lang = localStorage.getItem('pas_se_lang') || localStorage.getItem('se_lang') || 'zh-CN';
    if (!BASE_I18N[lang]) lang = 'zh-CN';
    let theme = localStorage.getItem('pas_se_theme') || localStorage.getItem('se_theme') || 'minimalist-light';
    if (!VALID_THEMES.includes(theme)) theme = 'minimalist-light';
    let noticeTimer = null;

    function t(key) {
      return (pageDict[lang] && pageDict[lang][key])
        || (BASE_I18N[lang] && BASE_I18N[lang][key])
        || (pageDict['zh-CN'] && pageDict['zh-CN'][key])
        || (BASE_I18N['zh-CN'] && BASE_I18N['zh-CN'][key])
        || key;
    }

    function devTypeLabel(dtype) {
      if (!dtype) return '—';
      const key = `devtype.${dtype}`;
      const val = t(key);
      return val === key ? dtype : val;
    }

    function applyTheme(next) {
      theme = VALID_THEMES.includes(next) ? next : 'minimalist-light';
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('pas_se_theme', theme);
      localStorage.setItem('se_theme', theme);
      const sel = document.getElementById('theme-select');
      if (sel) sel.value = theme;
    }

    function applyLang(next, triggerCallback = true) {
      lang = BASE_I18N[next] ? next : 'zh-CN';
      document.documentElement.setAttribute('lang', lang);
      localStorage.setItem('pas_se_lang', lang);
      localStorage.setItem('se_lang', lang);
      const sel = document.getElementById('lang-select');
      if (sel) sel.value = lang;
      document.querySelectorAll('[data-i18n]').forEach((el) => {
        el.textContent = t(el.dataset.i18n);
      });
      document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
        el.setAttribute('placeholder', t(el.dataset.i18nPlaceholder));
      });
      document.querySelectorAll('[data-i18n-title]').forEach((el) => {
        el.setAttribute('title', t(el.dataset.i18nTitle));
      });
      const resizer = document.querySelector('.sidebar-resizer');
      const toggleBtn = resizer?.querySelector('.sidebar-toggle-btn');
      if (resizer) resizer.title = t('ui.sidebar_resize');
      if (toggleBtn) {
        const isCol = resizer.classList.contains('is-collapsed');
        toggleBtn.title = t(isCol ? 'ui.sidebar_show' : 'ui.sidebar_hide');
        toggleBtn.setAttribute('aria-label', toggleBtn.title);
      }
      if (triggerCallback && typeof onLangChange === 'function') onLangChange(lang);
    }

    function esc(v) {
      return String(v ?? '').replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
      }[ch]));
    }

    function fmtNum(v, digits = 3) {
      if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
      return Number(v).toFixed(digits);
    }

    function fmtTime(iso) {
      if (!iso) return '—';
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return String(iso).slice(0, 19).replace('T', ' ');
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    }

    function debounce(fn, wait = 200) {
      let tid;
      return (...args) => {
        clearTimeout(tid);
        tid = setTimeout(() => fn(...args), wait);
      };
    }

    function notify(msg, isError = false) {
      const box = document.getElementById('notice');
      if (!box) return;
      box.textContent = msg;
      box.classList.toggle('error', Boolean(isError));
      box.hidden = false;
      clearTimeout(noticeTimer);
      noticeTimer = setTimeout(() => { box.hidden = true; }, isError ? 5200 : 3200);
    }

    async function api(url, options) {
      const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
      });
      const json = await res.json().catch(() => ({ ok: false, error: `HTTP ${res.status}` }));
      if (!res.ok || json.ok === false) {
        const msg = json.error || (json.data && json.data.error_message) || `HTTP ${res.status}`;
        throw new Error(msg);
      }
      return json.data;
    }

    async function refreshHealth() {
      try {
        const h = await api('/api/health?lite=1');
        const dot = document.getElementById('service-dot');
        const txt = document.getElementById('service-state');
        const ok = h && h.status === 'ok';
        if (dot) dot.style.background = ok ? '#2bc58e' : '#f59e0b';
        if (txt) txt.textContent = t(ok ? 'service.ok' : 'service.degraded');
      } catch (_) {
        const dot = document.getElementById('service-dot');
        if (dot) dot.style.background = '#dc2626';
      }
    }

    function openConfirm({ title, desc, okText, onConfirm }) {
      const dlg = document.getElementById('confirm-dialog');
      if (!dlg) return;
      document.getElementById('confirm-title').textContent = title;
      document.getElementById('confirm-desc').textContent = desc;
      const btnOk = document.getElementById('btn-confirm-ok');
      const btnCancel = document.getElementById('btn-confirm-cancel');
      btnOk.textContent = okText || t('action.confirm');
      const cleanup = () => {
        btnOk.onclick = null;
        btnCancel.onclick = null;
      };
      btnCancel.onclick = () => { cleanup(); dlg.close(); };
      btnOk.onclick = async () => {
        cleanup();
        dlg.close();
        if (typeof onConfirm === 'function') await onConfirm();
      };
      dlg.showModal();
      btnCancel.focus();
    }

    async function triggerRunSE(afterDone) {
      const btn = document.getElementById('btn-run-se');
      if (btn) btn.disabled = true;
      try {
        notify(t('msg.se_submitted'));
        await api('/api/actions/trigger', { method: 'POST', body: JSON.stringify({ task: 'se' }) });
        notify(t('msg.se_done'));
        if (typeof afterDone === 'function') await afterDone();
      } catch (err) {
        notify(err.message, true);
      } finally {
        if (btn) btn.disabled = false;
      }
    }

    function initShell({ onRefresh, afterRunSE } = {}) {
      if (typeof window.initSidebarSplitter === 'function') window.initSidebarSplitter();
      applyTheme(theme);
      applyLang(lang, false);
      const themeSel = document.getElementById('theme-select');
      const langSel = document.getElementById('lang-select');
      if (themeSel) themeSel.addEventListener('change', (e) => applyTheme(e.target.value));
      if (langSel) langSel.addEventListener('change', (e) => applyLang(e.target.value, true));
      const btnRun = document.getElementById('btn-run-se');
      if (btnRun) btnRun.addEventListener('click', () => triggerRunSE(afterRunSE || onRefresh));
      const btnRef = document.getElementById('btn-refresh');
      if (btnRef && typeof onRefresh === 'function') btnRef.addEventListener('click', () => onRefresh());
      refreshHealth();
    }

    return {
      t,
      getLang: () => lang,
      devTypeLabel,
      esc,
      fmtNum,
      fmtTime,
      debounce,
      notify,
      api,
      openConfirm,
      initShell,
      applyLang,
    };
  }

  /**
   * 为 .sidebar 与 .main 之间注入可拖拽分割条与一键隐藏目录树按钮（全站持久化）。
   */
  function initSidebarSplitter() {
    const shell = document.querySelector('.app-shell');
    const sidebar = shell?.querySelector('.sidebar');
    if (!shell || !sidebar || shell.querySelector('.sidebar-resizer')) return;

    const W_KEY = 'pas_sidebar_width';
    const C_KEY = 'pas_sidebar_collapsed';
    const MIN_W = 160;
    const MAX_W = 340;
    const COLLAPSE_THRESHOLD = 100;

    let savedWidth = Math.min(MAX_W, Math.max(MIN_W, Number(localStorage.getItem(W_KEY)) || 214));
    let collapsed = localStorage.getItem(C_KEY) === '1';

    const resizer = document.createElement('div');
    resizer.className = 'sidebar-resizer';
    resizer.setAttribute('role', 'separator');
    resizer.setAttribute('aria-orientation', 'vertical');
    resizer.title = '拖动调整宽度 / 双击隐藏或展开';

    const toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.className = 'sidebar-toggle-btn';
    resizer.appendChild(toggleBtn);
    sidebar.insertAdjacentElement('afterend', resizer);

    const emitResize = () => {
      window.dispatchEvent(new Event('resize'));
      setTimeout(() => window.dispatchEvent(new Event('resize')), 180);
    };

    const applyState = (notifyResize = false) => {
      sidebar.classList.toggle('is-collapsed', collapsed);
      resizer.classList.toggle('is-collapsed', collapsed);
      if (!collapsed) {
        sidebar.style.width = `${savedWidth}px`;
        sidebar.style.flexBasis = `${savedWidth}px`;
      }
      toggleBtn.textContent = collapsed ? '›' : '‹';
      toggleBtn.title = collapsed ? '展开左侧目录树' : '隐藏左侧目录树';
      toggleBtn.setAttribute('aria-label', toggleBtn.title);
      localStorage.setItem(C_KEY, collapsed ? '1' : '0');
      localStorage.setItem(W_KEY, String(Math.round(savedWidth)));
      if (notifyResize) emitResize();
    };

    toggleBtn.addEventListener('pointerdown', (e) => e.stopPropagation());
    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      collapsed = !collapsed;
      applyState(true);
    });

    resizer.addEventListener('dblclick', () => {
      collapsed = !collapsed;
      applyState(true);
    });

    let dragging = false;
    let moved = false;
    let startX = 0;

    resizer.addEventListener('pointerdown', (e) => {
      if (e.button !== 0 || e.target === toggleBtn) return;
      dragging = true;
      moved = false;
      startX = e.clientX;
      resizer.setPointerCapture(e.pointerId);
      sidebar.classList.add('is-resizing');
      resizer.classList.add('is-active');
      document.body.classList.add('sidebar-resizing');
    });

    resizer.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      if (Math.abs(e.clientX - startX) > 3) moved = true;
      const x = e.clientX;
      if (x < COLLAPSE_THRESHOLD) {
        collapsed = true;
        sidebar.classList.add('is-collapsed');
        resizer.classList.add('is-collapsed');
        toggleBtn.textContent = '›';
      } else {
        collapsed = false;
        savedWidth = Math.min(MAX_W, Math.max(MIN_W, x));
        sidebar.classList.remove('is-collapsed');
        resizer.classList.remove('is-collapsed');
        sidebar.style.width = `${savedWidth}px`;
        sidebar.style.flexBasis = `${savedWidth}px`;
        toggleBtn.textContent = '‹';
      }
    });

    const finishDrag = (e) => {
      if (!dragging) return;
      dragging = false;
      if (e && resizer.hasPointerCapture?.(e.pointerId)) {
        resizer.releasePointerCapture(e.pointerId);
      }
      sidebar.classList.remove('is-resizing');
      resizer.classList.remove('is-active');
      document.body.classList.remove('sidebar-resizing');
      if (!moved && collapsed) {
        // 折叠态单击窄边缘条即可快速展开
        collapsed = false;
      }
      applyState(true);
    };

    resizer.addEventListener('pointerup', finishDrag);
    resizer.addEventListener('pointercancel', finishDrag);

    applyState(false);
  }

  window.initSidebarSplitter = initSidebarSplitter;
  window.createSECommon = createSECommon;
})();
