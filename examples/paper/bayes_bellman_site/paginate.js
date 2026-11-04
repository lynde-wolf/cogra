// paginate.js: pour #source into fixed pages of one or more columns, the way
// an APA journal of about 1980 was made up. Part of cogra.paper.
//
//  - Text fills the first column, then the next, then the next page; a
//    paragraph that does not fit is split between words (the first part's
//    last line is justified, the rest continues unindented).
//  - Headings are not split and are not left at the foot of a column.
//  - A paragraph is not split if fewer than two of its lines would stay behind.
//  - Footnotes go at the foot of the column that holds their marker.
//  - Figures and tables go across the page at the top: on the current page if
//    it has no text yet, otherwise on the next one. A figure's continued
//    caption (.capcont) follows the figure.
//  - Screens narrower than 640 px get the unpaginated single column instead.
//
// #book carries the settings: data-columns, data-start (first folio),
// data-rh-verso and data-rh-recto (running heads). When it is done it sets
// data-pages on #book and data-paginated on <html>.
(function () {
  "use strict";
  var MIN_WIDTH = 640;
  var src = document.getElementById("source");
  var book = document.getElementById("book");

  function el(tag, cls) { var e = document.createElement(tag); if (cls) e.className = cls; return e; }

  // The source is hidden, so nothing has asked for the text face yet and
  // document.fonts.ready would resolve before it loads: load it explicitly,
  // or the pages are measured in a fallback face and overflow later.
  function ready() {
    var face = getComputedStyle(document.body).fontFamily;
    var faces = ["400 10pt", "italic 400 10pt", "700 10pt", "italic 700 10pt"].map(function (s) {
      return document.fonts.load(s + " " + face).catch(function () {});
    });
    var imgs = Array.prototype.slice.call(src.querySelectorAll("img"));
    return Promise.all(faces.concat([document.fonts.ready, typesetMath()]).concat(imgs.map(function (im) {
      return im.complete ? Promise.resolve() : new Promise(function (r) { im.onload = im.onerror = r; });
    })));
  }

  // Math (MathJax, when the page has any) is typeset in the source before
  // anything is measured. The source is shown off screen at the width of one
  // column meanwhile, so equation numbers sit at the column's edge and a
  // display too wide for it is scaled to fit.
  function typesetMath() {
    if (!(window.MathJax && MathJax.startup && MathJax.startup.promise)) return Promise.resolve();
    var n = Math.max(1, parseInt(book.dataset.columns || "2", 10));
    var probe = el("div");
    probe.style.width = "calc((var(--page-w) - var(--margin-l) - var(--margin-r) - " + (n - 1) +
                        " * var(--gutter)) / " + n + ")";
    document.body.appendChild(probe);
    var w = probe.offsetWidth;
    probe.remove();
    var s = src.style;
    s.display = "block"; s.position = "absolute"; s.left = "-10000px"; s.top = "0";
    s.width = w + "px"; s.fontSize = "var(--body)"; s.lineHeight = "var(--lead)";
    return MathJax.startup.promise
      .then(function () { return MathJax.typesetPromise([src]); })
      .catch(function () {})
      .then(function () { src.removeAttribute("style"); });
  }

  function paginate() {
    var nCols = Math.max(1, parseInt(book.dataset.columns || "2", 10));
    var start = parseInt(book.dataset.start || "1", 10);
    var notes = {};
    src.querySelectorAll(".notes-src .note").forEach(function (n) { notes[n.dataset.n] = n; });
    var authorNote = Array.prototype.slice.call(src.querySelectorAll(".authornote-src > *"));
    var queue = Array.prototype.slice.call(src.querySelector(".flowsrc").children).map(function (b) {
      return b.cloneNode(true);
    });
    var floatQueue = [], held = {};
    var sheets = 0, folio = start - 1, page = null, cols = null, colIdx = 0;

    function mkCol() {
      var col = el("div", "col"), flow = el("div", "flow"), feet = el("div", "feet");
      col.appendChild(flow); col.appendChild(feet);
      return { col: col, flow: flow, feet: feet, fixed: [] };
    }

    function syncFeet(c) {
      var seen = {}, out = c.fixed.map(function (n) { return n.cloneNode(true); });
      c.flow.querySelectorAll("sup.fn").forEach(function (m) {
        var n = m.dataset.n;
        if (!seen[n] && notes[n]) { seen[n] = 1; out.push(notes[n].cloneNode(true)); }
      });
      c.feet.replaceChildren.apply(c.feet, out);
    }

    function room(c) { return c.col.clientHeight - c.feet.offsetHeight - c.flow.offsetHeight; }
    function fits(c) { return room(c) >= -0.5; }
    function lead(b) { return parseFloat(getComputedStyle(b).lineHeight) || 14.7; }
    function bodyLead() { return parseFloat(getComputedStyle(page.sheet).lineHeight) || 14.7; }
    function empty() { return cols.every(function (c) { return c.flow.children.length === 0; }); }

    function newPage() {
      sheets += 1; folio += 1;
      var first = sheets === 1;
      var sheet = el("div", "sheet " + (folio % 2 ? "recto" : "verso"));
      if (!first) {
        var rh = el("div", "rh");
        rh.innerHTML = "<span>" + (folio % 2 ? book.dataset.rhRecto : book.dataset.rhVerso) +
                       '</span><span class="folio">' + folio + "</span>";
        sheet.appendChild(rh);
      }
      var body = el("div", "body"), floats = el("div", "floats"), colsBox = el("div", "cols");
      cols = [];
      for (var i = 0; i < nCols; i++) { cols.push(mkCol()); colsBox.appendChild(cols[i].col); }
      body.appendChild(floats); body.appendChild(colsBox); sheet.appendChild(body);
      book.appendChild(sheet);
      page = { sheet: sheet, body: body, floats: floats };
      colIdx = 0;
      if (first) {
        var front = src.querySelector(".front-src").cloneNode(true);
        front.className = "front";
        floats.appendChild(front);
        cols[0].fixed = authorNote.map(function (n) { return n.cloneNode(true); });
        syncFeet(cols[0]);
        var ffSrc = src.querySelector(".firstfoot-src");
        var ff = ffSrc ? ffSrc.cloneNode(true) : el("div");
        ff.className = "first-foot";
        ff.insertAdjacentHTML("beforeend", '<span class="folio">' + folio + "</span>");
        sheet.appendChild(ff);
      }
      while (floatQueue.length && placeFloat(floatQueue[0])) floatQueue.shift();
    }

    function nextCol() { if (colIdx < nCols - 1) colIdx += 1; else newPage(); }

    // A figure takes the text width; its image shrinks (keeping its
    // proportions) so that at least four lines of text still fit below it.
    // Tables cannot shrink: one that is too tall gets a page of its own.
    function placeFloat(fig) {
      var hadFloat = page.floats.querySelector("figure");
      page.floats.appendChild(fig);
      var minText = 4 * bodyLead();
      var spare = cols[0].col.clientHeight - cols[0].feet.offsetHeight - minText;
      if (spare < 0) {
        var img = fig.querySelectorAll("img");
        var cap = fig.querySelector("figcaption");
        var maxImg = page.body.clientHeight - (page.floats.offsetHeight - fig.offsetHeight) -
                     (cap ? cap.offsetHeight : 0) - minText - 20;
        if (hadFloat || (!empty() && img.length === 0)) { fig.remove(); return false; }
        if (img.length) {
          if (maxImg < 120) { fig.remove(); return false; }
          img.forEach(function (im) { im.style.maxHeight = maxImg + "px"; im.style.width = "auto"; });
        }
      }
      var n = fig.dataset.fig;
      if (held[n]) { queue = held[n].concat(queue); delete held[n]; }
      fig.dataset.placed = "1";
      return true;
    }

    // Word starts across the text nodes of b, as [node, offset] pairs.
    function wordStarts(b) {
      var out = [], prevSpace = true, w = document.createTreeWalker(b, NodeFilter.SHOW_TEXT), t;
      while ((t = w.nextNode())) {
        var s = t.nodeValue;
        for (var i = 0; i < s.length; i++) {
          var sp = /\s/.test(s[i]);
          if (!sp && prevSpace) out.push([t, i]);
          prevSpace = sp;
        }
      }
      return out;
    }

    // Detach everything from word k on into a new element of the same kind.
    function splitAt(b, k) {
      var starts = wordStarts(b);
      if (k >= starts.length) return null;
      var r = document.createRange();
      r.setStart(starts[k][0], starts[k][1]);
      r.setEndAfter(b.lastChild);
      var tail = b.cloneNode(false);
      tail.appendChild(r.extractContents());
      return tail;
    }

    function isHead(b) { return /\bh[12]\b/.test(b.className); }

    function place(b) {
      var c = cols[colIdx];
      if (b.tagName === "FIGURE") {
        if (empty() && !page.floats.querySelector("figure") && placeFloat(b)) return;
        floatQueue.push(b); held[b.dataset.fig] = held[b.dataset.fig] || []; return;
      }
      if (b.classList.contains("capcont") && held[b.dataset.fig] !== undefined &&
          !book.querySelector('figure[data-fig="' + b.dataset.fig + '"]')) {
        held[b.dataset.fig].push(b); return;
      }
      c.flow.appendChild(b); syncFeet(c);
      if (fits(c)) {
        // keep a heading with at least two lines of what follows
        if (isHead(b) && room(c) < 2.6 * lead(b) && c.flow.children.length > 1) {
          b.remove(); syncFeet(c); nextCol(); place(b);
        }
        return;
      }
      if (isHead(b) || b.classList.contains("nosplit") || b.tagName !== "P") {
        if (c.flow.children.length === 1) return;          // too big for any column: leave it
        b.remove(); syncFeet(c); nextCol(); place(b); return;
      }
      var html = b.innerHTML, n = wordStarts(b).length, lo = 0, hi = n - 1;
      while (lo < hi) {                                   // most words that still fit
        var mid = (lo + hi + 1) >> 1;
        b.innerHTML = html; splitAt(b, mid); syncFeet(c);
        if (fits(c)) lo = mid; else hi = mid - 1;
      }
      b.innerHTML = html;
      var tail = lo > 0 ? splitAt(b, lo) : null;
      syncFeet(c);
      var orphan = !tail || b.offsetHeight < 1.9 * lead(b) || !fits(c);
      if (orphan) {
        if (tail) { b.innerHTML = html; }
        if (c.flow.children.length === 1) { syncFeet(c); return; }
        b.remove(); syncFeet(c); nextCol(); place(b); return;
      }
      b.classList.add("split");
      // justifying the new last line can change the breaks; back off if so
      while (!fits(c) && lo > 1) {
        b.innerHTML = html; lo -= 1; tail = splitAt(b, lo); b.classList.add("split"); syncFeet(c);
      }
      tail.classList.remove("split"); tail.classList.add("cont");
      tail.removeAttribute("id");
      nextCol(); place(tail);
    }

    newPage();
    while (queue.length) place(queue.shift());
    for (var guard = 0; floatQueue.length && guard < 20; guard++) newPage();
    book.dataset.pages = sheets;
    // columns whose text runs past the foot (0 unless something could not be fitted)
    book.dataset.overflow = Array.prototype.filter.call(book.querySelectorAll(".col"), function (c) {
      return c.querySelector(".flow").offsetHeight + c.querySelector(".feet").offsetHeight > c.clientHeight + 1;
    }).length;
    document.documentElement.dataset.paginated = "1";
  }

  function fit() {
    var sheet = book.querySelector(".sheet");
    if (!sheet) return;
    book.style.zoom = 1;
    var w = sheet.offsetWidth;
    book.style.zoom = Math.min(1.45, (window.innerWidth - 24) / w);
  }

  if (window.innerWidth < MIN_WIDTH) {
    document.body.classList.add("unpaged");
    document.documentElement.dataset.paginated = "1";
    return;
  }
  ready().then(function () { paginate(); fit(); window.addEventListener("resize", fit); });
})();
