/* Progressive enhancement only: all research content is already in the HTML. */
(function () {
  'use strict';
  const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  function readable(value) {
    if (value === null || value === undefined) return '未公開／未核實';
    if (typeof value === 'string') return value;
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }
  function csvCell(value) {
    let text = readable(value);
    // Prefix dangerous spreadsheet formulas, including whitespace/control prefixes.
    if (/^[\s\u0000-\u001f\u007f]*[=+\-@]/u.test(text) || /^[\t\r\n]/u.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }
  function field(value, key, fallback = null) {
    return record(value) && Object.prototype.hasOwnProperty.call(value, key) ? value[key] : fallback;
  }
  function metric(value) {
    if (!record(value)) return value;
    for (const key of ['students', 'count', 'total']) {
      if (Object.prototype.hasOwnProperty.call(value, key)) return value[key];
    }
    return null;
  }
  function makeCSV(schools) {
    // Each row is one published enrolment entry; never sum years or infer grades.
    const columns = ['學校ID', '學校', '類別', '紀錄類別', '學年', '年級', '實際人數', '班數', '來源ID', '備註', '核實狀態', '原報告值', '總數範圍', '小六適用性', '班數口徑', '班數來源學年', '班數來源ID', '原報告班數', '來源備註'];
    const rows = [columns];
    const entries = value => Array.isArray(value) ? value : value == null ? [] : [value];
    schools.forEach(school => {
      if (!record(school)) { rows.push(['', readable(school), '', '不規則原始紀錄', '', '', null, null, '', '', null, null, null, null, null, null, null, null, null]); return; }
      const base = [school.id, school.name, school.category];
      const sourceRecords = record(school.sources) && !('id' in school.sources) && !('url' in school.sources)
        ? Object.entries(school.sources).map(([id, source]) => ({ id, ...(record(source) ? source : { note: source }) })) : entries(school.sources);
      const sourceNotes = refs => entries(refs).flatMap(ref => sourceRecords.filter(source => record(source) && String(source.id) === String(record(ref) ? ref.id : ref)).map(source => field(source, 'note'))).filter(note => note !== null);
      const enrolments = [{ label: '主記錄', value: school.enrolment }, ...entries(school.enrolment_history).map((value, i) => ({ label: `歷年記錄${i + 1}（不跨年相加）`, value }))];
      enrolments.forEach(({ label, value: enrolment }) => {
        const e = record(enrolment) ? enrolment : {};
        const row = (type, grade, value, published, total = false) => {
          const p = record(published) ? published : {};
          const year = field(p, 'academic_year', field(e, 'academic_year'));
          const sources = field(p, 'source_ids', field(e, 'source_ids'));
          const verification = total ? field(e, 'total_verification', field(p, 'verification')) : field(p, 'verification');
          const conflict = total && /unresolved.*conflict|conflict.*unresolved/i.test(String(verification));
          const reported = total ? field(e, 'reported_total', field(p, 'reported_total', value)) : field(p, 'reported_students', value);
          const notes = field(p, 'note', field(e, 'note'));
          const applicability = field(p, 'applicability', /^P6$|^小六(?:年級)?$/i.test(String(grade)) ? field(e.p6, 'applicability') : null);
          const classesYear = field(p, 'classes_academic_year', year);
          const classesSources = field(p, 'classes_source_ids', sources);
          rows.push([...base, `${label}／${type}`, year, grade,
            conflict || applicability === 'not_a_standard_primary_P6' ? null : value,
            field(p, 'classes'), sources, notes, verification, reported, field(e, 'total_scope'), applicability,
            field(p, 'classes_scope'), classesYear, classesSources, field(p, 'reported_classes'), sourceNotes(sources)]);
        };
        row('全校', '', metric(e.total), e.total, true);
        entries(e.grades).forEach(grade => {
          if (!record(grade)) { row('不規則年級紀錄', readable(grade), null, { academic_year: e.academic_year, note: readable(grade) }); return; }
          row('年級', grade.grade, grade.students, grade);
        });
        if (e.p6 !== null && e.p6 !== undefined) {
          row('獨立小六紀錄（勿與年級行重複相加）', 'P6', metric(e.p6), e.p6);
        }
      });
    });
    return '\ufeff' + rows.map(row => row.map(csvCell).join(',')).join('\r\n') + '\r\n';
  }
  function populateRawRecord(detail, schools) {
    if (!detail.open) return;
    const pre = detail.querySelector('pre');
    const key = Number(detail.dataset.schoolKey);
    if (!pre || pre.dataset.loaded || !Number.isInteger(key) || key < 0 || key >= schools.length) return;
    pre.textContent = JSON.stringify(schools[key], null, 2);
    pre.dataset.loaded = 'true';
  }
  function openAncestors(node) {
    let detail = node.closest('details');
    while (detail) {
      detail.open = true;
      detail = detail.parentElement ? detail.parentElement.closest('details') : null;
    }
  }
  function filtered(index, state) {
    const query = state.query.trim().toLocaleLowerCase();
    const rows = index.filter(item => (!query || item.search.toLocaleLowerCase().includes(query)) &&
      (!state.category || item.category === state.category) && (!state.knownP6 || item.p6_known));
    const key = state.sort === 'name' ? 'name' : state.sort.startsWith('total') ? 'total_sort' : 'p6_sort';
    const descending = state.sort.endsWith('desc');
    rows.sort((a, b) => {
      const x = a[key], y = b[key];
      const missingX = x === null || x === undefined, missingY = y === null || y === undefined;
      if (missingX !== missingY) return missingX ? 1 : -1;
      if (!missingX && x !== y) {
        const result = key === 'name' ? String(x).localeCompare(String(y), 'zh-Hant') : x - y;
        if (result) return descending ? -result : result;
      }
      return String(a.name).localeCompare(String(b.name), 'zh-Hant') || a.key - b.key;
    });
    return rows;
  }
  // Pure functions may also be contract-tested by Node without a browser or dependency.
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { csvCell, makeCSV, filtered, readable, populateRawRecord, openAncestors };
    return;
  }
  const payload = document.getElementById('site-data');
  if (!payload) return;
  let model;
  try { model = JSON.parse(payload.textContent); } catch (_) { return; }
  if (!Array.isArray(model.index) || !record(model.data) || !Array.isArray(model.data.schools)) return;
  document.querySelectorAll('details.raw-record[data-school-key]').forEach(detail => {
    detail.addEventListener('toggle', () => populateRawRecord(detail, model.data.schools));
  });
  const byId = id => document.getElementById(id);
  const q = byId('q'), category = byId('fType'), p6Only = byId('knownP6'), sort = byId('sortSchools');
  const destinationQuery = byId('destinationQuery'), destinationSelect = byId('destinationSchool');
  if (!q || !category || !p6Only || !sort) return;
  let current = model.index.slice();
  const schoolRows = Array.from(document.querySelectorAll('#rosterBody > tr[data-school-key]'));
  const schoolCards = Array.from(document.querySelectorAll('#cards > details[data-school-key]'));
  const socialRows = Array.from(document.querySelectorAll('#socialBody > tr[data-school-key]'));
  const sourceGroups = Array.from(document.querySelectorAll('#sourceGroups > details[data-school-key]'));
  const destinationBlocks = Array.from(document.querySelectorAll('#destinationBlocks > article[data-school-key]'));
  const containers = [[schoolRows, byId('rosterBody')], [schoolCards, byId('cards')], [socialRows, byId('socialBody')], [sourceGroups, byId('sourceGroups')]];
  function destinationFilter() {
    const visibleSchools = new Set(current.map(item => String(item.key)));
    const term = destinationQuery.value.trim().toLocaleLowerCase();
    const receiver = destinationSelect.value;
    const hasFilter = Boolean(term || receiver);
    let schoolCount = 0, entryCount = 0;
    destinationBlocks.forEach(block => {
      let visibleEntries = 0;
      block.querySelectorAll('tbody > tr[data-destination]:not([data-observed="false"])').forEach(row => {
        const name = row.dataset.destination;
        const show = visibleSchools.has(block.dataset.schoolKey) && (!term || name.toLocaleLowerCase().includes(term)) && (!receiver || name === receiver);
        row.hidden = !show;
        if (show) {
          visibleEntries += 1;
          if (hasFilter) openAncestors(row);
        }
      });
      block.hidden = !visibleSchools.has(block.dataset.schoolKey) || (hasFilter && visibleEntries === 0);
      if (!block.hidden) { schoolCount += 1; entryCount += visibleEntries; }
    });
    byId('destinationCount').textContent = `目前顯示 ${schoolCount} 校的 ${entryCount} 條接收中學紀錄（非志願次序）。`;
    byId('destinationEmpty').hidden = schoolCount > 0;
  }
  function render() {
    current = filtered(model.index, { query: q.value, category: category.value, knownP6: p6Only.checked, sort: sort.value });
    const visible = new Set(current.map(item => String(item.key)));
    const rank = new Map(current.map((item, i) => [String(item.key), i]));
    containers.forEach(([nodes, parent]) => {
      nodes.forEach(node => { node.hidden = !visible.has(node.dataset.schoolKey); });
      nodes.slice().sort((a, b) => (rank.get(a.dataset.schoolKey) ?? Infinity) - (rank.get(b.dataset.schoolKey) ?? Infinity)).forEach(node => parent.appendChild(node));
    });
    byId('rosterCount').textContent = `顯示 ${current.length} / ${model.index.length} 間學校；名冊、詳情、社媒及來源同步篩選。`;
    byId('schoolEmpty').hidden = current.length > 0;
    destinationFilter();
  }
  [q, category, p6Only, sort].forEach(control => control.addEventListener(control === q ? 'input' : 'change', render));
  byId('clearFilters').addEventListener('click', () => {
    q.value = ''; category.value = ''; p6Only.checked = false; sort.value = 'name';
    destinationQuery.value = ''; destinationSelect.value = ''; render(); q.focus();
  });
  destinationQuery.addEventListener('input', destinationFilter);
  destinationSelect.addEventListener('change', destinationFilter);
  byId('clearDestinations').addEventListener('click', () => { destinationQuery.value = ''; destinationSelect.value = ''; destinationFilter(); destinationQuery.focus(); });
  byId('showClasses').addEventListener('change', event => {
    document.querySelectorAll('.class-count').forEach(node => { node.hidden = !event.target.checked; });
  });
  function download(content, name, type) {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const link = document.createElement('a'); link.href = url; link.download = name;
    document.body.appendChild(link); link.click(); link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  byId('exportJSON').addEventListener('click', () => {
    const result = { ...model.data, schools: current.map(item => model.data.schools[item.key]) };
    download(JSON.stringify(result, null, 2) + '\n', 'schools-filtered.json', 'application/json;charset=utf-8');
    byId('exportStatus').textContent = `已匯出 ${current.length} 校 JSON；原始 summary 為全資料背景，未按篩選重算。`;
  });
  byId('exportCSV').addEventListener('click', () => {
    download(makeCSV(current.map(item => model.data.schools[item.key])), 'enrolment-filtered.csv', 'text/csv;charset=utf-8');
    byId('exportStatus').textContent = `已匯出 ${current.length} 校人數 CSV；活動、去向等完整欄位請用 JSON。`;
  });
  byId('expandAll').addEventListener('click', () => schoolCards.forEach(card => { if (!card.hidden) card.open = true; }));
  byId('collapseAll').addEventListener('click', () => schoolCards.forEach(card => { card.open = false; }));
  function deepLink() {
    let id;
    try { id = decodeURIComponent(window.location.hash.slice(1)); } catch (_) { return; }
    if (!id) return;
    const target = byId(id);
    if (!target) return;
    const card = target.closest('details.school-card');
    const owner = target.closest('[data-school-key]');
    if (owner && owner.hidden) {
      q.value = ''; category.value = ''; p6Only.checked = false;
      destinationQuery.value = ''; destinationSelect.value = ''; render();
    }
    openAncestors(target);
    // Section anchors remain useful when their comparison table is folded.
    if (['roster', 'classes', 'social'].includes(id)) {
      const section = target.closest('section');
      const fold = section && section.querySelector('details.fold-panel');
      if (fold) fold.open = true;
    }
    if (card) card.open = true;
    window.requestAnimationFrame(() => {
      target.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
      const focusTarget = target.tagName === 'DETAILS' ? target.querySelector('summary') : target;
      if (!focusTarget.hasAttribute('tabindex') && focusTarget.tagName !== 'SUMMARY') focusTarget.setAttribute('tabindex', '-1');
      focusTarget.focus({ preventScroll: true });
    });
  }
  const printDetails = new Map();
  window.addEventListener('beforeprint', () => document.querySelectorAll('details:not(.raw-record)').forEach(detail => { printDetails.set(detail, detail.open); detail.open = true; }));
  window.addEventListener('afterprint', () => { printDetails.forEach((open, detail) => { detail.open = open; }); printDetails.clear(); });
  document.documentElement.classList.add('js-ready');
  window.addEventListener('hashchange', deepLink);
  // Clicking the current hash does not fire hashchange, but should reopen it.
  document.addEventListener('click', event => {
    const link = event.target.closest && event.target.closest('a[href^="#"]');
    if (link && link.getAttribute('href') === window.location.hash) deepLink();
  });
  render(); deepLink();
})();
