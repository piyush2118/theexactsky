/* Place typeahead. Vanilla, because the plan says no frontend framework and
   because this is the only interactive thing on the page.

   The important behaviour is that the form cannot be submitted with a place the
   server did not resolve: the visible field is free text, the submitted field is
   a GeoNames id, and picking a suggestion is the only thing that sets it. A
   half-typed town silently matching the wrong city is how a chart ends up drawn
   for the wrong place. */

(function () {
  var input = document.getElementById('place');
  var hidden = document.getElementById('place_id');
  var list = document.getElementById('place-list');
  var note = document.getElementById('place-note');
  if (!input) return;

  var items = [];
  var cursor = -1;
  var timer = null;
  var lastQuery = '';

  function close() {
    list.hidden = true;
    list.innerHTML = '';
    items = [];
    cursor = -1;
    input.setAttribute('aria-expanded', 'false');
  }

  function choose(place) {
    input.value = place.label;
    hidden.value = place.id;
    note.textContent = place.tz + ' · ' + place.coords;
    close();
  }

  function draw(places) {
    items = places;
    cursor = -1;
    if (!places.length) { close(); return; }
    list.innerHTML = '';
    places.forEach(function (place, i) {
      var li = document.createElement('li');
      li.setAttribute('role', 'option');
      li.id = 'place-opt-' + i;
      li.innerHTML = '<div>' + escapeHtml(place.label) + '</div>' +
                     '<div class="tz">' + escapeHtml(place.tz) + '</div>';
      li.addEventListener('mousedown', function (e) {
        e.preventDefault();
        choose(place);
      });
      list.appendChild(li);
    });
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function highlight(next) {
    if (!items.length) return;
    cursor = (next + items.length) % items.length;
    Array.prototype.forEach.call(list.children, function (li, i) {
      li.setAttribute('aria-selected', i === cursor ? 'true' : 'false');
    });
    list.children[cursor].scrollIntoView({ block: 'nearest' });
  }

  function search() {
    var q = input.value.trim();
    if (q === lastQuery) return;
    lastQuery = q;
    if (q.length < 2) { close(); return; }
    fetch('/geo?q=' + encodeURIComponent(q))
      .then(function (r) { return r.json(); })
      .then(function (places) {
        // A slow response for an old query must not overwrite a newer one.
        if (input.value.trim() === q) draw(places);
      })
      .catch(close);
  }

  input.addEventListener('input', function () {
    // Typing invalidates any previous pick; the id must be re-earned.
    hidden.value = '';
    note.textContent = 'Pick a town from the list.';
    clearTimeout(timer);
    timer = setTimeout(search, 160);
  });

  input.addEventListener('keydown', function (e) {
    if (list.hidden) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); highlight(cursor + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); highlight(cursor - 1); }
    else if (e.key === 'Enter' && cursor >= 0) { e.preventDefault(); choose(items[cursor]); }
    else if (e.key === 'Escape') { close(); }
  });

  input.addEventListener('blur', function () { setTimeout(close, 120); });

  input.form.addEventListener('submit', function (e) {
    if (!hidden.value) {
      e.preventDefault();
      note.textContent = 'Choose a town from the list so the timezone is right.';
      input.focus();
    }
  });
})();
