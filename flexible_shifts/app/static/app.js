'use strict';

const baseUrl = (() => {
  const url = new URL(window.location.href);
  url.search = '';
  url.hash = '';
  if (!url.pathname.endsWith('/')) url.pathname += '/';
  return url;
})();

const state = {
  users: [],
  selectedUserIds: [],
  currentDate: new Date(),
  view: 'week',
  calendarData: { shifts: [], vacations: [] },
  range: null,
  reportYear: new Date().getFullYear(),
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function appUrl(path) {
  return new URL(path.replace(/^\//, ''), baseUrl).toString();
}

async function api(path, options = {}) {
  const response = await fetch(appUrl(`api/${path.replace(/^\//, '')}`), options);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data);
    } catch (_) {}
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function isoDate(dateValue) {
  const d = new Date(dateValue);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function parseIso(value) {
  const [year, month, day] = value.split('-').map(Number);
  return new Date(year, month - 1, day);
}

function addDays(dateValue, days) {
  const result = new Date(dateValue);
  result.setDate(result.getDate() + days);
  return result;
}

function startOfWeek(dateValue) {
  const d = new Date(dateValue);
  const day = d.getDay() || 7;
  d.setDate(d.getDate() - day + 1);
  d.setHours(0, 0, 0, 0);
  return d;
}

function endOfWeek(dateValue) { return addDays(startOfWeek(dateValue), 6); }
function startOfMonth(dateValue) { return new Date(dateValue.getFullYear(), dateValue.getMonth(), 1); }
function endOfMonth(dateValue) { return new Date(dateValue.getFullYear(), dateValue.getMonth() + 1, 0); }
function sameDay(a, b) { return isoDate(a) === isoDate(b); }

function formatHours(value) {
  const number = Number(value || 0);
  return number.toLocaleString('it-IT', { maximumFractionDigits: 2, minimumFractionDigits: 0 });
}

function formatDate(dateValue, options) {
  return new Intl.DateTimeFormat('it-IT', options).format(new Date(dateValue));
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function showToast(message, error = false) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.toggle('error', error);
  toast.classList.remove('hidden');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.add('hidden'), 3500);
}

function selectedUsers() {
  return state.users.filter((user) => state.selectedUserIds.includes(user.id));
}

function getUser(userId) {
  return state.users.find((user) => user.id === Number(userId));
}

async function loadUsers(preserveSelection = true) {
  const oldSelection = preserveSelection ? [...state.selectedUserIds] : [];
  state.users = await api('users');
  const activeIds = state.users.filter((user) => user.active).map((user) => user.id);
  state.selectedUserIds = oldSelection.filter((id) => activeIds.includes(id));
  if (!state.selectedUserIds.length && activeIds.length) state.selectedUserIds = [activeIds[0]];
  renderUserPicker();
  populateUserSelects();
  renderUsersManagement();
}

function renderUserPicker() {
  const list = $('#userPickerList');
  list.innerHTML = state.users.filter((user) => user.active).map((user) => `
    <label>
      <input type="checkbox" value="${user.id}" ${state.selectedUserIds.includes(user.id) ? 'checked' : ''}>
      <span>${escapeHtml(user.name)}</span>
    </label>
  `).join('') || '<div class="muted">Nessun utente attivo</div>';

  list.querySelectorAll('input').forEach((input) => {
    input.addEventListener('change', async () => {
      const id = Number(input.value);
      if (input.checked) state.selectedUserIds = [...new Set([...state.selectedUserIds, id])];
      else state.selectedUserIds = state.selectedUserIds.filter((item) => item !== id);
      updateUserPickerLabel();
      await refreshCalendar();
    });
  });
  updateUserPickerLabel();
}

function updateUserPickerLabel() {
  const users = selectedUsers();
  let label = 'Seleziona utenti';
  if (users.length === 1) label = users[0].name;
  if (users.length > 1) label = `${users.length} utenti selezionati`;
  $('#userPickerLabel').textContent = label;
}

function populateUserSelects() {
  const options = state.users.filter((user) => user.active).map((user) =>
    `<option value="${user.id}">${escapeHtml(user.name)}</option>`
  ).join('');
  ['#shiftUser', '#vacationUser', '#reportUser', '#importUser', '#exportUser'].forEach((selector) => {
    const select = $(selector);
    const previous = select.value;
    select.innerHTML = options;
    if ([...select.options].some((option) => option.value === previous)) select.value = previous;
  });
}

function calculateRange() {
  if (state.view === 'day') return { start: new Date(state.currentDate), end: new Date(state.currentDate) };
  if (state.view === 'month') {
    const first = startOfWeek(startOfMonth(state.currentDate));
    const last = endOfWeek(endOfMonth(state.currentDate));
    return { start: first, end: last };
  }
  return { start: startOfWeek(state.currentDate), end: endOfWeek(state.currentDate) };
}

function updatePeriodTitle() {
  if (state.view === 'day') {
    $('#periodTitle').textContent = formatDate(state.currentDate, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  } else if (state.view === 'month') {
    $('#periodTitle').textContent = formatDate(state.currentDate, { month: 'long', year: 'numeric' });
  } else {
    const start = startOfWeek(state.currentDate);
    const end = endOfWeek(state.currentDate);
    const startText = formatDate(start, { day: 'numeric', month: start.getMonth() === end.getMonth() ? undefined : 'short' });
    const endText = formatDate(end, { day: 'numeric', month: 'short', year: 'numeric' });
    $('#periodTitle').textContent = `${startText} - ${endText}`;
  }
}

async function refreshCalendar() {
  updatePeriodTitle();
  state.range = calculateRange();
  if (!state.selectedUserIds.length) {
    state.calendarData = { shifts: [], vacations: [] };
    renderCalendar();
    renderSummary();
    return;
  }
  $('#calendar').innerHTML = '<div class="empty-state"><div>Caricamento…</div></div>';
  try {
    const query = new URLSearchParams({
      user_ids: state.selectedUserIds.join(','),
      start: isoDate(state.range.start),
      end: isoDate(state.range.end),
    });
    state.calendarData = await api(`calendar?${query}`);
    renderCalendar();
    renderSummary();
  } catch (error) {
    $('#calendar').innerHTML = `<div class="empty-state"><div>Errore: ${escapeHtml(error.message)}</div></div>`;
    showToast(error.message, true);
  }
}

function shiftsForDate(dateString) {
  return state.calendarData.shifts.filter((shift) => shift.date === dateString);
}

function vacationsForDate(dateString) {
  return state.calendarData.vacations.filter((vacation) => vacation.start_date <= dateString && vacation.end_date >= dateString);
}

function shiftTimes(shift) {
  return shift.work_segments.map((segment) => `${segment.start}-${segment.end}`).join(' · ');
}

function pauseText(shift) {
  if (!shift.break_segments.length) return '';
  return shift.break_segments.map((segment) => `${segment.start}-${segment.end}`).join(' · ');
}

function shiftCard(shift, compact = false) {
  const user = getUser(shift.user_id);
  return `
    <article class="${compact ? 'month-chip' : 'shift-card'}" data-shift-id="${shift.id}">
      <div class="shift-user">${escapeHtml(user?.name || 'Utente')}</div>
      <div class="shift-times">${escapeHtml(shiftTimes(shift))}</div>
      ${compact ? '' : `<div class="shift-total">${formatHours(shift.total_hours)} h</div>`}
      ${!compact && shift.break_segments.length ? `<div class="pause-line">Pausa ${escapeHtml(pauseText(shift))}</div>` : ''}
    </article>`;
}

function vacationCard(vacation, compact = false) {
  const user = getUser(vacation.user_id);
  return `
    <article class="${compact ? 'month-chip vacation' : 'shift-card vacation-card'}" data-vacation-id="${vacation.id}">
      <div class="shift-user">${escapeHtml(user?.name || 'Utente')} · Ferie</div>
      ${compact ? '' : `<div class="shift-total">Settimana ${formatHours(vacation.credited_hours)} h</div>`}
    </article>`;
}

function bindCalendarActions() {
  $$('[data-shift-id]').forEach((element) => {
    element.addEventListener('click', () => {
      const shift = state.calendarData.shifts.find((item) => item.id === Number(element.dataset.shiftId));
      if (shift) openShiftDialog(shift.date, shift.user_id, shift);
    });
  });
  $$('[data-vacation-id]').forEach((element) => {
    element.addEventListener('click', async () => {
      const vacation = state.calendarData.vacations.find((item) => item.id === Number(element.dataset.vacationId));
      if (!vacation) return;
      if (!confirm(`Eliminare la settimana di ferie dal ${vacation.start_date} al ${vacation.end_date}?`)) return;
      try {
        await api(`vacations/${vacation.id}`, { method: 'DELETE' });
        showToast('Settimana di ferie eliminata');
        await refreshCalendar();
      } catch (error) { showToast(error.message, true); }
    });
  });
  $$('[data-add-date]').forEach((button) => {
    button.addEventListener('click', () => openShiftDialog(button.dataset.addDate));
  });
}

function renderCalendar() {
  if (!state.selectedUserIds.length) {
    $('#calendar').innerHTML = '<div class="empty-state"><div><strong>Nessun utente selezionato</strong><br>Seleziona almeno un utente oppure creane uno dal menu ⚙.</div></div>';
    return;
  }
  if (state.view === 'day') renderDayView();
  else if (state.view === 'month') renderMonthView();
  else renderWeekView();
  bindCalendarActions();
}

function renderWeekView() {
  const start = startOfWeek(state.currentDate);
  const days = Array.from({ length: 7 }, (_, index) => addDays(start, index));
  $('#calendar').innerHTML = `<div class="week-grid">${days.map((day) => {
    const dateString = isoDate(day);
    const shifts = shiftsForDate(dateString);
    const vacations = vacationsForDate(dateString);
    return `
      <section class="day-column ${sameDay(day, new Date()) ? 'today' : ''}">
        <header class="day-heading">
          <strong>${formatDate(day, { weekday: 'long' })}</strong>
          <span>${formatDate(day, { day: 'numeric', month: 'long' })}</span>
        </header>
        <div class="day-body">
          ${vacations.map((item) => vacationCard(item)).join('')}
          ${shifts.map((item) => shiftCard(item)).join('')}
          <button class="add-day-button" type="button" data-add-date="${dateString}">+ Aggiungi</button>
        </div>
      </section>`;
  }).join('')}</div>`;
}

function renderMonthView() {
  const first = startOfWeek(startOfMonth(state.currentDate));
  const days = Array.from({ length: 42 }, (_, index) => addDays(first, index));
  const weekdays = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'];
  $('#calendar').innerHTML = `
    <div class="month-grid">
      ${weekdays.map((day) => `<div class="month-weekday">${day}</div>`).join('')}
      ${days.map((day) => {
        const dateString = isoDate(day);
        const outside = day.getMonth() !== state.currentDate.getMonth();
        return `
          <section class="month-day ${outside ? 'outside' : ''} ${sameDay(day, new Date()) ? 'today' : ''}">
            <div class="month-day-number">
              <span>${day.getDate()}</span>
              <button class="text-button" type="button" data-add-date="${dateString}" title="Aggiungi turno">+</button>
            </div>
            <div class="month-day-items">
              ${vacationsForDate(dateString).map((item) => vacationCard(item, true)).join('')}
              ${shiftsForDate(dateString).map((item) => shiftCard(item, true)).join('')}
            </div>
          </section>`;
      }).join('')}
    </div>`;
}

function renderDayView() {
  const dateString = isoDate(state.currentDate);
  const shifts = shiftsForDate(dateString);
  const vacations = vacationsForDate(dateString);
  $('#calendar').innerHTML = `<div class="day-view">${selectedUsers().map((user) => {
    const shift = shifts.find((item) => item.user_id === user.id);
    const vacation = vacations.find((item) => item.user_id === user.id);
    let content = '<p class="muted">Nessun turno inserito.</p>';
    if (vacation) content = `<div class="large-time">Ferie</div><p>${formatHours(vacation.credited_hours)} ore accreditate nella settimana.</p>`;
    if (shift) content = `<div class="large-time">${escapeHtml(shiftTimes(shift))}</div><p>${formatHours(shift.total_hours)} h${shift.break_segments.length ? ` · pausa ${escapeHtml(pauseText(shift))}` : ''}</p>`;
    return `
      <section class="day-view-card">
        <h3>${escapeHtml(user.name)}</h3>
        ${content}
        <div class="day-actions">
          <button class="primary-button" type="button" ${shift ? `data-shift-id="${shift.id}"` : `data-add-date="${dateString}"`}>${shift ? 'Modifica turno' : '+ Inserisci turno'}</button>
        </div>
      </section>`;
  }).join('')}</div>`;
}

function renderSummary() {
  const users = selectedUsers();
  if (!users.length) { $('#summaryStrip').innerHTML = ''; return; }
  const shifts = state.calendarData.shifts;
  const periodLabel = state.view === 'day' ? 'nel giorno' : state.view === 'month' ? 'nel periodo visualizzato' : 'nella settimana';
  $('#summaryStrip').innerHTML = users.map((user) => {
    const userShifts = shifts.filter((shift) => shift.user_id === user.id);
    const hours = userShifts.reduce((sum, shift) => sum + Number(shift.total_hours), 0);
    const vacationStarts = new Set(state.calendarData.vacations.filter((vacation) => vacation.user_id === user.id).map((vacation) => vacation.start_date));
    const vacationHours = state.calendarData.vacations.filter((vacation) => vacation.user_id === user.id && vacation.start_date >= isoDate(state.range.start) && vacation.start_date <= isoDate(state.range.end)).reduce((sum, vacation) => sum + Number(vacation.credited_hours), 0);
    return `
      <div class="summary-card">
        <strong>${formatHours(hours + vacationHours)} h</strong>
        <span>${escapeHtml(user.name)} ${periodLabel}${vacationStarts.size ? ` · ${vacationStarts.size} sett. ferie` : ''}</span>
      </div>`;
  }).join('');
}

function addSegmentRow(start = '', end = '') {
  const row = document.createElement('div');
  row.className = 'segment-row';
  row.innerHTML = `
    <label>Start<input class="segment-start" type="time" required value="${escapeHtml(start)}"></label>
    <label>Stop<input class="segment-end" type="time" required value="${escapeHtml(end)}"></label>
    <button class="remove-segment" type="button" title="Rimuovi">×</button>`;
  row.querySelector('.remove-segment').addEventListener('click', () => {
    if ($('#workSegments').children.length <= 1) return showToast('È necessario almeno un intervallo', true);
    row.remove();
    calculateShiftTotal();
  });
  row.querySelectorAll('input').forEach((input) => input.addEventListener('input', calculateShiftTotal));
  $('#workSegments').append(row);
}

function minutesBetween(start, end) {
  if (!start || !end) return 0;
  const [sh, sm] = start.split(':').map(Number);
  const [eh, em] = end.split(':').map(Number);
  let a = sh * 60 + sm;
  let b = eh * 60 + em;
  if (b <= a) b += 1440;
  return b - a;
}

function calculateShiftTotal() {
  let total = $$('.segment-row').reduce((sum, row) => sum + minutesBetween(row.querySelector('.segment-start').value, row.querySelector('.segment-end').value), 0);
  if ($('#pauseEnabled').checked) total -= minutesBetween($('#pauseStart').value, $('#pauseEnd').value);
  $('#shiftCalculatedTotal').textContent = `Totale: ${formatHours(Math.max(0, total) / 60)} h`;
}

function openShiftDialog(dateString = isoDate(state.currentDate), userId = null, shift = null) {
  if (!state.users.some((user) => user.active)) return showToast('Crea prima almeno un utente', true);
  $('#shiftId').value = shift?.id || '';
  $('#shiftDialogTitle').textContent = shift ? 'Modifica turno' : 'Nuovo turno';
  $('#shiftUser').value = String(userId || state.selectedUserIds[0] || state.users.find((user) => user.active)?.id);
  $('#shiftDate').value = dateString;
  $('#shiftNote').value = shift?.note || '';
  $('#workSegments').innerHTML = '';
  (shift?.work_segments || [{ start: '', end: '' }]).forEach((segment) => addSegmentRow(segment.start, segment.end));
  const pause = shift?.break_segments?.[0];
  $('#pauseEnabled').checked = Boolean(pause);
  $('#pauseFields').classList.toggle('hidden', !pause);
  $('#pauseStart').value = pause?.start || '';
  $('#pauseEnd').value = pause?.end || '';
  $('#deleteShiftButton').classList.toggle('hidden', !shift);
  calculateShiftTotal();
  $('#shiftDialog').showModal();
}

function openVacationDialog() {
  if (!state.users.some((user) => user.active)) return showToast('Crea prima almeno un utente', true);
  $('#vacationUser').value = String(state.selectedUserIds[0] || state.users.find((user) => user.active)?.id);
  $('#vacationDate').value = isoDate(state.currentDate);
  $('#vacationHours').value = '';
  $('#vacationNote').value = '';
  updateVacationHint();
  $('#vacationDialog').showModal();
}

function updateVacationHint() {
  const user = getUser($('#vacationUser').value);
  if (!user) return;
  const days = user.employment_type === 'full_time' ? 'lunedì-venerdì' : 'lunedì-domenica';
  const weeklyHours = user.target_basis === 'weekly' ? user.target_hours : user.target_hours / 4;
  $('#vacationRuleHint').textContent = `${user.name}: ferie ${days}; accredito automatico ${formatHours(weeklyHours)} ore.`;
}

function resetUserForm() {
  $('#userId').value = '';
  $('#userFormTitle').textContent = 'Nuovo utente';
  $('#userName').value = '';
  $('#employmentType').value = 'part_time';
  $('#targetBasis').value = 'weekly';
  $('#targetHours').value = '30.5';
  $('#monthlyFromWeeklyMode').value = 'x4';
  $('#overtimeMin').value = '0';
  $('#overtimeMax').value = '12';
  $('#userActive').checked = true;
  $('#deleteUserButton').classList.add('hidden');
  updateWeeklyModeVisibility();
  $$('.user-list-item').forEach((item) => item.classList.remove('active'));
}

function fillUserForm(user) {
  $('#userId').value = user.id;
  $('#userFormTitle').textContent = `Modifica ${user.name}`;
  $('#userName').value = user.name;
  $('#employmentType').value = user.employment_type;
  $('#targetBasis').value = user.target_basis;
  $('#targetHours').value = user.target_hours;
  $('#monthlyFromWeeklyMode').value = user.monthly_from_weekly_mode;
  $('#overtimeMin').value = user.overtime_min;
  $('#overtimeMax').value = user.overtime_max;
  $('#userActive').checked = user.active;
  $('#deleteUserButton').classList.remove('hidden');
  updateWeeklyModeVisibility();
  $$('.user-list-item').forEach((item) => item.classList.toggle('active', Number(item.dataset.userId) === user.id));
}

function renderUsersManagement() {
  const list = $('#usersList');
  if (!list) return;
  list.innerHTML = state.users.map((user) => `
    <div class="user-list-item ${user.active ? '' : 'inactive'}" data-user-id="${user.id}">
      <strong>${escapeHtml(user.name)}</strong>
      <small>${user.employment_type === 'full_time' ? 'Full-time' : 'Part-time'} · ${formatHours(user.target_hours)} h ${user.target_basis === 'weekly' ? 'settimanali' : 'mensili'}</small>
      <small>Straordinari accettabili: ${formatHours(user.overtime_min)}-${formatHours(user.overtime_max)} h</small>
    </div>`).join('') || '<div class="muted">Nessun utente creato.</div>';
  list.querySelectorAll('[data-user-id]').forEach((item) => item.addEventListener('click', () => {
    const user = getUser(item.dataset.userId);
    if (user) fillUserForm(user);
  }));
}

function updateWeeklyModeVisibility() {
  $('#weeklyModeLabel').classList.toggle('hidden', $('#targetBasis').value !== 'weekly');
}

async function openReportDialog() {
  const activeUsers = state.users.filter((user) => user.active);
  if (!activeUsers.length) return showToast('Crea prima almeno un utente', true);
  $('#reportUser').value = String(state.selectedUserIds[0] || activeUsers[0].id);
  state.reportYear = state.currentDate.getFullYear();
  $('#reportDialog').showModal();
  await loadReport();
}

async function loadReport() {
  const userId = Number($('#reportUser').value);
  $('#reportYearLabel').textContent = state.reportYear;
  $('#reportContent').innerHTML = '<div class="empty-state"><div>Calcolo report…</div></div>';
  try {
    const report = await api(`reports/annual?user_id=${userId}&year=${state.reportYear}`);
    renderReport(report);
  } catch (error) {
    $('#reportContent').innerHTML = `<div class="empty-state"><div>${escapeHtml(error.message)}</div></div>`;
  }
}

function renderReport(report) {
  const activeMonths = report.summary.active_months;
  const tracksWeekends = report.user.employment_type === 'part_time';
  $('#reportContent').innerHTML = `
    <div class="report-layout">
      <div class="report-table-wrap">
        <table class="report-table">
          <thead><tr>
            <th>Mese</th><th>Ore totali</th><th>Straordinari</th><th>Standard</th><th>Saldo</th>
            <th>GWE lavorati</th><th>Su</th><th>Ferie</th><th>%</th>
          </tr></thead>
          <tbody>${report.months.map((month) => {
            const future = month.month > activeMonths;
            return `
            <tr class="${future ? 'future' : ''}">
              <td>${month.month_name}</td>
              <td>${future ? '' : formatHours(month.total_hours)}</td>
              <td class="${future ? '' : `overtime-${month.overtime_status}`}">${future ? '' : formatHours(month.overtime_hours)}</td>
              <td>${future ? '' : formatHours(month.standard_hours)}</td>
              <td>${future ? '' : formatHours(month.balance_hours)}</td>
              <td>${future ? '' : (tracksWeekends ? month.weekend_days_worked : '-')}</td>
              <td>${future ? '' : (tracksWeekends ? month.weekend_days_available : '-')}</td>
              <td>${future ? '' : month.vacation_weeks}</td>
              <td>${future ? '' : (tracksWeekends ? `${formatHours(month.weekend_percentage)}%` : '-')}</td>
            </tr>`;
          }).join('')}</tbody>
        </table>
      </div>
      <aside class="report-summary">
        ${summaryCard('Tot. ore contabilizzate', `${formatHours(report.summary.total_hours)} h`)}
        ${summaryCard('Ore realmente lavorate', `${formatHours(report.summary.worked_hours)} h`)}
        ${summaryCard('Ore ferie accreditate', `${formatHours(report.summary.vacation_hours)} h`)}
        ${summaryCard('Tot. straordinari', `${formatHours(report.summary.overtime_hours)} h`)}
        ${summaryCard('Tot. standard', `${formatHours(report.summary.standard_hours)} h`)}
        ${summaryCard('Saldo', `${formatHours(report.summary.balance_hours)} h`)}
        ${tracksWeekends ? summaryCard('GWE lavorati', report.summary.weekend_days_worked) : ''}
        ${tracksWeekends ? summaryCard('Su', report.summary.weekend_days_available) : ''}
        ${tracksWeekends ? summaryCard('Percentuale weekend', `${formatHours(report.summary.weekend_percentage)}%`) : ''}
        ${summaryCard('Settimane ferie', report.summary.vacation_weeks)}
      </aside>
    </div>`;
}

function summaryCard(label, value) {
  return `<div class="report-summary-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function openImportDialog() {
  if (!state.users.some((user) => user.active)) return showToast('Crea prima almeno un utente', true);
  $('#exportYear').value = state.currentDate.getFullYear();
  $('#importResult').classList.add('hidden');
  $('#importDialog').showModal();
}

function download(path) {
  const link = document.createElement('a');
  link.href = appUrl(`api/${path.replace(/^\//, '')}`);
  link.click();
}

function closePopovers() {
  $('#userPickerPanel').classList.add('hidden');
  $('#settingsMenu').classList.add('hidden');
  $('#userPickerButton').setAttribute('aria-expanded', 'false');
}

function wireEvents() {
  $('#userPickerButton').addEventListener('click', (event) => {
    event.stopPropagation();
    const panel = $('#userPickerPanel');
    const willOpen = panel.classList.contains('hidden');
    closePopovers();
    panel.classList.toggle('hidden', !willOpen);
    $('#userPickerButton').setAttribute('aria-expanded', String(willOpen));
  });
  $('#settingsButton').addEventListener('click', (event) => {
    event.stopPropagation();
    const menu = $('#settingsMenu');
    const willOpen = menu.classList.contains('hidden');
    closePopovers();
    menu.classList.toggle('hidden', !willOpen);
  });
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.user-picker-wrap') && !event.target.closest('.settings-wrap')) closePopovers();
  });

  $('#selectAllUsers').addEventListener('click', async () => {
    state.selectedUserIds = state.users.filter((user) => user.active).map((user) => user.id);
    renderUserPicker();
    await refreshCalendar();
  });
  $('#clearUsers').addEventListener('click', async () => {
    state.selectedUserIds = [];
    renderUserPicker();
    await refreshCalendar();
  });

  $('#prevPeriod').addEventListener('click', async () => {
    if (state.view === 'day') state.currentDate = addDays(state.currentDate, -1);
    else if (state.view === 'week') state.currentDate = addDays(state.currentDate, -7);
    else state.currentDate = new Date(state.currentDate.getFullYear(), state.currentDate.getMonth() - 1, 1);
    await refreshCalendar();
  });
  $('#nextPeriod').addEventListener('click', async () => {
    if (state.view === 'day') state.currentDate = addDays(state.currentDate, 1);
    else if (state.view === 'week') state.currentDate = addDays(state.currentDate, 7);
    else state.currentDate = new Date(state.currentDate.getFullYear(), state.currentDate.getMonth() + 1, 1);
    await refreshCalendar();
  });
  $('#todayButton').addEventListener('click', async () => { state.currentDate = new Date(); await refreshCalendar(); });
  $$('.view-switch button').forEach((button) => button.addEventListener('click', async () => {
    state.view = button.dataset.view;
    $$('.view-switch button').forEach((item) => item.classList.toggle('active', item === button));
    await refreshCalendar();
  }));

  $('#addShiftButton').addEventListener('click', () => openShiftDialog());
  $('#addVacationButton').addEventListener('click', openVacationDialog);
  $('#addWorkSegment').addEventListener('click', () => {
    if ($('#workSegments').children.length >= 2) return showToast('La prima versione supporta al massimo due intervalli di lavoro per giorno', true);
    addSegmentRow();
  });
  $('#pauseEnabled').addEventListener('change', () => {
    $('#pauseFields').classList.toggle('hidden', !$('#pauseEnabled').checked);
    if (!$('#pauseEnabled').checked) { $('#pauseStart').value = ''; $('#pauseEnd').value = ''; }
    calculateShiftTotal();
  });
  $('#pauseStart').addEventListener('input', calculateShiftTotal);
  $('#pauseEnd').addEventListener('input', calculateShiftTotal);

  $('#shiftForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const workSegments = $$('.segment-row').map((row) => ({
      start: row.querySelector('.segment-start').value,
      end: row.querySelector('.segment-end').value,
    }));
    const breakSegments = $('#pauseEnabled').checked ? [{ start: $('#pauseStart').value, end: $('#pauseEnd').value }] : [];
    if (breakSegments.length && (!breakSegments[0].start || !breakSegments[0].end)) return showToast('Completa entrambi gli orari della pausa', true);
    const payload = {
      user_id: Number($('#shiftUser').value),
      date: $('#shiftDate').value,
      work_segments: workSegments,
      break_segments: breakSegments,
      note: $('#shiftNote').value,
    };
    try {
      const id = $('#shiftId').value;
      await api(id ? `shifts/${id}` : 'shifts', { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      $('#shiftDialog').close();
      showToast(id ? 'Turno aggiornato' : 'Turno salvato');
      await refreshCalendar();
      if ($('#reportDialog').open) await loadReport();
    } catch (error) { showToast(error.message, true); }
  });

  $('#deleteShiftButton').addEventListener('click', async () => {
    const id = $('#shiftId').value;
    if (!id || !confirm('Eliminare questo turno?')) return;
    try {
      await api(`shifts/${id}`, { method: 'DELETE' });
      $('#shiftDialog').close();
      showToast('Turno eliminato');
      await refreshCalendar();
    } catch (error) { showToast(error.message, true); }
  });

  $('#vacationUser').addEventListener('change', updateVacationHint);
  $('#vacationForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {
      user_id: Number($('#vacationUser').value),
      date_in_week: $('#vacationDate').value,
      note: $('#vacationNote').value,
      credited_hours: $('#vacationHours').value ? Number($('#vacationHours').value) : null,
    };
    try {
      await api('vacations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      $('#vacationDialog').close();
      showToast('Settimana di ferie salvata');
      await refreshCalendar();
    } catch (error) { showToast(error.message, true); }
  });

  $$('[data-close-dialog]').forEach((button) => button.addEventListener('click', () => {
    const dialog = document.getElementById(button.dataset.closeDialog);
    if (dialog?.open) dialog.close();
  }));

  $('#newUserButton').addEventListener('click', resetUserForm);
  $('#targetBasis').addEventListener('change', updateWeeklyModeVisibility);
  $('#userForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const id = $('#userId').value;
    const payload = {
      name: $('#userName').value.trim(),
      employment_type: $('#employmentType').value,
      target_basis: $('#targetBasis').value,
      target_hours: Number($('#targetHours').value),
      monthly_from_weekly_mode: $('#monthlyFromWeeklyMode').value,
      overtime_min: Number($('#overtimeMin').value),
      overtime_max: Number($('#overtimeMax').value),
      active: $('#userActive').checked,
    };
    try {
      await api(id ? `users/${id}` : 'users', { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      showToast(id ? 'Utente aggiornato' : 'Utente creato');
      await loadUsers(true);
      resetUserForm();
      await refreshCalendar();
    } catch (error) { showToast(error.message, true); }
  });
  $('#deleteUserButton').addEventListener('click', async () => {
    const id = $('#userId').value;
    if (!id || !confirm('Eliminare l’utente e tutti i suoi turni, ferie e report?')) return;
    try {
      await api(`users/${id}`, { method: 'DELETE' });
      showToast('Utente eliminato');
      state.selectedUserIds = state.selectedUserIds.filter((item) => item !== Number(id));
      await loadUsers(true);
      resetUserForm();
      await refreshCalendar();
    } catch (error) { showToast(error.message, true); }
  });

  $('#settingsMenu').addEventListener('click', async (event) => {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    closePopovers();
    const action = button.dataset.action;
    if (action === 'users') { resetUserForm(); $('#usersDialog').showModal(); }
    if (action === 'reports') await openReportDialog();
    if (action === 'import') openImportDialog();
    if (action === 'backup') download('backup');
    if (action === 'about') $('#aboutDialog').showModal();
    if (action === 'sync') {
      try { const result = await api('sync', { method: 'POST' }); showToast(`Sincronizzati ${result.synced} utenti${result.errors?.length ? `; errori: ${result.errors.join(', ')}` : ''}`, Boolean(result.errors?.length)); }
      catch (error) { showToast(error.message, true); }
    }
  });

  $('#reportUser').addEventListener('change', loadReport);
  $('#reportPrevYear').addEventListener('click', async () => { state.reportYear -= 1; await loadReport(); });
  $('#reportNextYear').addEventListener('click', async () => { state.reportYear += 1; await loadReport(); });
  $('#printReport').addEventListener('click', () => window.print());

  $('#importForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const file = $('#importFile').files[0];
    if (!file) return;
    const form = new FormData();
    form.append('user_id', $('#importUser').value);
    form.append('file', file);
    try {
      const result = await api('import/csv', { method: 'POST', body: form });
      $('#importResult').textContent = JSON.stringify(result, null, 2);
      $('#importResult').classList.remove('hidden');
      showToast(`Importati ${result.imported}, aggiornati ${result.updated}, ferie ${result.vacations}`);
      await refreshCalendar();
    } catch (error) { showToast(error.message, true); }
  });
  $('#downloadTemplate').addEventListener('click', () => download('import/template.csv'));
  $('#exportCsvButton').addEventListener('click', () => download(`export/csv?user_id=${$('#exportUser').value}&year=${$('#exportYear').value}`));
  $('#backupButton').addEventListener('click', () => download('backup'));
}

async function init() {
  wireEvents();
  resetUserForm();
  try {
    await loadUsers(false);
    await refreshCalendar();
  } catch (error) {
    showToast(`Avvio non riuscito: ${error.message}`, true);
    $('#calendar').innerHTML = `<div class="empty-state"><div>${escapeHtml(error.message)}</div></div>`;
  }
  setInterval(async () => {
    if (!document.hidden) {
      await refreshCalendar();
      if ($('#reportDialog').open) await loadReport();
    }
  }, 30000);
}

init();
