// 12A猫 盤面別勝率：data/d<人数>.json を読み、左に盤面の一覧、右に選んだ盤面（#3-12 のような URL）を wiki ふうに出す
(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const val = (s) => { const [a, b] = String(s).split('/'); return b ? a / b : +a; };
  const pct = (s) => (val(s) * 100).toFixed(1) + '%';
  const fr = (s) => (String(s).includes('/') && String(s).length <= 9 ? `（${s}）` : '');
  const DAYS = [3, 4, 5];
  const D = {};
  const LEGEND = '<div class="legend sm"><b>記号</b>　霊＝霊能CO者、猫＝猫又CO者、ギ＝ギドラ（「狩人か猫又」とCOした人）、狩＝狩人CO者、灰＝グレー（今は占いの白黒は使わない）。'
    + 'w＝狼、k＝狂人（1w1k生存＝狼1人と狂人が生きている）。（狩生存）＝灰の中に狩人がいる、（猫生存）＝灰の中に猫又がいる。'
    + '内訳の 真＝本物・狂＝狂人・狼＝狼（例：猫真狂＝猫COの2人が本物と狂人）。ギの内訳は 狩＝本物の狩人・猫＝本物の猫又（例：ギ狩狼）。猫COが1人なら本物。</div>';
  // 盤面の並び：霊→猫（ギ）→狩→灰 の数の多い順
  const cnt = (b, l) => b.filter((x) => x === l).length;
  const order = (a, b) => {
    const k = (x) => [cnt(x.board, '霊'), cnt(x.board, '猫') + cnt(x.board, 'ギ'), cnt(x.board, '狩'), cnt(x.board, '灰')];
    const ka = k(a), kb = k(b);
    for (let i = 0; i < 4; i++) if (ka[i] !== kb[i]) return kb[i] - ka[i];
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
    let h = '<h1 class="pt">12A猫 盤面別勝率</h1><p>盤面（生きている人の見た目）を選ぶと、生存状況ごとに、<b>村はどう投票すればよいか</b>と、そのときの村勝率が内訳ごとに出ます。投票は一人ひとりの視点（自分の役しか分からない）で考えています。</p>' + LEGEND;
    for (const n of DAYS) {
      if (!D[n]) continue;
      h += `<h2>${n}人日（${D[n].length}盤面）</h2><ul class="blist">`;
      for (const b of D[n]) h += `<li><a href="#${n}-${b.id}">${esc(b.board.join(','))}</a><span class="v">${pct(b.v)}</span></li>`;
      h += '</ul>';
    }
    h += `<h2 id="rules">前提</h2><ul>
<li>配役：占い・霊能・狩人・猫又・狂人・狼3・村人4（12A猫）。今は占いの白黒を使わず、霊能CO・猫又CO・ギドラCO・狩人CO・灰の組み合わせだけを扱う（占い師は死亡している扱い）。ギドラは猫又CO・狩人COと同じ盤面には出ない。ギドラは2人以上で出すCOなので、ギが1人だけの盤面はない。ギドラが出ているときは、生きている本物の狩人・猫又はギドラに加わっているので、灰に狩人・猫又はいない。</li>
<li>猫又は役欠けがない（初日犠牲者にならない）。猫又COが1人で、それまでに道連れや猫噛みの死者が出ていなければ本物で確定。2人以上なら1人が本物、残りは狂人か狼。霊COが1人、狩COが1人のときも本物とする（偽のCOには本物が対抗する）。</li>
<li>COの正体：霊＝本物／狂人／狼、狩＝本物／狂人／狼、ギ＝狩人／猫又／狂人／狼。灰に残った霊能者はいない扱い。狩人COが出ているときは、本物の狩人が灰に潜伏していることはない（偽の狩人COには本物が対抗する）。</li>
<li>4・5人日：村の進め方の候補（昼に指定する区分の順、指定するか各自ランダムに入れるか、本物のCO者は対抗に入れるか、狩人の護衛先、GJの翌朝に狩人がCOするか）をすべて試し、それぞれに狼と狂人が自分の視点で最善を返したときに一番勝てるものを選ぶ。人外の最善は、交互に手を良くする探索（やり直し15回）で求めている（3人日ではすべての手を試した結果と一致することを確かめた）。夜は狩人が護衛（連続護衛あり）、狼が噛む（見分けのつかない人からはランダム）。本物の猫又を噛むと狼がランダムに1人死ぬ。GJの翌朝に狩人がCOすると、狩人と護衛先（白）が見た目に出る。</li>
<li>3人日は狼1人（狼2人なら決着済み）。吊りは投票：生きている全員が自分以外の1人に入れ、最多票の人が吊られる（同票なら同票の人からランダム）。狼を吊れば村の勝ち、人間を吊れば狼の勝ち。本物の猫又が吊られると、残りからランダムに1人を道連れにする（狼なら村の勝ち）。</li>
<li>視点：生存状況（1狼1狂生存・（狩生存）など）は全員が知っている。誰がどの役かは自分の役しか分からない（狼は狂人を、狂人は狼を知らない）。</li>
<li>表記：w＝狼、k＝狂人。1w1k生存＝狼1人と狂人が生きている。</li>
<li>村（村人・狩人・猫又・霊能者）は、盤面ごとに、見た目と自分の役から誰に入れるかを前もって1つ決める（1/2ずつなど確率で混ぜてもよい）。狼と狂人は、それを知ったうえで、自分から見える情報で村勝率が一番低くなる投票をする（2人で一番悪い組み合わせ）。村はその最悪に対して、すべての内訳の平均で一番勝てる決め方を選ぶ。内訳の重みは役の札（村人4・狼3・ほか1枚ずつ）の数から。</li>
</ul>`;
    return h;
  }

  // 数式（KaTeX）。読み込めなければ文字のまま
  const tex = (t, plain) => (window.katex ? katex.renderToString(t, { throwOnError: false }) : esc(plain || t));
  const fx = (s) => { const [a, b] = String(s).split('/'); return b ? `\\tfrac{${a}}{${b}}` : a; };
  const CIRC = '①②③④⑤⑥⑦⑧⑨⑩';
  // 分数のかけ算（文字列の分数どうし）
  const gcd = (a, b) => (b ? gcd(b, a % b) : a);
  const mul = (x, y) => {
    const [a, b = '1'] = String(x).split('/'), [c, d = '1'] = String(y).split('/');
    let n = BigInt(a) * BigInt(c), m = BigInt(b) * BigInt(d);
    const big = (p, q) => (q === 0n ? p : big(q, p % q));
    const g = big(n < 0n ? -n : n, m); if (g > 1n) { n /= g; m /= g; }
    return m === 1n ? String(n) : `${n}/${m}`;
  };

  function termTex(t) {
    const fs = t.f.map((x) => fx(x[1]));
    if (t.o && t.o[0] === '猫飛び') fs.push(fx(t.o[1]));
    if (t.o && t.o[0] === 'ランダム') fs.push('\\left(' + t.o[1].map((x) => (x[0] === '狼' ? fx(x[1]) : `${fx(x[1])}\\times${fx(x[2])}`)).join('+') + '\\right)');
    if (fs.length === 1 && !t.o) return fs[0];
    return (fs.length ? fs.join('\\times') : '1') + ' = ' + fx(t.v);
  }
  function termWords(t) {
    const w = t.f.map((x) => x[0]);
    if (t.o && t.o[0] === '猫飛び') w.push('猫飛び（道連れが狼）');
    if (t.o && t.o[0] === 'ランダム') w.push('同票のランダム（' + t.o[1].map((x) => (x[0] === '狼' ? '狼が吊られる' : '猫又が吊られて道連れが狼')).join('、') + '）');
    return w.length ? w.join(' × ') : '必ず狼が吊られる';
  }

  function page(n, b) {
    // wiki（ゲヘナのwiki）の書き方を、番号・改行・数式で見やすくしたもの
    let h = `<h1 class="pt">${esc(b.board.join(','))}<span class="day">${n}人日</span></h1>` + LEGEND;
    h += `<div class="headline"><div>村の最善の投票：<b>${esc(b.plan)}</b></div><div>村勝率（すべての内訳の平均）：${tex(fx(b.v), b.v)} <span class="sm">${pct(b.v)}</span></div>`
      + (b.plana ? `<div class="sm">比較：${esc(b.plana)} → ${esc(b.va)}（${pct(b.va)}）</div>` : '') + '</div>';
    h += '<nav class="toc"><b>目次</b><ol>' + b.secs.map((s, i) => `<li><a href="#${n}-${b.id}-c${i + 1}">${esc(s.title)}</a></li>`).join('') + `<li><a href="#${n}-${b.id}-sum">まとめ</a></li></ol></nav>`;
    b.secs.forEach((s, si) => {
      h += `<h2 id="c${si + 1}">${esc(s.title)}<span class="day">この盤面の ${pct(s.share)}</span></h2>`;
      h += '<table class="cmp"><thead><tr><th>村の投票</th><th>村勝率</th></tr></thead><tbody>';
      s.items.forEach((it, k) => {
        h += `<tr class="${it.best ? 'best' : ''}"><td>${CIRC[k]} ${esc(it.plan)}${it.best ? ' <span class="tag">最善</span>' : ' <span class="tag gray">比較</span>'}</td><td class="n">${tex(fx(it.v), it.v)} <span class="sm">${pct(it.v)}</span></td></tr>`;
      });
      h += '</tbody></table>';
      s.items.forEach((it, k) => {
        h += `<h3>${CIRC[k]} ${esc(it.plan)}なら</h3>`;
        if (it.paths) {
          h += '<ol class="terms">' + it.paths.map(([lab, p, v]) => `<li><span class="tw">${esc(lab)}</span>：<span class="tm">${tex(`${fx(p)}\\times${fx(v)} = ${fx(mul(p, v))}`)}</span></li>`).join('') + '</ol>';
          if (it.paths.length > 1) h += `<p class="total">合計 ${tex(it.paths.map(([, p, v]) => fx(mul(p, v))).filter((x) => x !== '0').join('+') + ' = ' + fx(it.v))}</p>`;
          return;
        }
        if (it.fixed.length) h += `<p class="sm">固定の票：${esc(it.fixed.join('、'))}（人外がいつもこの人に入れる）</p>`;
        if (!it.terms.length) { h += `<p>村勝ちになる票の入り方はない → ${tex('0')}</p>`; return; }
        h += '<ol class="terms">' + it.terms.map((t) => `<li><span class="tw">${esc(termWords(t))}</span>：<span class="tm">${tex(termTex(t))}</span></li>`).join('') + '</ol>';
        if (it.terms.length > 1) h += `<p class="total">合計 ${tex(it.terms.map((t) => fx(t.v)).join('+') + ' = ' + fx(it.v))}</p>`;
      });
    });
    h += `<h2 id="sum">まとめ</h2><table class="cmp"><thead><tr><th>生存状況</th><th>割合</th><th>最善</th>${b.plana ? '<th>比較</th>' : ''}</tr></thead><tbody>`;
    for (const x of b.summ) h += `<tr><td>${esc(x.sit)}</td><td class="n sm">${pct(x.share)}</td><td class="n">${tex(fx(x.v), x.v)} <span class="sm">${pct(x.v)}</span></td>${b.plana ? `<td class="n">${tex(fx(x.va), x.va)} <span class="sm">${pct(x.va)}</span></td>` : ''}</tr>`;
    h += `<tr class="best"><td><b>平均</b></td><td></td><td class="n">${tex(fx(b.v), b.v)} <span class="sm">${pct(b.v)}</span></td>${b.plana ? `<td class="n">${tex(fx(b.va), b.va)} <span class="sm">${pct(b.va)}</span></td>` : ''}</tr></tbody></table>`;
    h += `<p class="sm">最善：${esc(b.plan)}<br>${b.plana ? '比較：' + esc(b.plana) : ''}</p>`;
    h += '<p class="sm">読み方：「狼が真猫に入れる」などはその票が入る確率。猫飛び＝吊られた本物の猫又の道連れが狼に当たる確率。同票のランダム＝同票の人から吊りをくじで決めるときの、村が勝つ確率。固定の票＝人外がいつも同じ人に入れること。最善＝村は生存状況も内訳も分からないので、この盤面のすべての内訳を平均して一番勝てる投票の仕方（1つの内訳だけを見ると比較の方が高いこともある）。比較＝「全部入れる／1/2ずつ」の投票の仕方で、最善と違うもののうち一番よいもの。</p>';
    return h;
  }

  function route() {
    const m = location.hash.match(/^#(\d+)-(\d+)(?:-((?:c\d+)|sum))?$/);
    if (m && D[+m[1]]) {
      const n = +m[1], i = +m[2], b = D[n].find((x) => x.id === i);
      if (b) { side({ n, i }); $('#page').innerHTML = page(n, b); const el = m[3] && document.getElementById(m[3]); if (el) el.scrollIntoView(); else window.scrollTo(0, 0); document.title = `${n}人日 ${b.board.join(',')} - 12A猫 盤面別勝率`; return; }
    }
    side(null); $('#page').innerHTML = top(); document.title = '12A猫 盤面別勝率';
    if (location.hash === '#rules') setTimeout(() => { const el = document.getElementById('rules'); if (el) el.scrollIntoView(); }, 0);
  }
  $('#totop').addEventListener('click', (e) => { e.preventDefault(); window.scrollTo(0, 0); });
  window.addEventListener('hashchange', route);
  Promise.all(DAYS.map((n) => fetch(`data/d${n}.json`).then((r) => (r.ok ? r.json() : null)).then((d) => {
    if (!d) return;
    d.sort(order); d.forEach((b, i) => { b.id = i + 1; }); D[n] = d;
  }).catch(() => {}))).then(route);
})();
