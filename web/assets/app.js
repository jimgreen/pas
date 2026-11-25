const TASKS = ['se', 'lf', 'ca'];
const LABELS = {se:'状态估计 SE', lf:'潮流分析 LF', ca:'静态安全 CA'};
const PAGE_URLS = {overview:'/overview.html', se:'/analysis/se.html', lf:'/analysis/lf.html', ca:'/analysis/ca.html', runs:'/runs.html', settings:'/settings.html', workspace:'/workspace.html', measurements:'/measurements.html', limits:'/limits.html'};
const pageUrl = (route, query='') => {
  const key = route === '/overview' ? 'overview' : route === '/runs' ? 'runs' : route === '/settings' ? 'settings' : route === '/workspace' ? 'workspace' : route === '/measurements' ? 'measurements' : route === '/limits' ? 'limits' : route.match(/^\/analysis\/(se|lf|ca)/)?.[1];
  return `${PAGE_URLS[key] || PAGE_URLS.overview}${query}`;
};
const initialPage = document.body.dataset.page || location.hash.split('?')[0].slice(1) || '/overview';
const initialQuery = location.search || (location.hash.includes('?') ? `?${location.hash.split('?')[1]}` : '');
const state = {
  route: initialPage + initialQuery, token: 0, page: 0,
  filter: {task:'', status:'', source:''}, overviewTab:'tasks', settingsTab:'schedule', workspaceTab:'directory',
  tabs: {se:'summary',lf:'summary',ca:'summary'}, selected:{},
  browse: Object.fromEntries(TASKS.map(t => [t,{page:0,col:0,q:'',table:'',mode:'',sort:'',direction:'asc',view:'all'}])),
  controlTab:'config', summaryMode:'result', diagPage:0, diagCol:0, trend:{hours:24,metric:'runs',mode:'chart',page:0}, status:{}, watching:new Map(), exportData:null, logPage:0, scheduleTask:'se'
};
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const statusLabel = s => ({queued:'等待执行',running:'运行中',succeeded:'成功',failed:'失败'}[s] || s || '—');
const sourceLabel = s => s === 'manual' ? '人工触发' : '周期自动';
const number = v => v == null ? '—' : String(Number(Number(v).toPrecision(5)));
const pageSize = () => {
  const mode=state.tabs[task()],mobile=innerWidth<700;
  const reserved=mode==='diagnostics'?(mobile?630:540):mode==='details'?(mobile?570:500):(mobile?570:460);
  return Math.max(1,Math.min(8,Math.floor((innerHeight-reserved)/36)));
};
const colSize = () => innerWidth < 700 ? 3 : 6;
const task = () => state.route.match(/^\/analysis\/(se|lf|ca)/)?.[1];
const busy = t => [...(state.status.active_tasks || []), ...(state.status.pending_tasks || [])].includes(t);
const badge = s => `<span class="badge ${s === 'succeeded' ? 'success' : s === 'failed' ? 'failed' : s === 'running' || s === 'queued' ? 'running' : ''}">${esc(statusLabel(s))}</span>`;
const healthBadge = ok => `<span class="badge ${ok ? 'success' : 'failed'}">${ok ? '正常' : '需关注'}</span>`;
const button = t => `<button type="button" class="mini" data-task="${t}" ${busy(t)?'disabled':''}>${busy(t)?'执行中':'执行'} ${t.toUpperCase()}</button>`;
const tabs = (items, active) => `<div class="tabs">${items.map(([key,label])=>`<button class="tab ${key===active?'active':''}" data-tab="${key}">${label}</button>`).join('')}</div>`;
const metric = (label,value) => `<div class="metric"><span>${esc(label)}</span><strong title="${esc(value)}">${esc(value ?? '—')}</strong></div>`;
const empty = text => `<div class="empty">${esc(text)}</div>`;
function notify(text, error=false) {
  const box = document.querySelector('#notice'); box.textContent=text;
  box.className=`notice ${error?'error':'success'}`; box.hidden=false;
  clearTimeout(state.noticeTimer); state.noticeTimer=setTimeout(()=>box.hidden=true,6500);
}
async function api(url, body) {
  const res = await fetch(url, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(({already_running:'任务正在执行，请等待完成',invalid_task:'无效任务',service_stopping:'服务正在停止',no_failed_run:'没有可重试的失败任务'}[data.error]) || data.error || '请求失败');
  return data;
}
function pager(page,total,scope) {
  const pages=Math.max(1,Math.ceil(total/pageSize()));
  return `<div class="pager"><button class="mini" data-page="-1" data-scope="${scope}" ${page<=0?'disabled':''}>上一页</button><span>${page+1} / ${pages} 页 · ${total} 条</span><button class="mini" data-page="1" data-scope="${scope}" ${page>=pages-1?'disabled':''}>下一页</button></div>`;
}
function runTable(rows) {
  if (!rows.length) return empty('暂无运行记录');
  return `<div class="table-wrap"><table><thead><tr><th>任务 / 来源</th><th>状态</th><th>开始时间</th><th>耗时 / 操作</th></tr></thead><tbody>${rows.map(r=>`<tr><td title="${sourceLabel(r.execution_source)}">${r.task_type.toUpperCase()} · ${r.execution_source==='manual'?'人工':'周期'}</td><td>${badge(r.status)}</td><td data-value="${esc(r.started_at)}" title="${esc(r.started_at)}">${esc(r.started_at)}</td><td><a href="${pageUrl(`/analysis/${r.task_type}`,`?run=${r.run_id}`)}">${r.elapsed_seconds==null?'查看':Number(r.elapsed_seconds).toFixed(2)+'s'} →</a></td></tr>`).join('')}</tbody></table></div>`;
}
function jobsPanel(name) {
  const jobs = (state.status.jobs || []).filter(j=>!name || j.task===name).slice(-3).reverse();
  return jobs.length ? `<div class="job-list">${jobs.map(j=>`<div class="job-row"><strong>${j.task.toUpperCase()}</strong>${badge(j.status)}<span title="${esc(j.error_message || j.started_at || j.submitted_at)}">${esc(j.error_message || (j.elapsed_seconds == null ? sourceLabel(j.execution_source) : Number(j.elapsed_seconds).toFixed(2)+' s'))}</span>${j.run_id?`<a class="mini" href="${pageUrl(`/analysis/${j.task}`,`?run=${j.run_id}`)}">结果 #${j.run_id}</a>`:''}</div>`).join('')}</div>` : empty('暂无本次服务启动后的任务');
}
function serviceControls() {
  return `<div class="btn-row"><button type="button" class="primary" data-action="all">执行全部</button><button type="button" class="mini" data-action="retry-failed">重试失败任务</button><button type="button" class="mini" data-action="daemon-start">启动周期</button><button type="button" class="mini" data-action="daemon-stop">停止周期</button></div><p class="muted">停止周期后，已接受的计算仍会完成并保存结果。</p>`;
}
const TREND_METRICS={runs:'执行次数',succeeded:'成功次数',failed:'失败次数',avg_elapsed_seconds:'平均耗时（秒）'};
function trendChart(points) {
  const width=Math.max(290,document.querySelector('#app').clientWidth-60), height=220,left=42,right=14,top=20,bottom=34;
  const colors={se:'#1769e0',lf:'#14966b',ca:'#bb710a'},field=state.trend.metric;
  const series=TASKS.map(name=>points.map(p=>p.tasks?.[name]?.[field]??(field==='avg_elapsed_seconds'?null:0)));
  const max=Math.max(1,...series.flat().filter(v=>v!==null));
  const x=i=>left+(width-left-right)*i/Math.max(1,points.length-1);
  const y=v=>top+(height-top-bottom)*(1-v/max);
  const grid=[0,max/2,max].map(v=>`<line x1="${left}" x2="${width-right}" y1="${y(v)}" y2="${y(v)}" stroke="#e3e9f2"/><text x="${left-6}" y="${y(v)+4}" text-anchor="end" font-size="12" fill="#6d7890">${v===0?0:Number(v.toPrecision(3))}</text>`).join('');
  const lines=TASKS.map((name,n)=>{
    let path='';let gap=true;
    series[n].forEach((value,i)=>{if(value===null){gap=true;return;}path+=`${gap?'M':'L'}${x(i)},${y(value)} `;gap=false;});
    const marks=series[n].map((v,i)=>v===null?'':`<circle cx="${x(i)}" cy="${y(v)}" r="${n===2?2:3}" fill="${colors[name]}"><title>${esc(points[i].bucket)} UTC · ${name.toUpperCase()} ${Number(v.toPrecision(5))}</title></circle>`).join('');
    return `<path d="${path}" stroke="${colors[name]}" stroke-width="2" ${n===1?'stroke-dasharray="5 3"':''} fill="none"/>${marks}`;
  }).join('');
  return `<div class="trend-legend">${TASKS.map(n=>`<span><i style="background:${colors[n]}"></i>${n.toUpperCase()}</span>`).join('')}<span>${TREND_METRICS[field]}</span></div><svg class="trend-chart" style="height:220px" role="img" aria-label="按 UTC 小时统计的${TREND_METRICS[field]}" viewBox="0 0 ${width} ${height}"><title>完整小时窗口统计，当前小时尚未结束</title>${grid}${lines}<text x="${left}" y="${height-8}" font-size="12" fill="#6d7890">${esc(points[0]?.bucket.slice(5).replace('T',' '))}</text><text x="${width-right}" y="${height-8}" font-size="12" text-anchor="end" fill="#6d7890">${esc(points.at(-1)?.bucket.slice(5).replace('T',' '))} UTC</text></svg>`;
}
async function trends() {
  const token=state.token,cfg={...state.trend},points=(await api(`/api/metrics/trend?limit=${cfg.hours}`)).data;
  if(token!==state.token)return '';
  const rows=points.flatMap(p=>TASKS.map(name=>({hour:p.bucket+'Z',task:name.toUpperCase(),runs:p.tasks[name]?.runs||0,succeeded:p.tasks[name]?.succeeded||0,failed:p.tasks[name]?.failed||0,average:p.tasks[name]?.avg_elapsed_seconds??null})));
  const columns=['hour','task','runs','succeeded','failed','average'].map(name=>({name}));
  state.exportData={rows,columns,filename:`pas-trend-${cfg.hours}h.csv`};
  const tableRows=rows.slice(cfg.page*pageSize(),(cfg.page+1)*pageSize());
  return `<section class="card full-panel"><div class="section-head"><h2>运行趋势</h2><button class="mini" data-action="export">导出窗口统计</button></div><div class="filter-row"><select data-trend="hours" aria-label="趋势窗口">${[6,24,48,168].map(n=>`<option value="${n}" ${cfg.hours==n?'selected':''}>最近 ${n} 小时</option>`).join('')}</select><select data-trend="mode" aria-label="趋势展示"><option value="chart" ${cfg.mode==='chart'?'selected':''}>趋势图</option><option value="table" ${cfg.mode==='table'?'selected':''}>统计明细</option></select><select data-trend="metric" aria-label="趋势指标">${Object.entries(TREND_METRICS).map(([v,l])=>`<option value="${v}" ${cfg.metric===v?'selected':''}>${l}</option>`).join('')}</select></div>${cfg.mode==='chart'?trendChart(points):`<div class="table-wrap"><table><thead><tr><th>UTC 小时</th><th>任务</th><th>成功 / 失败 / 总数</th><th>均耗时（秒）</th></tr></thead><tbody>${tableRows.map(r=>`<tr><td data-value="${r.hour}">${r.hour.slice(5)}</td><td>${r.task}</td><td>${r.succeeded} / ${r.failed} / ${r.runs}</td><td>${r.average==null?'—':number(r.average)}</td></tr>`).join('')}</tbody></table></div>${pager(cfg.page,rows.length,'trend')}`}<p class="muted">当前小时尚未结束；空白耗时表示该小时没有已完成记录。所有次数来自完整时间窗口。</p></section>`;
}
async function overview() {
  if(state.overviewTab==='trend')return tabs([['tasks','任务监控'],['trend','运行趋势'],['jobs','执行管理'],['history','最近运行']],state.overviewTab)+`<div class="analysis-body">${await trends()}</div>`;
  const [overview,config] = await Promise.all([api('/api/overview'),api('/api/config')]);
  const d=overview.data;
  let content;
  if (state.overviewTab==='history') content=`<section class="card full-panel"><h2>最近运行</h2>${runTable(d.recent_runs.slice(0,pageSize()))}<a class="mini" href="${PAGE_URLS.runs}">筛选全部历史 →</a></section>`;
  else if(state.overviewTab==='jobs')content=`<section class="card"><h2>执行管理</h2>${serviceControls()}<div data-jobs>${jobsPanel()}</div></section>`;
  else content=`<div class="grid three task-cards">${TASKS.map(t=>{const cfg=config.data.tasks[t], latest=d.recent_runs.find(r=>r.task_type===t);return `<section class="card"><h2>${LABELS[t]}</h2>${metric('周期',`${cfg.period_seconds} 秒`)}${metric('自动执行',cfg.enabled?'启用':'停用')}<p>${latest?badge(latest.status):'暂无记录'}</p><div class="btn-row">${button(t)}<a class="mini" href="${PAGE_URLS[t]}">查看</a></div></section>`}).join('')}</div><section class="card service-card">${metric('累计执行',d.counts.total_runs)}${metric('执行失败',d.counts.failed_runs)}<button type="button" class="mini" data-tab="jobs">后台调度与任务进度 →</button></section>`;
  return tabs([['tasks','任务监控'],['trend','运行趋势'],['jobs','执行管理'],['history','最近运行']],state.overviewTab)+`<div class="analysis-body">${content}</div>`;
}
async function history(name) {
  const params = new URLSearchParams({limit:pageSize(),offset:state.page*pageSize()});
  if(name)params.set('task',name);
  else for(const [key,value] of Object.entries(state.filter))if(value)params.set(key,value);
  const data=await api(`/api/runs?${params}`);
  return `<section class="card full-panel"><div class="section-head"><h2>运行历史</h2><div class="btn-row">${(name?[name]:TASKS).map(button).join('')}</div></div>${name?'':`<div class="filter-row">${[['task',[['se','SE'],['lf','LF'],['ca','CA']]],['status',[['succeeded','成功'],['failed','失败'],['running','运行中']]],['source',[['manual','人工'],['schedule','周期']]]].map(([key,options])=>`<select aria-label="${key}" data-filter="${key}"><option value="">全部${{task:'任务',status:'状态',source:'来源'}[key]}</option>${options.map(([v,l])=>`<option value="${v}" ${state.filter[key]===v?'selected':''}>${l}</option>`).join('')}</select>`).join('')}<button class="mini" data-action="clear">重置</button></div>`}${runTable(data.data)}${pager(state.page,data.meta.total,'history')}</section>`;
}
const fieldLabels={measurement_name:'量测',measurement_type:'类型',measurement_idx:'量测序号',device_name:'设备',device_type:'设备类型',value:'原值',estimated_value:'估计值',residual:'残差',normalized_residual:'标准化残差',valid:'有效',source:'来源',reason:'原因',device_key:'设备',domain:'域',node_from:'首端节点',node_to:'末端节点',voltage_from:'首端电压',voltage_to:'末端电压',p_from:'首端 P',q_from:'首端 Q',p_to:'末端 P',q_to:'末端 Q',current_from:'首端电流',current_to:'末端电流',contingency:'故障场景',risk_source:'风险来源',risk_type:'风险类型',risk_info:'风险说明',risk_value_real:'风险值',risk_value_text:'风险值文本',risk_dist:'风险对象',created_at:'写入时间'};
function dataTable(data,cfg,name) {
  const columns=data.columns||[], count=colSize();
  cfg.col=Math.min(cfg.col,Math.max(0,Math.ceil(columns.length/count)-1));
  const cols=columns.slice(cfg.col*count,(cfg.col+1)*count);
  state.exportData={rows:data.rows,columns,filename:`${name}.csv`};
  return `<div class="field-pager"><button class="mini" data-col="-1" ${cfg.col===0?'disabled':''}>前组字段</button><span>字段 ${cfg.col*count+1}–${Math.min((cfg.col+1)*count,columns.length)} / ${columns.length}</span><button class="mini" data-col="1" ${(cfg.col+1)*count>=columns.length?'disabled':''}>后组字段</button><button class="mini" data-action="export">本页导出</button>${cfg.mode==='details'?'<button class="mini" data-action="export-filtered">筛选导出</button>':''}</div>${data.rows.length?`<div class="table-wrap"><table><thead><tr>${cols.map(c=>`<th title="${esc(c.name)}">${cfg.mode==='details'?`<button class="sort-head" data-sort="${c.name}">${esc(fieldLabels[c.name]||c.name)}${cfg.sort===c.name?(cfg.direction==='asc'?' ↑':' ↓'):''}</button>`:esc(fieldLabels[c.name]||c.name)}</th>`).join('')}</tr></thead><tbody>${data.rows.map(row=>`<tr>${cols.map(c=>`<td tabindex="0" data-value="${esc(row[c.name]??'—')}" title="点击查看完整值">${esc(row[c.name]??'—')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:empty('没有匹配记录')}${pager(cfg.page,data.meta.total,'browse')}`;
}
async function browser(name,id,mode) {
  const token=state.token, cfg=state.browse[name];
  if(cfg.mode!==mode){Object.assign(cfg,{page:0,col:0,q:'',mode,sort:'',direction:'asc',view:'all'});}
  const params=new URLSearchParams({limit:pageSize(),offset:cfg.page*pageSize(),q:cfg.q,sort:cfg.sort,direction:cfg.direction,view:cfg.view});
  let tableSelect='',url=`/api/results/${name}/${id}/details?${params}`;
  if(mode==='dbdef') {
    const tables=(await api(`/api/dbdef/${name}/${id}`)).data.tables;
    if(!tables.length)return `<section class="card">${empty('本次运行尚无 dbdef 结果')}</section>`;
    if(!tables.some(t=>t.table_name===cfg.table))cfg.table=tables[0].table_name;
    tableSelect=`<select data-table aria-label="dbdef 表">${tables.map(t=>`<option value="${t.table_name}" ${cfg.table===t.table_name?'selected':''}>${t.table_name} (${t.row_count})</option>`).join('')}</select>`;
    url=`/api/dbdef/${name}/${id}/${cfg.table}?${params}`;
  }
  const data=(await api(url)).data;
  if(token!==state.token)return '';
  const options={se:[['all','全部量测'],['invalid','无效量测'],['valid','有效量测']],lf:[['all','全部域'],['ac','AC'],['dc','DC'],['dcac','DC/AC'],['acac','AC/AC']],ca:[['all','全部场景'],['n0','N-0'],['n1','N-1']]}[name];
  return `<section class="card full-panel"><div class="section-head"><h2>${mode==='dbdef'?'dbdef 原始表':'计算明细'} · #${id}</h2></div><form data-search class="filter-row">${tableSelect}<input aria-label="搜索明细" name="q" value="${esc(cfg.q)}" placeholder="搜索全部字段"><button class="mini">筛选</button><button type="button" class="mini" data-action="reset-search">重置</button></form>${mode==='details'?`<div class="filter-row"><select aria-label="分类筛选" data-detail-view>${options.map(([v,l])=>`<option value="${v}" ${cfg.view===v?'selected':''}>${l}</option>`).join('')}</select><select aria-label="排序字段" data-detail-sort><option value="">默认顺序</option>${name==='se'?`<option value="abs_residual" ${cfg.sort==='abs_residual'?'selected':''}>残差绝对值</option>`:''}${data.columns.map(c=>`<option value="${c.name}" ${cfg.sort===c.name?'selected':''}>${fieldLabels[c.name]||c.name}</option>`).join('')}</select><button class="mini" data-action="direction">${cfg.direction==='asc'?'升序 ↑':'降序 ↓'}</button></div>`:''}${dataTable(data,cfg,`${name}-${id}-${mode==='dbdef'?cfg.table:'details'}`)}</section>`;
}
function summaryFields(name,s) {
  const fields=name==='se'?[['收敛',s.converged?'是':'否'],['可观测',s.observable?'是':'否'],['迭代次数',s.iterations],['目标函数',number(s.objective)],['残差',number(s.residual_inf)],['不良量测',s.bad_data_count]]:name==='lf'?[['收敛',s.converged?'是':'否'],['迭代次数',s.iterations],['范数',number(s.norm_f)],['AC 收敛',s.ac_converged==null?'—':s.ac_converged?'是':'否'],['DC 收敛',s.dc_converged==null?'—':s.dc_converged?'是':'否'],['原因',s.failure_reason||'—']]:[['风险等级',s.risk_level],['N-0 风险',s.n0_risk_count],['N-1 扫描',s.n1_scan_count],['N-1 风险',s.n1_risk_count]];
  return `<div class="metric-grid">${fields.map(([k,v])=>metric(k,v)).join('')}</div>`;
}
function controlView(cfg,name) {
  return `<div class="control-tabs"><button class="mini" data-control="config">周期参数</button><button class="mini" data-control="jobs">任务进度与服务</button></div><section class="card">${state.controlTab==='config'?scheduleEditor(cfg,name):`<h2>后台服务</h2>${serviceControls()}<div data-jobs="${task()?name:''}">${jobsPanel(task()?name:null)}</div>`}</section>`;
}
function scheduleEditor(cfg,name) {
  const t=cfg.tasks[name];
  return `<form data-schedule="${name}" class="schedule-form"><h2>${LABELS[name]} 调度参数</h2><label>周期（秒，1 至 604800）<input name="period" type="number" min="1" max="604800" step="any" required value="${t.period_seconds}"></label><label class="check"><input type="checkbox" name="enabled" ${t.enabled?'checked':''}> 启用周期自动执行</label><div class="btn-row"><button class="primary">保存并生效</button>${button(name)}</div><p class="muted">保存在 PAS 数据库；重启后恢复。修改周期后，从保存时刻重新计时。</p></form>`;
}
const METRIC_LABELS={kernel_seconds:'内核调用与整理',persistence_seconds:'写库（提交前）',model_read_seconds:'模型读取 / 复制',solve_seconds:'求解',normalization_seconds:'结果整理',model_cache_hit:'模型模板命中'};
function summaryView(name,id,d) {
  const r=d.run,s=d.result?.summary,mode=state.summaryMode;
  let content;
  if(mode==='timing')content=(d.result?.metrics||[]).map(m=>metric(METRIC_LABELS[m.name]||m.name,m.name==='model_cache_hit'?(m.value_real?'是':'否'):number(m.value_real)+' 秒')).join('')||empty('这条历史记录没有分项耗时');
  else if(mode==='info')content=[['触发方式',sourceLabel(r.execution_source)],['开始时间',r.started_at],['结束时间',r.finished_at],['输入指纹',r.input_fingerprint],['内核目录',r.kernel_root]].map(([l,v])=>`<div class="path-row"><strong>${l}</strong><span tabindex="0" data-value="${esc(v)}">${esc(v??'—')}</span></div>`).join('');
  else content=r.status==='failed'?`<p class="error-text" data-value="${esc(r.error_message)}">${esc(r.error_type)}：${esc(r.error_message)}</p>`:s?summaryFields(name,s)+metric('明细记录',d.result.detail_count)+metric('执行耗时',number(r.elapsed_seconds)+' 秒'):empty('正在计算，完成后可刷新查看');
  return `<div class="control-tabs">${[['result','计算结果'],['timing','性能分项'],['info','运行信息']].map(([v,l])=>`<button class="mini ${mode===v?'selected':''}" data-summary="${v}">${l}</button>`).join('')}</div><section class="card"><div class="section-head"><h2>运行 #${id}</h2>${badge(r.status)}</div>${content}<div class="btn-row"><button class="mini" data-tab="details">浏览明细</button><button class="mini" data-action="latest">读取最新结果</button>${button(name)}</div></section>`;
}
const DIAG_LABELS={total:'记录数',valid:'有效量测',invalid:'无效量测',max_abs_residual:'最大绝对残差',residual_count:'含残差记录',missing_power:'缺首端 P 记录',min_voltage:'首端电压最小值',max_voltage:'首端电压最大值',n0:'N-0 风险',n1:'N-1 风险',risk_types:'风险类型数',category:'分类',count:'数量',device_type:'设备类型',contingency:'故障场景'};
async function diagnosticView(name,id) {
  const d=(await api(`/api/results/${name}/${id}/diagnostics`)).data;
  const allKeys=Object.keys(d.groups[0]||{category:0,count:0}),count=colSize()-1;
  const pages=Math.max(1,Math.ceil((allKeys.length-1)/count));
  state.diagCol=Math.min(state.diagCol,pages-1);
  const keys=[allKeys[0],...allKeys.slice(1+state.diagCol*count,1+(state.diagCol+1)*count)];
  const rows=d.groups.slice(state.diagPage*pageSize(),(state.diagPage+1)*pageSize());
  const fields=pages>1?`<div class="field-pager"><button class="mini" data-diag-col="-1" ${state.diagCol===0?'disabled':''}>前组字段</button><span>字段组 ${state.diagCol+1} / ${pages}</span><button class="mini" data-diag-col="1" ${state.diagCol===pages-1?'disabled':''}>后组字段</button></div>`:'';
  return `<section class="card full-panel"><div class="section-head"><h2>诊断统计 · #${id}</h2><button class="mini" data-tab="details">查看明细</button></div><div class="diagnostic-metrics">${Object.entries(d.metrics).map(([k,v])=>`<span>${DIAG_LABELS[k]||k} <strong>${v==null?'—':number(v)}</strong></span>`).join('')}</div>${fields}<div class="table-wrap"><table><thead><tr>${keys.map(k=>`<th title="${DIAG_LABELS[k]||k}">${DIAG_LABELS[k]||k}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${keys.map(k=>`<td tabindex="0" data-value="${esc(r[k]??'—')}" title="点击查看完整值">${esc(typeof r[k]==='number'?number(r[k]):r[k]??'—')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${pager(state.diagPage,d.groups.length,'diagnostics')}<small class="muted">按已回写记录统计；空值表示该字段无可用数据。跨设备数值范围不作为越限判定。</small></section>`;
}
async function analysis(name) {
  const active=state.tabs[name];let content;
  if(active==='history')content=await history(name);
  else if(active==='operation') {
    const cfg=(await api('/api/config')).data;
    content=controlView(cfg,name);
  } else {
    const query=new URLSearchParams(state.route.split('?')[1]||'');
    let id=query.get('run')||state.selected[name];
    if(!id)id=(await api(`/api/runs?task=${name}&limit=1`)).data[0]?.run_id;
    if(!id)content=`<section class="card">${empty('暂无结果，可在执行控制中启动计算')}${button(name)}</section>`;
    else {
      state.selected[name]=id;
      if(active==='details'||active==='dbdef')content=await browser(name,id,active);
      else if(active==='diagnostics')content=await diagnosticView(name,id);
      else {
        const d=(await api(`/api/runs/${name}/${id}?compact=1`)).data,r=d.run,s=d.result?.summary;
        content=summaryView(name,id,d);

      }
    }
  }
  return tabs([['summary','结果摘要'],['diagnostics','诊断统计'],['history','运行记录'],['details','计算明细'],['dbdef','dbdef 表'],['operation','执行控制']],active)+`<div class="analysis-body">${content}</div>`;
}
async function workspace() {
  const cfg=(await api('/api/config')).data,w=cfg.workspace||{};
  let rows,title;
  if(state.workspaceTab==='model') {
    title='模型与计算输入';
    rows=[['SQLite 模型',cfg.tasks.lf?.model_file],['SE 量测',cfg.tasks.se?.measurement_file],['SCADA采集库',cfg.tasks.se?.scada_source_file],['SE 参数',cfg.tasks.se?.parameter_file],['LF 参数',cfg.tasks.lf?.parameter_file],['CA 限值',cfg.tasks.ca?.limit_file]];
  } else if(state.workspaceTab==='results') {
    title='计算结果与参数日志';
    rows=[['PAS 参数日志',cfg.control_database],...TASKS.map(t=>[`${t.toUpperCase()} 计算结果`,cfg.result_databases[t]])];
  } else {
    title='当前工作目录';
    rows=[['根目录',w.workspace_root],['运行态',w.runtime],['场景名',w.scenario],['工作目录',w.workspace_directory]];
  }
  const html=rows.map(([label,value])=>`<div class="workspace-row"><strong>${esc(label)}</strong><button class="workspace-path ghost" data-value="${esc(value||'未配置')}" title="查看完整路径">${esc(value||'未配置')}</button></div>`).join('');
  return tabs([['directory','目录参数'],['model','模型输入'],['results','结果数据库']],state.workspaceTab)+`<div class="analysis-body"><section class="card full-panel"><h2>${title}</h2>${html}</section></div>`;
}
async function settings() {
  let content;
  const cfg=(await api('/api/config')).data;
  const health=state.settingsTab==='database'?(await api('/api/health')).data:null;
  if(state.settingsTab==='schedule')content=`<div class="settings-select"><select aria-label="调度任务" data-schedule-task>${TASKS.map(t=>`<option value="${t}" ${state.scheduleTask===t?'selected':''}>${LABELS[t]}</option>`).join('')}</select></div>${controlView(cfg,state.scheduleTask)}`;
  else if(state.settingsTab==='logs') {
    const d=await api(`/api/logs?limit=${pageSize()}&offset=${state.logPage*pageSize()}`);
    content=`<section class="card full-panel"><h2>PAS 日志</h2><div class="table-wrap"><table><thead><tr><th>时间</th><th>级别</th><th>消息</th><th>上下文</th></tr></thead><tbody>${d.data.map(l=>`<tr><td data-value="${esc(l.created_at)}">${esc(l.created_at)}</td><td>${esc(l.level)}</td><td data-value="${esc(l.message)}">${esc(l.message)}</td><td data-value="${esc(l.context_json)}">${esc(l.context_json)}</td></tr>`).join('')}</tbody></table></div>${pager(state.logPage,d.meta.total,'logs')}</section>`;
  } else {
    const databases=health?.databases||{};
    const dbRows=[['PAS',databases.pas],...TASKS.map(t=>[t.toUpperCase(),databases[t]])].map(([name,item])=>`<div class="health-row"><strong>${name}</strong><span>${item?healthBadge(item.sqlite==='ok'&&item.exists):healthBadge(false)}</span><span class="health-path" tabindex="0" data-value="${esc(item?.path||'—')}" title="点击查看完整路径">${esc(item?.path||'—')}</span></div>`).join('');
    const taskRows=TASKS.map(name=>{const item=health?.tasks?.[name]||{};const latest=item.latest_run;return `<div class="health-row"><strong>${name.toUpperCase()}</strong><span>${healthBadge(item.inputs_ready!==false)}</span><span>${item.inputs_ready===false?`缺少：${esc((item.missing_inputs||[]).join('、'))}`:`最近 ${latest?`${statusLabel(latest.status)} · #${latest.run_id}`:'暂无运行'}`}</span></div>`;}).join('');
    content=`<div class="two health-grid"><section class="card"><div class="section-head"><h2>SQLite 数据库</h2>${healthBadge(health?.status==='ok')}</div>${dbRows}<div class="health-row"><strong>内核</strong><span>${healthBadge(Boolean(cfg.kernel_root))}</span><span class="health-path" tabindex="0" data-value="${esc(cfg.kernel_root)}" title="点击查看完整路径">${esc(cfg.kernel_root)}</span></div></section><section class="card"><div class="section-head"><h2>任务输入与最近运行</h2>${healthBadge(health?.status==='ok')}</div>${taskRows}</section></div>`;
  }
  return tabs([['schedule','调度参数'],['database','数据库'],['logs','运行日志']],state.settingsTab)+`<div class="analysis-body">${content}</div>`;
}
async function render() {
  const token=++state.token;state.exportData=null;
  const route=state.route.split('?')[0], name=task();
  document.querySelector('#page-title').textContent=name?LABELS[name]:({'/runs':'运行历史','/settings':'系统设置','/workspace':'工作目录','/measurements':'设备量测','/limits':'安全限值'}[route]||'运行总览');
  document.querySelectorAll('[data-route]').forEach(a=>a.classList.toggle('active',a.dataset.route===(name||route.slice(1))));
  try {
    const html=name?await analysis(name):route==='/runs'?await history():route==='/settings'?await settings():route==='/workspace'?await workspace():['/measurements','/limits'].includes(route)?await inputPage(route.slice(1)):await overview();
    if(token===state.token)document.querySelector('#app').innerHTML=html;
  } catch(e) {if(token===state.token)document.querySelector('#app').innerHTML=`<section class="card"><h2>加载失败</h2><p>${esc(e.message)}</p><button class="mini" data-action="refresh">重试</button></section>`;}
}
async function refreshStatus() {
  if(state.polling||document.hidden)return;state.polling=true;
  try {
    const d=(await api('/api/status')).data;state.status=d;
    document.querySelector('#service-state').textContent=d.daemon_running?'周期调度运行中':'Web 在线 · 周期停止';
    document.querySelectorAll('[data-task]').forEach(b=>{b.disabled=busy(b.dataset.task);b.textContent=`${busy(b.dataset.task)?'执行中':'执行'} ${b.dataset.task.toUpperCase()}`;});
    document.querySelectorAll('[data-jobs]').forEach(el=>el.innerHTML=jobsPanel(el.dataset.jobs));
    for(const [id,name] of state.watching) {
      const job=d.jobs?.find(j=>j.job_id===id)||(await api(`/api/jobs/${id}`)).data;
      if(['succeeded','failed'].includes(job.status)) {
        notify(`${LABELS[name]} ${statusLabel(job.status)}${job.run_id?' · 运行 #'+job.run_id:''}${job.error_message?'：'+job.error_message:''}`,job.status==='failed');
        state.watching.delete(id);
        // Keep forms and the selected historical run stable while polling.
        if(task()===name && state.tabs[name]==='summary' && !new URLSearchParams(state.route.split('?')[1]||'').has('run')){state.selected[name]=job.run_id;render();}
      }
    }
  } catch(e) {document.querySelector('#service-state').textContent='服务暂不可用';} finally {state.polling=false;}
}
async function submit(name) {
  const d=(await api('/api/actions/submit',name?{task:name}:{})).data;
  const jobs=d.tasks?Object.values(d.tasks):[d];
  for(const j of jobs)if(j.accepted)state.watching.set(j.job_id,j.task);
  notify(jobs.map(j=>`${j.task.toUpperCase()}：${j.accepted?'已接受，后台执行':'正在执行，未重复提交'}`).join('；'));
  await refreshStatus();
}
function exportPage() {
  const d=state.exportData;if(!d)return;
  const cell=v=>{let s=String(v??'');if(typeof v==='string'&&/^\s*[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
  const csv=[d.columns.map(c=>cell(c.name)),...d.rows.map(r=>d.columns.map(c=>cell(r[c.name])))].map(r=>r.join(',')).join('\r\n');
  const url=URL.createObjectURL(new Blob(['\ufeff',csv],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=d.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function showValue(value,page=0) {
  // Bound both wrapped line count and explicit newlines so every segment fits.
  const width=Math.max(20,Math.floor(Math.min(580,innerWidth*.9-44)/8));
  const lines=Math.max(4,Math.floor(innerHeight*.45/20));
  const chunks=[];let chunk='',line=0,column=0;
  for(const char of value){chunk+=char;column++;if(char==='\n'||column>=width){line++;column=0;}if(line>=lines){chunks.push(chunk);chunk='';line=0;}}
  if(chunk||!chunks.length)chunks.push(chunk);
  page=Math.min(page,chunks.length-1);
  const pages=chunks.length,dialog=document.querySelector('#value-dialog');
  state.value={value,page};
  dialog.innerHTML=`<h2>完整字段值</h2><pre>${esc(chunks[page])}</pre><div class="btn-row"><button class="mini" data-value-page="-1" ${page===0?'disabled':''}>上一段</button><span>${page+1} / ${pages}</span><button class="mini" data-value-page="1" ${page+1>=pages?'disabled':''}>下一段</button><button class="primary" data-action="close-dialog">关闭</button></div>`;
  if(!dialog.open)dialog.showModal();
}
document.addEventListener('submit',async e=>{
  if(!e.target.matches('[data-search],[data-schedule]'))return;e.preventDefault();
  try {
    const data=new FormData(e.target);
    if(e.target.matches('[data-search]')){Object.assign(state.browse[task()],{q:data.get('q'),page:0});return render();}
    const name=e.target.dataset.schedule;
    await api(`/api/schedules/${name}`,{period_seconds:Number(data.get('period')),enabled:data.has('enabled')});
    notify(`${LABELS[name]} 调度参数已保存并生效`);await refreshStatus();
  } catch(err){notify(err.message,true);}
});
document.addEventListener('change',e=>{
  if(e.target.matches('[data-trend]')){state.trend[e.target.dataset.trend]=e.target.value;state.trend.page=0;render();}
  if(e.target.matches('[data-detail-view],[data-detail-sort]')){state.browse[task()][e.target.hasAttribute('data-detail-view')?'view':'sort']=e.target.value;state.browse[task()].page=0;render();}

  if(e.target.matches('[data-filter]')){state.filter[e.target.dataset.filter]=e.target.value;state.page=0;render();}
  if(e.target.matches('[data-table]')){Object.assign(state.browse[task()],{table:e.target.value,page:0,col:0});render();}
  if(e.target.matches('[data-schedule-task]')){state.scheduleTask=e.target.value;render();}
});
document.addEventListener('click',async e=>{
  const el=e.target.closest('button,[data-value]');if(!el||el.disabled)return;
  if(el.closest('[data-schedule]') && el.dataset.task)e.preventDefault();
  try {
    if(el.dataset.task){el.disabled=true;return await submit(el.dataset.task);}
    if(el.hasAttribute('data-value'))return showValue(el.dataset.value);
    if(el.dataset.valuePage)return showValue(state.value.value,state.value.page+Number(el.dataset.valuePage));
    if(el.dataset.summary){state.summaryMode=el.dataset.summary;return render();}
    if(el.dataset.diagCol){state.diagCol+=Number(el.dataset.diagCol);return render();}
    if(el.dataset.sort){const c=state.browse[task()];c.direction=c.sort===el.dataset.sort&&c.direction==='asc'?'desc':'asc';c.sort=el.dataset.sort;c.page=0;return render();}
    if(el.dataset.control){state.controlTab=el.dataset.control;return render();}
    if(el.dataset.tab){if(task())state.tabs[task()]=el.dataset.tab;else if(state.route==='/settings')state.settingsTab=el.dataset.tab;else if(state.route==='/workspace')state.workspaceTab=el.dataset.tab;else state.overviewTab=el.dataset.tab;state.page=0;state.diagPage=0;return render();}
    if(el.dataset.page){const delta=Number(el.dataset.page);if(el.dataset.scope==='trend')state.trend.page+=delta;else if(el.dataset.scope==='diagnostics')state.diagPage+=delta;else if(el.dataset.scope==='browse')state.browse[task()].page+=delta;else if(el.dataset.scope==='logs')state.logPage+=delta;else state.page+=delta;return render();}
    if(el.dataset.col){state.browse[task()].col+=Number(el.dataset.col);return render();}
    const action=el.dataset.action;
    if(action==='all'||action==='run-all'){el.disabled=true;try{return await submit();}finally{el.disabled=false;}}
    if(action==='retry-failed'){el.disabled=true;try{const d=(await api('/api/actions/retry-failed',task()?{task:task()}:{})).data;const jobs=Object.values(d.tasks||{});for(const j of jobs)if(j.accepted)state.watching.set(j.job_id,j.task);notify(jobs.length?jobs.map(j=>`${j.task.toUpperCase()}：${j.accepted?'已接受重试':({no_failed_run:'最近任务未失败',already_running:'任务执行中'}[j.reason]||j.reason)}`).join('；'):'没有失败任务');await refreshStatus();}finally{el.disabled=false;}return render();}
    if(action?.startsWith('daemon-')){const r=await api(`/api/actions/daemon/${action.slice(7)}`,{});notify(r.data.stopping?'正在停止调度':action==='daemon-start'?'周期调度已启动':'周期调度已停止；当前任务将继续完成');return refreshStatus();}
    if(action==='direction'){const c=state.browse[task()];c.direction=c.direction==='asc'?'desc':'asc';c.page=0;return render();}
    if(action==='export-filtered'){const name=task(),id=state.selected[name],c=state.browse[name];const q=new URLSearchParams({q:c.q,sort:c.sort,direction:c.direction,view:c.view});const response=await fetch(`/api/export/${name}/${id}?${q}`);if(!response.ok)throw new Error((await response.json()).error);const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download=`${name}-${id}-filtered.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notify('筛选结果已导出，包含全部匹配行');return;}
    if(action==='export')return exportPage();
    if(action==='close-dialog')return document.querySelector('#value-dialog').close();
    if(action==='clear'){state.filter={task:'',status:'',source:''};state.page=0;}
    if(action==='reset-search')Object.assign(state.browse[task()],{q:'',page:0});
    if(action==='latest'){state.selected[task()]=null;window.location.href=pageUrl(state.route.split('?')[0]);return;}
    if(['refresh','clear','reset-search','latest'].includes(action))return render();
  }catch(err){notify(err.message,true);await refreshStatus();}
});
document.addEventListener('keydown',e=>{const target=e.target.closest?.('[data-value]');if(e.key==='Enter'&&target){e.preventDefault();showValue(target.dataset.value);}});
window.addEventListener('hashchange',()=>{const route=location.hash.slice(1)||'/overview';window.location.href=pageUrl(route,route.includes('?')?`?${route.split('?')[1]}`:'');});
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{state.page=0;state.logPage=0;state.diagPage=0;state.trend.page=0;for(const b of Object.values(state.browse))b.page=0;render();},180);});
(function initSidebarSplitter(){
  const shell=document.querySelector('.app-shell'),sidebar=shell?.querySelector('.sidebar');
  if(!shell||!sidebar||shell.querySelector('.sidebar-resizer'))return;
  const W_KEY='pas_sidebar_width',C_KEY='pas_sidebar_collapsed',MIN_W=160,MAX_W=340,TH=100;
  let savedWidth=Math.min(MAX_W,Math.max(MIN_W,Number(localStorage.getItem(W_KEY))||214));
  let collapsed=localStorage.getItem(C_KEY)==='1';
  const resizer=document.createElement('div');
  resizer.className='sidebar-resizer';resizer.setAttribute('role','separator');resizer.setAttribute('aria-orientation','vertical');
  resizer.title='拖动调整宽度 / 双击隐藏或展开';
  const btn=document.createElement('button');btn.type='button';btn.className='sidebar-toggle-btn';
  resizer.appendChild(btn);sidebar.insertAdjacentElement('afterend',resizer);
  const emitResize=()=>{window.dispatchEvent(new Event('resize'));setTimeout(()=>window.dispatchEvent(new Event('resize')),180);};
  const apply=(notify=false)=>{
    sidebar.classList.toggle('is-collapsed',collapsed);resizer.classList.toggle('is-collapsed',collapsed);
    if(!collapsed){sidebar.style.width=`${savedWidth}px`;sidebar.style.flexBasis=`${savedWidth}px`;}
    btn.textContent=collapsed?'›':'‹';btn.title=collapsed?'展开左侧目录树':'隐藏左侧目录树';btn.setAttribute('aria-label',btn.title);
    localStorage.setItem(C_KEY,collapsed?'1':'0');localStorage.setItem(W_KEY,String(Math.round(savedWidth)));
    if(notify)emitResize();
  };
  btn.addEventListener('pointerdown',e=>e.stopPropagation());
  btn.addEventListener('click',e=>{e.stopPropagation();collapsed=!collapsed;apply(true);});
  resizer.addEventListener('dblclick',()=>{collapsed=!collapsed;apply(true);});
  let dragging=false,moved=false,startX=0;
  resizer.addEventListener('pointerdown',e=>{if(e.button!==0||e.target===btn)return;dragging=true;moved=false;startX=e.clientX;resizer.setPointerCapture(e.pointerId);sidebar.classList.add('is-resizing');resizer.classList.add('is-active');document.body.classList.add('sidebar-resizing');});
  resizer.addEventListener('pointermove',e=>{if(!dragging)return;if(Math.abs(e.clientX-startX)>3)moved=true;if(e.clientX<TH){collapsed=true;sidebar.classList.add('is-collapsed');resizer.classList.add('is-collapsed');btn.textContent='›';}else{collapsed=false;savedWidth=Math.min(MAX_W,Math.max(MIN_W,e.clientX));sidebar.classList.remove('is-collapsed');resizer.classList.remove('is-collapsed');sidebar.style.width=`${savedWidth}px`;sidebar.style.flexBasis=`${savedWidth}px`;btn.textContent='‹';}});
  const end=e=>{if(!dragging)return;dragging=false;if(e&&resizer.hasPointerCapture?.(e.pointerId))resizer.releasePointerCapture(e.pointerId);sidebar.classList.remove('is-resizing');resizer.classList.remove('is-active');document.body.classList.remove('sidebar-resizing');if(!moved&&collapsed)collapsed=false;apply(true);};
  resizer.addEventListener('pointerup',end);resizer.addEventListener('pointercancel',end);
  apply(false);
})();
refreshStatus().then(render);
async function poll(){await refreshStatus();setTimeout(poll,state.watching.size||(state.status.active_tasks||[]).length?2000:6000);}
setTimeout(poll,6000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshStatus();});
