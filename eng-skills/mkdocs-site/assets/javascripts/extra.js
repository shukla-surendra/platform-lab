/* eng-skills site interactivity: word-bank filtering, word of the day, flashcards, speech. */
(function () {
  "use strict";

  // ------------------------------------------------------------------ helpers
  function siteBase() {
    try {
      var cfg = JSON.parse(document.getElementById("__config").textContent);
      return new URL(cfg.base + "/", location.href);
    } catch (e) {
      return new URL("./", location.href);
    }
  }
  function siteUrl(path) { return new URL(path, siteBase()).href; }

  var deckCache = {};
  function loadJSON(path) {
    if (!deckCache[path]) {
      deckCache[path] = fetch(siteUrl(path)).then(function (r) {
        if (!r.ok) throw new Error(path + " " + r.status);
        return r.json();
      });
    }
    return deckCache[path];
  }
  function loadDeck(id) { return loadJSON("assets/flashcards/" + id + ".json"); }

  var store = {
    get: function (k, d) {
      try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; }
    },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode */ } }
  };

  function speak(text) {
    if (!("speechSynthesis" in window) || !text) return;
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text.replace(/[\/(].*$/, "").trim() || text);
    u.lang = "en-US";
    u.rate = 0.9;
    var voices = window.speechSynthesis.getVoices();
    var pick = voices.find(function (v) { return /en[-_](US|GB)/i.test(v.lang) && /Samantha|Daniel|Google|Natural/i.test(v.name); }) ||
               voices.find(function (v) { return /^en/i.test(v.lang); });
    if (pick) u.voice = pick;
    window.speechSynthesis.speak(u);
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function dayKey(d) { d = d || new Date(); return d.getFullYear() + "-" + (d.getMonth() + 1) + "-" + d.getDate(); }
  function hashStr(s) { var h = 2166136261; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }

  // ------------------------------------------------------------- word banks
  function initWordBank() {
    var bar = document.querySelector(".wb-toolbar");
    if (!bar || bar.dataset.ready) return;
    bar.dataset.ready = "1";
    var list = document.querySelector(".wb-list");
    var entries = Array.prototype.slice.call(list.querySelectorAll(".wb-entry"));
    var input = bar.querySelector(".wb-filter");
    var deep = bar.querySelector(".wb-deep-toggle");
    var count = bar.querySelector(".wb-count b");
    var empty = document.querySelector(".wb-empty");
    var letters = Array.prototype.slice.call(bar.querySelectorAll("a.wb-letter"));
    var texts = null;

    // speak buttons on every entry heading
    entries.forEach(function (sec) {
      var h = sec.firstElementChild;
      if (!h || h.querySelector(".wb-speak")) return;
      var b = document.createElement("button");
      b.type = "button";
      b.className = "wb-speak";
      b.title = "Pronounce";
      b.setAttribute("aria-label", "Pronounce " + sec.dataset.term);
      b.textContent = "🔊";
      b.addEventListener("click", function (e) { e.preventDefault(); speak(h.firstChild ? h.firstChild.textContent : sec.dataset.term); });
      h.appendChild(b);
    });

    var t;
    function apply() {
      var q = input.value.trim().toLowerCase();
      var useDeep = deep.checked;
      if (useDeep && !texts) texts = entries.map(function (s) { return s.textContent.toLowerCase(); });
      var shown = 0, seen = {};
      entries.forEach(function (s, i) {
        var hit = !q || s.dataset.term.indexOf(q) !== -1 || (useDeep && texts[i].indexOf(q) !== -1);
        s.hidden = !hit;
        if (hit) { shown++; seen[s.dataset.letter] = true; }
      });
      count.textContent = shown.toLocaleString();
      empty.hidden = shown !== 0;
      letters.forEach(function (a) { a.classList.toggle("is-empty", !seen[a.dataset.letter]); });
      var url = new URL(location.href);
      if (q) url.searchParams.set("q", q); else url.searchParams.delete("q");
      history.replaceState(history.state, "", url);
    }
    input.addEventListener("input", function () { clearTimeout(t); t = setTimeout(apply, 120); });
    deep.addEventListener("change", apply);

    letters.forEach(function (a) {
      a.addEventListener("click", function (e) {
        var target = entries.find(function (s) { return !s.hidden && s.dataset.letter === a.dataset.letter; });
        if (!target) { e.preventDefault(); return; }
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
        flash(target);
        history.replaceState(history.state, "", "#" + target.firstElementChild.id);
      });
    });

    bar.querySelector(".wb-random").addEventListener("click", function () {
      var pool = entries.filter(function (s) { return !s.hidden; });
      if (!pool.length) return;
      var pick = pool[Math.floor(Math.random() * pool.length)];
      pick.scrollIntoView({ behavior: "smooth", block: "start" });
      flash(pick);
    });

    var q0 = new URL(location.href).searchParams.get("q");
    if (q0) { input.value = q0; apply(); }
    if (location.hash) {
      var el = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      var sec = el && el.closest(".wb-entry");
      if (sec) flash(sec);
    }

  }

  // "/" is Material's search; "f" focuses the word-bank filter (registered once)
  document.addEventListener("keydown", function (e) {
    if ((e.key !== "f" && e.key !== "F") || e.metaKey || e.ctrlKey || e.altKey) return;
    if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
    var input = document.querySelector(".wb-filter");
    if (input) { e.preventDefault(); input.focus(); }
  });

  function flash(el) {
    el.classList.remove("is-flash");
    void el.offsetWidth;
    el.classList.add("is-flash");
  }

  // --------------------------------------------------------- word of the day
  function initWotd() {
    var box = document.getElementById("wotd");
    if (!box || box.dataset.ready) return;
    box.dataset.ready = "1";
    var term = box.querySelector(".wotd-term");
    var pron = box.querySelector(".wotd-pron");
    var body = box.querySelector(".wotd-body");
    var open = box.querySelector(".wotd-open");
    var current = null;

    function show(card) {
      current = card;
      term.textContent = card.t;
      pron.textContent = card.p ? "/" + card.p + "/" : "";
      body.innerHTML = card.h;
      open.href = siteUrl(card.u);
    }
    loadDeck("vocab").then(function (cards) {
      cards = cards.filter(function (c) { return c.h && c.h.length > 40; });
      if (!cards.length) throw new Error("empty");
      show(cards[hashStr(dayKey()) % cards.length]);
      box.querySelector(".wotd-next").addEventListener("click", function () {
        show(cards[Math.floor(Math.random() * cards.length)]);
      });
    }).catch(function () { term.textContent = "Couldn't load the word list."; });
    box.querySelector(".wotd-speak").addEventListener("click", function () { if (current) speak(current.t); });

    // live due count from flashcard progress
    var due = document.querySelector(".js-due");
    if (due) {
      var st = store.get(FC_KEY, null);
      var now = Date.now(), n = 0;
      if (st && st.cards) Object.keys(st.cards).forEach(function (k) { if (st.cards[k].due <= now) n++; });
      due.textContent = n;
    }
  }

  function initSearchButtons() {
    Array.prototype.forEach.call(document.querySelectorAll(".js-open-search"), function (a) {
      if (a.dataset.ready) return;
      a.dataset.ready = "1";
      a.addEventListener("click", function (e) {
        e.preventDefault();
        var toggle = document.querySelector("[data-md-toggle=search]");
        if (toggle) { toggle.checked = true; toggle.dispatchEvent(new Event("change")); }
        setTimeout(function () { var i = document.querySelector("[data-md-component=search-query]"); if (i) i.focus(); }, 50);
      });
    });
  }

  // ------------------------------------------------------------- flashcards
  var FC_KEY = "eng-skills.flashcards.v1";
  var INTERVALS = [0, 1, 3, 7, 16, 35, 80]; // days per Leitner box
  var DAY = 86400000;

  function initFlashcards() {
    var root = document.getElementById("fc-app");
    if (!root || root.dataset.ready) return;
    root.dataset.ready = "1";

    var state = store.get(FC_KEY, null) || {};
    state.cards = state.cards || {};
    state.decks = state.decks || ["vocab", "technical"];
    state.newPerSession = state.newPerSession || 20;
    state.log = state.log || {};
    var urlDeck = new URL(location.href).searchParams.get("deck");
    if (urlDeck) state.decks = [urlDeck];

    var index = [], pool = [], queue = [], cur = null, revealed = false, sessionDone = 0;

    function save() { store.set(FC_KEY, state); }
    function key(c) { return c.d + "|" + c.t; }

    function streak() {
      var s = 0, d = new Date();
      if (!state.log[dayKey(d)]) d = new Date(d.getTime() - DAY);
      while (state.log[dayKey(d)]) { s++; d = new Date(d.getTime() - DAY); }
      return s;
    }

    function stats() {
      var now = Date.now(), due = 0, learning = 0, mastered = 0, fresh = 0;
      pool.forEach(function (c) {
        var r = state.cards[key(c)];
        if (!r) { fresh++; return; }
        if (r.due <= now) due++;
        if (r.box >= 4) mastered++; else learning++;
      });
      return { due: due, learning: learning, mastered: mastered, fresh: fresh, total: pool.length };
    }

    function shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }

    function buildQueue() {
      var now = Date.now();
      var due = [], fresh = [];
      pool.forEach(function (c) {
        var r = state.cards[key(c)];
        if (!r) fresh.push(c); else if (r.due <= now) due.push(c);
      });
      queue = shuffle(due).concat(shuffle(fresh).slice(0, state.newPerSession));
    }

    function renderShell() {
      root.innerHTML =
        '<div class="fc-decks" role="group" aria-label="Decks"></div>' +
        '<div class="fc-stats"></div>' +
        '<div class="fc-stage"></div>' +
        '<div class="fc-footer">' +
          '<label>New cards per session <select class="fc-new">' +
            [10, 20, 30, 50, 100].map(function (n) { return '<option' + (n === state.newPerSession ? " selected" : "") + ">" + n + "</option>"; }).join("") +
          "</select></label>" +
          '<button type="button" class="fc-link fc-reset">Reset progress</button>' +
        "</div>";
      var decks = root.querySelector(".fc-decks");
      index.forEach(function (d) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "fc-chip" + (state.decks.indexOf(d.id) !== -1 ? " is-on" : "");
        b.innerHTML = "<b>" + esc(d.label) + "</b><span>" + d.count.toLocaleString() + "</span>";
        b.title = d.desc;
        b.setAttribute("aria-pressed", state.decks.indexOf(d.id) !== -1);
        b.addEventListener("click", function () {
          var i = state.decks.indexOf(d.id);
          if (i === -1) state.decks.push(d.id); else if (state.decks.length > 1) state.decks.splice(i, 1);
          save(); renderShell(); loadPool();
        });
        decks.appendChild(b);
      });
      root.querySelector(".fc-new").addEventListener("change", function (e) {
        state.newPerSession = +e.target.value; save(); buildQueue(); next();
      });
      root.querySelector(".fc-reset").addEventListener("click", function () {
        if (!confirm("Reset all flashcard progress in this browser?")) return;
        state.cards = {}; state.log = {}; save(); buildQueue(); next();
      });
    }

    function renderStats() {
      var s = stats();
      root.querySelector(".fc-stats").innerHTML =
        stat(s.due, "due", "due") + stat(s.fresh, "new", "new") + stat(s.learning, "learning", "learning") +
        stat(s.mastered, "mastered", "mastered") + stat(streak(), "day streak 🔥", "streak") +
        '<div class="fc-progress" title="' + s.mastered + " of " + s.total + ' mastered"><i style="width:' +
        (s.total ? (100 * s.mastered / s.total).toFixed(1) : 0) + '%"></i></div>';
    }
    function stat(n, label, cls) { return '<div class="fc-stat fc-stat--' + cls + '"><b>' + n.toLocaleString() + "</b><span>" + label + "</span></div>"; }

    function next() {
      renderStats();
      cur = queue.shift() || null;
      revealed = false;
      var stage = root.querySelector(".fc-stage");
      if (!cur) {
        stage.innerHTML = '<div class="fc-card fc-done"><div class="fc-done-emoji">🎉</div><h2>Session complete</h2>' +
          "<p>" + (sessionDone ? "You reviewed <b>" + sessionDone + "</b> cards. " : "") + "Nothing else is due in these decks right now.</p>" +
          '<button type="button" class="md-button md-button--primary fc-more">Learn ' + state.newPerSession + " more new cards</button></div>";
        stage.querySelector(".fc-more").addEventListener("click", function () {
          var fresh = pool.filter(function (c) { return !state.cards[key(c)]; });
          queue = shuffle(fresh).slice(0, state.newPerSession);
          if (!queue.length) { stage.querySelector("p").textContent = "You've seen every card in these decks. Impressive!"; return; }
          next();
        });
        return;
      }
      var r = state.cards[key(cur)];
      var badge = r ? (r.box >= 4 ? "mastered" : "review") : "new";
      var deckLabel = (index.find(function (d) { return d.id === cur.d; }) || {}).label || cur.d;
      stage.innerHTML =
        '<div class="fc-card" tabindex="0">' +
          '<div class="fc-top"><span class="fc-badge fc-badge--' + badge + '">' + badge + "</span><span class=\"fc-deck\">" + esc(deckLabel) + "</span>" +
          '<span class="fc-left">' + (queue.length + 1) + " left</span></div>" +
          '<div class="fc-front"><div class="fc-term">' + esc(cur.t) + "</div>" +
          (cur.p ? '<div class="fc-pron">/' + esc(cur.p) + "/</div>" : "") +
          '<button type="button" class="wb-btn fc-speak" title="Pronounce (V)">🔊</button></div>' +
          '<div class="fc-back" hidden><div class="fc-body md-typeset">' + cur.h + "</div>" +
          '<a class="fc-open" href="' + esc(siteUrl(cur.u)) + '" target="_blank" rel="noopener">Open full entry ↗</a></div>' +
          '<div class="fc-actions">' +
            '<button type="button" class="md-button md-button--primary fc-reveal">Show meaning <kbd>Space</kbd></button>' +
            '<div class="fc-grades" hidden>' +
              grade(1, "Again", "again", "<1m") + grade(2, "Hard", "hard", ivl(r, 2)) + grade(3, "Good", "good", ivl(r, 3)) + grade(4, "Easy", "easy", ivl(r, 4)) +
            "</div>" +
            '<button type="button" class="fc-link fc-skip">Skip →</button>' +
          "</div>" +
        "</div>";
      stage.querySelector(".fc-reveal").addEventListener("click", reveal);
      stage.querySelector(".fc-speak").addEventListener("click", function () { speak(cur.t); });
      stage.querySelector(".fc-skip").addEventListener("click", function () { queue.push(cur); next(); });
      Array.prototype.forEach.call(stage.querySelectorAll(".fc-grade"), function (b) {
        b.addEventListener("click", function () { rate(+b.dataset.g); });
      });
    }

    function newBox(r, g) {
      var box = r ? r.box : 0;
      if (g === 1) return 0;
      if (g === 2) return Math.max(1, box);
      if (g === 3) return Math.min(box + 1, INTERVALS.length - 1);
      return Math.min(box + 2, INTERVALS.length - 1);
    }
    function ivl(r, g) {
      var d = INTERVALS[newBox(r, g)];
      return d >= 30 ? Math.round(d / 30) + "mo" : d + "d";
    }
    function grade(g, label, cls, hint) {
      return '<button type="button" class="fc-grade fc-grade--' + cls + '" data-g="' + g + '"><b>' + label + "</b><span>" + hint + " · " + g + "</span></button>";
    }

    function reveal() {
      if (!cur || revealed) return;
      revealed = true;
      var stage = root.querySelector(".fc-stage");
      stage.querySelector(".fc-back").hidden = false;
      stage.querySelector(".fc-reveal").hidden = true;
      stage.querySelector(".fc-grades").hidden = false;
    }

    function rate(g) {
      if (!cur || !revealed) return;
      var k = key(cur), r = state.cards[k];
      var box = newBox(r, g);
      state.cards[k] = { box: box, due: g === 1 ? Date.now() : Date.now() + INTERVALS[box] * DAY - 3600000 };
      var dk = dayKey();
      state.log[dk] = (state.log[dk] || 0) + 1;
      save();
      sessionDone++;
      if (g === 1) queue.splice(Math.min(3, queue.length), 0, cur);
      next();
    }

    function onKey(e) {
      if (!document.body.contains(root)) { document.removeEventListener("keydown", onKey); return; }
      if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) || e.metaKey || e.ctrlKey || e.altKey) return;
      if ((e.key === " " || e.key === "Enter") && !revealed) { e.preventDefault(); reveal(); }
      else if (/^[1-4]$/.test(e.key) && revealed) { e.preventDefault(); rate(+e.key); }
      else if (e.key === "v" || e.key === "V") { if (cur) speak(cur.t); }
      else if (e.key === "ArrowRight" && cur) { queue.push(cur); next(); }
    }
    document.addEventListener("keydown", onKey);

    function loadPool() {
      root.querySelector(".fc-stage").innerHTML = '<div class="fc-loading">Loading cards…</div>';
      Promise.all(state.decks.map(function (id) {
        return loadDeck(id).then(function (cards) { return cards.map(function (c) { c.d = id; return c; }); });
      })).then(function (lists) {
        pool = [].concat.apply([], lists);
        buildQueue();
        next();
      }).catch(function () {
        root.querySelector(".fc-stage").innerHTML = '<div class="fc-loading">Couldn\'t load the decks. Rebuild the site and try again.</div>';
      });
    }

    loadJSON("assets/flashcards/index.json").then(function (idx) {
      index = idx.filter(function (d) { return d.count > 0; });
      var valid = index.map(function (d) { return d.id; });
      state.decks = state.decks.filter(function (d) { return valid.indexOf(d) !== -1; });
      if (!state.decks.length) state.decks = [valid[0]];
      renderShell();
      loadPool();
    }).catch(function () {
      root.innerHTML = '<div class="fc-loading">Couldn\'t load the decks. Rebuild the site and try again.</div>';
    });
  }

  // ------------------------------------------------------------------ boot
  function boot() {
    initWordBank();
    initWotd();
    initFlashcards();
    initSearchButtons();
  }
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(boot); // Material instant navigation
  } else {
    document.addEventListener("DOMContentLoaded", boot);
  }
})();
