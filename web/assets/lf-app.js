/* PAS 在线潮流计算（LF）五页统一前端引擎：主画面 / 潮流图 / 潮流明细 / 参数与方式 / 运行日志 */
(() => {
  'use strict';

  const I18N = {
    'zh-CN': {
      'brand.sub': '在线分析平台',
      'nav.overview': '总览',
      'nav.analysis': '分析功能',
      'nav.se_root': '状态估计 SE',
      'nav.lf_root': '潮流分析 LF',
      'nav.lf_main': '主画面',
      'nav.lf_flow': '潮流图',
      'nav.lf_results': '潮流明细',
      'nav.lf_params': '参数与方式',
      'nav.lf_logs': '运行日志',
      'nav.ca': '静态安全 CA',
      'nav.management': '运行管理',
      'nav.runs': '运行历史',
      'nav.measurements': '设备量测',
      'nav.limits': '安全限值',
      'nav.workspace': '工作目录',
      'nav.settings': '系统设置',
      'service.checking': '服务检查中',
      'service.daemon_on': '周期运行中',
      'service.daemon_off': 'Web 在线 · 周期未启动',
      'service.offline': '服务离线',
      'title.lf_main': '潮流分析 LF',
      'title.lf_flow': '在线潮流图',
      'title.lf_results': '潮流明细与曲线',
      'title.lf_params': 'LF 算法参数与方式',
      'title.lf_logs': 'LF 运行日志',
      'action.run_lf': '执行 LF',
      'action.running_lf': '计算中…',
      'action.auto_refresh': '自刷',
      'action.refresh': '刷新',
      'action.export_csv': '导出 CSV',
      'action.cancel': '取消',
      'action.confirm': '确认',
      'action.locate': '定位',
      'action.edit': '编辑',
      'action.delete': '删除',
      'action.adjust': '方式调整',
      'common.all': '全部',
      'common.empty': '暂无记录',
      'bool.on': '开启',
      'bool.off': '关闭',
      'link.more': '更多…',
      'theme.light': '极简明亮',
      'theme.dark': '精密暗黑',
      'theme.bento': '便当盒网格',
      'theme.glass': '毛玻璃拟态',
      'theme.editorial': '编辑杂志',
      'theme.cyan': '科幻 · 电光青',
      'theme.purple': '科幻 · 赛博紫',
      'theme.matrix': '科幻 · 矩阵绿',
      'status.converged': '收敛',
      'status.diverged': '未收敛',
      'status.succeeded': '成功',
      'status.failed': '失败',
      'status.running': '运行中',
      'snap.latest': '最新断面',
      'snap.history': '历史回放',
      'home.power_title': '功率平衡与基态',
      'home.ctrl_title': '运行控制与极值',
      'home.energy_hub': '交直流能量流中枢',
      'home.sankey_sub': '交直流能量流（动态桑基）',
      'home.acdc_mix': '交直流源荷结构',
      'home.converters': '互联换流器 / 分域工况',
      'home.grid_health': '全网电压与负载分布',
      'home.v_dist': '母线电压区间分布 (pu)',
      'home.l_dist': '支路负载率区间分布 (%)',
      'home.base_state': '求解基态与方式',
      'home.top_load': '重过载排行',
      'home.v_extremes': '电压偏差与越限',
      'metric.loss_rate': '网损率 %',
      'metric.max_load': '最大负载 %',
      'metric.total_load': '总负荷',
      'metric.min_v': '最低电压 pu',
      'metric.elapsed': '计算耗时 s',
      'kv.source_se': '输入源 SE 断面',
      'kv.mode': '运行模式',
      'kv.total_gen': '总发电有功',
      'kv.total_load': '总负荷有功',
      'kv.total_loss': '全网总网损',
      'kv.loss_rate': '全网网损率',
      'kv.ac_gen_load': '交流 发电 / 负荷',
      'kv.ac_loss': '交流 网损',
      'kv.dc_gen_load': '直流 发电 / 负荷',
      'kv.dc_loss': '直流 网损',
      'kv.iters': '迭代次数 (AC / DC)',
      'kv.norm_f': '最大不平衡量',
      'kv.elapsed': '求解耗时',
      'kv.overrides': '生效方式调整',
      'kv.use_se': 'SE 基态注入',
      'kv.v_min': '全网最低电压',
      'kv.v_max': '全网最高电压',
      'kv.max_load': '最大设备负载率',
      'kv.alerts': '电压越限 / 重过载',
      'flow.mode_lf': 'LF 潮流值',
      'flow.mode_loading': '负载率 %',
      'flow.mode_diff': 'LF − SE 偏差',
      'flow.alerts': '越限与重载',
      'flow.dev_detail': '设备潮流',
      'topo.fit': '适应画布',
      'topo.jump_ph': '定位设备…',
      'res.branches': '支路与换流器',
      'res.buses': '母线电压',
      'res.units': '电源与负荷',
      'res.trend': '历史趋势',
      'res.only_abn': '仅越限/重载',
      'ph.search_dev': '搜索设备',
      'ph.search_log': '搜索日志',
      'col.idx': '编号',
      'col.domain': '域',
      'col.dev_type': '设备类',
      'col.device': '设备名称',
      'col.p_from': '首端 P',
      'col.q_from': '首端 Q',
      'col.i_from': '首端 I',
      'col.p_to': '末端 P',
      'col.p_loss': '损耗 P',
      'col.loading': '负载率 %',
      'col.p_se_diff': 'SE / ΔP',
      'col.vbase': '基准 U',
      'col.v_pu': '电压 (pu)',
      'col.v_eng': '电压值',
      'col.angle': '相角 (°)',
      'col.v_se_diff': 'SE / ΔU',
      'col.status': '状态',
      'col.ctrl': '控制方式',
      'col.p_lf': '有功 P',
      'col.q_lf': '无功 Q',
      'col.v_lf': '电压 U',
      'col.i_lf': '电流 I',
      'col.note': '备注',
      'col.ops': '操作',
      'params.reset': '恢复默认',
      'params.save': '保存参数',
      'params.trial': '保存并试算对比',
      'params.tab_para': '算法参数',
      'params.tab_ov': '方式调整方案',
      'params.saved': 'LF 参数已保存',
      'params.reset_done': '已恢复 lf.para 默认值',
      'params.reset_title': '恢复默认 LF 参数',
      'params.reset_desc': '确认从 lf.para 恢复默认求解参数？',
      'ov.dlg_title': '方式调整',
      'ov.field': '调整字段',
      'ov.value': '设定值',
      'ov.add': '+ 新增调整',
      'ov.run_trial': '按方式试算对比',
      'ov.clear_all': '清空方式',
      'ov.save_only': '保存',
      'ov.save_and_run': '保存并重算 LF',
      'ov.saved': '方式调整已保存',
      'ov.deleted': '方式调整已删除',
      'ov.cleared': '方式调整已清空',
      'ov.del_confirm': '确认删除该条方式调整？',
      'ov.clear_confirm': '确认清空全部方式调整方案并回归纯 SE 基态？',
      'trial.title': '试算对比',
      'trial.loss': '网损率',
      'trial.min_v': '最低 U',
      'trial.max_load': '最大负载',
      'trial.alerts': '越限数',
      'logs.total': '日志总数',
      'logs.err24': '24h ERR/WARN',
      'logs.ret': '常规保留天数',
      'logs.err_ret': 'ERROR 保留天数',
      'logs.max_rows': '最大保留条数',
      'logs.pending': '待清理',
      'logs.tab_stream': '日志明细',
      'logs.tab_runs': '运行与调度',
      'logs.tab_policy': '清理策略',
      'logs.runs_title': 'LF 历史运行记录',
      'logs.pol_enabled': '自动清理',
      'logs.purge_now': '立即按策略清理',
      'logs.purge_confirm': '确认按当前策略永久清理到期/超限 LF 日志？',
      'logs.pol_saved': '日志策略已保存',
      'logs.purged': '已清理日志 {n} 条',
      'sched.title': 'LF 周期调度',
      'sched.period': '周期 (s)',
      'sched.enabled': '启用周期自动执行',
      'sched.save': '保存调度',
      'sched.start': '启动周期',
      'sched.stop': '停止周期',
      'sched.saved': 'LF 周期调度已保存',
      'msg.lf_submitted': 'LF 任务已提交执行',
      'msg.lf_done': 'LF 计算完成 (#{id})',
      'msg.lf_failed': 'LF 计算失败：{msg}',
      'pager.prev': '上一页',
      'pager.next': '下一页',
    },
    'en-US': {
      'brand.sub': 'Online Power Analysis',
      'nav.overview': 'Overview',
      'nav.analysis': 'Analysis',
      'nav.se_root': 'State Estimation SE',
      'nav.lf_root': 'Load Flow LF',
      'nav.lf_main': 'Home',
      'nav.lf_flow': 'Flow Map',
      'nav.lf_results': 'LF Details',
      'nav.lf_params': 'Params & Study',
      'nav.lf_logs': 'Run Logs',
      'nav.ca': 'Contingency CA',
      'nav.management': 'Management',
      'nav.runs': 'Run History',
      'nav.measurements': 'Measurements',
      'nav.limits': 'Limits',
      'nav.workspace': 'Workspace',
      'nav.settings': 'Settings',
      'service.checking': 'Checking',
      'service.daemon_on': 'Scheduler Active',
      'service.daemon_off': 'Web Online · Idle',
      'service.offline': 'Offline',
      'title.lf_main': 'Load Flow Overview',
      'title.lf_flow': 'Online Flow Map',
      'title.lf_results': 'LF Details & Trends',
      'title.lf_params': 'LF Params & Study Overrides',
      'title.lf_logs': 'LF Run Logs',
      'action.run_lf': 'Run LF Now',
      'action.running_lf': 'Solving LF…',
      'action.auto_refresh': 'Auto Refresh',
      'action.refresh': 'Refresh',
      'action.export_csv': 'Export CSV',
      'action.cancel': 'Cancel',
      'action.confirm': 'Confirm',
      'action.locate': 'Locate',
      'action.edit': 'Edit',
      'action.delete': 'Delete',
      'action.adjust': 'Adjust',
      'common.all': 'All',
      'common.empty': 'No records',
      'bool.on': 'ON',
      'bool.off': 'OFF',
      'link.more': 'More…',
      'theme.light': 'Minimalist Light',
      'theme.dark': 'Precision Dark',
      'theme.bento': 'Bento Grid',
      'theme.glass': 'Glassmorphism',
      'theme.editorial': 'Editorial',
      'theme.cyan': 'Sci-Fi · Cyan',
      'theme.purple': 'Sci-Fi · Purple',
      'theme.matrix': 'Sci-Fi · Matrix',
      'status.converged': 'Converged',
      'status.diverged': 'Diverged',
      'status.succeeded': 'Succeeded',
      'status.failed': 'Failed',
      'status.running': 'Running',
      'snap.latest': 'Latest',
      'snap.history': 'History',
      'home.power_title': 'Power Balance & Base',
      'home.ctrl_title': 'Control & Extremes',
      'home.energy_hub': 'AC/DC Energy Flow Hub',
      'home.sankey_sub': 'AC/DC Power Flow (Sankey)',
      'home.acdc_mix': 'AC/DC Source-Load Mix',
      'home.converters': 'Converters & Domains',
      'home.grid_health': 'Voltage & Loading Profile',
      'home.v_dist': 'Bus Voltage Distribution (pu)',
      'home.l_dist': 'Branch Loading Distribution (%)',
      'home.base_state': 'Base State & Study',
      'home.top_load': 'Top Loading',
      'home.v_extremes': 'Voltage Extremes',
      'metric.loss_rate': 'Loss %',
      'metric.max_load': 'Max Load %',
      'metric.total_load': 'Total Load',
      'metric.min_v': 'Min V (pu)',
      'metric.elapsed': 'Elapsed (s)',
      'kv.source_se': 'Source SE Run',
      'kv.mode': 'Mode',
      'kv.total_gen': 'Total Gen P',
      'kv.total_load': 'Total Load P',
      'kv.total_loss': 'Total Loss P',
      'kv.loss_rate': 'Loss Rate',
      'kv.ac_gen_load': 'AC Gen / Load',
      'kv.ac_loss': 'AC Loss',
      'kv.dc_gen_load': 'DC Gen / Load',
      'kv.dc_loss': 'DC Loss',
      'kv.iters': 'Iterations (AC/DC)',
      'kv.norm_f': 'Max Mismatch',
      'kv.elapsed': 'Solve Time',
      'kv.overrides': 'Active Overrides',
      'kv.use_se': 'SE Base Injection',
      'kv.v_min': 'Min Bus Voltage',
      'kv.v_max': 'Max Bus Voltage',
      'kv.max_load': 'Max Loading',
      'kv.alerts': 'V Viol / Overload',
      'flow.mode_lf': 'LF Values',
      'flow.mode_loading': 'Loading %',
      'flow.mode_diff': 'LF − SE Diff',
      'flow.alerts': 'Alerts',
      'flow.dev_detail': 'Device Flow',
      'topo.fit': 'Fit',
      'topo.jump_ph': 'Locate device…',
      'res.branches': 'Branches & Conv',
      'res.buses': 'Bus Voltages',
      'res.units': 'Gen & Loads',
      'res.trend': 'History Trend',
      'res.only_abn': 'Abnormal Only',
      'ph.search_dev': 'Search device',
      'ph.search_log': 'Search logs',
      'col.idx': 'Idx',
      'col.domain': 'Dom',
      'col.dev_type': 'Type',
      'col.device': 'Device',
      'col.p_from': 'P From',
      'col.q_from': 'Q From',
      'col.i_from': 'I From',
      'col.p_to': 'P To',
      'col.p_loss': 'Loss P',
      'col.loading': 'Load %',
      'col.p_se_diff': 'SE / ΔP',
      'col.vbase': 'Vbase',
      'col.v_pu': 'V (pu)',
      'col.v_eng': 'Voltage',
      'col.angle': 'Angle (°)',
      'col.v_se_diff': 'SE / ΔV',
      'col.status': 'Status',
      'col.ctrl': 'Ctrl',
      'col.p_lf': 'P',
      'col.q_lf': 'Q',
      'col.v_lf': 'V',
      'col.i_lf': 'I',
      'col.note': 'Note',
      'col.ops': 'Actions',
      'params.reset': 'Reset',
      'params.save': 'Save',
      'params.trial': 'Save & Trial',
      'params.tab_para': 'LF Parameters',
      'params.tab_ov': 'Study Overrides',
      'params.saved': 'LF parameters saved',
      'params.reset_done': 'Reset to lf.para defaults',
      'params.reset_title': 'Reset LF Parameters',
      'params.reset_desc': 'Restore defaults from lf.para?',
      'ov.dlg_title': 'Study Override',
      'ov.field': 'Field',
      'ov.value': 'Value',
      'ov.add': '+ Add Override',
      'ov.run_trial': 'Trial Compare',
      'ov.clear_all': 'Clear All',
      'ov.save_only': 'Save',
      'ov.save_and_run': 'Save & Run LF',
      'ov.saved': 'Override saved',
      'ov.deleted': 'Override deleted',
      'ov.cleared': 'Overrides cleared',
      'ov.del_confirm': 'Delete this override?',
      'ov.clear_confirm': 'Clear all study overrides?',
      'trial.title': 'Trial Compare',
      'trial.loss': 'Loss',
      'trial.min_v': 'Min V',
      'trial.max_load': 'Max Load',
      'trial.alerts': 'Alerts',
      'logs.total': 'Total Logs',
      'logs.err24': '24h ERR/WARN',
      'logs.ret': 'Retention Days',
      'logs.err_ret': 'Error Ret. Days',
      'logs.max_rows': 'Max Rows',
      'logs.pending': 'Pending Purge',
      'logs.tab_stream': 'Log Stream',
      'logs.tab_runs': 'Runs & Schedule',
      'logs.tab_policy': 'Retention Policy',
      'logs.runs_title': 'LF Run History',
      'logs.pol_enabled': 'Auto Cleanup',
      'logs.purge_now': 'Purge Now',
      'logs.purge_confirm': 'Permanently purge expired LF logs?',
      'logs.pol_saved': 'Log policy saved',
      'logs.purged': 'Purged {n} rows',
      'sched.title': 'LF Schedule',
      'sched.period': 'Period (s)',
      'sched.enabled': 'Enable periodic run',
      'sched.save': 'Save',
      'sched.start': 'Start',
      'sched.stop': 'Stop',
      'sched.saved': 'Schedule saved',
      'msg.lf_submitted': 'LF job queued',
      'msg.lf_done': 'LF completed (#{id})',
      'msg.lf_failed': 'LF failed: {msg}',
      'pager.prev': 'Prev',
      'pager.next': 'Next',
    },
    'ru-RU': {
      'brand.sub': 'Онлайн-анализ сети',
      'nav.overview': 'Обзор',
      'nav.analysis': 'Анализ',
      'nav.se_root': 'Оценка сост. SE',
      'nav.lf_root': 'Потокораспр. LF',
      'nav.lf_main': 'Главная',
      'nav.lf_flow': 'Схема потоков',
      'nav.lf_results': 'Детали УР',
      'nav.lf_params': 'Параметры и режим',
      'nav.lf_logs': 'Журнал работы',
      'nav.ca': 'Надёжность N-1',
      'nav.management': 'Управление',
      'nav.runs': 'История',
      'nav.measurements': 'Измерения',
      'nav.limits': 'Ограничения',
      'nav.workspace': 'Каталог',
      'nav.settings': 'Настройки',
      'service.checking': 'Проверка',
      'service.daemon_on': 'Планировщик вкл.',
      'service.daemon_off': 'Веб онлайн · Стоп',
      'service.offline': 'Офлайн',
      'title.lf_main': 'Панель расчёта УР',
      'title.lf_flow': 'Схема потоков LF',
      'title.lf_results': 'Детали и тренды УР',
      'title.lf_params': 'Параметры и коррекция режима',
      'title.lf_logs': 'Журнал УР',
      'action.run_lf': 'Запустить LF',
      'action.running_lf': 'Расчёт LF…',
      'action.auto_refresh': 'Автообновл.',
      'action.refresh': 'Обновить',
      'action.export_csv': 'Экспорт CSV',
      'action.cancel': 'Отмена',
      'action.confirm': 'Подтвердить',
      'action.locate': 'На схеме',
      'action.edit': 'Изм.',
      'action.delete': 'Удал.',
      'action.adjust': 'Режим',
      'common.all': 'Все',
      'common.empty': 'Нет данных',
      'bool.on': 'Вкл',
      'bool.off': 'Выкл',
      'link.more': 'Ещё…',
      'theme.light': 'Светлая',
      'theme.dark': 'Тёмная',
      'theme.bento': 'Бенто-сетка',
      'theme.glass': 'Стекло',
      'theme.editorial': 'Редакционная',
      'theme.cyan': 'Кибер · Циан',
      'theme.purple': 'Кибер · Пурпур',
      'theme.matrix': 'Кибер · Матрица',
      'status.converged': 'Сошёлся',
      'status.diverged': 'Не сошёлся',
      'status.succeeded': 'Успешно',
      'status.failed': 'Ошибка',
      'status.running': 'Выполн.',
      'snap.latest': 'Последний',
      'snap.history': 'Архив',
      'home.power_title': 'Баланс и база SE',
      'home.ctrl_title': 'Контроль и экстремумы',
      'home.energy_hub': 'Потоки энергии AC/DC',
      'home.sankey_sub': 'Диаграмма Санки (AC/DC)',
      'home.acdc_mix': 'Структура AC/DC',
      'home.converters': 'Преобразователи / Потери',
      'home.grid_health': 'Распределение U и загрузки',
      'home.v_dist': 'Узлы по напряжению (о.е.)',
      'home.l_dist': 'Ветви по загрузке (%)',
      'home.base_state': 'Базовый режим и коррекции',
      'home.top_load': 'Загрузка оборуд.',
      'home.v_extremes': 'Отклонения U',
      'metric.loss_rate': 'Потери %',
      'metric.max_load': 'Макс. загр. %',
      'metric.total_load': 'Нагрузка',
      'metric.min_v': 'Мин. U (о.е.)',
      'metric.elapsed': 'Время (с)',
      'kv.source_se': 'Базовый расчёт SE',
      'kv.mode': 'Режим',
      'kv.total_gen': 'Генерация P',
      'kv.total_load': 'Нагрузка P',
      'kv.total_loss': 'Потери P',
      'kv.loss_rate': 'Доля потерь',
      'kv.ac_gen_load': 'AC Ген / Нагр',
      'kv.ac_loss': 'Потери AC',
      'kv.dc_gen_load': 'DC Ген / Нагр',
      'kv.dc_loss': 'Потери DC',
      'kv.iters': 'Итерации (AC/DC)',
      'kv.norm_f': 'Макс. невязка',
      'kv.elapsed': 'Время расчёта',
      'kv.overrides': 'Коррекций режима',
      'kv.use_se': 'База из SE',
      'kv.v_min': 'Мин. напряжение',
      'kv.v_max': 'Макс. напряжение',
      'kv.max_load': 'Макс. загрузка',
      'kv.alerts': 'Наруш. U / Перегр.',
      'flow.mode_lf': 'Значения LF',
      'flow.mode_loading': 'Загрузка %',
      'flow.mode_diff': 'LF − SE Δ',
      'flow.alerts': 'Нарушения',
      'flow.dev_detail': 'Оборудование',
      'topo.fit': 'Вписать',
      'topo.jump_ph': 'Найти объект…',
      'res.branches': 'Ветви и преобр.',
      'res.buses': 'Узлы U',
      'res.units': 'Ген. и нагр.',
      'res.trend': 'Тренды',
      'res.only_abn': 'Только наруш.',
      'ph.search_dev': 'Поиск оборуд.',
      'ph.search_log': 'Поиск в логах',
      'col.idx': '#',
      'col.domain': 'Тип',
      'col.dev_type': 'Класс',
      'col.device': 'Устройство',
      'col.p_from': 'P нач.',
      'col.q_from': 'Q нач.',
      'col.i_from': 'I нач.',
      'col.p_to': 'P кон.',
      'col.p_loss': 'Потери P',
      'col.loading': 'Загр. %',
      'col.p_se_diff': 'SE / ΔP',
      'col.vbase': 'Uбаз',
      'col.v_pu': 'U (о.е.)',
      'col.v_eng': 'U факт',
      'col.angle': 'Угол (°)',
      'col.v_se_diff': 'SE / ΔU',
      'col.status': 'Статус',
      'col.ctrl': 'Режим',
      'col.p_lf': 'P',
      'col.q_lf': 'Q',
      'col.v_lf': 'U',
      'col.i_lf': 'I',
      'col.note': 'Прим.',
      'col.ops': 'Действия',
      'params.reset': 'Сброс',
      'params.save': 'Сохранить',
      'params.trial': 'Сохр. и тест LF',
      'params.tab_para': 'Параметры УР',
      'params.tab_ov': 'Коррекция режима',
      'params.saved': 'Параметры сохранены',
      'params.reset_done': 'Сброшено к lf.para',
      'params.reset_title': 'Сброс параметров LF',
      'params.reset_desc': 'Восстановить настройки из lf.para?',
      'ov.dlg_title': 'Коррекция режима',
      'ov.field': 'Поле',
      'ov.value': 'Значение',
      'ov.add': '+ Коррекция',
      'ov.run_trial': 'Тест режима',
      'ov.clear_all': 'Очистить всё',
      'ov.save_only': 'Сохранить',
      'ov.save_and_run': 'Сохр. и расчёт LF',
      'ov.saved': 'Сохранено',
      'ov.deleted': 'Удалено',
      'ov.cleared': 'Очищено',
      'ov.del_confirm': 'Удалить коррекцию?',
      'ov.clear_confirm': 'Очистить все коррекции режима?',
      'trial.title': 'Сравнение',
      'trial.loss': 'Потери',
      'trial.min_v': 'Мин. U',
      'trial.max_load': 'Макс. загр.',
      'trial.alerts': 'Наруш.',
      'logs.total': 'Записей',
      'logs.err24': '24ч Ош./Пред.',
      'logs.ret': 'Хранение (дн)',
      'logs.err_ret': 'Ошибки (дн)',
      'logs.max_rows': 'Макс. строк',
      'logs.pending': 'К удалению',
      'logs.tab_stream': 'Журнал',
      'logs.tab_runs': 'Запуски и цикл',
      'logs.tab_policy': 'Очистка',
      'logs.runs_title': 'История запусков LF',
      'logs.pol_enabled': 'Автоочистка',
      'logs.purge_now': 'Очистить сейчас',
      'logs.purge_confirm': 'Удалить устаревшие записи журнала LF?',
      'logs.pol_saved': 'Политика сохранена',
      'logs.purged': 'Удалено {n} записей',
      'sched.title': 'Расписание LF',
      'sched.period': 'Период (с)',
      'sched.enabled': 'Автозапуск по циклу',
      'sched.save': 'Сохранить',
      'sched.start': 'Старт',
      'sched.stop': 'Стоп',
      'sched.saved': 'Сохранено',
      'msg.lf_submitted': 'Расчёт LF в очереди',
      'msg.lf_done': 'Расчёт LF завершён (#{id})',
      'msg.lf_failed': 'Ошибка LF: {msg}',
      'pager.prev': 'Назад',
      'pager.next': 'Далее',
    },
  };

  const LF_PARAM_SCHEMA = [
    {
      group: { 'zh-CN': '求解器控制 (lf.para)', 'en-US': 'Solver Control (lf.para)', 'ru-RU': 'Управление решателем' },
      fields: [
        { key: 'tol', type: 'float', min: 1e-14, max: 1e-1, step: 'any', label: { 'zh-CN': '收敛精度容差 (tol)', 'en-US': 'Tolerance (tol)', 'ru-RU': 'Точность (tol)' } },
        { key: 'max_iter', type: 'int', min: 1, max: 2000, label: { 'zh-CN': '最大迭代次数 (max_iter)', 'en-US': 'Max Iterations', 'ru-RU': 'Макс. итераций' } },
        { key: 'min_voltage', type: 'float', min: 1e-5, max: 0.9, step: 'any', label: { 'zh-CN': '最低电压保护 (min_voltage)', 'en-US': 'Min Voltage Floor', 'ru-RU': 'Нижний предел U' } },
        { key: 'divergence_threshold', type: 'float', min: 10, max: 1e12, step: 'any', label: { 'zh-CN': '发散判据阈值', 'en-US': 'Divergence Threshold', 'ru-RU': 'Порог расходимости' } },
      ],
    },
    {
      group: { 'zh-CN': 'SE 联动与越限阈值', 'en-US': 'SE Linkage & Thresholds', 'ru-RU': 'Связь с SE и пороги' },
      fields: [
        { key: 'use_se_base', type: 'bool', label: { 'zh-CN': '自动消费 SE 收敛基态', 'en-US': 'Use SE Converged Base', 'ru-RU': 'База из SE' } },
        { key: 'cascade_ca', type: 'bool', label: { 'zh-CN': '收敛后联动触发 CA', 'en-US': 'Cascade Trigger CA', 'ru-RU': 'Автозапуск CA' } },
        { key: 'v_min_pu', type: 'float', min: 0.5, max: 1.05, step: '0.01', label: { 'zh-CN': '电压下限 (pu)', 'en-US': 'Voltage Min (pu)', 'ru-RU': 'Мин. U (о.е.)' } },
        { key: 'v_max_pu', type: 'float', min: 0.95, max: 1.5, step: '0.01', label: { 'zh-CN': '电压上限 (pu)', 'en-US': 'Voltage Max (pu)', 'ru-RU': 'Макс. U (о.е.)' } },
        { key: 'overload_warn_pct', type: 'float', min: 10, max: 200, step: '1', label: { 'zh-CN': '重载预警阈值 (%)', 'en-US': 'Heavy Load Warn (%)', 'ru-RU': 'Пред. загр. (%)' } },
        { key: 'overload_limit_pct', type: 'float', min: 20, max: 300, step: '1', label: { 'zh-CN': '过载越限阈值 (%)', 'en-US': 'Overload Limit (%)', 'ru-RU': 'Лимит загр. (%)' } },
        { key: 'do_cycle', type: 'int', min: 1, max: 604800, label: { 'zh-CN': '周期参考 (s)', 'en-US': 'Cycle Reference (s)', 'ru-RU': 'Цикл (с)' } },
      ],
    },
  ];

  const VIEW = document.body.dataset.lfView || 'home';
  const SVG_NS = 'http://www.w3.org/2000/svg';

  const st = {
    lang: localStorage.getItem('pas_se_lang') || localStorage.getItem('se_lang') || 'zh-CN',
    theme: localStorage.getItem('pas_se_theme') || localStorage.getItem('se_theme') || 'minimalist-light',
    selectedRunId: '',
    convergedRuns: [],
    home: null,
    homeMetric: 'loss_rate',
    autoRefresh: localStorage.getItem('pas_lf_autorefresh') === '1',
    autoTimer: null,
    lastRunId: null,
    topo: null,
    svgLoaded: false,
    svgMode: 'lf',
    selectedDevId: null,
    svgT: { scale: 1, tx: 0, ty: 0, vbW: 2518, vbH: 2143 },
    res: { kind: 'branches', domain: 'all', devType: '', onlyAbn: false, q: '', page: 0, size: 40, trendMetric: 'loss_rate', trendLimit: 60 },
    paramsSub: 'para',
    overrides: [],
    ovFilter: { type: '', q: '' },
    catalog: null,
    logs: { tab: 'stream', page: 0, size: 40, level: '', stage: 'all', window: 'all', runId: '', q: '' },
    watchingJobId: null,
    noticeTimer: null,
    confirmFn: null,
  };

  function t(k, vars = {}) {
    const d = I18N[st.lang] || I18N['zh-CN'];
    let s = d[k] ?? I18N['zh-CN'][k] ?? k;
    Object.entries(vars).forEach(([a, b]) => { s = s.replaceAll(`{${a}}`, String(b)); });
    return s;
  }
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  function fmtNum(v, d = 2) {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
    const n = Number(v);
    if (!Number.isFinite(n)) return '—';
    if (Math.abs(n) >= 1000) return n.toFixed(1);
    if (Math.abs(n) >= 100) return n.toFixed(2);
    if (Math.abs(n) >= 1) return n.toFixed(d);
    if (Math.abs(n) === 0) return '0';
    return Number(n.toPrecision(3)).toString();
  }
  function fmtTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso).slice(0, 19).replace('T', ' ');
    const p = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }
  function notify(msg, isErr = false) {
    const el = document.getElementById('notice');
    if (!el) return;
    el.textContent = msg;
    el.className = `notice ${isErr ? 'error' : 'ok'}`;
    el.hidden = false;
    clearTimeout(st.noticeTimer);
    st.noticeTimer = setTimeout(() => { el.hidden = true; }, 4000);
  }
  async function api(url, body = null, method = null) {
    const m = method || (body !== null ? 'POST' : 'GET');
    const opts = { method: m, headers: {} };
    if (body !== null && m !== 'GET' && m !== 'DELETE') {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const r = await fetch(url, opts);
    const j = await r.json();
    if (!j.ok) throw new Error(j.error || `HTTP ${r.status}`);
    return j.data;
  }
  function on(id, ev, fn) { const el = document.getElementById(id); if (el) el.addEventListener(ev, fn); }

  function applyTheme() {
    document.documentElement.setAttribute('data-theme', st.theme);
    const s = document.getElementById('theme-select');
    if (s) s.value = st.theme;
  }
  function applyI18n() {
    document.documentElement.lang = st.lang;
    const s = document.getElementById('lang-select');
    if (s) s.value = st.lang;
    document.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  }

  function openConfirm({ title, desc, okText, onConfirm }) {
    const dlg = document.getElementById('confirm-dialog');
    if (!dlg) return;
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-desc').textContent = desc;
    document.getElementById('btn-confirm-ok').textContent = okText || t('action.confirm');
    st.confirmFn = onConfirm;
    dlg.showModal();
    document.getElementById('btn-confirm-cancel')?.focus();
  }

  function populateRunSelect() {
    const sel = document.getElementById('lf-run-select');
    if (!sel) return;
    const opts = [`<option value="">${esc(t('snap.latest'))}</option>`];
    (st.convergedRuns || []).forEach((r) => {
      const ts = fmtTime(r.calc_time).slice(5);
      const loss = r.loss_rate != null ? `${Number(r.loss_rate).toFixed(2)}%` : '—';
      const seTag = r.source_se_run_id ? ` · SE#${r.source_se_run_id}` : '';
      opts.push(`<option value="${r.run_id}">${esc(t('snap.history'))} #${r.run_id} · ${esc(ts)}${seTag} · L${loss}</option>`);
    });
    sel.innerHTML = opts.join('');
    sel.value = st.selectedRunId || '';
    sel.classList.toggle('is-history', Boolean(st.selectedRunId));
  }

  function updateStatusPill(latest) {
    const pill = document.getElementById('lf-status-pill');
    const meta = document.getElementById('lf-run-meta');
    if (pill) {
      if (!latest) {
        pill.textContent = '—';
        pill.className = 'se-pill neutral';
      } else {
        pill.textContent = latest.converged ? t('status.converged') : t('status.diverged');
        pill.className = `se-pill ${latest.converged ? 'ok' : 'bad'}`;
      }
    }
    if (meta && latest) {
      const seRef = latest.source_se_run_id ? ` · SE #${latest.source_se_run_id}` : '';
      meta.textContent = `LF #${latest.run_id}${seRef} · ${fmtTime(latest.calc_time)}`;
    }
  }

  /* ==================== 通用 SVG 折线图（渐变面积 + 阈值参考线 + 十字准星 + 点击跳转） ==================== */
  function renderSimpleLineChart(container, rows, { metricKey, label, unit = '', color = null, threshold = null, thresholdLabel = '', onClickRun = null }) {
    if (!container) return;
    if (!rows?.length) {
      container.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
      return;
    }
    const vals = rows.map((r) => (r[metricKey] != null && Number.isFinite(Number(r[metricKey])) ? Number(r[metricKey]) : null));
    const finite = vals.filter((v) => v !== null);
    if (!finite.length) {
      container.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
      return;
    }
    const rect = container.getBoundingClientRect();
    const W = Math.max(420, Math.floor(rect.width || 620));
    const H = Math.max(160, Math.floor(rect.height || 210));
    const pad = { left: 54, right: 24, top: 14, bottom: 26 };
    const pW = W - pad.left - pad.right;
    const pH = H - pad.top - pad.bottom;
    let minV = Math.min(...finite);
    let maxV = Math.max(...finite);
    if (threshold != null && Number.isFinite(threshold)) {
      minV = Math.min(minV, threshold);
      maxV = Math.max(maxV, threshold);
    }
    if (Math.abs(maxV - minV) < 1e-6) { const sp = Math.max(0.5, Math.abs(maxV) * 0.1); minV -= sp; maxV += sp; }
    else { const m = (maxV - minV) * 0.1; minV -= m; maxV += m; }
    const n = rows.length;
    const xAt = (i) => pad.left + (n === 1 ? pW / 2 : (pW * i) / (n - 1));
    const yAt = (v) => pad.top + pH * (1 - (v - minV) / (maxV - minV));
    const stroke = color || cssVar('--chart-se') || '#2563EB';
    const grid = cssVar('--chart-grid') || '#E2E8F0';
    const muted = cssVar('--text-secondary') || '#64748B';
    const gradId = `lfGrad_${Math.random().toString(36).slice(2, 7)}`;

    let gridSvg = '';
    for (let i = 0; i <= 4; i++) {
      const v = minV + ((maxV - minV) * i) / 4;
      const y = yAt(v);
      gridSvg += `<line x1="${pad.left}" x2="${W - pad.right}" y1="${y}" y2="${y}" stroke="${grid}" stroke-dasharray="3 3"/>`;
      gridSvg += `<text x="${pad.left - 6}" y="${y + 4}" text-anchor="end" font-size="11" fill="${muted}" class="tabular">${fmtNum(v, 2)}</text>`;
    }
    if (unit) gridSvg += `<text x="${pad.left + 4}" y="${pad.top - 2}" font-size="11" fill="${muted}">${esc(unit)}</text>`;
    const xTicks = n <= 5 ? [...Array(n).keys()] : [0, Math.floor((n - 1) * 0.25), Math.floor((n - 1) * 0.5), Math.floor((n - 1) * 0.75), n - 1];
    xTicks.forEach((idx, pos) => {
      const anchor = n === 1 ? 'middle' : pos === 0 ? 'start' : pos === xTicks.length - 1 ? 'end' : 'middle';
      gridSvg += `<text x="${xAt(idx)}" y="${H - 6}" text-anchor="${anchor}" font-size="11" fill="${muted}" class="tabular">${esc(fmtTime(rows[idx].calc_time).slice(11, 16))}</text>`;
    });

    let thrSvg = '';
    if (threshold != null && Number.isFinite(threshold)) {
      const ty = yAt(threshold);
      thrSvg = `<line x1="${pad.left}" x2="${W - pad.right}" y1="${ty.toFixed(1)}" y2="${ty.toFixed(1)}" stroke="var(--sem-warn)" stroke-width="1.3" stroke-dasharray="5 3"/>`
        + (thresholdLabel ? `<text x="${W - pad.right - 4}" y="${(ty - 4).toFixed(1)}" text-anchor="end" font-size="10.5" fill="var(--sem-warn)">${esc(thresholdLabel)}</text>` : '');
    }

    let pathD = '';
    let dots = '';
    let firstX = null;
    let lastX = null;
    vals.forEach((v, i) => {
      if (v === null) return;
      const x = xAt(i); const y = yAt(v);
      if (firstX === null) firstX = x;
      lastX = x;
      pathD += `${pathD ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)} `;
      if (n <= 60) dots += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.7" fill="${stroke}"/>`;
    });
    const areaD = (firstX !== null && lastX !== null && firstX !== lastX)
      ? `${pathD} L${lastX.toFixed(1)},${(H - pad.bottom).toFixed(1)} L${firstX.toFixed(1)},${(H - pad.bottom).toFixed(1)} Z`
      : '';

    container.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="${onClickRun ? 'cursor:pointer' : ''}">
        <defs>
          <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${stroke}" stop-opacity="0.24"/>
            <stop offset="100%" stop-color="${stroke}" stop-opacity="0.01"/>
          </linearGradient>
        </defs>
        ${gridSvg}
        ${thrSvg}
        ${areaD ? `<path d="${areaD}" fill="url(#${gradId})"/>` : ''}
        <path d="${pathD}" fill="none" stroke="${stroke}" stroke-width="2.2" stroke-linejoin="round"/>
        ${dots}
        <line class="se-crosshair" x1="0" x2="0" y1="${pad.top}" y2="${H - pad.bottom}" stroke="${muted}" stroke-dasharray="3 3" visibility="hidden"/>
      </svg>
      <div class="se-chart-tip tabular" hidden></div>`;

    const svgEl = container.querySelector('svg');
    const cross = container.querySelector('.se-crosshair');
    const tip = container.querySelector('.se-chart-tip');
    let curIdx = -1;
    svgEl.addEventListener('mousemove', (e) => {
      const box = svgEl.getBoundingClientRect();
      const relX = ((e.clientX - box.left) / box.width) * W;
      const clamped = Math.max(pad.left, Math.min(W - pad.right, relX));
      curIdx = n === 1 ? 0 : Math.round(((clamped - pad.left) / pW) * (n - 1));
      const cx = xAt(curIdx);
      cross.setAttribute('x1', String(cx));
      cross.setAttribute('x2', String(cx));
      cross.setAttribute('visibility', 'visible');
      const r = rows[curIdx];
      tip.innerHTML = `<div style="color:${muted}">#${r.run_id} · ${esc(fmtTime(r.calc_time))}</div><div>${esc(label)}: <strong>${fmtNum(vals[curIdx], 3)} ${esc(unit)}</strong></div>`;
      tip.hidden = false;
      const left = e.clientX - box.left + 12;
      tip.style.left = `${left + 180 > box.width ? Math.max(6, left - 195) : left}px`;
      tip.style.top = `${Math.max(6, e.clientY - box.top - 24)}px`;
    });
    svgEl.addEventListener('mouseleave', () => { curIdx = -1; cross.setAttribute('visibility', 'hidden'); tip.hidden = true; });
    if (typeof onClickRun === 'function') {
      svgEl.addEventListener('click', () => { if (curIdx >= 0 && rows[curIdx]?.run_id) onClickRun(rows[curIdx].run_id); });
    }
  }

  /* ==================== 1. 主画面 (lf-main.html) ==================== */
  function renderLfHeroStrip(data) {
    const host = document.getElementById('lf-hero-strip');
    if (!host) return;
    const lat = data.latest;
    const pu = lat?.p_unit || 'kW';
    const genP = Number(lat?.total_gen_p || 0);
    const loadP = Number(lat?.total_load_p || 0);
    const acGen = Number(lat?.ac_gen_p || 0);
    const dcGen = Number(lat?.dc_gen_p || 0);
    const acShare = genP > 1e-6 ? Math.round((acGen / genP) * 100) : 0;
    const lossRate = Number(lat?.loss_rate || 0);
    const maxLoad = Number(lat?.max_loading_pct || 0);
    const olWarn = Number(data.params?.overload_warn_pct || 80);
    const olLim = Number(data.params?.overload_limit_pct || 100);
    const vViol = Number(lat?.v_violation_count || 0);
    const olCnt = Number(lat?.overload_count || 0);

    const lossTone = lossRate > 8 ? 'bad' : (lossRate > 5 ? 'warn' : 'ok');
    const loadTone = maxLoad >= olLim ? 'bad' : (maxLoad >= olWarn ? 'warn' : 'ok');
    const vTone = vViol > 0 ? 'bad' : 'ok';

    const tiles = [
      {
        tone: 'accent',
        label: t('kv.total_gen'),
        badge: `AC ${acShare}% / DC ${100 - acShare}%`,
        badgeCls: 'accent',
        val: `${fmtNum(genP, 1)}<small>${esc(pu)}</small>`,
        valCls: '',
        sub: `AC ${fmtNum(acGen, 1)} · DC ${fmtNum(dcGen, 1)}`,
        meter: Math.max(8, Math.min(100, acShare)),
      },
      {
        tone: 'ok',
        label: t('kv.total_load'),
        badge: `${data.bus_total ?? '—'} Bus`,
        badgeCls: 'ok',
        val: `${fmtNum(loadP, 1)}<small>${esc(pu)}</small>`,
        valCls: '',
        sub: `AC ${fmtNum(lat?.ac_load_p, 1)} · DC ${fmtNum(lat?.dc_load_p, 1)}`,
        meter: genP > 1e-6 ? Math.min(100, (loadP / genP) * 100) : 0,
      },
      {
        tone: lossTone,
        label: t('kv.loss_rate'),
        badge: `${fmtNum(lat?.total_loss_p, 2)} ${pu}`,
        badgeCls: lossTone,
        val: `${fmtNum(lossRate, 2)}<small>%</small>`,
        valCls: lossTone,
        sub: `AC ${fmtNum(lat?.ac_loss_p, 2)} · DC ${fmtNum(lat?.dc_loss_p, 2)}`,
        meter: Math.min(100, lossRate * 10),
      },
      {
        tone: loadTone,
        label: t('kv.max_load'),
        badge: olCnt > 0 ? `过载 ${olCnt}` : '安全裕度足',
        badgeCls: loadTone,
        val: `${fmtNum(maxLoad, 1)}<small>%</small>`,
        valCls: loadTone,
        sub: lat?.max_loading_dev || '—',
        subDev: lat?.max_loading_dev || '',
        meter: Math.min(100, maxLoad),
      },
      {
        tone: vTone,
        label: t('kv.alerts'),
        badge: vViol > 0 ? `越限 ${vViol}` : '电压正常',
        badgeCls: vTone,
        val: lat?.min_v_pu != null ? `${Number(lat.min_v_pu).toFixed(3)}<small>~${Number(lat.max_v_pu || 1).toFixed(3)}</small>` : '—',
        valCls: vTone,
        sub: lat?.min_v_bus ? `最低 ${lat.min_v_bus}` : '—',
        subDev: lat?.min_v_bus || '',
        meter: lat?.min_v_pu != null ? Math.max(0, Math.min(100, (Number(lat.min_v_pu) - 0.85) / 0.25 * 100)) : 0,
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
          ${c.subDev
            ? `<a class="pas-hero-sub pas-clickable" data-pas-device="${esc(c.subDev)}" title="${esc(c.sub)}">${esc(c.sub)}</a>`
            : `<span class="pas-hero-sub tabular" title="${esc(c.sub)}">${esc(c.sub)}</span>`}
        </div>
        <div class="pas-hero-meter"><i style="width:${Math.max(0, Math.min(100, c.meter)).toFixed(1)}%"></i></div>
      </div>`).join('');
  }

  async function loadHomeView() {
    const data = await api('/api/lf/home');
    st.home = data;
    const latest = data.latest;
    st.lastRunId = latest?.run_id ?? null;
    updateStatusPill(latest);
    const pu = latest?.p_unit || 'kW';
    const uu = latest?.u_unit || 'V';

    // 顶部 5 格大屏态势带
    renderLfHeroStrip(data);

    // 左栏 1：动态光流交直流桑基图
    const skMeta = document.getElementById('lf-sankey-meta');
    if (skMeta) skMeta.textContent = latest ? `${fmtNum(latest.total_gen_p, 1)} ${pu} · L ${fmtNum(latest.loss_rate, 2)}%` : '—';
    if (window.PAS_KIT?.renderSankey) {
      window.PAS_KIT.renderSankey(document.getElementById('lf-home-sankey'), {
        leftNodes: [
          { label: '交流发电', value: Number(latest?.ac_gen_p || 0), color: '#38bdf8' },
          { label: '直流发电', value: Number(latest?.dc_gen_p || 0), color: '#22c55e' },
        ],
        midNode: { label: '交直流母线', color: 'var(--accent)' },
        rightNodes: [
          { label: '交流负荷', value: Number(latest?.ac_load_p || 0), color: '#6366f1' },
          { label: '直流负荷', value: Number(latest?.dc_load_p || 0), color: '#14b8a6' },
          { label: '交流网损', value: Number(latest?.ac_loss_p || 0), color: '#f59e0b' },
          { label: '直流网损', value: Number(latest?.dc_loss_p || 0), color: '#ef4444' },
        ],
        unit: pu,
        height: 170,
        compact: true,
      });
    }

    // 左栏 2：交直流源荷结构环形图
    const mixMeta = document.getElementById('lf-mix-meta');
    if (mixMeta) mixMeta.textContent = latest ? `网损 ${fmtNum(latest.total_loss_p, 2)} ${pu}` : '—';
    if (window.PAS_KIT?.renderDonut) {
      window.PAS_KIT.renderDonut(document.getElementById('lf-home-mix-donut'), {
        slices: [
          { label: '交流负荷', value: Number(Number(latest?.ac_load_p || 0).toFixed(1)), color: '#6366f1' },
          { label: '直流负荷', value: Number(Number(latest?.dc_load_p || 0).toFixed(1)), color: '#14b8a6' },
          { label: '交流网损', value: Number(Number(latest?.ac_loss_p || 0).toFixed(2)), color: '#f59e0b' },
          { label: '直流网损', value: Number(Number(latest?.dc_loss_p || 0).toFixed(2)), color: '#ef4444' },
        ],
        centerTitle: `总计 ${pu}`,
        centerValue: fmtNum(latest?.total_gen_p, 1),
        size: 98,
      });
    }

    // 左栏 3：互联换流器动态工况条（无换流器时降级为 AC/DC 网损对比）
    const convHost = document.getElementById('lf-home-converters');
    if (convHost) {
      const convs = data.converters || [];
      if (convs.length) {
        convHost.innerHTML = `<div class="pas-conv-list">${convs.slice(0, 4).map((c) => {
          const pct = Math.max(0, Math.min(100, Number(c.loading_pct || 0)));
          const col = c.overload ? 'var(--sem-danger)' : (pct >= 80 ? 'var(--sem-warn)' : 'var(--accent)');
          const dir = Number(c.p_from || 0) >= 0 ? '→' : '←';
          return `<div class="pas-conv-card">
            <div class="pas-conv-head">
              <a class="pas-clickable" data-pas-device="${esc(c.device_name)}" title="${esc(c.device_type)}">${esc(c.device_name)}</a>
              <span class="tabular"><strong>${fmtNum(Math.abs(Number(c.p_from || 0)), 1)} ${esc(pu)}</strong> ${dir} · <strong style="color:${col}">${fmtNum(pct, 1)}%</strong></span>
            </div>
            <div class="pas-conv-bar"><i style="width:${Math.max(3, pct).toFixed(1)}%;background:${col}"></i></div>
          </div>`;
        }).join('')}</div>`;
      } else if (window.PAS_KIT?.renderBarChart) {
        window.PAS_KIT.renderBarChart(convHost, {
          items: [
            { label: t('kv.ac_loss'), value: Number(latest?.ac_loss_p || 0), color: '#f59e0b' },
            { label: t('kv.dc_loss'), value: Number(latest?.dc_loss_p || 0), color: '#ef4444' },
          ],
          unit: pu,
          digits: 2,
        });
      }
    }

    // 中栏 1 & 2：母线电压分布直方图 + 支路负载率分布直方图
    const vDistMeta = document.getElementById('lf-vdist-meta');
    if (vDistMeta) vDistMeta.textContent = `${data.bus_total ?? 0} 母线`;
    if (window.PAS_KIT?.renderHistogram) {
      window.PAS_KIT.renderHistogram(document.getElementById('lf-home-vbins'), {
        bins: data.voltage_bins || [],
        unit: '条母线',
        height: 106,
      });
    }

    const lDistMeta = document.getElementById('lf-ldist-meta');
    if (lDistMeta) lDistMeta.textContent = `${data.branch_total ?? 0} 支路`;
    if (window.PAS_KIT?.renderHistogram) {
      window.PAS_KIT.renderHistogram(document.getElementById('lf-home-lbins'), {
        bins: data.loading_bins || [],
        unit: '条支路',
        height: 106,
      });
    }

    // 中栏 3：求解基态与方式控制胶囊
    const seSrc = document.getElementById('lf-se-src-link');
    if (seSrc) {
      seSrc.innerHTML = latest?.source_se_run_id
        ? `<a class="se-more-link" style="margin:0;padding:0" href="/se-flow.html?run_id=${latest.source_se_run_id}">SE #${latest.source_se_run_id} →</a>`
        : '<span class="se-muted">—</span>';
    }
    const baseChips = document.getElementById('lf-home-base-chips');
    if (baseChips) {
      baseChips.innerHTML = [
        [t('kv.iters'), latest ? `${latest.iterations} (${latest.ac_iterations ?? '—'}/${latest.dc_iterations ?? '—'})` : '—', ''],
        [t('kv.norm_f'), latest?.norm_f != null ? Number(latest.norm_f).toExponential(1) : '—', ''],
        [t('kv.elapsed'), latest?.elapsed_seconds != null ? `${Number(latest.elapsed_seconds).toFixed(3)} s` : '—', ''],
        [t('kv.overrides'), `${data.overrides?.enabled ?? 0} / ${data.overrides?.total ?? 0}`, (data.overrides?.enabled || 0) > 0 ? 'warn' : ''],
      ].map(([k, v, cls]) => `<div class="pas-stat-chip"><span>${esc(k)}</span><strong class="tabular ${cls}">${esc(v)}</strong></div>`).join('');
    }

    // 右上：趋势曲线摘要与图表
    document.getElementById('lf-home-rate-items').innerHTML = `
      <span class="se-home-rate-item"><span>${esc(t('kv.total_load'))}</span><strong class="tabular">${fmtNum(latest?.total_load_p, 2)} ${esc(pu)}</strong></span>
      <span class="se-home-rate-item"><span>${esc(t('kv.loss_rate'))}</span><strong class="tabular ok">${fmtNum(latest?.loss_rate, 2)}%</strong></span>
      <span class="se-home-rate-item"><span>${esc(t('kv.max_load'))}</span><strong class="tabular ${(latest?.max_loading_pct || 0) >= 80 ? 'bad' : ''}">${fmtNum(latest?.max_loading_pct, 1)}%</strong></span>
    `;
    renderHomeChart();

    // 右下左卡：重过载排行
    const loadHost = document.getElementById('lf-home-top-load');
    const topLoad = data.top_loading || [];
    if (window.PAS_KIT?.renderBarChart) {
      window.PAS_KIT.renderBarChart(loadHost, {
        items: topLoad.slice(0, 8).map((b) => ({
          label: b.device_name,
          device: b.device_name,
          value: Number(b.loading_pct || 0),
          sub: `有功 ${fmtNum(b.p_from, 2)} ${pu}`,
          subShort: `${fmtNum(b.p_from, 1)}${pu}`,
          color: b.overload ? '#ef4444' : ((b.loading_pct || 0) >= 80 ? '#f59e0b' : 'var(--accent)'),
        })),
        maxVal: 100,
        threshold: Number(data.params?.overload_warn_pct || 80),
        unit: '%',
        digits: 1,
        emptyText: t('common.empty'),
      });
    }

    // 右下右卡：电压双向偏差图
    const vHost = document.getElementById('lf-home-v-extremes');
    const vList = data.voltage_extremes || [];
    if (window.PAS_KIT?.renderDivergingBar) {
      window.PAS_KIT.renderDivergingBar(vHost, {
        items: vList.slice(0, 8).map((b) => ({
          label: b.device_name,
          device: b.device_name,
          value: Number(b.v_pu || 1.0),
          sub: `实际电压 ${fmtNum(b.v_eng, 2)} ${uu}`,
        })),
        center: 1.0,
        span: 0.22,
        lowWarn: Number(data.params?.v_min_pu || 0.93),
        highWarn: Number(data.params?.v_max_pu || 1.07),
        unit: 'pu',
        emptyText: t('common.empty'),
      });
    }

    const log = data.latest_log;
    if (log) {
      document.getElementById('lf-log-tag').textContent = log.level || 'INFO';
      document.getElementById('lf-log-msg').textContent = log.message || '—';
      document.getElementById('lf-log-time').textContent = fmtTime(log.calc_time);
      const foot = document.getElementById('lf-home-footer-log');
      if (foot && log.run_id) foot.href = `/lf-logs.html?run_id=${log.run_id}`;
    }
  }

  function renderHomeChart() {
    if (!st.home) return;
    const rows = st.home.trend_series || [];
    const m = st.homeMetric;
    const uMap = { loss_rate: '%', max_loading_pct: '%', total_load_p: st.home.latest?.p_unit || 'kW', min_v_pu: 'pu' };
    const lMap = { loss_rate: t('metric.loss_rate'), max_loading_pct: t('metric.max_load'), total_load_p: t('metric.total_load'), min_v_pu: t('metric.min_v') };
    const thrMap = {
      max_loading_pct: Number(st.home.params?.overload_warn_pct || 80),
      min_v_pu: Number(st.home.params?.v_min_pu || 0.93),
    };
    const thrLblMap = {
      max_loading_pct: `预警 ${thrMap.max_loading_pct}%`,
      min_v_pu: `下限 ${thrMap.min_v_pu} pu`,
    };
    renderSimpleLineChart(document.getElementById('lf-home-chart'), rows, {
      metricKey: m,
      label: lMap[m] || m,
      unit: uMap[m] || '',
      threshold: thrMap[m] ?? null,
      thresholdLabel: thrLblMap[m] || '',
      onClickRun: (rid) => { window.location.href = `/lf-flow.html?run_id=${rid}`; },
    });
  }

  /* ==================== 2. 在线潮流图 (lf-flow.html) ==================== */
  async function ensureSvgLoaded() {
    if (st.svgLoaded) return;
    const canvas = document.getElementById('lf-svg-canvas');
    if (!canvas) return;
    const resp = await fetch('/api/se/svg');
    if (!resp.ok) { canvas.innerHTML = `<div class="se-empty">SVG unavailable</div>`; return; }
    canvas.innerHTML = await resp.text();
    const svg = canvas.querySelector('svg');
    if (!svg) return;
    const vb = (svg.getAttribute('viewBox') || '0 0 2518 2143').split(/\s+/).map(Number);
    st.svgT.vbW = vb[2] || 2518;
    st.svgT.vbH = vb[3] || 2143;
    svg.removeAttribute('width'); svg.removeAttribute('height');
    svg.style.width = `${st.svgT.vbW}px`; svg.style.height = `${st.svgT.vbH}px`;
    st.svgLoaded = true;
    setupSvgPanZoom();
    fitSvg();
  }

  function applySvgT() {
    const c = document.getElementById('lf-svg-canvas');
    if (c) c.style.transform = `translate(${st.svgT.tx}px, ${st.svgT.ty}px) scale(${st.svgT.scale})`;
    const lbl = document.getElementById('svg-zoom-label');
    if (lbl) lbl.textContent = `${Math.round(st.svgT.scale * 100)}%`;
  }
  function fitSvg() {
    const vp = document.getElementById('lf-svg-viewport');
    if (!vp) return;
    const r = vp.getBoundingClientRect();
    const s = Math.min((r.width - 24) / st.svgT.vbW, (r.height - 24) / st.svgT.vbH);
    st.svgT.scale = Math.max(0.15, Math.min(2.5, s || 0.45));
    st.svgT.tx = (r.width - st.svgT.vbW * st.svgT.scale) / 2;
    st.svgT.ty = (r.height - st.svgT.vbH * st.svgT.scale) / 2;
    applySvgT();
  }
  function zoomSvg(factor, cx, cy) {
    const vp = document.getElementById('lf-svg-viewport');
    if (!vp) return;
    const r = vp.getBoundingClientRect();
    const ox = cx ?? r.width / 2; const oy = cy ?? r.height / 2;
    const prev = st.svgT.scale;
    const next = Math.max(0.15, Math.min(4, prev * factor));
    st.svgT.tx = ox - ((ox - st.svgT.tx) * next) / prev;
    st.svgT.ty = oy - ((oy - st.svgT.ty) * next) / prev;
    st.svgT.scale = next;
    applySvgT();
  }
  function setupSvgPanZoom() {
    const vp = document.getElementById('lf-svg-viewport');
    if (!vp) return;
    let drag = false; let moved = false; let sx = 0; let sy = 0; let stx = 0; let sty = 0;
    vp.addEventListener('wheel', (e) => {
      e.preventDefault();
      const r = vp.getBoundingClientRect();
      zoomSvg(e.deltaY < 0 ? 1.15 : 0.87, e.clientX - r.left, e.clientY - r.top);
    }, { passive: false });
    vp.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      drag = true; moved = false; sx = e.clientX; sy = e.clientY; stx = st.svgT.tx; sty = st.svgT.ty;
    });
    window.addEventListener('pointermove', (e) => {
      if (!drag) return;
      if (Math.hypot(e.clientX - sx, e.clientY - sy) > 4) moved = true;
      st.svgT.tx = stx + (e.clientX - sx); st.svgT.ty = sty + (e.clientY - sy);
      applySvgT();
    });
    window.addEventListener('pointerup', () => { drag = false; });
    vp.addEventListener('click', (e) => {
      if (moved) return;
      const el = e.target.closest('[dev-id], g.mg[dev]');
      if (!el) return;
      const did = el.getAttribute('dev-id') || el.getAttribute('dev');
      if (did && st.topo?.devices?.[did]) selectFlowDevice(did);
    });
  }

  function focusFlowDevice(devId) {
    selectFlowDevice(devId);
    const svg = document.querySelector('#lf-svg-canvas svg');
    const vp = document.getElementById('lf-svg-viewport');
    if (!svg || !vp) return;
    const el = svg.querySelector(`[dev-id="${CSS.escape(devId)}"]`) || svg.querySelector(`g.mg[dev="${CSS.escape(devId)}"]`);
    if (!el) return;
    try {
      const bb = el.getBBox();
      const r = vp.getBoundingClientRect();
      st.svgT.scale = Math.max(st.svgT.scale, 0.9);
      st.svgT.tx = r.width / 2 - (bb.x + bb.width / 2) * st.svgT.scale;
      st.svgT.ty = r.height / 2 - (bb.y + bb.height / 2) * st.svgT.scale;
      applySvgT();
    } catch (_) {}
  }

  function renderLfSvgBindings() {
    const svg = document.querySelector('#lf-svg-canvas svg');
    if (!svg || !st.topo) return;
    const devices = st.topo.devices || {};
    const mode = st.svgMode;
    const cLf = cssVar('--chart-se') || '#2563EB';
    const cOk = cssVar('--chart-ok') || '#0D9488';
    const cWarn = cssVar('--sem-warn') || '#D97706';
    const cBad = cssVar('--chart-bad') || '#DC2626';

    svg.querySelectorAll('.se-bad-ring').forEach((n) => n.remove());
    svg.querySelectorAll('.se-bad-device,.se-dev-selected').forEach((n) => n.classList.remove('se-bad-device', 'se-dev-selected'));

    svg.querySelectorAll('g.mg[dev]').forEach((mg) => {
      const did = mg.getAttribute('dev');
      const dev = devices[did];
      if (!dev) return;
      const slots = dev.svg_slots || {};
      let boxAlert = Boolean(dev.has_alert);
      mg.querySelectorAll('text').forEach((textEl) => {
        const mv = textEl.querySelector('tspan.mv[mt]');
        if (!mv) return;
        const slot = slots[mv.getAttribute('mt')];
        if (!slot) return;
        const tspans = Array.from(textEl.children).filter((n) => n.tagName.toLowerCase() === 'tspan');
        const unitSpan = tspans.length >= 3 ? tspans[tspans.length - 1] : null;
        if (mode === 'loading') {
          mv.textContent = slot.loading_pct != null ? `${fmtNum(slot.loading_pct, 1)}` : fmtNum(slot.lf);
          if (unitSpan) unitSpan.textContent = slot.loading_pct != null ? '%' : (slot.unit || '');
          mv.setAttribute('fill', slot.is_alert ? cBad : ((slot.loading_pct || 0) >= 80 ? cWarn : cOk));
        } else if (mode === 'diff') {
          const d = slot.diff;
          mv.textContent = d == null ? '—' : `${d >= 0 ? '+' : ''}${fmtNum(d, 2)}`;
          if (unitSpan) unitSpan.textContent = slot.unit || '';
          mv.setAttribute('fill', slot.is_alert ? cBad : cLf);
        } else {
          mv.textContent = fmtNum(slot.lf);
          if (unitSpan) unitSpan.textContent = slot.unit || '';
          mv.setAttribute('fill', slot.is_alert ? cBad : cLf);
        }
      });
      let bg = mg.querySelector('rect.se-mg-bg');
      if (bg) bg.remove();
      try {
        const bb = mg.getBBox();
        if (bb.width > 0 && bb.height > 0) {
          bg = document.createElementNS(SVG_NS, 'rect');
          bg.setAttribute('class', `se-mg-bg${boxAlert ? ' is-bad' : ''}`);
          bg.setAttribute('x', String(bb.x - 5)); bg.setAttribute('y', String(bb.y - 3));
          bg.setAttribute('width', String(bb.width + 10)); bg.setAttribute('height', String(bb.height + 6));
          mg.insertBefore(bg, mg.firstChild);
        }
      } catch (_) {}
    });

    (st.topo.alert_dev_ids || []).forEach((did) => {
      svg.querySelectorAll(`[dev-id="${CSS.escape(did)}"]`).forEach((el) => {
        if ((el.id || '').startsWith('label_')) return;
        el.classList.add('se-bad-device');
        try {
          const bb = el.getBBox();
          if (bb.width > 0 && bb.height > 0 && el.parentNode) {
            const ring = document.createElementNS(SVG_NS, 'rect');
            ring.setAttribute('class', 'se-bad-ring');
            ring.setAttribute('x', String(bb.x - 10)); ring.setAttribute('y', String(bb.y - 10));
            ring.setAttribute('width', String(bb.width + 20)); ring.setAttribute('height', String(bb.height + 20));
            ring.setAttribute('rx', '10');
            if (el.getAttribute('transform')) ring.setAttribute('transform', el.getAttribute('transform'));
            el.parentNode.insertBefore(ring, el);
          }
        } catch (_) {}
      });
    });

    if (st.selectedDevId) {
      svg.querySelectorAll(`[dev-id="${CSS.escape(st.selectedDevId)}"]`).forEach((el) => {
        if (!(el.id || '').startsWith('label_')) el.classList.add('se-dev-selected');
      });
    }
  }

  function renderFlowSidePanels() {
    const alerts = st.topo?.alerts || [];
    const pill = document.getElementById('lf-alert-count');
    if (pill) {
      pill.textContent = String(alerts.length);
      pill.className = `se-pill tabular ${alerts.length ? 'bad' : 'ok'}`;
    }
    const list = document.getElementById('lf-alert-list');
    if (list) {
      list.innerHTML = alerts.length ? alerts.map((a) => `
        <button type="button" class="se-bad-item" data-lf-focus="${esc(a.dev_id)}">
          <div class="top"><span>${esc(a.device_name)}</span><span class="tabular">${fmtNum(a.value, 2)} ${esc(a.unit)}</span></div>
          <div class="vals">${esc(a.detail)}</div>
        </button>`).join('') : `<div class="se-empty">—</div>`;
    }
    const jump = document.getElementById('lf-device-jump');
    if (jump && st.topo?.devices) {
      const devs = Object.values(st.topo.devices).sort((a, b) => a.name.localeCompare(b.name));
      jump.innerHTML = `<option value="">${esc(t('topo.jump_ph'))}</option>` + devs.map((d) => `<option value="${esc(d.dev_id)}">${esc(d.name)} (${esc(d.device_type)})</option>`).join('');
      if (st.selectedDevId) jump.value = st.selectedDevId;
    }
  }

  function selectFlowDevice(devId) {
    st.selectedDevId = devId;
    renderLfSvgBindings();
    const dev = st.topo?.devices?.[devId];
    const tEl = document.getElementById('lf-insp-title');
    const tpEl = document.getElementById('lf-insp-type');
    const bEl = document.getElementById('lf-insp-body');
    if (!dev || !bEl) {
      if (tEl) tEl.textContent = t('flow.dev_detail');
      if (tpEl) tpEl.textContent = '—';
      if (bEl) bEl.innerHTML = `<div class="se-empty">—</div>`;
      return;
    }
    tEl.textContent = dev.name;
    tpEl.textContent = `${dev.device_type} #${dev.idx}`;
    const adjTypes = ['ACBreak', 'DCBreak', 'ACGenerator', 'DCGenerator', 'ACLoad', 'DCLoad', 'ACBranch', 'DCBranch', 'ACZeroBranch', 'DCDCConverter', 'DCACConverter'];
    const canAdj = adjTypes.includes(dev.device_type);
    const bar = canAdj ? `
      <div class="se-insp-actions">
        <button type="button" class="se-btn primary mini" data-lf-adjust="${esc(dev.device_type)}|${dev.idx}|${esc(dev.name)}">${esc(t('action.adjust'))}</button>
      </div>` : '';
    const rows = Object.values(dev.metrics || {}).map((m) => `
      <tr class="${m.is_alert ? 'is-bad' : ''}">
        <td>${esc(m.metric)} <small class="se-muted">${esc(m.unit)}</small></td>
        <td class="num tabular"><strong>${fmtNum(m.lf, 3)}</strong></td>
        <td class="num tabular">${fmtNum(m.se, 3)}</td>
        <td class="num tabular">${m.diff == null ? '—' : `${m.diff >= 0 ? '+' : ''}${fmtNum(m.diff, 3)}`}</td>
      </tr>`).join('');
    const lat = st.topo?.latest;
    const sysCard = lat ? `
      <div class="se-kv-divider" style="margin:8px 0 6px"></div>
      <div style="font-size:11.5px;font-weight:700;color:var(--text-secondary);margin-bottom:4px">当前断面摘要 · LF #${lat.run_id}</div>
      <div class="se-kv-list">
        <div class="se-kv-row"><span class="k">源 SE 断面</span><span class="v tabular">${lat.source_se_run_id ? `SE #${lat.source_se_run_id}` : '—'}</span></div>
        <div class="se-kv-row"><span class="k">总发电 / 总负荷</span><span class="v tabular">${fmtNum(lat.total_gen_p, 1)} / ${fmtNum(lat.total_load_p, 1)} ${esc(lat.p_unit || 'kW')}</span></div>
        <div class="se-kv-row"><span class="k">全网网损率</span><span class="v tabular">${fmtNum(lat.loss_rate, 3)}% (${fmtNum(lat.total_loss_p, 2)} ${esc(lat.p_unit || 'kW')})</span></div>
        <div class="se-kv-row"><span class="k">最大支路负载率</span><span class="v tabular">${fmtNum(lat.max_loading_pct, 1)}% (${esc(lat.max_loading_dev || '—')})</span></div>
        <div class="se-kv-row"><span class="k">最低 / 最高电压</span><span class="v tabular">${fmtNum(lat.min_v_pu, 4)} / ${fmtNum(lat.max_v_pu, 4)} pu</span></div>
      </div>` : '';
    bEl.innerHTML = `${bar}
      ${dev.loading_pct != null ? `<div class="se-kv-row" style="padding:3px 0"><span class="k">${esc(t('col.loading'))}</span><strong class="v tabular">${fmtNum(dev.loading_pct, 1)}%</strong></div>` : ''}
      ${dev.alert_reason ? `<div class="se-kv-row" style="padding:3px 0"><span class="k">状态</span><strong class="v bad">${esc(dev.alert_reason)}</strong></div>` : ''}
      <table class="se-insp-table">
        <thead><tr><th>Metric</th><th class="num">LF</th><th class="num">SE</th><th class="num">Δ</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>${sysCard}`;
  }

  async function loadFlowView() {
    const url = st.selectedRunId ? `/api/lf/topology-values?run_id=${encodeURIComponent(st.selectedRunId)}` : '/api/lf/topology-values';
    st.topo = await api(url);
    updateStatusPill(st.topo.latest);
    await ensureSvgLoaded();
    renderFlowSidePanels();
    renderLfSvgBindings();
    const qp = new URLSearchParams(window.location.search);
    const qpDevName = qp.get('device');
    let targetDevId = qp.get('dev_id');
    if (!targetDevId && qpDevName && st.topo?.devices) {
      const hit = Object.entries(st.topo.devices).find(([, d]) => String(d.device_name || d.name || '') === qpDevName);
      if (hit) targetDevId = hit[0];
    }
    if (!st.selectedDevId && targetDevId && st.topo.devices?.[targetDevId]) {
      focusFlowDevice(targetDevId);
    } else {
      // 默认选中首个告警设备（无告警时选中负载率最高设备），避免右侧「设备潮流」整块空白
      if (!st.selectedDevId || !st.topo.devices?.[st.selectedDevId]) {
        const firstAlert = (st.topo.alerts || [])[0]?.dev_id;
        if (firstAlert && st.topo.devices?.[firstAlert]) {
          st.selectedDevId = firstAlert;
        } else {
          const allDevs = Object.values(st.topo.devices || {});
          allDevs.sort((a, b) => (Number(b.loading_pct) || -1) - (Number(a.loading_pct) || -1));
          if (allDevs[0]?.dev_id) st.selectedDevId = allDevs[0].dev_id;
        }
      }
      selectFlowDevice(st.selectedDevId);
    }
    // 注入负载热力图例与动态流向开关（幂等）
    const zoomBar = document.querySelector('#lf-svg-viewport')?.previousElementSibling;
    if (zoomBar && !document.getElementById('lf-flow-legend')) {
      const legend = document.createElement('span');
      legend.id = 'lf-flow-legend';
      legend.className = 'pas-flow-legend';
      legend.innerHTML = '<span><i style="background:#22c55e"></i>&lt;60%</span><span><i style="background:#f59e0b"></i>60–80%</span><span><i style="background:#ef4444"></i>&gt;80%</span>';
      const animBtn = document.createElement('button');
      animBtn.type = 'button';
      animBtn.className = 'se-btn mini';
      animBtn.textContent = '流向动效';
      animBtn.addEventListener('click', () => {
        const svgEl = document.querySelector('#lf-svg-canvas svg');
        if (!svgEl) return;
        const on = svgEl.classList.toggle('pas-flow-animated');
        animBtn.classList.toggle('primary', on);
      });
      zoomBar.appendChild(legend);
      zoomBar.appendChild(animBtn);
    }
  }

  /* ==================== 3. 潮流明细与趋势 (lf-results.html) ==================== */
  async function loadResultsView() {
    const r = st.res;
    const isTrend = r.kind === 'trend';
    document.querySelectorAll('#lf-res-subtab-seg .seg').forEach((b) => b.classList.toggle('active', b.dataset.kind === r.kind));
    document.getElementById('lf-res-filters').hidden = isTrend;
    document.getElementById('lf-trend-controls').hidden = !isTrend;
    document.getElementById('lf-res-table-wrap').hidden = isTrend;
    document.getElementById('lf-res-pager').hidden = isTrend;
    document.getElementById('lf-trend-chart-host').hidden = !isTrend;
    document.getElementById('btn-lf-export').hidden = isTrend;

    if (isTrend) {
      const series = await api(`/api/lf/history/stats?limit=${r.trendLimit}`);
      const m = r.trendMetric;
      const uMap = { loss_rate: '%', max_loading_pct: '%', total_load_p: series[0]?.p_unit || 'kW', min_v_pu: 'pu', elapsed_seconds: 's' };
      const lMap = { loss_rate: t('metric.loss_rate'), max_loading_pct: t('metric.max_load'), total_load_p: t('metric.total_load'), min_v_pu: t('metric.min_v'), elapsed_seconds: t('metric.elapsed') };
      renderSimpleLineChart(document.getElementById('lf-trend-chart-host'), series, {
        metricKey: m,
        label: lMap[m] || m,
        unit: uMap[m] || '',
        onClickRun: (rid) => { window.location.href = `/lf-flow.html?run_id=${rid}`; },
      });
      return;
    }

    const qs = new URLSearchParams({
      kind: r.kind,
      domain: r.domain,
      device_type: r.devType,
      only_abnormal: r.onlyAbn ? '1' : '0',
      q: r.q,
      limit: String(r.size),
      offset: String(r.page * r.size),
    });
    if (st.selectedRunId) qs.set('run_id', st.selectedRunId);
    const data = await api(`/api/lf/results?${qs}`);
    updateStatusPill(data.latest);
    const dtSel = document.getElementById('lf-res-devtype');
    if (dtSel) {
      dtSel.innerHTML = `<option value="">${esc(t('common.all'))}</option>` + (data.available_types || []).map((x) => `<option value="${esc(x)}">${esc(x)}</option>`).join('');
      dtSel.value = r.devType;
    }
    const wrap = document.getElementById('lf-res-table-wrap');
    const rows = data.rows || [];
    const pu = data.latest?.p_unit || 'kW';
    const uu = data.latest?.u_unit || 'V';
    const iu = data.latest?.i_unit || 'A';
    if (!rows.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
    } else if (r.kind === 'buses') {
      wrap.innerHTML = `<table class="se-data-table"><thead><tr>
        <th>${esc(t('col.idx'))}</th><th>${esc(t('col.domain'))}</th><th>${esc(t('col.device'))}</th>
        <th class="num">${esc(t('col.vbase'))}</th><th class="num">${esc(t('col.v_pu'))}</th><th class="num">${esc(t('col.v_eng'))} (${esc(uu)})</th>
        <th class="num">${esc(t('col.angle'))}</th><th class="num">${esc(t('col.v_se_diff'))}</th><th>${esc(t('col.status'))}</th><th class="se-sticky-right">${esc(t('col.ops'))}</th>
      </tr></thead><tbody>${rows.map((x) => `<tr class="${x.v_status !== 'normal' ? 'row-bad' : ''}">
        <td class="tabular">${x.device_idx}</td><td><span class="se-pill neutral">${esc(x.domain)}</span></td>
        <td><strong>${esc(x.device_name)}</strong></td><td class="num tabular">${fmtNum(x.vbase, 1)}</td>
        <td class="num tabular ${x.v_status !== 'normal' ? 'cell-bad' : ''}">${x.v_pu != null ? Number(x.v_pu).toFixed(4) : '—'}</td>
        <td class="num tabular">${fmtNum(x.v_eng, 2)}</td><td class="num tabular">${fmtNum(x.angle_deg, 2)}</td>
        <td class="num tabular">${fmtNum(x.v_se, 2)} / ${x.v_diff == null ? '—' : `${x.v_diff >= 0 ? '+' : ''}${fmtNum(x.v_diff, 2)}`}</td>
        <td><span class="se-pill ${x.v_status === 'normal' ? 'ok' : 'bad'}">${esc(x.v_status)}</span></td>
        <td class="se-sticky-right"><a class="se-btn mini se-link-btn" href="/lf-flow.html?dev_id=${encodeURIComponent(`${x.device_type}-${x.device_idx}`)}${st.selectedRunId ? `&run_id=${st.selectedRunId}` : ''}">${esc(t('action.locate'))}</a></td>
      </tr>`).join('')}</tbody></table>`;
    } else if (r.kind === 'units') {
      wrap.innerHTML = `<table class="se-data-table"><thead><tr>
        <th>${esc(t('col.idx'))}</th><th>${esc(t('col.dev_type'))}</th><th>${esc(t('col.device'))}</th><th>${esc(t('col.ctrl'))}</th>
        <th class="num">${esc(t('col.p_lf'))} (${esc(pu)})</th><th class="num">${esc(t('col.q_lf'))}</th><th class="num">${esc(t('col.v_lf'))} (${esc(uu)})</th><th class="num">${esc(t('col.i_lf'))} (${esc(iu)})</th>
        <th class="num">${esc(t('col.loading'))}</th><th class="num">${esc(t('col.p_se_diff'))}</th><th class="se-sticky-right">${esc(t('col.ops'))}</th>
      </tr></thead><tbody>${rows.map((x) => `<tr class="${x.overload ? 'row-bad' : ''}">
        <td class="tabular">${x.device_idx ?? '—'}</td><td>${esc(x.device_type)}</td><td><strong>${esc(x.device_name)}</strong></td>
        <td><span class="se-tag">${esc(x.control_type || '—')}</span></td>
        <td class="num tabular">${fmtNum(x.p_lf, 3)}</td><td class="num tabular">${fmtNum(x.q_lf, 3)}</td>
        <td class="num tabular">${fmtNum(x.v_lf, 2)}</td><td class="num tabular">${fmtNum(x.i_lf, 2)}</td>
        <td class="num tabular ${x.overload ? 'cell-bad' : ''}">${x.loading_pct != null ? `${fmtNum(x.loading_pct, 1)}%` : '—'}</td>
        <td class="num tabular">${fmtNum(x.p_se, 2)} / ${x.p_diff == null ? '—' : `${x.p_diff >= 0 ? '+' : ''}${fmtNum(x.p_diff, 2)}`}</td>
        <td class="se-sticky-right"><a class="se-btn mini se-link-btn" href="/lf-flow.html?dev_id=${encodeURIComponent(`${x.device_type}-${x.device_idx}`)}${st.selectedRunId ? `&run_id=${st.selectedRunId}` : ''}">${esc(t('action.locate'))}</a></td>
      </tr>`).join('')}</tbody></table>`;
    } else {
      wrap.innerHTML = `<table class="se-data-table"><thead><tr>
        <th>${esc(t('col.idx'))}</th><th>${esc(t('col.dev_type'))}</th><th>${esc(t('col.device'))}</th>
        <th class="num">${esc(t('col.p_from'))} (${esc(pu)})</th><th class="num">${esc(t('col.q_from'))}</th><th class="num">${esc(t('col.i_from'))} (${esc(iu)})</th>
        <th class="num">${esc(t('col.p_to'))}</th><th class="num">${esc(t('col.p_loss'))}</th>
        <th class="num">${esc(t('col.loading'))}</th><th class="num">${esc(t('col.p_se_diff'))}</th><th class="se-sticky-right">${esc(t('col.ops'))}</th>
      </tr></thead><tbody>${rows.map((x) => `<tr class="${x.overload ? 'row-bad' : ''}">
        <td class="tabular">${x.device_idx ?? '—'}</td><td>${esc(x.device_type)}</td><td><strong>${esc(x.device_name)}</strong></td>
        <td class="num tabular">${fmtNum(x.p_from, 3)}</td><td class="num tabular">${fmtNum(x.q_from, 3)}</td>
        <td class="num tabular">${fmtNum(x.i_from, 2)}</td><td class="num tabular">${fmtNum(x.p_to, 3)}</td>
        <td class="num tabular">${fmtNum(x.p_loss, 4)}</td>
        <td class="num tabular ${x.overload ? 'cell-bad' : ''}">${x.loading_pct != null ? `${fmtNum(x.loading_pct, 1)}%` : '—'}</td>
        <td class="num tabular">${fmtNum(x.p_se, 2)} / ${x.p_diff == null ? '—' : `${x.p_diff >= 0 ? '+' : ''}${fmtNum(x.p_diff, 2)}`}</td>
        <td class="se-sticky-right"><a class="se-btn mini se-link-btn" href="/lf-flow.html?dev_id=${encodeURIComponent(`${x.device_type}-${x.device_idx}`)}${st.selectedRunId ? `&run_id=${st.selectedRunId}` : ''}">${esc(t('action.locate'))}</a></td>
      </tr>`).join('')}</tbody></table>`;
    }
    const total = data.meta?.total || 0;
    const pages = Math.max(1, Math.ceil(total / r.size));
    document.getElementById('lf-res-pager').innerHTML = `
      <button type="button" class="se-btn mini" id="btn-lf-res-prev" ${r.page <= 0 ? 'disabled' : ''}>${esc(t('pager.prev'))}</button>
      <span class="tabular">${r.page + 1} / ${pages} · ${total}</span>
      <button type="button" class="se-btn mini" id="btn-lf-res-next" ${r.page >= pages - 1 ? 'disabled' : ''}>${esc(t('pager.next'))}</button>`;
  }

  /* ==================== 4. 参数与方式 (lf-params.html) ==================== */
  async function ensureCatalog() {
    if (!st.catalog) st.catalog = await api('/api/lf/model-catalog');
    return st.catalog;
  }

  async function openOverrideDialog(prefill = null) {
    const dlg = document.getElementById('lf-override-dialog');
    if (!dlg) return;
    const cat = await ensureCatalog();
    const dtSel = document.getElementById('fov-dev-type');
    const types = Object.keys(cat.override_fields || {});
    dtSel.innerHTML = types.map((dt) => `<option value="${esc(dt)}">${esc(dt)}</option>`).join('');
    const syncSub = (selDev, selField) => {
      const dt = dtSel.value;
      const devs = (cat.devices || {})[dt] || [];
      const devSel = document.getElementById('fov-dev-name');
      devSel.innerHTML = devs.map((d) => `<option value="${esc(d.name)}" data-idx="${d.idx}">${esc(d.name)} (#${d.idx})</option>`).join('');
      if (selDev) devSel.value = selDev;
      const fields = (cat.override_fields || {})[dt] || [];
      const fSel = document.getElementById('fov-field');
      fSel.innerHTML = fields.map((f) => `<option value="${esc(f)}">${esc(f)}</option>`).join('');
      if (selField) fSel.value = selField;
    };
    document.getElementById('fov-id').value = prefill?.id || '';
    dtSel.value = (prefill?.device_type && types.includes(prefill.device_type)) ? prefill.device_type : types[0];
    syncSub(prefill?.device_name, prefill?.field);
    document.getElementById('fov-value').value = prefill?.value ?? 0;
    document.getElementById('fov-note').value = prefill?.note || '';
    dtSel.onchange = () => syncSub();
    dlg.showModal();
  }

  async function submitOverrideForm(alsoRun = false) {
    const id = document.getElementById('fov-id').value;
    const devSel = document.getElementById('fov-dev-name');
    const opt = devSel?.selectedOptions?.[0];
    const payload = {
      device_type: document.getElementById('fov-dev-type').value,
      device_idx: opt?.dataset?.idx ? Number(opt.dataset.idx) : null,
      device_name: devSel.value,
      field: document.getElementById('fov-field').value,
      value: Number(document.getElementById('fov-value').value),
      enabled: 1,
      note: document.getElementById('fov-note').value.trim(),
    };
    if (id) await api(`/api/lf/overrides/${id}`, payload, 'PUT');
    else await api('/api/lf/overrides', payload, 'POST');
    document.getElementById('lf-override-dialog')?.close();
    notify(t('ov.saved'));
    if (alsoRun) {
      await api('/api/actions/trigger', { task: 'lf' });
      notify(t('msg.lf_done', { id: '' }));
      await refreshAll();
    } else if (VIEW === 'params') {
      await loadOverridesTable();
    }
  }

  async function loadParamsView() {
    const params = await api('/api/lf/params');
    const updEl = document.getElementById('lf-params-updated');
    if (updEl) updEl.textContent = params.updated_at ? fmtTime(params.updated_at) : '—';
    let html = '';
    LF_PARAM_SCHEMA.forEach((grp) => {
      grp.fields.forEach((f) => {
        const lbl = f.label[st.lang] || f.label['zh-CN'];
        const val = params[f.key];
        if (f.type === 'bool') {
          html += `<label class="se-field"><span>${esc(lbl)}</span><select name="${esc(f.key)}"><option value="0" ${Number(val) === 0 ? 'selected' : ''}>${esc(t('bool.off'))}</option><option value="1" ${Number(val) === 1 ? 'selected' : ''}>${esc(t('bool.on'))}</option></select></label>`;
        } else {
          html += `<label class="se-field"><span>${esc(lbl)}</span><input class="tabular" type="number" name="${esc(f.key)}" value="${esc(val)}" min="${f.min}" max="${f.max}" step="${f.step || '1'}" required></label>`;
        }
      });
    });
    const formEl = document.getElementById('lf-params-form');
    if (formEl) formEl.innerHTML = html;
    await loadOverridesTable();
  }

  async function saveLfParams() {
    const fd = new FormData(document.getElementById('lf-params-form'));
    const payload = {};
    LF_PARAM_SCHEMA.forEach((grp) => grp.fields.forEach((f) => {
      const raw = fd.get(f.key);
      if (raw !== null) payload[f.key] = f.type === 'float' ? Number(raw) : parseInt(String(raw), 10);
    }));
    await api('/api/lf/params', payload);
    notify(t('params.saved'));
    await loadParamsView();
  }

  async function runLfTrialCompare(saveFirst = true) {
    const bar = document.getElementById('lf-trial-bar');
    try {
      const before = (await api('/api/lf/home'))?.latest;
      if (saveFirst) await saveLfParams();
      await api('/api/actions/trigger', { task: 'lf' });
      const after = (await api('/api/lf/home'))?.latest;
      if (bar && after) {
        const bLoss = before?.loss_rate != null ? `${Number(before.loss_rate).toFixed(2)}%` : '—';
        const bV = before?.min_v_pu != null ? Number(before.min_v_pu).toFixed(4) : '—';
        const bL = before?.max_loading_pct != null ? `${Number(before.max_loading_pct).toFixed(1)}%` : '—';
        const bA = before ? (before.v_violation_count + before.overload_count) : '—';
        const aA = (after.v_violation_count || 0) + (after.overload_count || 0);
        bar.innerHTML = `
          <strong class="tag">${esc(t('trial.title'))}</strong>
          <span class="tabular">${esc(t('trial.loss'))}: ${bLoss} → <b>${Number(after.loss_rate || 0).toFixed(2)}%</b></span>
          <span class="tabular">${esc(t('trial.min_v'))}: ${bV} → <b>${after.min_v_pu != null ? Number(after.min_v_pu).toFixed(4) : '—'}</b></span>
          <span class="tabular">${esc(t('trial.max_load'))}: ${bL} → <b>${Number(after.max_loading_pct || 0).toFixed(1)}%</b></span>
          <span class="tabular">${esc(t('trial.alerts'))}: ${bA} → <b>${aA}</b></span>
          <button type="button" class="se-btn mini" id="btn-lf-trial-close">×</button>`;
        bar.hidden = false;
        document.getElementById('btn-lf-trial-close')?.addEventListener('click', () => { bar.hidden = true; });
      }
      notify(t('msg.lf_done', { id: after?.run_id || '' }));
    } catch (err) {
      notify(err.message, true);
    }
  }

  async function loadOverridesTable() {
    const [cat, rows, unitsRes] = await Promise.all([
      ensureCatalog(),
      api(`/api/lf/overrides?device_type=${encodeURIComponent(st.ovFilter.type)}&q=${encodeURIComponent(st.ovFilter.q)}`),
      api('/api/lf/results?kind=units&limit=30').catch(() => ({ rows: [] })),
    ]);
    st.overrides = rows || [];
    const cntEl = document.getElementById('lf-ov-count');
    if (cntEl) cntEl.textContent = String(st.overrides.length);
    const sel = document.getElementById('ov-type-filter');
    if (sel) {
      const types = Object.keys(cat.override_fields || {});
      sel.innerHTML = `<option value="">${esc(t('common.all'))}</option>` + types.map((x) => `<option value="${esc(x)}">${esc(x)}</option>`).join('');
      sel.value = st.ovFilter.type;
    }
    const wrap = document.getElementById('lf-ov-table-wrap');
    if (!st.overrides.length) {
      // 无方式调整条目时，直接展示当前可调电源/负荷基态运行清单（点击即可快速新增方式调整），杜绝下方大片空白
      const units = (unitsRes?.rows || []).filter((u) => {
        if (st.ovFilter.type && u.device_type !== st.ovFilter.type) return false;
        if (st.ovFilter.q && !`${u.device_name} ${u.device_type}`.toLowerCase().includes(st.ovFilter.q.toLowerCase())) return false;
        return true;
      });
      if (!units.length) {
        wrap.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
        return;
      }
      wrap.innerHTML = `<table class="se-data-table"><thead><tr>
        <th>${esc(t('col.dev_type'))}</th><th>${esc(t('col.device'))}</th><th>${esc(t('col.ctrl'))}</th>
        <th class="num">P (LF)</th><th class="num">Q (LF)</th><th class="num">V (LF)</th><th class="num">P (SE)</th>
        <th class="se-sticky-right">${esc(t('col.ops'))}</th>
      </tr></thead><tbody>${units.map((u) => `<tr>
        <td>${esc(u.device_type)}</td><td><strong>${esc(u.device_name)}</strong></td><td>${esc(u.control_type || '—')}</td>
        <td class="num tabular">${fmtNum(u.p_lf, 2)}</td><td class="num tabular">${fmtNum(u.q_lf, 2)}</td>
        <td class="num tabular">${fmtNum(u.v_lf, 2)}</td><td class="num tabular">${fmtNum(u.p_se, 2)}</td>
        <td class="se-sticky-right"><button type="button" class="se-btn mini primary" data-lf-adjust="${esc(u.device_type)}|${u.device_idx}|${esc(u.device_name)}">${esc(t('action.adjust'))}</button></td>
      </tr>`).join('')}</tbody></table>`;
      return;
    }
    wrap.innerHTML = `<table class="se-data-table"><thead><tr>
      <th>#</th><th>${esc(t('col.dev_type'))}</th><th>${esc(t('col.device'))}</th><th>${esc(t('ov.field'))}</th>
      <th class="num">${esc(t('ov.value'))}</th><th>${esc(t('col.status'))}</th><th>${esc(t('col.note'))}</th><th class="se-sticky-right">${esc(t('col.ops'))}</th>
    </tr></thead><tbody>${st.overrides.map((r) => `<tr>
      <td class="tabular">${r.id}</td><td>${esc(r.device_type)}</td><td><strong>${esc(r.device_name)}</strong></td>
      <td class="tabular">${esc(r.field)}</td><td class="num tabular"><strong>${esc(r.value)}</strong></td>
      <td><span class="se-pill ${r.enabled ? 'ok' : 'neutral'}">${esc(t(r.enabled ? 'bool.on' : 'bool.off'))}</span></td>
      <td>${esc(r.note || '—')}</td>
      <td class="se-sticky-right">
        <button type="button" class="se-btn mini" data-ov-act="edit" data-ov-id="${r.id}">${esc(t('action.edit'))}</button>
        <button type="button" class="se-btn mini" data-ov-act="toggle" data-ov-id="${r.id}">${esc(t(r.enabled ? 'bool.off' : 'bool.on'))}</button>
        <button type="button" class="se-btn mini danger-ghost" data-ov-act="del" data-ov-id="${r.id}">${esc(t('action.delete'))}</button>
      </td>
    </tr>`).join('')}</tbody></table>`;
  }

  /* ==================== 5. 运行日志 (lf-logs.html) ==================== */
  async function loadLogsView() {
    const [sum, page, home, cfg] = await Promise.all([
      api('/api/lf/logs/summary'),
      api(`/api/lf/logs?level=${encodeURIComponent(st.logs.level)}&stage=${encodeURIComponent(st.logs.stage)}&window=${encodeURIComponent(st.logs.window)}&run_id=${encodeURIComponent(st.logs.runId)}&q=${encodeURIComponent(st.logs.q)}&limit=${st.logs.size}&offset=${st.logs.page * st.logs.size}`),
      api('/api/lf/home'),
      api('/api/config'),
    ]);
    document.getElementById('lf-kpi-log-total').textContent = sum.total ?? 0;
    document.getElementById('lf-kpi-err').textContent = sum.error_24h ?? 0;
    document.getElementById('lf-kpi-warn').textContent = `/ ${sum.warn_24h ?? 0}`;
    document.getElementById('lf-kpi-ret').textContent = sum.policy?.retention_days ?? 30;
    document.getElementById('lf-kpi-pend').textContent = sum.pending_purge?.total_to_delete ?? 0;

    if (sum.policy) {
      document.getElementById('lfp-enabled').value = String(sum.policy.enabled ?? 1);
      document.getElementById('lfp-ret').value = sum.policy.retention_days ?? 30;
      document.getElementById('lfp-err').value = sum.policy.keep_error_days ?? 90;
      document.getElementById('lfp-max').value = sum.policy.max_rows ?? 50000;
    }
    const stgEl = document.getElementById('lf-stage-stats');
    if (stgEl) {
      const raw = sum.by_stage;
      const entries = Array.isArray(raw)
        ? raw.map((it) => [String(it.stage ?? it.name ?? '—'), Number(it.cnt ?? it.count ?? 0)])
        : Object.entries(raw || {}).map(([k, v]) => [String(k), Number(v ?? 0)]);
      entries.sort((a, b) => b[1] - a[1]);
      stgEl.innerHTML = entries.length
        ? entries.map(([k, v]) => `<div class="se-kv-row"><span class="k">${esc(k)}</span><strong class="v tabular">${v}</strong></div>`).join('')
        : `<div class="se-empty">${esc(t('common.empty'))}</div>`;
    }

    const wrap = document.getElementById('lf-log-table-wrap');
    const rows = page.rows || [];
    wrap.innerHTML = rows.length ? `<table class="se-table"><thead><tr>
      <th>Time</th><th>Run</th><th>Level</th><th>Stage</th><th>Source</th><th class="num">ms</th><th>Message</th>
    </tr></thead><tbody>${rows.map((r) => `<tr>
      <td class="tabular">${esc(fmtTime(r.calc_time))}</td>
      <td class="tabular">${r.run_id ? `#${r.run_id}` : '—'}</td>
      <td><span class="se-pill ${r.level === 'ERROR' ? 'bad' : r.level === 'WARN' ? 'warn' : 'info'}">${esc(r.level)}</span></td>
      <td><span class="se-tag">${esc(r.stage)}</span></td><td>${esc(r.source)}</td>
      <td class="num tabular">${r.elapsed_ms != null ? fmtNum(r.elapsed_ms, 1) : '—'}</td>
      <td class="se-cell-msg" title="${esc(r.message)}">${esc(r.message)}</td>
    </tr>`).join('')}</tbody></table>` : `<div class="se-empty">${esc(t('common.empty'))}</div>`;

    const pages = Math.max(1, Math.ceil((page.total || 0) / st.logs.size));
    document.getElementById('lf-log-pager').innerHTML = `
      <button type="button" class="se-btn mini" id="btn-lf-log-prev" ${st.logs.page <= 0 ? 'disabled' : ''}>${esc(t('pager.prev'))}</button>
      <span class="tabular">${st.logs.page + 1} / ${pages} · ${page.total || 0}</span>
      <button type="button" class="se-btn mini" id="btn-lf-log-next" ${st.logs.page >= pages - 1 ? 'disabled' : ''}>${esc(t('pager.next'))}</button>`;

    const runsWrap = document.getElementById('lf-runs-table-wrap');
    const rList = home.recent_runs || [];
    runsWrap.innerHTML = rList.length ? `<table class="se-table"><thead><tr>
      <th>Run</th><th>SE</th><th>${esc(t('col.status'))}</th><th>Time</th><th class="num">${esc(t('kv.loss_rate'))}</th><th class="num">s</th><th>${esc(t('col.ops'))}</th>
    </tr></thead><tbody>${rList.map((r) => `<tr>
      <td class="tabular">#${r.run_id}</td>
      <td class="tabular">${r.source_se_run_id ? `SE#${r.source_se_run_id}` : '—'}</td>
      <td><span class="se-pill ${r.status === 'succeeded' ? 'ok' : r.status === 'failed' ? 'bad' : 'warn'}">${esc(t(`status.${r.status}`))}</span></td>
      <td class="tabular">${esc(fmtTime(r.started_at))}</td>
      <td class="num tabular">${r.loss_rate != null ? `${Number(r.loss_rate).toFixed(2)}%` : '—'}</td>
      <td class="num tabular">${r.elapsed_seconds != null ? Number(r.elapsed_seconds).toFixed(3) : '—'}</td>
      <td><div class="se-row-actions">
        <button type="button" class="se-btn mini" data-lf-log-run="${r.run_id}">Log</button>
        ${r.status === 'succeeded' ? `<a class="se-btn mini se-link-btn" href="/lf-flow.html?run_id=${r.run_id}">${esc(t('nav.lf_flow'))}</a>` : ''}
        ${r.status === 'succeeded' ? `<a class="se-btn mini se-link-btn" href="/lf-results.html?run_id=${r.run_id}">${esc(t('nav.lf_results'))}</a>` : ''}
      </div></td>
    </tr>`).join('')}</tbody></table>` : `<div class="se-empty">${esc(t('common.empty'))}</div>`;

    const sf = document.getElementById('lf-schedule-form');
    const lfCfg = cfg.tasks?.lf || { period_seconds: 60, enabled: true };
    if (sf) { sf.elements.period_seconds.value = lfCfg.period_seconds; sf.elements.enabled.checked = Boolean(lfCfg.enabled); }
  }

  /* ==================== 全局刷新与状态轮询 ==================== */
  async function refreshAll() {
    try {
      const qp = new URLSearchParams(window.location.search);
      if (!st._initUrl) {
        st._initUrl = true;
        if (qp.get('run_id')) {
          st.selectedRunId = qp.get('run_id');
          if (VIEW === 'logs') {
            st.logs.runId = qp.get('run_id');
            const inp = document.getElementById('lf-log-runid');
            if (inp) inp.value = st.logs.runId;
          }
        }
        if (VIEW === 'results' && qp.get('kind')) st.res.kind = qp.get('kind');
      }
      if (VIEW === 'flow' || VIEW === 'results') {
        st.convergedRuns = await api('/api/lf/runs/converged?limit=30').catch(() => []);
        populateRunSelect();
      }
      if (VIEW === 'home') await loadHomeView();
      else if (VIEW === 'flow') await loadFlowView();
      else if (VIEW === 'results') await loadResultsView();
      else if (VIEW === 'params') await loadParamsView();
      else if (VIEW === 'logs') await loadLogsView();
    } catch (err) {
      notify(err.message, true);
    }
  }

  async function pollStatus() {
    try {
      const s = await api('/api/status');
      const dot = document.getElementById('service-dot');
      const txt = document.getElementById('service-state');
      if (txt) txt.textContent = s.daemon_running ? t('service.daemon_on') : t('service.daemon_off');
      if (dot) dot.style.background = s.daemon_running ? '#10B981' : '#F59E0B';
      const busy = [...(s.active_tasks || []), ...(s.pending_tasks || [])].includes('lf');
      const btn = document.getElementById('btn-run-lf');
      if (btn) { btn.disabled = busy; btn.textContent = busy ? t('action.running_lf') : t('action.run_lf'); }
      if (st.watchingJobId) {
        const job = (s.jobs || []).find((j) => j.job_id === st.watchingJobId) || await api(`/api/jobs/${st.watchingJobId}`).catch(() => null);
        if (job && ['succeeded', 'failed'].includes(job.status)) {
          st.watchingJobId = null;
          if (job.status === 'succeeded') { notify(t('msg.lf_done', { id: job.run_id || '' })); await refreshAll(); }
          else notify(t('msg.lf_failed', { msg: job.error_message || '' }), true);
        }
      }
    } catch (_) {
      const txt = document.getElementById('service-state');
      if (txt) txt.textContent = t('service.offline');
    }
  }

  function syncAutoRefresh() {
    const btn = document.getElementById('btn-auto-refresh');
    if (btn) btn.classList.toggle('active', st.autoRefresh);
    clearInterval(st.autoTimer);
    if (st.autoRefresh && VIEW === 'home') {
      st.autoTimer = setInterval(async () => {
        try {
          const runs = await api('/api/lf/runs/converged?limit=1');
          const topId = runs?.[0]?.run_id ?? null;
          if (topId !== null && topId !== st.lastRunId) await loadHomeView();
        } catch (_) {}
      }, 10000);
    }
  }

  function initSidebarSplitter() {
    const shell = document.querySelector('.app-shell');
    const sidebar = shell?.querySelector('.sidebar');
    if (!shell || !sidebar || shell.querySelector('.sidebar-resizer')) return;
    let w = Math.min(340, Math.max(160, Number(localStorage.getItem('pas_sidebar_width')) || 214));
    let collapsed = localStorage.getItem('pas_sidebar_collapsed') === '1';
    const res = document.createElement('div');
    res.className = 'sidebar-resizer';
    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'sidebar-toggle-btn';
    res.appendChild(btn);
    sidebar.insertAdjacentElement('afterend', res);
    const apply = () => {
      sidebar.classList.toggle('is-collapsed', collapsed);
      res.classList.toggle('is-collapsed', collapsed);
      if (!collapsed) { sidebar.style.width = `${w}px`; sidebar.style.flexBasis = `${w}px`; }
      btn.textContent = collapsed ? '›' : '‹';
      localStorage.setItem('pas_sidebar_collapsed', collapsed ? '1' : '0');
      localStorage.setItem('pas_sidebar_width', String(Math.round(w)));
    };
    btn.addEventListener('click', (e) => { e.stopPropagation(); collapsed = !collapsed; apply(); window.dispatchEvent(new Event('resize')); });
    res.addEventListener('dblclick', () => { collapsed = !collapsed; apply(); window.dispatchEvent(new Event('resize')); });
    apply();
  }

  function bindEvents() {
    on('lang-select', 'change', async (e) => {
      st.lang = e.target.value;
      localStorage.setItem('pas_se_lang', st.lang);
      localStorage.setItem('se_lang', st.lang);
      applyI18n();
      populateRunSelect();
      await refreshAll();
    });
    on('theme-select', 'change', (e) => {
      st.theme = e.target.value;
      localStorage.setItem('pas_se_theme', st.theme);
      localStorage.setItem('se_theme', st.theme);
      applyTheme();
      if (VIEW === 'home') renderHomeChart();
      if (VIEW === 'flow') renderLfSvgBindings();
    });
    on('btn-refresh', 'click', refreshAll);
    on('btn-auto-refresh', 'click', () => {
      st.autoRefresh = !st.autoRefresh;
      localStorage.setItem('pas_lf_autorefresh', st.autoRefresh ? '1' : '0');
      syncAutoRefresh();
    });
    on('btn-run-lf', 'click', async () => {
      try {
        const res = await api('/api/actions/submit', { task: 'lf' });
        if (res.accepted) { st.watchingJobId = res.job_id; notify(t('msg.lf_submitted')); }
        await pollStatus();
      } catch (err) { notify(err.message, true); }
    });
    on('lf-run-select', 'change', async (e) => {
      st.selectedRunId = e.target.value || '';
      e.target.classList.toggle('is-history', Boolean(st.selectedRunId));
      st.res.page = 0;
      if (VIEW === 'flow') await loadFlowView();
      else if (VIEW === 'results') await loadResultsView();
    });
    on('lf-home-chart-seg', 'click', (e) => {
      const btn = e.target.closest('.seg');
      if (!btn) return;
      st.homeMetric = btn.dataset.hmetric;
      document.querySelectorAll('#lf-home-chart-seg .seg').forEach((b) => b.classList.toggle('active', b === btn));
      renderHomeChart();
    });
    let lfResizeTimer;
    window.addEventListener('resize', () => {
      if (VIEW !== 'home') return;
      clearTimeout(lfResizeTimer);
      lfResizeTimer = setTimeout(() => renderHomeChart(), 140);
    });

    // 潮流图
    on('lf-svg-mode', 'change', (e) => { st.svgMode = e.target.value; renderLfSvgBindings(); });
    on('lf-device-jump', 'change', (e) => { if (e.target.value) focusFlowDevice(e.target.value); });
    on('btn-svg-zoom-in', 'click', () => zoomSvg(1.25));
    on('btn-svg-zoom-out', 'click', () => zoomSvg(0.8));
    on('btn-svg-fit', 'click', fitSvg);

    // 潮流明细
    on('lf-res-subtab-seg', 'click', (e) => {
      const btn = e.target.closest('.seg');
      if (!btn) return;
      st.res.kind = btn.dataset.kind; st.res.devType = ''; st.res.page = 0;
      loadResultsView();
    });
    on('lf-res-domain', 'change', (e) => { st.res.domain = e.target.value; st.res.page = 0; loadResultsView(); });
    on('lf-res-devtype', 'change', (e) => { st.res.devType = e.target.value; st.res.page = 0; loadResultsView(); });
    on('btn-lf-res-abn', 'click', (e) => { st.res.onlyAbn = !st.res.onlyAbn; e.currentTarget.classList.toggle('active', st.res.onlyAbn); st.res.page = 0; loadResultsView(); });
    let rTimer;
    on('lf-res-search', 'input', (e) => { st.res.q = e.target.value; st.res.page = 0; clearTimeout(rTimer); rTimer = setTimeout(loadResultsView, 200); });
    on('lf-trend-metric', 'change', (e) => { st.res.trendMetric = e.target.value; loadResultsView(); });
    on('lf-trend-limit', 'change', (e) => { st.res.trendLimit = Number(e.target.value); loadResultsView(); });
    on('btn-lf-export', 'click', () => {
      const qs = new URLSearchParams({ kind: st.res.kind, domain: st.res.domain, device_type: st.res.devType, only_abnormal: st.res.onlyAbn ? '1' : '0', q: st.res.q });
      if (st.selectedRunId) qs.set('run_id', st.selectedRunId);
      window.location.href = `/api/lf/results/export?${qs}`;
    });

    // 参数与方式
    on('lf-params-subtab-seg', 'click', (e) => {
      const btn = e.target.closest('.seg');
      if (!btn) return;
      st.paramsSub = btn.dataset.psub;
      loadParamsView();
    });
    on('btn-lf-params-save', 'click', async () => { try { await saveLfParams(); } catch (err) { notify(err.message, true); } });
    on('btn-lf-trial', 'click', () => runLfTrialCompare(true));
    on('btn-ov-run-trial', 'click', () => runLfTrialCompare(false));
    on('btn-lf-params-reset', 'click', () => {
      openConfirm({
        title: t('params.reset_title'),
        desc: t('params.reset_desc'),
        okText: t('params.reset'),
        onConfirm: async () => {
          try { await api('/api/lf/params/reset', {}); notify(t('params.reset_done')); await loadParamsView(); } catch (err) { notify(err.message, true); }
        },
      });
    });
    on('ov-type-filter', 'change', (e) => { st.ovFilter.type = e.target.value; loadOverridesTable(); });
    let ovT;
    on('ov-search-input', 'input', (e) => { st.ovFilter.q = e.target.value; clearTimeout(ovT); ovT = setTimeout(loadOverridesTable, 200); });
    on('btn-add-override', 'click', () => openOverrideDialog(null));
    on('btn-clear-overrides', 'click', () => {
      openConfirm({
        title: t('ov.clear_all'),
        desc: t('ov.clear_confirm'),
        okText: t('action.confirm'),
        onConfirm: async () => {
          try { await api('/api/lf/overrides/clear', {}); notify(t('ov.cleared')); await loadOverridesTable(); } catch (err) { notify(err.message, true); }
        },
      });
    });
    on('btn-ov-cancel', 'click', () => document.getElementById('lf-override-dialog')?.close());
    on('lf-ov-form', 'submit', async (e) => { e.preventDefault(); try { await submitOverrideForm(false); } catch (err) { notify(err.message, true); } });
    on('btn-ov-save-run', 'click', async () => { try { await submitOverrideForm(true); } catch (err) { notify(err.message, true); } });

    // 日志与调度
    on('lf-logs-tabs', 'click', (e) => {
      const btn = e.target.closest('.se-tab');
      if (!btn) return;
      st.logs.tab = btn.dataset.lsub;
      document.querySelectorAll('#lf-logs-tabs .se-tab').forEach((b) => b.classList.toggle('active', b === btn));
      document.querySelectorAll('[data-lpanel]').forEach((p) => p.classList.toggle('active', p.dataset.lpanel === st.logs.tab));
    });
    on('lf-log-level', 'change', (e) => { st.logs.level = e.target.value; st.logs.page = 0; loadLogsView(); });
    on('lf-log-stage', 'change', (e) => { st.logs.stage = e.target.value; st.logs.page = 0; loadLogsView(); });
    on('lf-log-window', 'change', (e) => { st.logs.window = e.target.value; st.logs.page = 0; loadLogsView(); });
    let lTimer;
    on('lf-log-runid', 'input', (e) => { st.logs.runId = e.target.value; st.logs.page = 0; clearTimeout(lTimer); lTimer = setTimeout(loadLogsView, 200); });
    on('lf-log-search', 'input', (e) => { st.logs.q = e.target.value; st.logs.page = 0; clearTimeout(lTimer); lTimer = setTimeout(loadLogsView, 200); });
    on('btn-lf-logs-export', 'click', () => {
      const qs = new URLSearchParams({ level: st.logs.level, stage: st.logs.stage, window: st.logs.window, run_id: st.logs.runId, q: st.logs.q });
      window.location.href = `/api/lf/logs/export?${qs}`;
    });
    on('lf-schedule-form', 'submit', async (e) => {
      e.preventDefault();
      try {
        await api('/api/schedules/lf', { period_seconds: Number(e.target.elements.period_seconds.value), enabled: Boolean(e.target.elements.enabled.checked) });
        notify(t('sched.saved'));
      } catch (err) { notify(err.message, true); }
    });
    on('btn-daemon-start', 'click', async () => { try { await api('/api/actions/daemon/start', {}); await pollStatus(); } catch (err) { notify(err.message, true); } });
    on('btn-daemon-stop', 'click', async () => { try { await api('/api/actions/daemon/stop', {}); await pollStatus(); } catch (err) { notify(err.message, true); } });
    on('lf-log-policy-form', 'submit', async (e) => {
      e.preventDefault();
      try {
        await api('/api/lf/logs/policy', {
          enabled: Number(document.getElementById('lfp-enabled').value),
          retention_days: Number(document.getElementById('lfp-ret').value),
          keep_error_days: Number(document.getElementById('lfp-err').value),
          max_rows: Number(document.getElementById('lfp-max').value),
        });
        notify(t('logs.pol_saved'));
        await loadLogsView();
      } catch (err) { notify(err.message, true); }
    });
    on('btn-lf-purge', 'click', () => {
      openConfirm({
        title: t('logs.purge_now'),
        desc: t('logs.purge_confirm'),
        okText: t('action.confirm'),
        onConfirm: async () => {
          try { const res = await api('/api/lf/logs/purge', { dry_run: false }); notify(t('logs.purged', { n: res.deleted })); await loadLogsView(); } catch (err) { notify(err.message, true); }
        },
      });
    });

    // 确认框
    on('btn-confirm-cancel', 'click', () => { st.confirmFn = null; document.getElementById('confirm-dialog')?.close(); });
    on('btn-confirm-ok', 'click', async () => { const fn = st.confirmFn; st.confirmFn = null; document.getElementById('confirm-dialog')?.close(); if (fn) await fn(); });

    // 全局点击委派
    document.addEventListener('click', async (e) => {
      const fBtn = e.target.closest('[data-lf-focus]');
      if (fBtn) { focusFlowDevice(fBtn.dataset.lfFocus); return; }
      const adjBtn = e.target.closest('[data-lf-adjust]');
      if (adjBtn) {
        const [dt, idx, dn] = adjBtn.dataset.lfAdjust.split('|');
        await openOverrideDialog({ device_type: dt, device_idx: Number(idx), device_name: dn });
        return;
      }
      const ovBtn = e.target.closest('[data-ov-act]');
      if (ovBtn) {
        const oid = Number(ovBtn.dataset.ovId);
        const row = st.overrides.find((x) => Number(x.id) === oid);
        if (!row) return;
        const act = ovBtn.dataset.ovAct;
        if (act === 'edit') await openOverrideDialog(row);
        else if (act === 'toggle') {
          try { await api(`/api/lf/overrides/${oid}`, { ...row, enabled: row.enabled ? 0 : 1 }, 'PUT'); notify(t('ov.saved')); await loadOverridesTable(); } catch (err) { notify(err.message, true); }
        } else if (act === 'del') {
          openConfirm({
            title: t('ov.dlg_title'),
            desc: `${t('ov.del_confirm')} (${row.device_name}.${row.field})`,
            okText: t('action.delete'),
            onConfirm: async () => {
              try { await api(`/api/lf/overrides/${oid}`, null, 'DELETE'); notify(t('ov.deleted')); await loadOverridesTable(); } catch (err) { notify(err.message, true); }
            },
          });
        }
        return;
      }
      const logRunBtn = e.target.closest('[data-lf-log-run]');
      if (logRunBtn) {
        st.logs.runId = logRunBtn.dataset.lfLogRun;
        st.logs.page = 0;
        const inp = document.getElementById('lf-log-runid');
        if (inp) inp.value = st.logs.runId;
        document.querySelector('#lf-logs-tabs .se-tab[data-lsub="stream"]')?.click();
        await loadLogsView();
        return;
      }
      if (e.target.id === 'btn-lf-res-prev' && st.res.page > 0) { st.res.page -= 1; await loadResultsView(); }
      else if (e.target.id === 'btn-lf-res-next') { st.res.page += 1; await loadResultsView(); }
      else if (e.target.id === 'btn-lf-log-prev' && st.logs.page > 0) { st.logs.page -= 1; await loadLogsView(); }
      else if (e.target.id === 'btn-lf-log-next') { st.logs.page += 1; await loadLogsView(); }
    });
  }

  applyTheme();
  applyI18n();
  initSidebarSplitter();
  bindEvents();
  syncAutoRefresh();
  refreshAll();
  pollStatus();
  if (window.PAS_KIT?.createPoller) {
    window.PAS_KIT.createPoller(pollStatus, 8000, { useSSE: true });
  } else {
    setInterval(() => { if (!document.hidden) pollStatus(); }, 4000);
  }
})();
