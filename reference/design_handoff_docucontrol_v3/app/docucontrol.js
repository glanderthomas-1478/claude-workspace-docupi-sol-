/* ============================================================
   DocuControl 2026 — Dashboard v3 interactivity
   ============================================================ */
(function () {
  'use strict';

  /* ---------- Main tab switching ---------- */
  document.querySelectorAll('.navstrip .tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      var view = tab.getAttribute('data-view');
      document.querySelectorAll('.navstrip .tab').forEach(function (t) { t.classList.toggle('active', t === tab); });
      document.querySelectorAll('.view').forEach(function (v) { v.classList.toggle('active', v.id === 'view-' + view); });
      window.scrollTo({ top: 0 });
    });
  });

  /* ---------- Settings sub-tabs ---------- */
  document.querySelectorAll('.subnav .sub').forEach(function (sub) {
    sub.addEventListener('click', function () {
      var key = sub.getAttribute('data-sub');
      document.querySelectorAll('.subnav .sub').forEach(function (s) { s.classList.toggle('active', s === sub); });
      document.querySelectorAll('.subview').forEach(function (v) { v.classList.toggle('active', v.id === 'sub-' + key); });
      if (key === 'monitor') startMonitor(); else stopMonitor();
    });
  });

  /* ---------- Filter reset ---------- */
  window.resetFilters = function (btn) {
    var bar = btn.closest('.filterbar');
    bar.querySelectorAll('select').forEach(function (s) { s.selectedIndex = 0; });
    bar.querySelectorAll('input').forEach(function (i) { if (i.type !== 'date') i.value = ''; });
  };

  /* ============================================================
     FILE MANAGER (TotalCommander style)
     ============================================================ */
  var fm = {
    internal: [
      { name: 'CH021667_Instrumente_134C_2026-04-13.pdf', date: '13.04.2026', size: 48.2 },
      { name: 'CH021666_Instrumente_134C_2026-04-13.pdf', date: '13.04.2026', size: 47.9 },
      { name: 'CH021665_BowieDick_2026-04-13.pdf', date: '13.04.2026', size: 31.4 },
      { name: 'CH021664_Vakuumtest_2026-04-13.pdf', date: '13.04.2026', size: 22.8 },
      { name: 'CH021663_Instrumente_134C_2026-04-12.pdf', date: '12.04.2026', size: 49.1 },
      { name: 'CH021662_Textilien_121C_2026-04-12.pdf', date: '12.04.2026', size: 52.7 },
      { name: 'CH021661_Instrumente_134C_2026-04-12.pdf', date: '12.04.2026', size: 48.5 },
      { name: 'CH021660_BowieDick_2026-04-12.pdf', date: '12.04.2026', size: 31.2 },
      { name: 'CH021659_Instrumente_134C_2026-04-11.pdf', date: '11.04.2026', size: 47.4 },
      { name: 'CH021658_Vakuumtest_2026-04-11.pdf', date: '11.04.2026', size: 22.6 }
    ],
    usb: [
      { name: 'CH021666_Instrumente_134C_2026-04-13.pdf', date: '13.04.2026', size: 47.9 },
      { name: 'CH021665_BowieDick_2026-04-13.pdf', date: '13.04.2026', size: 31.4 },
      { name: 'CH021663_Instrumente_134C_2026-04-12.pdf', date: '12.04.2026', size: 49.1 }
    ],
    usbConnected: true,
    focus: 'internal',
    sel: { internal: new Set(), usb: new Set() }
  };
  var CAP = { internal: 32 * 1024, usb: 16 * 1024 }; // MB

  function fmt(mb) { return mb >= 1024 ? (mb / 1024).toFixed(1) + ' GB' : mb.toFixed(1) + ' MB'; }
  function paneUsed(p) { return fm[p].reduce(function (s, f) { return s + f.size; }, 0); }

  function renderPane(p) {
    var pane = document.getElementById('pane-' + p);
    if (!pane) return;
    var tbody = pane.querySelector('tbody');
    var sel = fm.sel[p];
    var files = fm[p];

    pane.classList.toggle('focused', fm.focus === p);

    // Storage bar reflects total disk usage (set in markup); the list below
    // only shows the most recent protocols, so we leave the bar stable.

    if (p === 'usb' && !fm.usbConnected) {
      tbody.innerHTML = '<tr><td colspan="4"><div class="fm-empty"><i class="bi bi-usb-drive"></i><p>Kein USB-Speicher verbunden.<br>Stecken Sie einen USB-Stick ein.</p></div></td></tr>';
      pane.querySelector('.pane-foot .selinfo').textContent = '';
      pane.querySelector('.pane-foot .count').textContent = '0 Dateien';
      return;
    }

    if (!files.length) {
      tbody.innerHTML = '<tr><td colspan="4"><div class="fm-empty"><i class="bi bi-folder2-open"></i><p>Keine Protokolle vorhanden.</p></div></td></tr>';
    } else {
      tbody.innerHTML = files.map(function (f, i) {
        return '<tr data-i="' + i + '" class="' + (sel.has(i) ? 'sel' : '') + '">' +
          '<td class="fn"><i class="bi bi-file-earmark-pdf-fill"></i> ' + f.name + '</td>' +
          '<td class="muted">' + f.date + '</td>' +
          '<td class="right muted">' + f.size.toFixed(1) + ' KB</td>' +
          '<td class="right"><div class="act">' +
            '<button class="icon-btn" title="Herunterladen" data-act="dl"><i class="bi bi-download"></i></button>' +
            '<button class="icon-btn danger" title="Löschen" data-act="del"><i class="bi bi-trash"></i></button>' +
          '</div></td></tr>';
      }).join('');
    }

    var n = sel.size;
    var selSize = Array.from(sel).reduce(function (s, i) { return s + (files[i] ? files[i].size : 0); }, 0);
    pane.querySelector('.pane-foot .selinfo').textContent = n ? (n + ' markiert · ' + selSize.toFixed(1) + ' KB') : '';
    pane.querySelector('.pane-foot .count').textContent = files.length + ' Datei' + (files.length === 1 ? '' : 'en');
    updateToolbar();
  }

  function updateToolbar() {
    var p = fm.focus;
    var n = fm.sel[p].size;
    var other = p === 'internal' ? 'usb' : 'internal';
    var canMove = n > 0 && (other !== 'usb' || fm.usbConnected) && (p !== 'usb' || fm.usbConnected);
    document.getElementById('btnCopy').disabled = !canMove;
    document.getElementById('btnMove').disabled = !canMove;
    document.getElementById('btnDelete').disabled = n === 0;
    var arrow = p === 'internal' ? 'bi-arrow-right' : 'bi-arrow-left';
    document.querySelectorAll('#btnCopy .dir, #btnMove .dir').forEach(function (el) {
      el.className = 'dir bi ' + arrow;
    });
    document.getElementById('toDest').textContent = other === 'usb' ? 'USB' : 'Intern';
  }

  function bindPane(p) {
    var pane = document.getElementById('pane-' + p);
    if (!pane) return;
    pane.addEventListener('click', function (e) {
      fm.focus = p;
      var tr = e.target.closest('tr[data-i]');
      var actBtn = e.target.closest('[data-act]');
      if (actBtn && tr) {
        var idx = +tr.getAttribute('data-i');
        if (actBtn.getAttribute('data-act') === 'del') {
          fm.sel[p] = new Set([idx]);
          openDeleteModal(p);
        }
        renderPane(p); renderPane(p === 'internal' ? 'usb' : 'internal');
        return;
      }
      if (tr) {
        var i = +tr.getAttribute('data-i');
        var sel = fm.sel[p];
        if (e.metaKey || e.ctrlKey) { sel.has(i) ? sel.delete(i) : sel.add(i); }
        else if (sel.has(i) && sel.size === 1) { sel.clear(); }
        else { sel.clear(); sel.add(i); }
      }
      renderPane('internal'); renderPane('usb');
    });
  }

  // toolbar actions
  function doTransfer(move) {
    var src = fm.focus, dst = src === 'internal' ? 'usb' : 'internal';
    var sel = Array.from(fm.sel[src]).sort(function (a, b) { return b - a; });
    sel.forEach(function (i) {
      var f = fm[src][i];
      if (!fm[dst].some(function (x) { return x.name === f.name; })) fm[dst].unshift({ name: f.name, date: f.date, size: f.size });
    });
    if (move) { sel.forEach(function (i) { fm[src].splice(i, 1); }); }
    fm.sel[src].clear();
    renderPane('internal'); renderPane('usb');
  }

  /* ---------- Delete confirmation modal ---------- */
  var pendingDelete = null;
  function openDeleteModal(p) {
    pendingDelete = p;
    var files = Array.from(fm.sel[p]).map(function (i) { return fm[p][i]; }).filter(Boolean);
    var list = document.getElementById('delFileList');
    list.innerHTML = files.map(function (f) { return '<div><i class="bi bi-file-earmark-pdf"></i> ' + f.name + '</div>'; }).join('');
    document.getElementById('delCount').textContent = files.length;
    document.getElementById('delPlural').textContent = files.length === 1 ? 'dieses Protokoll' : 'diese ' + files.length + ' Protokolle';
    document.getElementById('delLocation').textContent = p === 'internal' ? 'Internem Speicher' : 'USB-Speicher';
    showModal('modalDelete');
  }
  document.getElementById('btnDelete').addEventListener('click', function () { openDeleteModal(fm.focus); });
  document.getElementById('confirmDelete').addEventListener('click', function () {
    if (pendingDelete) {
      var p = pendingDelete;
      var sel = Array.from(fm.sel[p]).sort(function (a, b) { return b - a; });
      sel.forEach(function (i) { fm[p].splice(i, 1); });
      fm.sel[p].clear();
      renderPane('internal'); renderPane('usb');
    }
    hideModal('modalDelete'); pendingDelete = null;
  });

  document.getElementById('btnCopy').addEventListener('click', function () { doTransfer(false); });
  document.getElementById('btnMove').addEventListener('click', function () { doTransfer(true); });
  document.getElementById('btnRefresh').addEventListener('click', function (e) {
    var ic = e.currentTarget.querySelector('.bi');
    ic.style.transition = 'transform .5s'; ic.style.transform = 'rotate(360deg)';
    setTimeout(function () { ic.style.transition = 'none'; ic.style.transform = 'none'; }, 520);
  });
  // USB connect/disconnect demo toggle
  var usbToggle = document.getElementById('usbToggle');
  if (usbToggle) usbToggle.addEventListener('click', function () {
    fm.usbConnected = !fm.usbConnected;
    fm.sel.usb.clear();
    document.getElementById('pane-usb').querySelector('.usb-status').classList.toggle('off', !fm.usbConnected);
    document.getElementById('pane-usb').querySelector('.usb-status span:last-child').textContent = fm.usbConnected ? 'Verbunden' : 'Getrennt';
    usbToggle.textContent = fm.usbConnected ? 'USB trennen (Demo)' : 'USB verbinden (Demo)';
    renderPane('usb'); updateToolbar();
  });

  bindPane('internal'); bindPane('usb');
  renderPane('internal'); renderPane('usb');

  /* ============================================================
     MODAL helpers
     ============================================================ */
  function showModal(id) { document.getElementById(id).classList.add('show'); }
  function hideModal(id) { document.getElementById(id).classList.remove('show'); }
  window.hideModal = hideModal;
  document.querySelectorAll('.modal-overlay').forEach(function (ov) {
    ov.addEventListener('click', function (e) { if (e.target === ov) ov.classList.remove('show'); });
  });

  /* ============================================================
     NETWORK — DHCP / static segmented + save warning
     ============================================================ */
  var ipMode = 'dhcp';
  document.querySelectorAll('#ipModeSeg button').forEach(function (b) {
    b.addEventListener('click', function () {
      ipMode = b.getAttribute('data-mode');
      document.querySelectorAll('#ipModeSeg button').forEach(function (x) { x.classList.toggle('active', x === b); });
      var stat = ipMode === 'static';
      document.querySelectorAll('.static-field input').forEach(function (i) { i.disabled = !stat; });
      document.getElementById('dhcpNote').style.display = stat ? 'none' : 'flex';
    });
  });
  document.getElementById('saveNetwork').addEventListener('click', function () {
    document.getElementById('netModeLabel').textContent = ipMode === 'static' ? 'statische' : 'dynamische (DHCP)';
    var ip = ipMode === 'static' ? (document.getElementById('staticIp').value || '192.168.178.50') : 'automatisch (DHCP)';
    document.getElementById('netIpLabel').textContent = ip;
    showModal('modalNetwork');
  });
  document.getElementById('confirmNetwork').addEventListener('click', function () {
    hideModal('modalNetwork');
    var s = document.getElementById('netSaved');
    s.style.display = 'flex';
    setTimeout(function () { s.style.display = 'none'; }, 3200);
  });

  /* ============================================================
     CLOCK / RTC
     ============================================================ */
  function tickClocks() {
    var now = new Date();
    // topbar live clock (date + time with seconds)
    var bt = document.getElementById('barTime');
    var bd = document.getElementById('barDate');
    if (bt) bt.textContent = now.toLocaleTimeString('de-DE');
    if (bd) bd.textContent = now.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
    var sys = document.getElementById('sysTime');
    var sysD = document.getElementById('sysDate');
    if (sys) {
      sys.textContent = now.toLocaleTimeString('de-DE');
      sysD.textContent = now.toLocaleDateString('de-DE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    }
    // RTC drifts 4s behind for realism
    var rtc = new Date(now.getTime() - 4000);
    var rt = document.getElementById('rtcTime');
    var rd = document.getElementById('rtcDate');
    if (rt) {
      rt.textContent = rtc.toLocaleTimeString('de-DE');
      rd.textContent = rtc.toLocaleDateString('de-DE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    }
  }
  setInterval(tickClocks, 1000); tickClocks();
  var setRtc = document.getElementById('setRtc');
  if (setRtc) setRtc.addEventListener('click', function () {
    var s = document.getElementById('rtcSaved');
    s.style.display = 'inline-flex';
    setTimeout(function () { s.style.display = 'none'; }, 2600);
  });

  /* ============================================================
     LIVE MONITOR — simulated serial stream
     ============================================================ */
  var monTimer = null, monPaused = false, monAuto = true;
  var termBody = document.getElementById('termBody');
  var SAMPLE = [
    { c: 'l-info', t: 'SYSTEM Sterilisator-Link aktiv · /dev/ttyUSB0 @ 9600 8N1' },
    { c: 'l-rx', t: 'RX  PROG: Instrumente 134°C  PHASE: Vorvakuum' },
    { c: 'l-rx', t: 'RX  T1=121.4°C  T2=120.9°C  P=1.04bar' },
    { c: 'l-rx', t: 'RX  PHASE: Aufheizen  T1=128.7°C  P=2.11bar' },
    { c: 'l-rx', t: 'RX  PHASE: Sterilisation  T1=134.2°C  P=3.06bar  t=00:03:30' },
    { c: 'l-ok', t: 'OK  Haltezeit erreicht · Plateau stabil ±0.3°C' },
    { c: 'l-rx', t: 'RX  PHASE: Trocknung  P=0.21bar' },
    { c: 'l-feed', t: '---- SEITENVORSCHUB ---- Protokoll CH021668 ----' },
    { c: 'l-ok', t: 'OK  Charge CH021668 BESTANDEN · PDF erzeugt (48,6 KB)' },
    { c: 'l-warn', t: 'WARN USB-Schreibcache 78% · Synchronisation empfohlen' }
  ];
  var si = 0;
  function ts() { return new Date().toLocaleTimeString('de-DE'); }
  function pushLine() {
    if (!termBody || monPaused) return;
    var s = SAMPLE[si % SAMPLE.length]; si++;
    var div = document.createElement('div');
    div.className = s.c;
    div.innerHTML = '<span class="ts">[' + ts() + ']</span> ' + s.t;
    termBody.appendChild(div);
    while (termBody.children.length > 200) termBody.removeChild(termBody.firstChild);
    if (monAuto) termBody.scrollTop = termBody.scrollHeight;
  }
  function startMonitor() {
    if (monTimer || !termBody) return;
    if (!termBody.children.length) { for (var i = 0; i < 6; i++) pushLine(); }
    monTimer = setInterval(pushLine, 1600);
  }
  function stopMonitor() { if (monTimer) { clearInterval(monTimer); monTimer = null; } }
  var bPause = document.getElementById('monPause');
  if (bPause) bPause.addEventListener('click', function () {
    monPaused = !monPaused;
    bPause.innerHTML = monPaused ? '<i class="bi bi-play-fill"></i> Fortsetzen' : '<i class="bi bi-pause-fill"></i> Pause';
  });
  var bClear = document.getElementById('monClear');
  if (bClear) bClear.addEventListener('click', function () { if (termBody) termBody.innerHTML = ''; });
  var bAuto = document.getElementById('monAuto');
  if (bAuto) bAuto.addEventListener('change', function () { monAuto = bAuto.checked; });

})();
