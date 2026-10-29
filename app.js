// 12A猫 盤面別勝率：data/d<人数>.json を読み、左に盤面の一覧、右に選んだ盤面（#3-12 のような URL）を wiki ふうに出す
(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const val = (s) => { const [a, b] = String(s).split('/'); return b ? a / b : +a; };
  const pct = (s) => (val(s) * 100).toFixed(1) + '%';
  const fr = (s) => (String(s).includes('/') && String(s).length <= 9 ? `（${s}）` : '');
  const DAYS = [3];
  const D = {};
  const LEGEND = '<div class="legend sm"><b>記号</b>　霊＝霊能CO者、狩＝狩人CO者、ギ＝ギドラ（「狩人か猫又」とCOした人）、猫＝猫又CO者、灰＝グレー（今は占いの白黒は使わない）。'
    + '1狼1狂生存＝狼1人と狂人が生きている。（狩生存）＝灰の中に狩人がいる、（猫生存）＝灰の中に猫又がいる。'
    + '内訳の 真＝本物・狂＝狂人・狼＝狼（例：霊真狂＝霊能CO者2人が本物と狂人）。ギの内訳は 狩＝本物の狩人・猫＝本物の猫又（例：ギ狩狼）。猫COが1人なら本物（下の前提）。</div>';
  // 盤面の並び：占い→霊能→狩人→猫又→灰 の数の多い順
  const cnt = (b, l) => b.filter((x) => x === l).length;
  const order = (a, b) => {
    for (const l of ['占', '霊', '狩', 'ギ', '猫', '灰']) { const d = cnt(b.board, l) - cnt(a.board, l); if (d) return d; }
    return a.board.join(',') < b.board.join(',') ? -1 : 1;
  };

  function side(cur) {
    let h = '<div class="mb"><div class="mh">メニュー</div><a href="#">トップページ</a><a href="#rules">前提</a></div>';
    for (const n of DAYS) {
      if (!D[n]) continue;
      const open = cur && cur.n === n ? ' open' : '';
      h += `<details class="mb"${open}><summary class="mh">${n}人日（${D[n].length}）</summary><ul>`;
      D[n].forEach((b, i) => { h += `<li><a href="#${n}-${b.id}"${cur && cur.n === n && cur.i === b.id ? ' class="cur"' : ''}>${esc(b.board.join(','))}</a></li>`; });
      h += '</ul></details>';
    }
    $('#side').innerHTML = h;
  }

  function top() {
    let h = '<h1 class="pt">12A猫 盤面別勝率</h1><p>盤面（生きている人の見た目）を選ぶと、内訳ごとに<b>どの区分を吊るとどれだけ勝てるか</b>と、村から見た最善の吊り先が出ます。</p>' + LEGEND;
    for (const n of DAYS) {
      if (!D[n]) continue;
      h += `<h2>${n}人日（${D[n].length}盤面）</h2><table class="bl"><tbody>`;
      for (const b of D[n]) {
        const top = Math.max(...Object.values(b.avg).map(val));
        const bs = Object.keys(b.avg).filter((c) => Math.abs(val(b.avg[c]) - top) < 1e-12);
        h += `<tr><td><a href="#${n}-${b.id}">${esc(b.board.join(','))}</a></td><td class="sm">${esc(bs.join('・'))}を吊る</td><td class="n">${pct(b.avg[bs[0]])}</td></tr>`;
      }
      h += '</tbody></table>';
    }
    h += `<h2 id="rules">前提</h2><ul>
<li>配役：占い・霊能・狩人・猫又・狂人・狼3・村人4（12A猫）。今は占いの白黒を使わず、霊能CO・狩人CO・ギドラCO・猫又CO・灰の組み合わせだけを扱う（占い師は死亡している扱い）。</li>
<li>猫又は役欠けがない（初日犠牲者にならない）。猫又COが1人で、それまでに道連れや猫噛みの死者が出ていなければ、その猫又は本物で確定。2人以上いれば1人が本物、残りは狂人か狼。</li>
<li>ギ（ギドラ）＝本物の狩人・猫又が「狩人か猫又」とCOしたもの（狂人・狼が混ざることもある）。灰に残った霊能者はいない扱い。</li>
<li>3人日は狼1人（狼2人なら決着済み）。その日の吊りで狼を吊れば村の勝ち、人間を吊れば狼の勝ち。本物の猫又を吊ると、残りからランダムに1人を道連れにする（狼なら村の勝ち）。PP は5人日以上なので3人日には起きない。</li>
<li>村は見た目しか分からないので、吊る区分（灰・白・猫…）を1つ決め、区分の中からランダムに吊る。内訳ごとの値は、その区分を吊ったときの厳密な村勝率。</li>
<li>COの真偽：霊＝本物／狂人／狼、狩＝本物／狂人／狼、ギ＝狩人／猫又／狂人／狼。</li>
<li>「平均」と「最善の吊り先」：役の札（村人4・狼3・霊能・狩人・猫又・狂人1枚ずつ）から生き残りが選ばれたとする重みで、ありうる内訳を平均したもの。CO者が本物か偽物かの見込みはこの重みで決まるので、実戦の読みで変わる。</li>
</ul>`;
    return h;
  }

  function page(n, b) {
    let h = `<h1 class="pt">${esc(b.board.join(','))}<span class="day">${n}人日</span></h1>` + LEGEND;
    h += '<h2>まとめ</h2><ul class="arrow">';
    const cls = Object.keys(b.avg).sort((x, y) => val(b.avg[y]) - val(b.avg[x]));
    const top = Math.max(...cls.map((c) => val(b.avg[c])));
    for (const c of cls) h += `<li>${esc(c)}を吊る → ${pct(b.avg[c])}${fr(b.avg[c])}${Math.abs(val(b.avg[c]) - top) < 1e-12 ? ' <b>← 最善</b>' : ''}</li>`;
    h += '</ul><p class="sm">平均は役の札の数からの重み。下の内訳ごとの値はこの重みによらない。</p>';
    const sits = [];
    for (const c of b.cases) if (!sits.includes(c.sit)) sits.push(c.sit);
    for (const s of sits) {
      h += `<h2>${esc(s)}</h2>`;
      for (const c of b.cases.filter((x) => x.sit === s)) {
        const vs = cls.map((k) => {
          const v = c.vals[k];
          return `${esc(k)}を吊る → ${val(v) === 1 ? '<b>村勝ち</b>' : val(v) === 0 ? '狼勝ち' : pct(v) + fr(v)}`;
        });
        h += `<h3>${esc(c.det || '内訳')}<span class="sm">（この盤面の ${pct(c.share)}）</span></h3><ul class="arrow">${vs.map((x) => `<li>${x}</li>`).join('')}</ul>`;
      }
    }
    return h;
  }

  function route() {
    const m = location.hash.match(/^#(\d+)-(\d+)$/);
    if (m && D[+m[1]]) {
      const n = +m[1], i = +m[2], b = D[n].find((x) => x.id === i);
      if (b) { side({ n, i }); $('#page').innerHTML = page(n, b); window.scrollTo(0, 0); document.title = `${n}人日 ${b.board.join(',')} - 12A猫 盤面別勝率`; return; }
    }
    side(null); $('#page').innerHTML = top(); document.title = '12A猫 盤面別勝率';
    if (location.hash === '#rules') setTimeout(() => { const el = document.getElementById('rules'); if (el) el.scrollIntoView(); }, 0);
  }
  $('#totop').addEventListener('click', (e) => { e.preventDefault(); window.scrollTo(0, 0); });
  window.addEventListener('hashchange', route);
  Promise.all(DAYS.map((n) => fetch(`data/d${n}.json`).then((r) => r.json()).then((d) => {
    d.sort(order); d.forEach((b, i) => { b.id = i + 1; }); D[n] = d;
  }))).then(route);
})();
