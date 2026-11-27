/* 新版大屏可投放 EMS 状态估计主画面（量测清洗流水线 + 五维雷达 + 分类合格率 + 24h 双曲线 + 最大残差 Top） */
(() => {
  'use strict';

  const I18N = {
    'zh-CN': {
      'title.home': '状态估计 SE',
      'sec.meas_flow': '量测清洗与构成',
      'sec.health_radar': '估计质量画像',
      'sec.top_residuals': '最大残差 Top 测点',
      'sec.solve_metrics': '求解结果与运行指标',
      'sub.pipeline': '量测清洗流水线',
      'sub.donut': '量测健康构成',
      'sub.topology': '交直流拓扑规模',
      'sub.radar': 'SE 五维健康雷达',
      'sub.by_type': '分类型量测合格率',
      'sub.run_cfg': '当前基态与调度',
      'btn.start_calc': '执行 SE',
      'btn.pause_calc': '停周期',
      'btn.resume_calc': '启周期',
      'btn.open_flow': '潮流图 →',
      'r.cur_pass': '当前合格率',
      'r.today_avg': '今日平均',
      'r.yest_avg': '对比日平均',
      'r.conv_rate': '当日收敛率',
      'chart.mode_pass': '合格率对比',
      'chart.mode_bad': '坏数据趋势',
      'foot.run_info': '运行信息',
      'link.more': '更多…',
      'link.prefilter': '预过滤',
      'link.pseudo': '伪量测',
      'link.bad': '坏量测',
      'link.params': '参数…',
      'yes': '是',
      'no': '否',
      'conv.ok': '全网收敛',
      'conv.fail': '未收敛',
      'obs.ok': '全网可观测',
      'obs.lack': '缺秩 {n}',
      'lg.today': '今日合格率',
      'lg.yest': '对比日合格率',
      'lg.bad': '今日坏数据点数',
      'msg.daemon_on': '周期调度已启动',
      'msg.daemon_off': '周期调度已暂停',
      'action.auto_on': '自刷:开',
      'action.auto_off': '自刷:关',
      'chart.click_log': '点击查看日志',
      'chart.bad_cnt': '坏数据',
      'hero.pass_rate': '量测合格率',
      'hero.conv_rate': '当日收敛率',
      'hero.redundancy': '量测冗余度',
      'hero.bad_pf': '坏数据 / 预过滤',
      'hero.solve': '求解耗时 / 迭代',
      'pipe.total': '采集量测总数',
      'pipe.prefilter': '预过滤拦截',
      'pipe.valid': '有效 + 伪量测',
      'pipe.bad': '坏数据辨识',
      'pipe.good': '合格估计量测',
      'donut.good': '正常有效',
      'donut.pf': '预过滤',
      'donut.bad': '坏数据',
      'donut.miss': '缺测/坏质量',
      'donut.center': '量测总数',
      'radar.pass': '合格率',
      'radar.conv': '收敛率',
      'radar.cov': '覆盖率',
      'radar.obs': '可观测',
      'radar.red': '冗余度',
      'cat.U': '电压 U',
      'cat.P': '有功 P',
      'cat.Q': '无功 Q',
      'cat.I': '电流 I',
      'cat.OTHER': '其他',
      'topo.bus': '母线 (交/直)',
      'topo.branch': '交直流支路',
      'topo.conv': '换流器',
      'topo.dev': '建模设备总数',
      'cfg.cycle': '周期调度',
      'cfg.flat': '平启动',
      'cfg.tol': '收敛容差',
      'solve.obj': '目标函数 J(x)',
      'solve.res': '总残差 / 最大',
      'solve.runs': '当日收敛 / 运行',
      'solve.host': '运行主机',
      'empty.res': '暂无高残差测点',
    },
    'en-US': {
      'title.home': 'State Estimation Console',
      'sec.meas_flow': 'Measurement Pipeline',
      'sec.health_radar': 'Quality Profile',
      'sec.top_residuals': 'Top Residual Points',
      'sec.solve_metrics': 'Solver & Daily KPIs',
      'sub.pipeline': 'Cleaning Pipeline',
      'sub.donut': 'Health Breakdown',
      'sub.topology': 'AC/DC Grid Scale',
      'sub.radar': '5D Health Radar',
      'sub.by_type': 'Pass Rate by Type',
      'sub.run_cfg': 'Runtime & Cycle',
      'btn.start_calc': 'Run SE',
      'btn.pause_calc': 'Pause Cycle',
      'btn.resume_calc': 'Start Cycle',
      'btn.open_flow': 'Flow Map →',
      'r.cur_pass': 'Current',
      'r.today_avg': 'Today Avg',
      'r.yest_avg': 'Compare Avg',
      'r.conv_rate': 'Conv Rate',
      'chart.mode_pass': 'Pass Rate',
      'chart.mode_bad': 'Bad Data',
      'foot.run_info': 'Run Log',
      'link.more': 'More…',
      'link.prefilter': 'Prefilter',
      'link.pseudo': 'Pseudo',
      'link.bad': 'Bad',
      'link.params': 'Params…',
      'yes': 'On',
      'no': 'Off',
      'conv.ok': 'Converged',
      'conv.fail': 'Diverged',
      'obs.ok': 'Observable',
      'obs.lack': 'Deficit {n}',
      'lg.today': 'Today Pass Rate',
      'lg.yest': 'Compare Pass Rate',
      'lg.bad': 'Today Bad Data',
      'msg.daemon_on': 'Periodic scheduler started',
      'msg.daemon_off': 'Periodic scheduler paused',
      'action.auto_on': 'Auto: On',
      'action.auto_off': 'Auto: Off',
      'chart.click_log': 'Click to open log',
      'chart.bad_cnt': 'Bad',
      'hero.pass_rate': 'Pass Rate',
      'hero.conv_rate': 'Daily Conv Rate',
      'hero.redundancy': 'Redundancy',
      'hero.bad_pf': 'Bad / Prefiltered',
      'hero.solve': 'Solve Time / Iter',
      'pipe.total': 'Raw Telemetry',
      'pipe.prefilter': 'Prefiltered',
      'pipe.valid': 'Valid + Pseudo',
      'pipe.bad': 'Bad Detected',
      'pipe.good': 'Qualified Est.',
      'donut.good': 'Qualified',
      'donut.pf': 'Prefiltered',
      'donut.bad': 'Bad Data',
      'donut.miss': 'Missing/BadQ',
      'donut.center': 'Total',
      'radar.pass': 'Pass',
      'radar.conv': 'Conv',
      'radar.cov': 'Cover',
      'radar.obs': 'Observ',
      'radar.red': 'Redund',
      'cat.U': 'Voltage U',
      'cat.P': 'Active P',
      'cat.Q': 'Reactive Q',
      'cat.I': 'Current I',
      'cat.OTHER': 'Other',
      'topo.bus': 'Buses (AC/DC)',
      'topo.branch': 'Branches',
      'topo.conv': 'Converters',
      'topo.dev': 'Total Devices',
      'cfg.cycle': 'Cycle',
      'cfg.flat': 'Flat Start',
      'cfg.tol': 'Tolerance',
      'solve.obj': 'Objective J(x)',
      'solve.res': 'Total / Max Res',
      'solve.runs': 'Conv / Runs',
      'solve.host': 'Host',
      'empty.res': 'No high-residual points',
    },
    'ru-RU': {
      'title.home': 'Пульт оценки состояния SE',
      'sec.meas_flow': 'Поток измерений',
      'sec.health_radar': 'Профиль качества',
      'sec.top_residuals': 'Топ невязок ТИ',
      'sec.solve_metrics': 'Решатель и итоги дня',
      'sub.pipeline': 'Конвейер очистки ТИ',
      'sub.donut': 'Состав измерений',
      'sub.topology': 'Масштаб AC/DC сети',
      'sub.radar': 'Радар качества SE',
      'sub.by_type': 'Годность по типам',
      'sub.run_cfg': 'Режим и цикл',
      'btn.start_calc': 'Запуск SE',
      'btn.pause_calc': 'Пауза',
      'btn.resume_calc': 'Старт',
      'btn.open_flow': 'Схема →',
      'r.cur_pass': 'Текущ.',
      'r.today_avg': 'Сегодня',
      'r.yest_avg': 'Вчера',
      'r.conv_rate': 'Сходимость',
      'chart.mode_pass': 'Годность %',
      'chart.mode_bad': 'Плохие ТИ',
      'foot.run_info': 'Журнал',
      'link.more': 'Далее…',
      'link.prefilter': 'Фильтр',
      'link.pseudo': 'Псевдо',
      'link.bad': 'Сбои',
      'link.params': 'Парам…',
      'yes': 'Да',
      'no': 'Нет',
      'conv.ok': 'Сходится',
      'conv.fail': 'Расходится',
      'obs.ok': 'Наблюдаема',
      'obs.lack': 'Дефицит {n}',
      'lg.today': 'Сегодня',
      'lg.yest': 'Сравнение',
      'lg.bad': 'Плохие ТИ сегодня',
      'msg.daemon_on': 'Цикл запущен',
      'msg.daemon_off': 'Цикл остановлен',
      'action.auto_on': 'Авто: Вкл',
      'action.auto_off': 'Авто: Выкл',
      'chart.click_log': 'Клик — журнал',
      'chart.bad_cnt': 'Сбои',
      'hero.pass_rate': 'Доля годных ТИ',
      'hero.conv_rate': 'Сходимость дня',
      'hero.redundancy': 'Избыточность',
      'hero.bad_pf': 'Сбои / Фильтр',
      'hero.solve': 'Время / Итерац.',
      'pipe.total': 'Всего ТИ',
      'pipe.prefilter': 'Отфильтровано',
      'pipe.valid': 'Валид. + Псевдо',
      'pipe.bad': 'Выявлено сбоев',
      'pipe.good': 'Годных оценок',
      'donut.good': 'Годные',
      'donut.pf': 'Фильтр',
      'donut.bad': 'Плохие',
      'donut.miss': 'Пропуск',
      'donut.center': 'Всего',
      'radar.pass': 'Годн.',
      'radar.conv': 'Сход.',
      'radar.cov': 'Охват',
      'radar.obs': 'Набл.',
      'radar.red': 'Избыт.',
      'cat.U': 'Напр. U',
      'cat.P': 'Актив. P',
      'cat.Q': 'Реакт. Q',
      'cat.I': 'Ток I',
      'cat.OTHER': 'Прочее',
      'topo.bus': 'Узлы AC/DC',
      'topo.branch': 'Ветви',
      'topo.conv': 'Преобр.',
      'topo.dev': 'Оборуд.',
      'cfg.cycle': 'Цикл',
      'cfg.flat': 'Плоск. старт',
      'cfg.tol': 'Точность',
      'solve.obj': 'Цель J(x)',
      'solve.res': 'Сумм./Макс.',
      'solve.runs': 'Сход./Зап.',
      'solve.host': 'Сервер',
      'empty.res': 'Нет крупных невязок',
    },
  };

  let homeData = null;
  let chartMode = 'pass';

  const common = window.createSECommon(I18N, () => {
    if (homeData) renderHome(homeData);
  });
  const { t, esc, fmtNum, fmtTime, api, notify } = common;

  function renderHeroStrip(d) {
    const host = document.getElementById('se-hero-strip');
    if (!host) return;
    const latest = d.latest;
    const obs = d.observability || {};
    const pf = d.prefilter || {};
    const ctrl = d.control || {};
    const ts = d.today_stats || {};

    const passRate = ts.current_pass_rate != null ? Number(ts.current_pass_rate) : null;
    const deltaPass = (passRate != null && ts.yesterday_avg_pass_rate != null)
      ? (passRate - Number(ts.yesterday_avg_pass_rate))
      : null;
    const deltaBadge = deltaPass != null
      ? `${deltaPass >= 0 ? '▲ +' : '▼ '}${deltaPass.toFixed(2)}%`
      : (ts.today_avg_pass_rate != null ? `均 ${Number(ts.today_avg_pass_rate).toFixed(1)}%` : '—');
    const passTone = passRate == null ? 'accent' : (passRate >= 95 ? 'ok' : (passRate >= 85 ? 'warn' : 'bad'));

    const convRate = Number(ts.today_conv_rate || 0);
    const convTone = convRate >= 95 ? 'ok' : (convRate >= 80 ? 'warn' : 'bad');

    const red = obs.redundancy != null ? Number(obs.redundancy) : null;
    const defCnt = Number(obs.deficiency || 0);
    const obsPct = obs.state_count > 0 ? Math.min(100, (Number(obs.rank || 0) / Number(obs.state_count)) * 100) : (obs.observable ? 100 : 0);
    const obsTone = defCnt > 0 ? 'bad' : (red != null && red < 1.2 ? 'warn' : 'ok');

    const badCnt = Number(latest?.bad_data_count ?? ctrl.bad_total ?? 0);
    const pfCnt = Number(pf.total ?? 0);
    const badTone = badCnt > 0 ? 'bad' : (pfCnt > 0 ? 'warn' : 'ok');

    const elapsed = latest?.elapsed_seconds != null ? Number(latest.elapsed_seconds) : null;
    const iters = latest?.iterations ?? 0;

    const tiles = [
      {
        tone: passTone,
        label: t('hero.pass_rate'),
        badge: deltaBadge,
        badgeCls: deltaPass == null ? 'accent' : (deltaPass >= 0 ? 'ok' : 'warn'),
        val: passRate != null ? `${passRate.toFixed(2)}<small>%</small>` : '—',
        valCls: passTone === 'accent' ? '' : passTone,
        sub: `${obs.good_meas_count ?? 0} / ${obs.valid_meas_count ?? 0}`,
        meter: passRate ?? 0,
      },
      {
        tone: convTone,
        label: t('hero.conv_rate'),
        badge: `${ts.today_converged ?? 0} / ${ts.today_runs ?? 0}`,
        badgeCls: convTone,
        val: `${convRate.toFixed(1)}<small>%</small>`,
        valCls: convTone,
        sub: latest ? (latest.converged ? t('conv.ok') : t('conv.fail')) : '—',
        meter: convRate,
      },
      {
        tone: obsTone,
        label: t('hero.redundancy'),
        badge: defCnt > 0 ? t('obs.lack', { n: defCnt }) : t('obs.ok'),
        badgeCls: defCnt > 0 ? 'bad' : 'ok',
        val: red != null ? `${red.toFixed(2)}<small>×</small>` : '—',
        valCls: defCnt > 0 ? 'bad' : '',
        sub: `R ${obs.rank ?? 0} / S ${obs.state_count ?? 0}`,
        meter: obsPct,
      },
      {
        tone: badTone,
        label: t('hero.bad_pf'),
        badge: `${Number(pf.prefilter_rate || 0).toFixed(1)}% PF`,
        badgeCls: pfCnt > 0 ? 'warn' : 'ok',
        val: `${badCnt}<small> / ${pfCnt}</small>`,
        valCls: badCnt > 0 ? 'bad' : 'ok',
        sub: `未确认 ${ctrl.bad_unacked ?? 0} · 缺测 ${pf.nomeas_count ?? 0}`,
        meter: Math.min(100, (obs.meas_count > 0 ? ((badCnt + pfCnt) / obs.meas_count) * 100 : 0) * 4),
      },
      {
        tone: 'accent',
        label: t('hero.solve'),
        badge: `${iters} iter`,
        badgeCls: 'accent',
        val: elapsed != null ? `${elapsed.toFixed(3)}<small>s</small>` : '—',
        valCls: '',
        sub: latest ? `J(x) ${fmtNum(latest.objective, 3)}` : '—',
        meter: elapsed != null ? Math.min(100, Math.max(8, (1 - Math.min(elapsed, 5) / 5) * 100)) : 0,
      },
    ];

    host.innerHTML = tiles.map((c) => `
      <div class="pas-hero-tile tone-${c.tone}">
        <div class="pas-hero-top">
          <span class="pas-hero-lbl">${esc(c.label)}</span>
          <span class="pas-hero-badge tabular ${c.badgeCls}">${esc(c.badge)}</span>
        </div>
        <div class="pas-hero-val-row">
          <div class="pas-hero-val tabular ${c.valCls}">${c.val}</div>
          <span class="pas-hero-sub tabular">${esc(c.sub)}</span>
        </div>
        <div class="pas-hero-meter"><i style="width:${Math.max(0, Math.min(100, c.meter)).toFixed(1)}%"></i></div>
      </div>`).join('');
  }

  function renderMainChart(seriesObj) {
    const host = document.getElementById('home-pass-chart');
    const legend = document.getElementById('home-pass-legend');
    const today = seriesObj?.today || [];
    const yest = seriesObj?.yesterday || [];

    if (chartMode === 'bad') {
      legend.innerHTML = `<span><i style="background:var(--sem-warn)"></i>${esc(t('lg.bad'))} (${esc(seriesObj?.today_date || '')})</span>`;
      if (!today.length) {
        host.innerHTML = `<div class="se-empty">—</div>`;
        return;
      }
      const w = Math.max(420, host.clientWidth || 620);
      const h = Math.max(170, host.clientHeight || 220);
      const pad = { top: 14, right: 20, bottom: 24, left: 42 };
      const plotW = w - pad.left - pad.right;
      const plotH = h - pad.top - pad.bottom;
      const maxBad = Math.max(4, ...today.map((p) => Number(p.bad_data_count || 0)));
      const xOf = (minOfDay) => pad.left + (Math.max(0, Math.min(1440, minOfDay)) / 1440) * plotW;
      const yOf = (val) => pad.top + plotH - (val / maxBad) * plotH;
      const yTicks = [0, 0.5, 1].map((r) => maxBad * r);
      const xHours = [0, 3, 6, 9, 12, 15, 18, 21, 24];
      const barW = Math.max(4, Math.min(14, plotW / Math.max(today.length * 1.8, 20)));

      host.innerHTML = `
        <svg viewBox="0 0 ${w} ${h}" width="100%" height="100%" preserveAspectRatio="none">
          <rect x="${pad.left}" y="${pad.top}" width="${plotW}" height="${plotH}" fill="var(--bg-subtle)" opacity="0.35"/>
          ${yTicks.map((v) => {
            const y = yOf(v);
            return `<line x1="${pad.left}" y1="${y.toFixed(1)}" x2="${w - pad.right}" y2="${y.toFixed(1)}" stroke="var(--grid-line)" stroke-dasharray="2 3"/>
                    <text x="${pad.left - 6}" y="${(y + 3.5).toFixed(1)}" text-anchor="end" fill="var(--text-secondary)" font-size="10.5" class="tabular">${Math.round(v)}</text>`;
          }).join('')}
          ${xHours.map((hr) => {
            const x = xOf(hr * 60);
            return `<line x1="${x.toFixed(1)}" y1="${pad.top}" x2="${x.toFixed(1)}" y2="${pad.top + plotH}" stroke="var(--grid-line)" stroke-dasharray="2 3"/>
                    <text x="${x.toFixed(1)}" y="${h - 6}" text-anchor="${hr === 0 ? 'start' : hr === 24 ? 'end' : 'middle'}" fill="var(--text-secondary)" font-size="10" class="tabular">${String(hr).padStart(2, '0')}:00</text>`;
          }).join('')}
          ${today.map((p) => {
            const v = Number(p.bad_data_count || 0);
            const x = xOf(p.minute) - barW / 2;
            const bh = Math.max(v > 0 ? 3 : 1, (v / maxBad) * plotH);
            const y = pad.top + plotH - bh;
            const fill = v > 0 ? 'var(--sem-danger)' : 'var(--sem-ok)';
            return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="${fill}" opacity="${v > 0 ? '0.88' : '0.35'}"/>`;
          }).join('')}
          <line id="home-crosshair" x1="0" y1="${pad.top}" x2="0" y2="${pad.top + plotH}" stroke="var(--accent)" stroke-width="1" stroke-dasharray="3 3" visibility="hidden"/>
          <rect id="home-chart-overlay" x="${pad.left}" y="${pad.top}" width="${plotW}" height="${plotH}" fill="transparent" style="cursor:crosshair"/>
        </svg>
        <div class="se-chart-tip" id="home-chart-tip" hidden></div>`;

      bindChartHover(host, today.map((p) => ({ ...p, series: 'today', date: seriesObj.today_date })), xOf, (p) => yOf(Number(p.bad_data_count || 0)), false);
      return;
    }

    legend.innerHTML = `
      <span><i style="background:var(--accent)"></i>${esc(t('lg.today'))} (${esc(seriesObj?.today_date || '')})</span>
      <span><i style="background:var(--text-secondary)"></i>${esc(t('lg.yest'))} (${esc(seriesObj?.compare_date || '')})</span>`;

    if (!today.length && !yest.length) {
      host.innerHTML = `<div class="se-empty">—</div>`;
      return;
    }

    const w = Math.max(420, host.clientWidth || 620);
    const h = Math.max(170, host.clientHeight || 220);
    const pad = { top: 14, right: 20, bottom: 24, left: 46 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const allVals = [...today, ...yest].map((p) => Number(p.pass_rate));
    let minY = Math.min(...allVals);
    let maxY = Math.max(...allVals);
    if (maxY - minY < 1.0) {
      minY = Math.max(0, Math.floor((minY - 1.5) * 10) / 10);
      maxY = Math.min(100, Math.ceil((maxY + 0.5) * 10) / 10);
      if (maxY <= minY) { minY = 95; maxY = 100; }
    } else {
      minY = Math.max(0, Math.floor(minY - 0.5));
      maxY = Math.min(100, Math.ceil(maxY + 0.5));
    }

    const xOf = (minOfDay) => pad.left + (Math.max(0, Math.min(1440, minOfDay)) / 1440) * plotW;
    const yOf = (val) => pad.top + plotH - ((val - minY) / (maxY - minY || 1)) * plotH;

    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((r) => minY + (maxY - minY) * r);
    const xHours = plotW < 460
      ? [0, 4, 8, 12, 16, 20, 24]
      : (plotW < 620 ? [0, 3, 6, 9, 12, 15, 18, 21, 24] : [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]);
    const polyStr = (arr) => arr.map((p) => `${xOf(p.minute).toFixed(1)},${yOf(p.pass_rate).toFixed(1)}`).join(' ');
    const todayArea = today.length > 1
      ? `${xOf(today[0].minute).toFixed(1)},${(pad.top + plotH).toFixed(1)} ${polyStr(today)} ${xOf(today[today.length - 1].minute).toFixed(1)},${(pad.top + plotH).toFixed(1)}`
      : '';

    host.innerHTML = `
      <svg viewBox="0 0 ${w} ${h}" width="100%" height="100%" preserveAspectRatio="none">
        <defs>
          <linearGradient id="sePassGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.26"/>
            <stop offset="100%" stop-color="var(--accent)" stop-opacity="0.01"/>
          </linearGradient>
        </defs>
        <rect x="${pad.left}" y="${pad.top}" width="${plotW}" height="${plotH}" fill="var(--bg-subtle)" opacity="0.35"/>
        ${yTicks.map((v) => {
          const y = yOf(v);
          return `<line x1="${pad.left}" y1="${y.toFixed(1)}" x2="${w - pad.right}" y2="${y.toFixed(1)}" stroke="var(--grid-line)" stroke-dasharray="2 3"/>
                  <text x="${pad.left - 6}" y="${(y + 3.5).toFixed(1)}" text-anchor="end" fill="var(--text-secondary)" font-size="10.5" class="tabular">${v.toFixed(1)}%</text>`;
        }).join('')}
        ${xHours.map((hr) => {
          const x = xOf(hr * 60);
          return `<line x1="${x.toFixed(1)}" y1="${pad.top}" x2="${x.toFixed(1)}" y2="${pad.top + plotH}" stroke="var(--grid-line)" stroke-dasharray="2 3"/>
                  <text x="${x.toFixed(1)}" y="${h - 6}" text-anchor="${hr === 0 ? 'start' : hr === 24 ? 'end' : 'middle'}" fill="var(--text-secondary)" font-size="10" class="tabular">${String(hr).padStart(2, '0')}:00</text>`;
        }).join('')}
        ${yest.length > 1 ? `<polyline fill="none" stroke="var(--text-secondary)" stroke-width="1.5" stroke-dasharray="4 3" opacity="0.75" points="${polyStr(yest)}"/>` : ''}
        ${todayArea ? `<polygon points="${todayArea}" fill="url(#sePassGrad)"/>` : ''}
        ${today.length > 1 ? `<polyline fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linejoin="round" points="${polyStr(today)}"/>` : ''}
        ${today.length <= 60 ? today.map((p) => `<circle cx="${xOf(p.minute).toFixed(1)}" cy="${yOf(p.pass_rate).toFixed(1)}" r="2.7" fill="var(--accent)"/>`).join('') : ''}
        <line id="home-crosshair" x1="0" y1="${pad.top}" x2="0" y2="${pad.top + plotH}" stroke="var(--accent)" stroke-width="1" stroke-dasharray="3 3" visibility="hidden"/>
        <circle id="home-hover-dot" cx="0" cy="0" r="4.5" fill="var(--accent)" stroke="var(--bg-surface)" stroke-width="1.6" visibility="hidden"/>
        <rect id="home-chart-overlay" x="${pad.left}" y="${pad.top}" width="${plotW}" height="${plotH}" fill="transparent" style="cursor:crosshair"/>
      </svg>
      <div class="se-chart-tip" id="home-chart-tip" hidden></div>`;

    const allPts = [
      ...today.map((p) => ({ ...p, series: 'today', date: seriesObj.today_date })),
      ...yest.map((p) => ({ ...p, series: 'yest', date: seriesObj.compare_date })),
    ];
    bindChartHover(host, allPts, xOf, (p) => yOf(p.pass_rate), true);
  }

  function bindChartHover(host, allPts, xOf, yOfFn, hasDot) {
    const overlay = document.getElementById('home-chart-overlay');
    const cross = document.getElementById('home-crosshair');
    const dot = document.getElementById('home-hover-dot');
    const tip = document.getElementById('home-chart-tip');
    if (!overlay || !cross || !tip) return;
    let nearestPt = null;

    overlay.addEventListener('mousemove', (e) => {
      const rect = overlay.getBoundingClientRect();
      const relX = Math.max(0, Math.min(1, (e.clientX - rect.left) / (rect.width || 1)));
      const targetMin = relX * 1440;
      let best = null;
      let bestDist = Infinity;
      for (const p of allPts) {
        const d = Math.abs(p.minute - targetMin);
        if (d < bestDist) { bestDist = d; best = p; }
      }
      nearestPt = best;
      if (!best) return;
      const sx = xOf(best.minute);
      cross.setAttribute('x1', sx.toFixed(1));
      cross.setAttribute('x2', sx.toFixed(1));
      cross.setAttribute('visibility', 'visible');
      if (hasDot && dot) {
        dot.setAttribute('cx', sx.toFixed(1));
        dot.setAttribute('cy', yOfFn(best).toFixed(1));
        dot.setAttribute('visibility', 'visible');
      }
      const hostRect = host.getBoundingClientRect();
      const leftPx = Math.min(hostRect.width - 175, Math.max(8, e.clientX - hostRect.left + 12));
      const topPx = Math.max(6, Math.min(hostRect.height - 72, e.clientY - hostRect.top - 12));
      tip.style.left = `${leftPx}px`;
      tip.style.top = `${topPx}px`;
      tip.innerHTML = `
        <div class="tip-hd tabular">${esc(best.date)} ${esc(best.time_hm)} · #${best.run_id}</div>
        <div class="tip-row"><span>${esc(best.series === 'today' ? t('lg.today') : t('lg.yest'))}</span><strong class="tabular">${Number(best.pass_rate).toFixed(2)}%</strong></div>
        <div class="tip-row"><span>${esc(t('chart.bad_cnt'))}</span><strong class="tabular">${best.bad_data_count}</strong></div>
        <div class="tip-sub">${esc(t('chart.click_log'))}</div>`;
      tip.hidden = false;
    });

    overlay.addEventListener('mouseleave', () => {
      cross.setAttribute('visibility', 'hidden');
      if (dot) dot.setAttribute('visibility', 'hidden');
      tip.hidden = true;
      nearestPt = null;
    });

    overlay.addEventListener('click', () => {
      if (nearestPt && nearestPt.run_id) {
        window.location.href = `/se-logs.html?run_id=${encodeURIComponent(nearestPt.run_id)}`;
      }
    });
  }

  function renderHome(d) {
    homeData = d;
    const latest = d.latest;
    const obs = d.observability || {};
    const pf = d.prefilter || {};
    const ctrl = d.control || {};
    const params = d.params || {};
    const sched = d.schedule || {};
    const ts = d.today_stats || {};
    const rt = d.runtime || {};

    // 顶栏状态与按钮
    const convPill = document.getElementById('home-conv-pill');
    if (latest) {
      const ok = Boolean(latest.converged);
      convPill.className = `se-pill ${ok ? 'ok' : 'bad'}`;
      convPill.textContent = ok ? t('conv.ok') : t('conv.fail');
      document.getElementById('home-run-meta').textContent = `SE #${latest.run_id} · ${fmtTime(latest.calc_time)}`;
    } else {
      convPill.className = 'se-pill neutral';
      convPill.textContent = '—';
      document.getElementById('home-run-meta').textContent = '—';
    }

    const sePeriodicOn = Boolean(sched.enabled);
    const btnToggle = document.getElementById('btn-home-toggle-daemon');
    if (btnToggle) {
      btnToggle.dataset.running = sePeriodicOn ? '1' : '0';
      btnToggle.classList.toggle('active', sePeriodicOn);
      btnToggle.textContent = sePeriodicOn ? t('btn.pause_calc') : t('btn.resume_calc');
    }

    // 顶部大屏英雄指标带
    renderHeroStrip(d);

    // 左栏 1：量测清洗动态流水线
    const totalMeas = Number(obs.meas_count || 0);
    const pfCnt = Number(pf.total || 0);
    const validCnt = Number(obs.valid_meas_count || 0);
    const pseudoEff = Number(ctrl.pseudo_result_total || 0);
    const badCnt = Number(latest?.bad_data_count ?? ctrl.bad_total ?? 0);
    const goodCnt = Number(obs.good_meas_count ?? Math.max(0, validCnt - badCnt));
    const missCnt = Number(pf.nomeas_count || 0);
    const denom = Math.max(1, totalMeas);

    const pipeMeta = document.getElementById('se-pipe-meta');
    if (pipeMeta) pipeMeta.textContent = `${totalMeas} → ${goodCnt}`;
    if (window.PAS_KIT?.renderPipelineFlow) {
      window.PAS_KIT.renderPipelineFlow(document.getElementById('se-meas-pipeline'), {
        steps: [
          {
            label: t('pipe.total'),
            value: totalMeas,
            pct: 100,
            tone: 'accent',
            href: '/se-measurements.html',
            tip: `${t('pipe.total')}: <strong>${totalMeas}</strong> (缺测/坏质 ${missCnt})`,
          },
          {
            label: t('pipe.prefilter'),
            value: pfCnt,
            display: `${pfCnt} (${Number(pf.prefilter_rate || 0).toFixed(1)}%)`,
            pct: Math.min(100, (pfCnt / denom) * 100),
            tone: pfCnt > 0 ? 'warn' : 'ok',
            href: '/se-prefilter.html',
            tip: `规则命中 ${pf.by_rule ?? 0} · 内核过滤 ${pf.by_kernel ?? 0} · 规则 ${pf.rule_enabled ?? 0}/${pf.rule_total ?? 0}`,
          },
          {
            label: t('pipe.valid'),
            value: validCnt,
            display: `${validCnt}${pseudoEff > 0 ? ` (+${pseudoEff})` : ''}`,
            pct: Math.min(100, (validCnt / denom) * 100),
            tone: 'accent',
            href: '/se-pseudo.html',
            tip: `有效量测 ${validCnt} · 定向伪量测生效 ${pseudoEff} · 遥测屏蔽 ${ctrl.policy_enabled ?? 0}/${ctrl.policy_total ?? 0}`,
          },
          {
            label: t('pipe.bad'),
            value: badCnt,
            display: `${badCnt} (未确 ${ctrl.bad_unacked ?? 0})`,
            pct: Math.min(100, (badCnt / denom) * 100),
            tone: badCnt > 0 ? 'bad' : 'ok',
            href: '/se-bad.html',
            tip: `坏量测 ${badCnt} · 未确认 ${ctrl.bad_unacked ?? 0} · 可疑遥信 ${pf.suspect_count ?? 0}`,
          },
          {
            label: t('pipe.good'),
            value: goodCnt,
            display: `${goodCnt} (${Number(ts.current_pass_rate || 0).toFixed(1)}%)`,
            pct: Math.min(100, (goodCnt / denom) * 100),
            tone: 'ok',
            href: '/se-measurements.html?sub=balance',
            tip: `合格量测 ${goodCnt} / 有效 ${validCnt}`,
          },
        ],
      });
    }

    // 左栏 2：量测健康构成环形图
    if (window.PAS_KIT?.renderDonut) {
      window.PAS_KIT.renderDonut(document.getElementById('se-home-meas-donut'), {
        slices: [
          { label: t('donut.good'), value: goodCnt, color: '#22c55e' },
          { label: t('donut.pf'), value: pfCnt, color: '#f59e0b' },
          { label: t('donut.bad'), value: badCnt, color: '#ef4444' },
          { label: t('donut.miss'), value: missCnt, color: '#64748b' },
        ],
        centerTitle: t('donut.center'),
        centerValue: String(totalMeas || (goodCnt + pfCnt + badCnt + missCnt)),
        size: 100,
      });
    }

    // 左栏 3：交直流拓扑规模胶囊
    const topoHost = document.getElementById('se-topo-chips');
    if (topoHost) {
      const busTxt = obs.ac_bus_count != null && obs.dc_bus_count != null
        ? `${obs.bus_count ?? 0} (${obs.ac_bus_count}/${obs.dc_bus_count})`
        : String(obs.bus_count ?? 0);
      topoHost.innerHTML = [
        [t('topo.bus'), busTxt],
        [t('topo.branch'), String(ctrl.branch_count ?? 0)],
        [t('topo.conv'), String(ctrl.converter_count ?? 0)],
        [t('topo.dev'), String(ctrl.total_devices ?? 0)],
      ].map(([k, v]) => `<div class="pas-stat-chip"><span>${esc(k)}</span><strong class="tabular">${esc(v)}</strong></div>`).join('');
    }

    // 中栏 1：SE 五维质量雷达图
    const obsBadge = document.getElementById('se-obs-badge');
    const defCnt = Number(obs.deficiency || 0);
    if (obsBadge) {
      obsBadge.textContent = defCnt > 0 ? t('obs.lack', { n: defCnt }) : t('obs.ok');
      obsBadge.className = `se-pill tabular ${defCnt > 0 ? 'bad' : 'ok'}`;
    }
    const covVal = totalMeas > 0 ? (validCnt / totalMeas) * 100 : 0;
    const obsScore = obs.state_count > 0 ? Math.min(100, (Number(obs.rank || 0) / Number(obs.state_count)) * 100) : (obs.observable ? 100 : 0);
    const redScore = obs.redundancy != null ? Math.min(100, (Number(obs.redundancy) / 2.5) * 100) : 0;
    if (window.PAS_KIT?.renderRadarChart) {
      window.PAS_KIT.renderRadarChart(document.getElementById('se-health-radar'), {
        size: 162,
        axes: [
          { label: t('radar.pass'), value: Number(ts.current_pass_rate || 0), max: 100, unit: '%' },
          { label: t('radar.conv'), value: Number(ts.today_conv_rate || 0), max: 100, unit: '%' },
          { label: t('radar.cov'), value: covVal, max: 100, unit: '%' },
          { label: t('radar.obs'), value: obsScore, max: 100, unit: '%', sub: `R=${obs.rank ?? 0} / S=${obs.state_count ?? 0}` },
          { label: t('radar.red'), value: redScore, max: 100, unit: 'pt', sub: `${Number(obs.redundancy || 0).toFixed(2)}×` },
        ],
      });
    }

    // 中栏 2：分类型量测合格率柱图
    const byType = d.meas_by_type || [];
    const typeMeta = document.getElementById('se-type-meta');
    if (typeMeta) typeMeta.textContent = byType.length ? `${byType.length} 类` : '—';
    if (window.PAS_KIT?.renderBarChart) {
      const catColor = { U: '#38bdf8', P: '#22c55e', Q: '#a855f7', I: '#f59e0b', OTHER: '#64748b' };
      const items = byType.length
        ? byType.map((c) => ({
          label: t(`cat.${c.category}`) || c.category,
          value: Number(c.pass_rate || 0),
          color: c.bad > 0 ? '#f59e0b' : (catColor[c.category] || 'var(--accent)'),
          sub: `合格 ${c.good} / 有效 ${c.valid} · 坏数据 ${c.bad}`,
          subShort: `${c.good}/${c.valid}`,
        }))
        : [
          { label: t('r.cur_pass'), value: Number(ts.current_pass_rate || 0), color: '#22c55e' },
          { label: t('radar.cov'), value: covVal, color: '#38bdf8' },
        ];
      window.PAS_KIT.renderBarChart(document.getElementById('se-type-bars'), {
        items,
        maxVal: 100,
        unit: '%',
        digits: 1,
      });
    }

    // 中栏 3：精简核心基态与调度配置胶囊（移除 15 行冗余超参数列表）
    const sceneEl = document.getElementById('h-model-scene');
    if (sceneEl) sceneEl.textContent = rt.scenario ? `${rt.runtime || 'realtime'} / ${rt.scenario}` : '—';
    const cfgHost = document.getElementById('se-cfg-chips');
    if (cfgHost) {
      const periodTxt = sched.period_seconds != null ? `${sched.period_seconds}s` : `${params.do_cycle ?? 60}s`;
      cfgHost.innerHTML = [
        [t('cfg.cycle'), `${sched.enabled ? t('yes') : t('no')} · ${periodTxt}`, sched.enabled ? 'ok' : ''],
        [t('cfg.flat'), params.flat_start ? t('yes') : t('no'), ''],
        [t('cfg.tol'), params.tol != null ? Number(params.tol).toExponential(0) : '—', ''],
      ].map(([k, v, cls]) => `<div class="pas-stat-chip"><span>${esc(k)}</span><strong class="tabular ${cls}">${esc(v)}</strong></div>`).join('');
    }

    // 右上：合格率摘要 + 双曲线 / 坏数据柱图
    document.getElementById('h-r-cur').textContent = ts.current_pass_rate != null ? `${Number(ts.current_pass_rate).toFixed(2)}%` : '—';
    document.getElementById('h-r-today').textContent = ts.today_avg_pass_rate != null ? `${Number(ts.today_avg_pass_rate).toFixed(2)}%` : '—';
    document.getElementById('h-r-yest').textContent = ts.yesterday_avg_pass_rate != null ? `${Number(ts.yesterday_avg_pass_rate).toFixed(2)}%` : '—';
    document.getElementById('h-r-conv').textContent = `${Number(ts.today_conv_rate || 0).toFixed(1)}%`;
    renderMainChart(d.pass_rate_series);

    // 右下左卡：最大残差 Top 测点（点击设备打开 360° 抽屉）
    const topRes = d.top_residuals || [];
    if (window.PAS_KIT?.renderBarChart) {
      const badThr = Number(params.baderr_eps || 3.0);
      window.PAS_KIT.renderBarChart(document.getElementById('se-top-residuals'), {
        items: topRes.map((r) => ({
          label: r.device_name || r.measurement_name,
          device: r.device_name || '',
          value: Number(r.score || 0),
          color: r.is_bad ? '#ef4444' : (Number(r.score || 0) >= badThr * 0.7 ? '#f59e0b' : 'var(--accent)'),
          sub: `${r.measurement_type} · 量测 ${fmtNum(r.value, 3)} / 估计 ${fmtNum(r.estimated_value, 3)}`,
          subShort: r.category,
        })),
        threshold: badThr,
        unit: 'σ',
        digits: 2,
        emptyText: t('empty.res'),
      });
    }

    // 右下右卡：三率对比柱图 + 核心求解结果胶囊
    if (window.PAS_KIT?.renderBarChart) {
      window.PAS_KIT.renderBarChart(document.getElementById('se-home-rate-bars'), {
        items: [
          { label: t('r.cur_pass'), value: Number(ts.current_pass_rate || 0), color: '#22c55e' },
          { label: t('r.conv_rate'), value: Number(ts.today_conv_rate || 0), color: '#38bdf8' },
          { label: t('radar.cov'), value: covVal, color: '#6366f1' },
        ],
        maxVal: 100,
        unit: '%',
        digits: 1,
      });
    }
    const solveHost = document.getElementById('se-solve-chips');
    if (solveHost) {
      const totRes = latest?.total_residual != null ? fmtNum(latest.total_residual, Math.abs(Number(latest.total_residual)) >= 100 ? 1 : 2) : '—';
      const infRes = latest?.residual_inf != null ? fmtNum(latest.residual_inf, Math.abs(Number(latest.residual_inf)) >= 100 ? 1 : 2) : '—';
      solveHost.innerHTML = [
        [t('solve.obj'), latest ? fmtNum(latest.objective, 4) : '—', ''],
        [t('solve.res'), latest ? `${totRes} / ${infRes}` : '—', ''],
        [t('solve.runs'), `${ts.today_converged ?? 0} / ${ts.today_runs ?? 0}`, 'ok'],
        [t('solve.host'), rt.host || '—', ''],
      ].map(([k, v, cls]) => `<div class="pas-stat-chip"><span>${esc(k)}</span><strong class="tabular ${cls}" title="${esc(v)}">${esc(v)}</strong></div>`).join('');
    }

    // 底部运行信息条
    const log = d.latest_log;
    if (log) {
      document.getElementById('h-log-time').textContent = fmtTime(log.calc_time);
      document.getElementById('h-log-msg').textContent = `[${log.level}/${log.stage}] ${log.message}`;
    } else {
      document.getElementById('h-log-time').textContent = '—';
      document.getElementById('h-log-msg').textContent = '—';
    }
  }

  let autoRefreshOn = localStorage.getItem('pas_se_home_auto') !== '0';
  let lastHomeSig = '';

  function syncAutoBtn() {
    const btn = document.getElementById('btn-auto-refresh');
    if (!btn) return;
    btn.classList.toggle('active', autoRefreshOn);
    btn.textContent = t(autoRefreshOn ? 'action.auto_on' : 'action.auto_off');
  }

  async function refreshAll(silent = false) {
    try {
      const data = await api('/api/se/home');
      const sig = `${data.latest?.run_id || 0}|${data.latest_log?.log_id || 0}|${data.today_stats?.today_runs || 0}|${data.schedule?.enabled ? 1 : 0}`;
      if (silent && sig === lastHomeSig) return;
      lastHomeSig = sig;
      renderHome(data);
    } catch (err) {
      if (!silent) notify(err.message, true);
    }
  }

  function bindEvents() {
    document.getElementById('btn-home-start')?.addEventListener('click', async () => {
      const btn = document.getElementById('btn-home-start');
      btn.disabled = true;
      try {
        notify(t('msg.se_submitted'));
        await api('/api/actions/trigger', { method: 'POST', body: JSON.stringify({ task: 'se' }) });
        notify(t('msg.se_done'));
        await refreshAll();
      } catch (err) {
        notify(err.message, true);
      } finally {
        btn.disabled = false;
      }
    });

    document.getElementById('btn-home-toggle-daemon')?.addEventListener('click', async (e) => {
      const running = e.currentTarget.dataset.running === '1';
      const periodSec = Number(homeData?.schedule?.period_seconds ?? homeData?.params?.do_cycle ?? 60);
      try {
        await api('/api/schedules/se', {
          method: 'POST',
          body: JSON.stringify({ period_seconds: periodSec, enabled: !running }),
        });
        notify(running ? t('msg.daemon_off') : t('msg.daemon_on'));
        await refreshAll();
      } catch (err) {
        notify(err.message, true);
      }
    });

    document.querySelectorAll('#se-chart-mode [data-mode]').forEach((btn) => {
      btn.addEventListener('click', () => {
        chartMode = btn.dataset.mode || 'pass';
        document.querySelectorAll('#se-chart-mode [data-mode]').forEach((b) => b.classList.toggle('active', b === btn));
        if (homeData) renderMainChart(homeData.pass_rate_series);
      });
    });

    let timer;
    window.addEventListener('resize', () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (homeData) renderMainChart(homeData.pass_rate_series);
      }, 150);
    });
  }

  /**
   * 绑定主画面 4 处可拖拽分割符（左/中列宽、右栏上下高度、右下两卡比例），支持双击复位与持久化。
   */
  function initHomeSplitters() {
    const grid = document.getElementById('se-home-grid');
    const right = document.getElementById('se-home-right');
    const bottom = document.getElementById('se-home-bottom');
    const sCol1 = document.getElementById('split-col1');
    const sCol2 = document.getElementById('split-col2');
    const sRightH = document.getElementById('split-right-h');
    const sBotV = document.getElementById('split-bottom-v');
    if (!grid || !right || !bottom) return;

    const LAYOUT_KEY = 'pas_se_home_layout_v2';
    const DEFAULTS = { col1: 274, col2: 266, bottomH: null, botRatio: 0.52 };

    let layout = { ...DEFAULTS };
    try {
      const saved = JSON.parse(localStorage.getItem(LAYOUT_KEY) || '{}');
      if (saved && typeof saved === 'object') {
        if (Number.isFinite(saved.col1)) layout.col1 = Math.max(210, Math.min(480, Number(saved.col1)));
        if (Number.isFinite(saved.col2)) layout.col2 = Math.max(210, Math.min(480, Number(saved.col2)));
        if (Number.isFinite(saved.bottomH) && saved.bottomH >= 150) layout.bottomH = Number(saved.bottomH);
        if (Number.isFinite(saved.botRatio)) layout.botRatio = Math.max(0.30, Math.min(0.70, Number(saved.botRatio)));
      }
    } catch (_) {
      layout = { ...DEFAULTS };
    }

    let rafId = 0;
    const scheduleChartRedraw = () => {
      if (rafId) return;
      rafId = requestAnimationFrame(() => {
        rafId = 0;
        if (homeData) renderMainChart(homeData.pass_rate_series);
      });
    };

    const applyLayout = (redraw = false) => {
      if (!document.body.classList.contains('pas-wall-mode')) {
        grid.style.setProperty('--col1', `${Math.round(layout.col1)}px`);
        grid.style.setProperty('--col2', `${Math.round(layout.col2)}px`);
      } else {
        grid.style.removeProperty('--col1');
        grid.style.removeProperty('--col2');
      }
      right.style.setProperty('--bottom-h', layout.bottomH != null ? `${Math.round(layout.bottomH)}px` : 'minmax(200px, 44%)');
      bottom.style.setProperty('--bot-left', `calc(${(layout.botRatio * 100).toFixed(2)}% - 4px)`);
      if (redraw) scheduleChartRedraw();
    };

    const saveLayout = () => {
      try { localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout)); } catch (_) {}
    };

    const bindDrag = (el, orientation, onMove, onReset) => {
      if (!el) return;
      let dragging = false;
      const bodyCls = orientation === 'v' ? 'se-splitting-v' : 'se-splitting-h';
      el.addEventListener('dblclick', () => { onReset(); applyLayout(true); saveLayout(); });
      el.addEventListener('pointerdown', (e) => {
        if (e.button !== 0) return;
        dragging = true;
        el.setPointerCapture(e.pointerId);
        el.classList.add('is-active');
        document.body.classList.add(bodyCls);
      });
      el.addEventListener('pointermove', (e) => { if (dragging) { onMove(e); applyLayout(true); } });
      const end = (e) => {
        if (!dragging) return;
        dragging = false;
        if (e && el.hasPointerCapture?.(e.pointerId)) el.releasePointerCapture(e.pointerId);
        el.classList.remove('is-active');
        document.body.classList.remove(bodyCls);
        saveLayout();
        scheduleChartRedraw();
      };
      el.addEventListener('pointerup', end);
      el.addEventListener('pointercancel', end);
    };

    bindDrag(sCol1, 'v', (e) => {
      const rect = grid.getBoundingClientRect();
      const maxCol1 = Math.max(210, Math.min(480, rect.width - layout.col2 - 360 - 16));
      layout.col1 = Math.max(210, Math.min(maxCol1, e.clientX - rect.left - 4));
    }, () => { layout.col1 = DEFAULTS.col1; });

    bindDrag(sCol2, 'v', (e) => {
      const rect = grid.getBoundingClientRect();
      const maxCol2 = Math.max(210, Math.min(480, rect.width - layout.col1 - 360 - 16));
      layout.col2 = Math.max(210, Math.min(maxCol2, e.clientX - rect.left - layout.col1 - 12));
    }, () => { layout.col2 = DEFAULTS.col2; });

    bindDrag(sRightH, 'h', (e) => {
      const rect = right.getBoundingClientRect();
      const maxBottom = Math.max(150, rect.height - 190);
      layout.bottomH = Math.max(150, Math.min(maxBottom, rect.bottom - e.clientY - 4));
    }, () => { layout.bottomH = DEFAULTS.bottomH; });

    bindDrag(sBotV, 'v', (e) => {
      const rect = bottom.getBoundingClientRect();
      if (rect.width <= 0) return;
      layout.botRatio = Math.max(0.30, Math.min(0.70, (e.clientX - rect.left) / rect.width));
    }, () => { layout.botRatio = DEFAULTS.botRatio; });

    window.addEventListener('resize', () => applyLayout(false));
    applyLayout(false);
  }

  common.initShell({ onRefresh: () => refreshAll(false), afterRunSE: () => refreshAll(false) });
  syncAutoBtn();
  const btnAuto = document.getElementById('btn-auto-refresh');
  if (btnAuto) {
    btnAuto.addEventListener('click', () => {
      autoRefreshOn = !autoRefreshOn;
      localStorage.setItem('pas_se_home_auto', autoRefreshOn ? '1' : '0');
      syncAutoBtn();
      if (autoRefreshOn) refreshAll(true);
    });
  }
  if (window.PAS_KIT?.createPoller) {
    window.PAS_KIT.createPoller(() => { if (autoRefreshOn) refreshAll(true); }, 15000, { useSSE: true });
  } else {
    setInterval(() => {
      if (autoRefreshOn && !document.hidden) refreshAll(true);
    }, 10000);
  }
  initHomeSplitters();
  bindEvents();
  refreshAll(false);
})();
