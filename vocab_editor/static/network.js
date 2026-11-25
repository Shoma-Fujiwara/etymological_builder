// 既存HTMLの #graph, #current, #detail, #back, #nodeSearch, #searchButton, #searchResults を使用
// network は Flask テンプレートから渡された {nodes,edges}
const svg = document.getElementById('graph');
const currentLabel = document.getElementById('current');
const detail = document.getElementById('detail');
const backButton = document.getElementById('back');
const searchInput = document.getElementById('nodeSearch');
const searchButton = document.getElementById('searchButton');
const searchResults = document.getElementById('searchResults');
const chapterFilter = document.getElementById('chapterFilter');
const stackFilter = document.getElementById('stackFilter');
const stackInventory = document.getElementById('stackInventory');
const inventoryStacks = network.stacks || [];
const wordRelations = network.word_relations || [];
const NS = 'http://www.w3.org/2000/svg';
const nodes = new Map(network.nodes.map(n => [n.id, n]));
const neighbors = new Map([...nodes.keys()].map(id => [id, new Set()]));
for (const edge of network.edges) {
  neighbors.get(edge.source)?.add(edge.target);
  neighbors.get(edge.target)?.add(edge.source);
}
const chapters = [...new Set(network.edges.map(e => String(e.chapter)).filter(c => c && c !== 'undefined'))]
  .sort((a,b) => Number(a) - Number(b));
