const TASKS = ['se', 'lf', 'ca'];
const LABELS = {se:'状态估计 SE', lf:'潮流分析 LF', ca:'静态安全 CA'};
const state = {
  route: location.hash.slice(1) || '/overview', token: 0, page: 0,
  filter: {task:'', status:'', source:''}, overviewTab:'tasks', settingsTab:'schedule',
  tabs: {se:'summary',lf:'summary',ca:'summary'}, selected:{},
  browse: Object.fromEntries(TASKS.map(t => [t,{page:0,col:0,q:'',table:'',mode:''}])),
  controlTab:'config', status:{}, watching:new Map(), exportData:null, logPage:0, scheduleTask:'se'
};
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const statusLabel = s => ({queued:'等待执行',running:'运行中',succeeded:'成功',failed:'失败'}[s] || s || '—');
const sourceLabel = s => s === 'manual' ? '人工触发' : '周期自动';
const number = v => v == null ? '—' : Number(v).toPrecision(5);
const pageSize = () => Math.max(2, Math.min(8, Math.floor((innerHeight - (innerWidth < 700 ? 490 : 380)) / 36)));
const colSize = () => innerWidth < 700 ? 3 : 6;
const task = () => state.route.match(/^\/analysis\/(se|lf|ca)/)?.[1];
const busy = t => [...(state.status.active_tasks || []), ...(state.status.pending_tasks || [])].includes(t);
const badge = s => `<span class="badge ${s === 'succeeded' ? 'success' : s === 'failed' ? 'failed' : s === 'running' || s === 'queued' ? 'running' : ''}">${esc(statusLabel(s))}</span>`;
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
  if (!res.ok || !data.ok) throw new Error(({already_running:'任务正在执行，请等待完成',invalid_task:'无效任务',service_stopping:'服务正在停止'}[data.error]) || data.error || '请求失败');
  return data;
}
function pager(page,total,scope) {
  const pages=Math.max(1,Math.ceil(total/pageSize()));
  return `<div class="pager"><button class="mini" data-page="-1" data-scope="${scope}" ${page<=0?'disabled':''}>上一页</button><span>${page+1} / ${pages} 页 · ${total} 条</span><button class="mini" data-page="1" data-scope="${scope}" ${page>=pages-1?'disabled':''}>下一页</button></div>`;
}
function runTable(rows) {
  if (!rows.length) return empty('暂无运行记录');
  return `<div class="table-wrap"><table><thead><tr><th>任务 / 来源</th><th>状态</th><th>开始时间</th><th>耗时 / 操作</th></tr></thead><tbody>${rows.map(r=>`<tr><td title="${sourceLabel(r.execution_source)}">${r.task_type.toUpperCase()} · ${r.execution_source==='manual'?'人工':'周期'}</td><td>${badge(r.status)}</td><td data-value="${esc(r.started_at)}" title="${esc(r.started_at)}">${esc(r.started_at)}</td><td><a href="#/analysis/${r.task_type}?run=${r.run_id}">${r.elapsed_seconds==null?'查看':Number(r.elapsed_seconds).toFixed(2)+'s'} →</a></td></tr>`).join('')}</tbody></table></div>`;
}
function jobsPanel(name) {
  const jobs = (state.status.jobs || []).filter(j=>!name || j.task===name).slice(-3).reverse();
  return jobs.length ? `<div class="job-list">${jobs.map(j=>`<div class="job-row"><strong>${j.task.toUpperCase()}</strong>${badge(j.status)}<span title="${esc(j.error_message || j.started_at || j.submitted_at)}">${esc(j.error_message || (j.elapsed_seconds == null ? sourceLabel(j.execution_source) : Number(j.elapsed_seconds).toFixed(2)+' s'))}</span>${j.run_id?`<a class="mini" href="#/analysis/${j.task}?run=${j.run_id}">结果 #${j.run_id}</a>`:''}</div>`).join('')}</div>` : empty('暂无本次服务启动后的任务');
}
function serviceControls() {
  return `<div class="btn-row"><button class="primary" data-action="all">执行全部</button><button class="mini" data-action="daemon-start">启动周期</button><button class="mini" data-action="daemon-stop">停止周期</button></div><p class="muted">停止周期后，已接受的计算仍会完成并保存结果。</p>`;
}
async function overview() {
  const [overview,config] = await Promise.all([api('/api/overview'),api('/api/config')]);
  const d=overview.data;
  let content;
  if (state.overviewTab==='history') content=`<section class="card full-panel"><h2>最近运行</h2>${runTable(d.recent_runs.slice(0,pageSize()))}<a class="mini" href="#/runs">筛选全部历史 →</a></section>`;
  else if(state.overviewTab==='jobs')content=`<section class="card"><h2>执行管理</h2>${serviceControls()}<div data-jobs>${jobsPanel()}</div></section>`;
  else content=`<div class="grid three task-cards">${TASKS.map(t=>{const cfg=config.data.tasks[t], latest=d.recent_runs.find(r=>r.task_type===t);return `<section class="card"><h2>${LABELS[t]}</h2>${metric('周期',`${cfg.period_seconds} 秒`)}${metric('自动执行',cfg.enabled?'启用':'停用')}<p>${latest?badge(latest.status):'暂无记录'}</p><div class="btn-row">${button(t)}<a class="mini" href="#/analysis/${t}">查看</a></div></section>`}).join('')}</div><section class="card service-card">${metric('累计执行',d.counts.total_runs)}${metric('执行失败',d.counts.failed_runs)}<button class="mini" data-tab="jobs">后台调度与任务进度 →</button></section>`;
  return tabs([['tasks','任务监控'],['jobs','执行管理'],['history','最近运行']],state.overviewTab)+`<div class="analysis-body">${content}</div>`;
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
  return `<div class="field-pager"><button class="mini" data-col="-1" ${cfg.col===0?'disabled':''}>前组字段</button><span>字段 ${cfg.col*count+1}–${Math.min((cfg.col+1)*count,columns.length)} / ${columns.length}</span><button class="mini" data-col="1" ${(cfg.col+1)*count>=columns.length?'disabled':''}>后组字段</button><button class="mini" data-action="export">导出本页</button></div>${data.rows.length?`<div class="table-wrap"><table><thead><tr>${cols.map(c=>`<th title="${esc(c.name)}">${esc(fieldLabels[c.name]||c.name)}</th>`).join('')}</tr></thead><tbody>${data.rows.map(row=>`<tr>${cols.map(c=>`<td tabindex="0" data-value="${esc(row[c.name]??'—')}" title="点击查看完整值">${esc(row[c.name]??'—')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:empty('没有匹配记录')}${pager(cfg.page,data.meta.total,'browse')}`;
}
async function browser(name,id,mode) {
  const token=state.token, cfg=state.browse[name];
  if(cfg.mode!==mode){Object.assign(cfg,{page:0,col:0,q:'',mode});}
  const params=new URLSearchParams({limit:pageSize(),offset:cfg.page*pageSize(),q:cfg.q});
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
  return `<section class="card full-panel"><div class="section-head"><h2>${mode==='dbdef'?'dbdef 原始表':'计算明细'} · #${id}</h2></div><form data-search class="filter-row">${tableSelect}<input aria-label="搜索明细" name="q" value="${esc(cfg.q)}" placeholder="搜索全部字段"><button class="mini">筛选</button><button type="button" class="mini" data-action="reset-search">重置</button></form>${dataTable(data,cfg,`${name}-${id}-${mode==='dbdef'?cfg.table:'details'}`)}</section>`;
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
      else {
        const d=(await api(`/api/runs/${name}/${id}?compact=1`)).data,r=d.run,s=d.result?.summary;
        content=`<section class="card"><div class="section-head"><h2>运行 #${id} · ${sourceLabel(r.execution_source)}</h2>${badge(r.status)}</div>${r.status==='failed'?`<p class="error-text" data-value="${esc(r.error_message)}">${esc(r.error_type)}：${esc(r.error_message)}</p>`:s?summaryFields(name,s):empty('正在计算，完成后可刷新查看')}${metric('耗时',r.elapsed_seconds==null?'—':number(r.elapsed_seconds)+' 秒')}${(d.result?.metrics||[]).map(m=>metric(m.name==='kernel_seconds'?'内核调用及结果整理':'结果写入（提交前）',number(m.value_real)+' 秒')).join('')}${metric('明细记录',d.result?.detail_count ?? 0)}<div class="btn-row"><button class="mini" data-tab="details">浏览全部明细</button><button class="mini" data-tab="dbdef">dbdef 表</button><button class="mini" data-action="latest">读取最新结果</button>${button(name)}</div></section>`;
      }
    }
  }
  return tabs([['summary','结果摘要'],['history','运行记录'],['details','计算明细'],['dbdef','dbdef 表'],['operation','执行控制']],active)+`<div class="analysis-body">${content}</div>`;
}
async function settings() {
  const cfg=(await api('/api/config')).data;let content;
  if(state.settingsTab==='schedule')content=`<div class="settings-select"><select aria-label="调度任务" data-schedule-task>${TASKS.map(t=>`<option value="${t}" ${state.scheduleTask===t?'selected':''}>${LABELS[t]}</option>`).join('')}</select></div>${controlView(cfg,state.scheduleTask)}`;
  else if(state.settingsTab==='logs') {
    const d=await api(`/api/logs?limit=${pageSize()}&offset=${state.logPage*pageSize()}`);
    content=`<section class="card full-panel"><h2>PAS 日志</h2><div class="table-wrap"><table><thead><tr><th>时间</th><th>级别</th><th>消息</th><th>上下文</th></tr></thead><tbody>${d.data.map(l=>`<tr><td data-value="${esc(l.created_at)}">${esc(l.created_at)}</td><td>${esc(l.level)}</td><td data-value="${esc(l.message)}">${esc(l.message)}</td><td data-value="${esc(l.context_json)}">${esc(l.context_json)}</td></tr>`).join('')}</tbody></table></div>${pager(state.logPage,d.meta.total,'logs')}</section>`;
  } else content=`<section class="card"><h2>SQLite 数据库</h2>${[['PAS',cfg.control_database],...TASKS.map(t=>[t.toUpperCase(),cfg.result_databases[t]]),['内核目录',cfg.kernel_root]].map(([k,v])=>`<div class="path-row"><strong>${k}</strong><span tabindex="0" data-value="${esc(v)}">${esc(v)}</span></div>`).join('')}</section>`;
  return tabs([['schedule','调度参数'],['database','数据库'],['logs','运行日志']],state.settingsTab)+`<div class="analysis-body">${content}</div>`;
}
async function render() {
  const token=++state.token;state.exportData=null;
  const route=state.route.split('?')[0], name=task();
  document.querySelector('#page-title').textContent=name?LABELS[name]:({'/runs':'运行历史','/settings':'系统设置'}[route]||'运行总览');
  document.querySelectorAll('[data-route]').forEach(a=>a.classList.toggle('active',a.dataset.route===(name||route.slice(1))));
  try {
    const html=name?await analysis(name):route==='/runs'?await history():route==='/settings'?await settings():await overview();
    if(token===state.token)document.querySelector('#app').innerHTML=html;
  } catch(e) {if(token===state.token)document.querySelector('#app').innerHTML=`<section class="card"><h2>加载失败</h2><p>${esc(e.message)}</p><button class="mini" data-action="refresh">重试</button></section>`;}
}
async function refreshStatus() {
  if(state.polling)return;state.polling=true;
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
  const cell=v=>{let s=String(v??'');if(/^[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
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
    if(el.dataset.control){state.controlTab=el.dataset.control;return render();}
    if(el.dataset.tab){if(task())state.tabs[task()]=el.dataset.tab;else if(state.route==='/settings')state.settingsTab=el.dataset.tab;else state.overviewTab=el.dataset.tab;state.page=0;return render();}
    if(el.dataset.page){const delta=Number(el.dataset.page);if(el.dataset.scope==='browse')state.browse[task()].page+=delta;else if(el.dataset.scope==='logs')state.logPage+=delta;else state.page+=delta;return render();}
    if(el.dataset.col){state.browse[task()].col+=Number(el.dataset.col);return render();}
    const action=el.dataset.action;
    if(action==='all'||action==='run-all'){el.disabled=true;try{return await submit();}finally{el.disabled=false;}}
    if(action?.startsWith('daemon-')){const r=await api(`/api/actions/daemon/${action.slice(7)}`,{});notify(r.data.stopping?'正在停止调度':action==='daemon-start'?'周期调度已启动':'周期调度已停止；当前任务将继续完成');return refreshStatus();}
    if(action==='export')return exportPage();
    if(action==='close-dialog')return document.querySelector('#value-dialog').close();
    if(action==='clear'){state.filter={task:'',status:'',source:''};state.page=0;}
    if(action==='reset-search')Object.assign(state.browse[task()],{q:'',page:0});
    if(action==='latest'){state.selected[task()]=null;state.route=state.route.split('?')[0];if(location.hash.slice(1)!==state.route){location.hash=state.route;return;}}
    if(['refresh','clear','reset-search','latest'].includes(action))return render();
  }catch(err){notify(err.message,true);await refreshStatus();}
});
document.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target.matches('[data-value]'))showValue(e.target.dataset.value);});
window.addEventListener('hashchange',()=>{state.route=location.hash.slice(1)||'/overview';state.page=0;const name=task();if(name&&state.route.includes('?run=')){state.tabs[name]='summary';Object.assign(state.browse[name],{page:0,col:0,q:''});}render();});
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{state.page=0;state.logPage=0;for(const b of Object.values(state.browse))b.page=0;render();},180);});
refreshStatus().then(render);window.setInterval(refreshStatus,2000);