for (const chapter of chapters) {
  const option = document.createElement('option');
  option.value = chapter;
  option.textContent = `Chapter ${chapter}`;
  chapterFilter.append(option);
}
let selectedChapter = 'all';
let selectedStack = 'all';
function refreshStackFilter() {
  stackFilter.replaceChildren();
  const all = document.createElement('option'); all.value = 'all'; all.textContent = 'すべてのStack'; stackFilter.append(all);
  for (const item of inventoryStacks.filter(s => selectedChapter === 'all' || s.chapter === selectedChapter)) {
    const option = document.createElement('option'); option.value = item.stack;
    option.textContent = `${item.stack} ${item.main_word}`; stackFilter.append(option);
  }
  if (![...stackFilter.options].some(o => o.value === selectedStack)) selectedStack = 'all';
  stackFilter.value = selectedStack;
}
function showInventoryWord(word) {
  detail.replaceChildren();
  const title = document.createElement('h2'); title.textContent = word.word; detail.append(title);
  const meta = document.createElement('p'); meta.textContent = `Chapter ${word.chapter} / Stack ${word.stack} / ${word.role === 'main' ? 'メイン単語' : '関連単語'}`; detail.append(meta);
  const status = document.createElement('p'); status.textContent = word.verified ? '語源の接続を確認済み' : '語源接続は未確認（破線でStackへの所属を表示）'; detail.append(status);
  const headings = [['品詞・意味', Object.entries(word.meanings || {}).flatMap(([pos, meanings]) => [`${pos}：${Array.isArray(meanings) ? meanings.join('、') : meanings}`])], ['語の構成', (word.parts || []).map(p => `${p.form}：${p.meaning || ''}`)], ['派生語', (word.derivatives || []).map(d => `${d.word}：${d.meaning || ''}`)]];
  for (const [heading, values] of headings) {
    if (!values.length) continue;
    const h = document.createElement('h3'); h.textContent = heading; detail.append(h);
    const ul = document.createElement('ul');
    for (const value of values) { const li = document.createElement('li'); li.textContent = value; ul.append(li); }
    detail.append(ul);
  }
}
function renderInventory() {
  stackInventory.replaceChildren();
  const filtered = inventoryStacks.filter(s => (selectedChapter === 'all' || s.chapter === selectedChapter) && (selectedStack === 'all' || s.stack === selectedStack));
  const total = filtered.reduce((n,s) => n + s.words.length, 0);
  const linked = filtered.reduce((n,s) => n + s.words.filter(w => w.verified).length, 0);
  const heading = document.createElement('h2'); heading.textContent = `登録済み単語：${total}語（語源接続確認済み ${linked}語 / 要確認 ${total-linked}語）`; stackInventory.append(heading);
  const note = document.createElement('p'); note.textContent = 'すべてYAMLに登録された単語です。橙色は語源の接続が未確定の単語（破線はStack所属のみ）。クリックすると詳細を確認できます。'; stackInventory.append(note);
  for (const stack of filtered) {
    const group = document.createElement('div'); group.className = 'stack-group';
    const title = document.createElement('strong'); title.textContent = `Stack ${stack.stack}：${stack.main_word}（${stack.words.length}語）`; group.append(title);
    for (const word of stack.words) {
      const button = document.createElement('button'); button.type = 'button';
      button.className = `word-button${word.verified ? '' : ' unlinked'}`;
      button.textContent = word.word; button.addEventListener('click', () => showInventoryWord(word)); group.append(button);
    }
    stackInventory.append(group);
  }
}
refreshStackFilter();
let center = nodes.has('chapter-head:7') ? 'chapter-head:7' : nodes.has('part:ad') ? 'part:ad' : network.nodes[0]?.id;
function activeEdges() {
  return network.edges.filter(e => (selectedChapter === 'all' || String(e.chapter) === selectedChapter) && (selectedStack === 'all' || String(e.stack) === selectedStack));
}
function chapterStart(chapter) {
  const firstMain = network.edges.find(e => String(e.chapter) === chapter && e.role === 'main');
  return firstMain?.source || network.edges.find(e => String(e.chapter) === chapter)?.source || center;
}
const history = [];
let positions = new Map();
let dragging = null;
let panState = null;
function element(tag, attrs = {}) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}
function getSvgPoint(evt) {
  const p = svg.createSVGPoint(); p.x = evt.clientX; p.y = evt.clientY;
  return p.matrixTransform(svg.getScreenCTM().inverse());
}
function showNode(id) {
  const node = nodes.get(id); if (!node) return;
  detail.replaceChildren();
  const h = document.createElement('h2'); h.textContent = node.label; detail.append(h);
  const p = document.createElement('p'); p.textContent = node.type === 'unverified_word' ? '語源接続は未確認（この丸は単語であり、語根ではありません）' : `語根・接辞の意味：${node.meaning || '未登録'}`; detail.append(p);
  if (node.main_chapters?.length) {
    const ch = document.createElement('p');
    ch.textContent = `章の中心接頭辞：${node.main_chapters.map(c => `Chapter ${c}`).join('、')}`;
    detail.append(ch);
  }
  if (node.related_words?.some(item => selectedChapter === 'all' || String(item.chapter) === selectedChapter)) {
    const h3 = document.createElement('h3'); h3.textContent = '関連単語（単独語根）'; detail.append(h3);
    const ul = document.createElement('ul');
    for (const item of node.related_words.filter(item => selectedChapter === 'all' || String(item.chapter) === selectedChapter)) {
      const li = document.createElement('li'); li.textContent = `${item.word}：${item.meaning || '未登録'}`; ul.append(li);
    }
    detail.append(ul);
  }
}
function showWord(edge) {
  detail.replaceChildren();
  const h = document.createElement('h2'); h.textContent = edge.word || edge.label; detail.append(h);
  const p = document.createElement('p'); p.textContent = `意味：${edge.meaning || '未登録'}`; detail.append(p);
  const meta = document.createElement('p'); meta.textContent = `Chapter ${edge.chapter} / Stack ${edge.stack} / ${edge.role === 'main' ? 'メイン単語' : '関連単語'}`; detail.append(meta);
  if (edge.verified === false) { const note = document.createElement('p'); note.textContent = edge.note || '破線はStack所属のみを表します'; detail.append(note); }
  if (edge.parts?.length) {
    const h3 = document.createElement('h3'); h3.textContent = '語の構成'; detail.append(h3);
    const ul = document.createElement('ul');
    for (const part of edge.parts) { const li = document.createElement('li'); li.textContent = `${part.form}：${part.meaning || '未登録'}`; ul.append(li); }
    detail.append(ul);
  }
  if (edge.derivatives?.length) {
    const h3 = document.createElement('h3'); h3.textContent = '派生語'; detail.append(h3);
    const ul = document.createElement('ul');
    for (const item of edge.derivatives) { const li = document.createElement('li'); li.textContent = `${item.word}：${item.meaning || '未登録'}`; ul.append(li); }
    detail.append(ul);
  }
}
function moveTo(id) {
  if (!nodes.has(id) || id === center) return;
  history.push(center); center = id; draw();
}
function hiddenDerivedEdges() {
  const edges = activeEdges();
  const hidden = new Set();

  for (const relation of wordRelations) {
    const base = edges.find(e =>
      String(e.stack) === String(relation.stack) &&
      e.word.toLowerCase() === relation.base_word &&
      e.verified === true &&
      (e.source === center || e.target === center)
    );

    if (!base) continue;

    const derived = edges.find(e =>
      String(e.stack) === String(relation.stack) &&
      e.word.toLowerCase() === relation.derived_word &&
      e.verified === false
    );

    if (derived) hidden.add(derived);
  }

  return hidden;
}
function getVisible() {
  const adjacent = new Set();
  const hidden = hiddenDerivedEdges();

  for (const edge of activeEdges()) {
    if (hidden.has(edge)) continue;

    if (edge.source === center) adjacent.add(edge.target);
    if (edge.target === center) adjacent.add(edge.source);
  }

  return new Set([center, ...adjacent]);
}
function draw() {
  svg.replaceChildren(); positions = new Map();
  if (!center) { currentLabel.textContent = 'ノードがありません'; return; }
  currentLabel.textContent = `中心：${nodes.get(center).label}`;
  backButton.disabled = history.length === 0;
  showNode(center);
  renderInventory();
  const visible = getVisible();
  const adjacent = [...visible].filter(id => id !== center).sort();
  const cx = 500, cy = 350;
  positions.set(center, [cx, cy]);
  const count = adjacent.length;
  const radius = Math.max(360, count * 65);
  adjacent.forEach((id, i) => {
    const angle = 2 * Math.PI * i / Math.max(count, 1) - Math.PI / 2;
    positions.set(id, [cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)]);
  });
  const margin = 230;
  const half = Math.max(350, radius + margin);
  svg.setAttribute('viewBox', `${cx-half} ${cy-half} ${half*2} ${half*2}`);
  const hidden = hiddenDerivedEdges();
  const visibleEdges = activeEdges().filter(e =>
    !hidden.has(e) &&
    (
      (e.source === center && visible.has(e.target)) ||
      (e.target === center && visible.has(e.source))
    )
  );
  // 同じ2ノードを結ぶ複数の単語を重ねず、すべて見えるようにする。
  // 並行線の順番は固定し、ドラッグしてもラベルと線を一緒に移動する。
  const parallelGroups = new Map();
  const labelPlacements = [];
  // Keep labels outside node circles and away from previously placed labels.
  function overlaps(a, b, pad = 6) {
    return a.x < b.x + b.w + pad && a.x + a.w + pad > b.x &&
           a.y < b.y + b.h + pad && a.y + a.h + pad > b.y;
  }
  function placeEdgeLabels(edge, a, b, c, d, offset, label, meaningLabel) {
    const vx = c - a, vy = d - b;
    const dist = Math.hypot(vx, vy) || 1;
    const nx = -vy / dist, ny = vx / dist;
    const baseT = 0.5;
    const wordW = Math.max(75, (edge.label || '').length * 13);
    const meaningW = Math.max(60, ((edge.meaning || '').split(' / ')[0]).length * 18);
    const width = Math.max(wordW, meaningW) + 16;
    const height = 58;
    const blockers = [...positions.values()].map(([px, py]) => ({
        x: px-100, y: py-100, w: 200, h: 220
    }));
    let best = null, bestScore = Infinity;
    // Prefer the midpoint; try different positions along and across the line.
    for (const t of [baseT, 0.40, 0.60, 0.30, 0.70, 0.22, 0.78]) {
      for (const shift of [0, -28, 28, -56, 56, -90, 90, -125, 125]) {
        const x = a + vx*t + nx*(offset+shift);
        const y = b + vy*t + ny*(offset+shift);
        const rect = {x:x-width/2,y:y-29,w:width,h:height};
        const collisions = blockers.reduce((n,r) => n+(overlaps(rect,r,10)?1:0),0)*1000 +
          labelPlacements.reduce((n,r) => n+(overlaps(rect,r,7)?1:0),0)*500;
        const score = collisions + Math.abs(t-0.5)*90 + Math.abs(shift)*0.5;
        if (score < bestScore) {bestScore=score;best={x,y,rect};}
        if (score === 0) break;
      }
    }
    labelPlacements.push(best.rect);
    label.setAttribute('x',best.x);
    label.setAttribute('y',best.y-8);
    meaningLabel.setAttribute('x',best.x);
    meaningLabel.setAttribute('y',best.y+17);
  }
  for (const edge of visibleEdges) {
    const key = [edge.source, edge.target].sort().join('||');
    if (!parallelGroups.has(key)) parallelGroups.set(key, []);
    parallelGroups.get(key).push(edge);
  }
  const parallelOffsets = new Map();
  for (const group of parallelGroups.values()) {
    group.forEach((edge, index) => parallelOffsets.set(edge, (index - (group.length - 1) / 2) * 65));
  }
  for (const edge of visibleEdges) {
    const [x1, y1] = positions.get(edge.source), [x2, y2] = positions.get(edge.target);
    const g = element('g', {class: 'word-edge'});
    const line = element('line', {x1, y1, x2, y2, stroke: edge.verified === false ? '#e8a65c' : (edge.role === 'main' ? '#4a80c4' : '#9baec7'), 'stroke-width': edge.role === 'main' ? 3.5 : 2.5, ...(edge.verified === false ? {'stroke-dasharray':'7 5'} : {})});
    g.append(line);
    const label = element('text', {'text-anchor': 'middle', 'font-size': '22', 'font-weight': edge.role === 'main' ? '700' : '500', fill: '#284a73', 'paint-order': 'stroke', stroke: 'white', 'stroke-width': '5', 'stroke-linejoin': 'round'});
    label.textContent = edge.label;
    g.append(label);
    const meaningLabel = element('text', {'text-anchor': 'middle', 'font-size': '17', fill: '#51657c', 'paint-order': 'stroke', stroke: 'white', 'stroke-width': '4', 'stroke-linejoin': 'round'});
    meaningLabel.textContent = (edge.meaning || '').split(' / ')[0];
    meaningLabel.style.cursor = 'pointer';
    meaningLabel.addEventListener('click', () => showWord(edge));
    g.append(meaningLabel);
    const hit = element('line', {x1, y1, x2, y2, stroke: 'transparent', 'stroke-width': 22, style: 'cursor:pointer'});
    g.append(hit);
    const update = () => {
      const [a, b] = positions.get(edge.source), [c, d] = positions.get(edge.target);
      const distance = Math.hypot(d - b, c - a) || 1;
      // 垂直方向にずらすことで同一ノード間の単語ラベルが隠れない。
      const offset = parallelOffsets.get(edge) || 0;
      const dx = -(d - b) / distance * offset;
      const dy = (c - a) / distance * offset;
      line.setAttribute('x1', a + dx); line.setAttribute('y1', b + dy);
      line.setAttribute('x2', c + dx); line.setAttribute('y2', d + dy);
      hit.setAttribute('x1', a + dx); hit.setAttribute('y1', b + dy);
      hit.setAttribute('x2', c + dx); hit.setAttribute('y2', d + dy);
      placeEdgeLabels(edge, a, b, c, d, offset, label, meaningLabel);
    };
    g.updatePosition = update; update();
    hit.addEventListener('click', () => showWord(edge));
    label.style.cursor = 'pointer'; label.addEventListener('click', () => showWord(edge));
    svg.append(g);
  }
    // 既存単語を構成要素に含む関連語を補助表示する
    // 既存単語から派生した関連語を表示
  for (const relation of wordRelations) {
    if (selectedChapter !== 'all' &&
        String(relation.chapter) !== selectedChapter) continue;

    if (selectedStack !== 'all' &&
        String(relation.stack) !== selectedStack) continue;

    const baseEdge = visibleEdges.find(e =>
      String(e.stack) === String(relation.stack) &&
      e.word.toLowerCase() === relation.base_word &&
      e.verified === true
    );

    if (!baseEdge) continue;

    const derivedEdge = activeEdges().find(e =>
      String(e.stack) === String(relation.stack) &&
      e.word.toLowerCase() === relation.derived_word
    );

    if (!derivedEdge || derivedEdge.verified !== false) continue;

    const group = element('g', {class: 'word-relation'});

    const line = element('line', {
      stroke: '#059669',
      'stroke-width': 2.5
    });

    const rect = element('rect', {
      width: Math.max(125, relation.derived_word.length * 9 + 24),
      height: 34,
      rx: 9,
      fill: '#d1fae5',
      stroke: '#059669',
      'stroke-width': 1.5
    });

    const label = element('text', {
      'text-anchor': 'middle',
      'font-size': 13,
      'font-weight': 600,
      fill: '#065f46',
      style: 'cursor:pointer'
    });

    label.textContent = relation.derived_word;

    const openDetail = () => showWord(derivedEdge);

    rect.style.cursor = 'pointer';
    rect.addEventListener('click', openDetail);
    label.addEventListener('click', openDetail);

    group.append(line, rect, label);
    svg.append(group);

    const update = () => {
      const a = positions.get(baseEdge.source);
      const b = positions.get(baseEdge.target);

      if (!a || !b) return;

      const mx = (a[0] + b[0]) / 2;
      const my = (a[1] + b[1]) / 2;

      const targetX = mx;
      const targetY = my + 90;

      line.setAttribute('x1', mx);
      line.setAttribute('y1', my + 15);
      line.setAttribute('x2', targetX);
      line.setAttribute('y2', targetY - 17);

      const width = Number(rect.getAttribute('width'));

      rect.setAttribute('x', targetX - width / 2);
      rect.setAttribute('y', targetY - 17);

      label.setAttribute('x', targetX);
      label.setAttribute('y', targetY + 5);
    };

    group.updatePosition = update;
    update();
  }
  for (const [id, [x, y]] of positions) {
    const node = nodes.get(id);
    const g = element('g', {class: `node${id === center ? ' center' : ''}${node.main_chapters?.length ? ' chapter-main' : ''}${node.type === 'unverified_word' ? ' unverified-word' : ''}`, transform: `translate(${x},${y})`, style: 'cursor:grab;touch-action:none'});
    const circle = element('circle', {r: id === center ? 85 : 75});
    g.append(circle);
    const label = element('text', {class: 'node-label', 'text-anchor': 'middle', 'font-size': node.variants?.length ? '12' : '15', 'font-weight': '700', 'pointer-events': 'none'});
    const rawNodeLabel = String(node.label || '');
    const circleRadius = id === center ? 85 : 75;
    // SVG text is not automatically wrapped; split at separators, shrink long labels.
    const parts = rawNodeLabel.split(/\s*\/\s*/).filter(Boolean);
    const rows = parts.length > 1 ? (() => {
      const result = []; let line = '';
      for (const part of parts) {
        const next = line ? `${line} / ${part}` : part;
        if (next.length > 11 && line) { result.push(line); line = part; }
        else line = next;
      }
      if (line) result.push(line);
      return result;
    })() : [rawNodeLabel];
    const maxChars = Math.max(...rows.map(t => t.length),1);
    const fontSize = Math.min(26, Math.max(10, (circleRadius*1.55)/(maxChars*0.61)));
    label.setAttribute('font-size', String(fontSize));
    rows.forEach((text, index) => {
      const tspan = element('tspan', {x:0,dy:index===0?0:fontSize*1.18});
      tspan.textContent=text; label.append(tspan);
    });
    label.setAttribute('y', String(-(rows.length-1)*fontSize*0.59));
    g.append(label);
    const meaningLabel = element('text', {'text-anchor': 'middle', 'font-size': '17', 'pointer-events': 'none', fill: '#475569', y: id === center ? 103 : 93});
    meaningLabel.textContent = (node.meaning || '').split(/[、，,/]/)[0];
    g.append(meaningLabel);
    g.addEventListener('pointerdown', evt => {
      if (evt.button !== 0) return;
      const p = getSvgPoint(evt);
      dragging = {id, pointerId: evt.pointerId, startX: p.x, startY: p.y, lastX: p.x, lastY: p.y, moved: false};
      g.setPointerCapture(evt.pointerId);
    });
    g.addEventListener('pointermove', evt => {
      if (!dragging || dragging.id !== id || dragging.pointerId !== evt.pointerId) return;
      const p = getSvgPoint(evt);
      if (Math.hypot(p.x - dragging.startX, p.y - dragging.startY) > 5) dragging.moved = true;
      if (!dragging.moved) return;
      const [oldX, oldY] = positions.get(id);
      const nx = oldX + p.x - dragging.lastX, ny = oldY + p.y - dragging.lastY;
      positions.set(id, [nx, ny]); g.setAttribute('transform', `translate(${nx},${ny})`);
      dragging.lastX = p.x; dragging.lastY = p.y;
      labelPlacements.length = 0;
      for (const e of svg.querySelectorAll('.word-edge, .word-relation')) {
        e.updatePosition();
      }
    });
    g.addEventListener('pointerup', evt => {
      if (!dragging || dragging.pointerId !== evt.pointerId) return;
      const moved = dragging.moved; dragging = null;
      if (!moved) showNode(id);
    });
    g.addEventListener('pointercancel', () => { dragging = null; });
    g.addEventListener('dblclick', evt => { evt.preventDefault(); moveTo(id); });
    svg.append(g);
  }
}
function getViewBox() { const v = svg.viewBox.baseVal; return {x:v.x,y:v.y,width:v.width,height:v.height}; }
function setViewBox(v) { svg.setAttribute('viewBox', `${v.x} ${v.y} ${v.width} ${v.height}`); }
svg.addEventListener('pointerdown', evt => {
  if (evt.target !== svg || evt.button !== 0) return;
  const p = getSvgPoint(evt); panState = {pointerId:evt.pointerId,x:p.x,y:p.y}; svg.setPointerCapture(evt.pointerId);
});
svg.addEventListener('pointermove', evt => {
  if (!panState || panState.pointerId !== evt.pointerId) return;
  const p = getSvgPoint(evt), v = getViewBox();
  setViewBox({...v,x:v.x + panState.x-p.x,y:v.y + panState.y-p.y});
});
svg.addEventListener('pointerup', evt => { if (panState?.pointerId === evt.pointerId) panState = null; });
svg.addEventListener('pointercancel', evt => { if (panState?.pointerId === evt.pointerId) panState = null; });
chapterFilter.addEventListener('change', () => {
  selectedChapter = chapterFilter.value;
  history.length = 0;
  selectedStack = 'all'; refreshStackFilter();
  if (selectedChapter !== 'all') center = chapterStart(selectedChapter);
  draw();
});
stackFilter.addEventListener('change', () => { selectedStack = stackFilter.value; history.length = 0; if (selectedStack !== 'all' && nodes.has(`stack-root:${selectedStack}`)) center = `stack-root:${selectedStack}`; else if (selectedChapter !== 'all') center = chapterStart(selectedChapter); draw(); });
backButton.addEventListener('click', () => { if (!history.length) return; center = history.pop(); draw(); });
function searchNodes() {
  const q = searchInput.value.trim().toLowerCase(); searchResults.replaceChildren();
  const placeholder = document.createElement('option'); placeholder.value = ''; placeholder.textContent = '検索結果を選択'; searchResults.append(placeholder);
  if (!q) return;
  const allowed = new Set(activeEdges().flatMap(e => [e.source, e.target]));
  const matches = [...nodes.values()].filter(n => allowed.has(n.id) && n.label.toLowerCase().includes(q)).sort((a,b) => a.label.localeCompare(b.label));
  for (const node of matches) { const o = document.createElement('option'); o.value = node.id; o.textContent = `${node.label}（語根・接辞）`; searchResults.append(o); }
  placeholder.textContent = matches.length ? `${matches.length}件見つかりました` : '該当なし';
}
searchButton.addEventListener('click', searchNodes);
searchInput.addEventListener('keydown', evt => { if (evt.key === 'Enter') searchNodes(); });
searchResults.addEventListener('change', () => { if (searchResults.value) { moveTo(searchResults.value); showNode(searchResults.value); } });
draw();

const params = new URLSearchParams(window.location.search);
const targetChapter = params.get('chapter');
const targetStack = params.get('stack');
const targetWord = params.get('word');

if (targetChapter && targetStack && targetWord) {
  if (chapters.includes(targetChapter)) {
    selectedChapter = targetChapter;
    chapterFilter.value = targetChapter;

    selectedStack = targetStack;
    refreshStackFilter();

    const edge = activeEdges().find(e =>
      e.word === targetWord
    );

    if (edge) {
      center = edge.source;
      draw();
      showWord(edge);
    } else {
      const stack = inventoryStacks.find(s =>
        String(s.chapter) === targetChapter &&
        String(s.stack) === targetStack
      );

      const word = stack?.words.find(w =>
        w.word === targetWord
      );

      center = nodes.has(`stack-root:${targetStack}`)
        ? `stack-root:${targetStack}`
        : chapterStart(targetChapter);

      draw();

      if (word) showInventoryWord(word);
    }
  }
}
