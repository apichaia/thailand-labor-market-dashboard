"""Small visual effects: numbers on the cards count up, and (only when the viewer switches it on) soft click sounds.

Everything runs in the browser. Sound is OFF by default, is synthesised with the Web Audio API (no audio files) and is
only ever played after the viewer's own click, which is what browsers require. Viewers whose system asks for reduced
motion get the final numbers immediately."""
from __future__ import annotations

import streamlit as st

_JS = r"""
export default function(component) {
    const { data } = component;
    const w = window;
    w.__lmFx = w.__lmFx || { sound: false, ctx: null, lastChime: 0, installed: false };
    const fx = w.__lmFx;
    fx.sound = !!(data && data.sound);
    document.documentElement.classList.toggle('lm-dark', !!(data && data.dark));
    fx.help = (data && data.help) || {};
    fx.helpKey = (data && data.help_key) || {};
    const osReduced = () => !!(w.matchMedia && w.matchMedia('(prefers-reduced-motion: reduce)').matches);
    // a viewer whose system asks for reduced motion can switch the animation on with the button in the sidebar (remembered in this browser)
    const motionOn = () => document.documentElement.classList.contains('lm-motion');
    const reducedMotion = () => osReduced() && !motionOn();
    function syncMotion() {
        if (fx.motionSaved === undefined) {   // read the browser storage once (reading it on every page change is slow)
            fx.motionSaved = false;
            try { fx.motionSaved = localStorage.getItem('lm_motion') === '1'; } catch (e) { /* storage blocked: the choice just is not remembered */ }
        }
        const saved = fx.motionSaved;
        const r = document.documentElement.classList;
        r.toggle('lm-os-reduced', osReduced());
        r.toggle('lm-motion', saved);
        document.querySelectorAll('.lm-motion-btn').forEach((b) => {
            const label = saved ? 'แอนิเมชันเปิดอยู่ · กดเพื่อปิด' : 'เครื่องของคุณตั้งค่าลดการเคลื่อนไหวไว้ · กดเพื่อเปิดแอนิเมชัน';
            if (b.textContent !== label) b.textContent = label;   // only when it differs: writing the text is itself a DOM change the observer would see
        });
    }

    fx.tone = function(freq, dur, gain, delay) {
        if (!fx.sound) return;
        try {
            fx.ctx = fx.ctx || new (w.AudioContext || w.webkitAudioContext)();
            if (fx.ctx.state === 'suspended') fx.ctx.resume();
            const t0 = fx.ctx.currentTime + (delay || 0);
            const osc = fx.ctx.createOscillator();
            const g = fx.ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, t0);
            g.gain.setValueAtTime(0.0001, t0);
            g.gain.exponentialRampToValueAtTime(gain, t0 + 0.012);
            g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
            osc.connect(g); g.connect(fx.ctx.destination);
            osc.start(t0); osc.stop(t0 + dur + 0.02);
        } catch (e) { /* no audio available: stay silent */ }
    };
    fx.tick = function() { fx.tone(880, 0.07, 0.05, 0); };
    fx.pick = function() { fx.tone(660, 0.09, 0.06, 0); fx.tone(990, 0.14, 0.05, 0.07); };
    fx.chime = function() {
        const now = Date.now();
        if (now - fx.lastChime < 900) return;
        fx.lastChime = now;
        fx.tone(740, 0.16, 0.035, 0); fx.tone(1110, 0.22, 0.03, 0.09);
    };

    function fmt(v, dec, sep) {
        return v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: sep });
    }
    fx.prev = fx.prev || {};
    function keyOf(el) {
        if (el.dataset.nk) return el.dataset.nk;
        const g = el.closest ? el.closest('.gcard') : null;
        if (!g) return null;
        const c = Array.from(g.classList).find((x) => /^g[0-9]$/.test(x));
        return c ? 'gcard:' + c : null;
    }
    function run(el) {
        const target = parseFloat(el.dataset.count);
        if (!isFinite(target) || el._target === el.dataset.count) return;
        el._target = el.dataset.count;
        const dec = parseInt(el.dataset.dec || '0', 10), sep = el.dataset.sep === '1', sign = el.dataset.sign || '';
        const show = (v) => sign + fmt(v, dec, sep);
        const key = keyOf(el);
        const from = (key && fx.prev[key] !== undefined) ? fx.prev[key] : 0;   // a card that changes value glides from the old number
        if (reducedMotion()) { el.textContent = show(target); if (key) fx.prev[key] = target; return; }
        const t0 = Date.now(), dur = from === 0 ? 1000 : 800;
        el.textContent = show(from);
        let finished = false;
        function finish() {
            if (finished) return;
            finished = true;
            el.textContent = show(target);
            if (key) fx.prev[key] = target;
            if (key && key.indexOf('gcard') === 0) fx.chime();
        }
        function step() {
            if (finished) return;
            const k = Math.min(1, (Date.now() - t0) / dur), e = 1 - Math.pow(1 - k, 4);
            el.textContent = show(from + (target - from) * e);
            if (k < 1) setTimeout(step, 28); else finish();
        }
        step();
        setTimeout(finish, dur + 250);   // timers still fire in a hidden tab: the number can never stay stuck
    }
    // numbers inside sentences and legends become counters too (idempotent: a container is processed once)
    function autoNums() {
        document.querySelectorAll('.ins b, .rlg b, .gc-delta, [data-testid="stMetricValue"]').forEach((box, bi) => {
            if (box.dataset.auto === '1') return;
            box.dataset.auto = '1';
            const walker = document.createTreeWalker(box, NodeFilter.SHOW_TEXT);
            const nodes = [];
            while (walker.nextNode()) nodes.push(walker.currentNode);
            let n = 0;
            nodes.forEach((node) => {
                const txt = node.nodeValue;
                const re = /([+\-−]?)(\d[\d,]*(?:\.\d+)?)/g;
                let m, last = 0, frag = null;
                while ((m = re.exec(txt)) !== null) {
                    frag = frag || document.createDocumentFragment();
                    frag.appendChild(document.createTextNode(txt.slice(last, m.index)));
                    const raw = m[2].replace(/,/g, '');
                    const span = document.createElement('span');
                    span.className = 'num';
                    span.dataset.count = raw;
                    span.dataset.dec = String((raw.split('.')[1] || '').length);
                    span.dataset.sep = m[2].indexOf(',') >= 0 ? '1' : '0';
                    span.dataset.sign = m[1];
                    span.dataset.nk = 'auto:' + (box.className || box.tagName) + ':' + bi + ':' + (n++);
                    span.textContent = m[0];
                    frag.appendChild(span);
                    last = m.index + m[0].length;
                }
                if (frag) {
                    frag.appendChild(document.createTextNode(txt.slice(last)));
                    node.parentNode.replaceChild(frag, node);
                }
            });
        });
    }
    function tidyRail() {
        document.querySelectorAll('.st-key-rail [data-testid="stIconMaterial"]').forEach((e) => {
            if (['expand_more', 'expand_less'].indexOf(e.textContent.trim()) >= 0 && e.style.display !== 'none') e.style.display = 'none';   // the rail shows icons only
        });
    }
    function scan() { tidyRail(); autoNums(); document.querySelectorAll('.num[data-count]').forEach(run); }

    if (!fx.installed) {
        fx.installed = true;
        document.addEventListener('click', (e) => {
            if (!fx.sound) return;
            const path = e.composedPath ? e.composedPath() : [e.target];
            const first = path[0];
            if (first && first.getAttribute && first.getAttribute('data-region')) { fx.pick(); return; }
            const el = e.target && e.target.closest ? e.target.closest('button, label, [role="tab"], [role="radio"], [data-baseweb="select"]') : null;
            if (el) fx.tick();
        }, true);
    }
    // ---- progressive enhancements: without this script everything is simply visible ----
    const root = document.documentElement;
    root.classList.add('lm-js');
    const scroller = () => document.querySelector('[data-testid="stMain"]') || document.querySelector('section.stMain');

    // cards and charts pop up the first time they are scrolled into view (position check, so it also works in a hidden tab)
    function reveal() {
        const pending = Array.from(document.querySelectorAll('[class*="st-key-card_"]:not(.in)'));
        let n = 0;
        pending.forEach((el) => {
            const r = el.getBoundingClientRect();
            const seen = r.width > 0 && r.top < innerHeight * 0.94 && r.bottom > 0;
            if (!seen && !reducedMotion()) return;
            if (!reducedMotion()) el.style.animationDelay = (n++ * 90) + 'ms';   // cards that appear together pop one after another
            el.classList.add('in');
        });
    }
    let revealTimer = null;
    function queueReveal() { clearTimeout(revealTimer); revealTimer = setTimeout(reveal, 40); }

    // the corner mascot pops up after the banner has scrolled away and hops when scrolling stops
    function mascotState() {
        const m = document.querySelector('.mascot-fixed');
        if (!m) return;
        m.classList.add('show');   // the mascot is always on screen (it first pops in)
    }
    if (!fx.scrollBound) {
        fx.scrollBound = true;
        let timer = null;
        document.addEventListener('scroll', () => {
            mascotState();
            queueReveal();
            if (fx.busy && fx.aim) fx.aim();
            const m = document.querySelector('.mascot-fixed');
            if (!m || !m.classList.contains('show')) return;
            m.classList.remove('hop');
            clearTimeout(timer);
            timer = setTimeout(() => { if (!reducedMotion()) { void m.offsetWidth; m.classList.add('hop'); } }, 220);
        }, true);

        // the pupils look toward the pointer
        let pending = false, mx = 0, my = 0;
        document.addEventListener('mousemove', (e) => {
            mx = e.clientX; my = e.clientY;
            if (pending || reducedMotion()) return;
            pending = true;
            setTimeout(() => {
                pending = false;
                document.querySelectorAll('.mc3d, .mc').forEach((svg) => {
                    const r = svg.getBoundingClientRect();
                    if (r.width === 0 || r.bottom < 0 || r.top > innerHeight) return;
                    const dx = mx - (r.left + r.width / 2), dy = my - (r.top + r.height * 0.64);
                    const d = Math.hypot(dx, dy) || 1, k = Math.min(1, d / 240) * 2.2;
                    svg.querySelectorAll('.mc-pupil, .m3-pupil').forEach((p) => { p.style.transform = `translate(${(dx / d * k).toFixed(2)}px, ${(dy / d * k).toFixed(2)}px)`; });
                });
            }, 90);
        }, { passive: true });

        // a click on the banner mascot makes it hop (and, when sound is on, say hello)
        document.addEventListener('click', (e) => {
            const wrap = e.target && e.target.closest ? e.target.closest('.mascot-wrap') : null;
            if (!wrap) return;
            wrap.classList.remove('hop'); void wrap.offsetWidth; wrap.classList.add('hop');
            fx.pick();
        }, true);
    }
    // ---- the roaming mascot (3D): turns toward where it goes, then walks with steps matched to its speed ----
    const TIPS = ['คลิกที่ภาคบนแผนที่เพื่อซูมดูได้นะ', 'เลือกปีและไตรมาสได้ที่ตัวกรองด้านซ้าย', 'ชี้ที่กราฟเพื่อดูตัวเลขชัด ๆ', 'ช่องว่างในกราฟ = ไม่มีข้อมูลที่เชื่อถือได้', 'กดแท็บใต้แบนเนอร์เพื่อเปลี่ยนหน้าได้นะ', 'สวัสดี! วันนี้ดูข้อมูลอะไรดี?'];
    const STATES = ['walking', 'dance', 'jump', 'look', 'sleep', 'wave', 'explain'];
    const FRONT = -28;                                         // degrees: standing, turned a little toward the viewer
    function roam() {
        if (fx.roaming) return;
        fx.roaming = true;
        let x = null, tipIdx = Math.floor(Math.random() * TIPS.length);
        const later = (ms, fn) => setTimeout(() => { if (!fx.busy) fn(); }, ms);   // random actions are cancelled while a chart is being explained
        function parts() {
            const m = document.querySelector('.mascot-fixed');
            return m ? { m, pos: m.querySelector('.mf-pos'), flip: m.querySelector('.mf-flip'), bub: m.querySelector('.mf-bubble') } : null;
        }
        function bounds() {
            const sc = scroller(), l = sc ? sc.getBoundingClientRect().left : 0;
            return [Math.max(l + 10, 10), innerWidth - 84];
        }
        const face = (p, deg) => p.flip.style.setProperty('--ry', deg + 'deg');
        function place(p, bw, center) {
            p.bub.style.left = center + 'px';
            p.bub.style.setProperty('--tail', Math.min(Math.max(31 - center + bw / 2, 14), bw - 14) + 'px');
        }
        function say(p, text, ms) {
            p.bub.textContent = text;
            p.bub.classList.remove('long');
            const bw = p.bub.offsetWidth, [lo, hi] = bounds(), cx = x + 31;
            let center = 31;                                  // keep the bubble on screen
            if (cx + bw / 2 > hi + 70) center -= (cx + bw / 2) - (hi + 70);
            if (cx - bw / 2 < lo) center += lo - (cx - bw / 2);
            place(p, bw, center);
            p.bub.classList.add('on');
            clearTimeout(fx.bubTimer);
            fx.bubTimer = setTimeout(() => p.bub.classList.remove('on'), ms);
        }
        function clear(p) { STATES.forEach((st) => p.m.classList.remove(st)); }

        // walk along the ground: turn first, then step. Walking = 58 px/s with a 0.72 s step cycle (about 21 px per step); running = 115 px/s
        function walkTo(p, tx, then, tm) {
            tm = tm || later;
            const dist = Math.abs(tx - x);
            if (dist < 6) { then(); return; }
            const run = dist > 380, speed = run ? 115 : 58, T = run ? 0.46 : 0.72, ms = dist / speed * 1000;
            face(p, tx > x ? 58 : -58);
            tm(420, () => {
                p.m.style.setProperty('--T', T + 's');
                p.m.classList.add('walking');
                p.pos.classList.add('go');
                p.pos.style.transition = 'left ' + ms + 'ms cubic-bezier(.22,.04,.78,.96)';
                p.pos.style.left = tx + 'px';
                x = tx;
                tm(ms + 60, () => {
                    p.m.classList.remove('walking');
                    p.pos.style.transition = '';
                    face(p, FRONT);
                    tm(450, then);
                });
            });
        }
        // hop up onto (or down from) a ledge: a spring-like jump, not a slide
        function climb(p, nb, then, tm) {
            tm = tm || later;
            p.m.classList.add('jump');
            p.pos.style.transition = 'bottom 640ms cubic-bezier(.25,1.35,.4,1)';
            p.pos.style.bottom = nb + 'px';
            tm(720, () => { p.m.classList.remove('jump'); p.pos.style.transition = ''; then(); });
        }
        // a ghost's way of getting about: it fades out where it stands and fades in at the target
        function ghostTo(p, tx, nb, then, tm) {
            tm = tm || later;
            p.m.classList.remove('walking');
            p.pos.style.transition = 'opacity 240ms ease, filter 240ms ease';
            p.pos.style.opacity = '0'; p.pos.style.filter = 'blur(5px)';
            tm(280, () => {
                p.pos.style.transition = 'none';
                p.pos.classList.add('go');
                p.pos.style.left = tx + 'px'; p.pos.style.bottom = nb + 'px'; x = tx;
                face(p, FRONT);
                void p.pos.offsetWidth;
                p.pos.style.transition = 'opacity 280ms ease, filter 280ms ease';
                p.pos.style.opacity = '1'; p.pos.style.filter = 'blur(0)';
                tm(320, () => { p.pos.style.transition = ''; p.pos.style.opacity = ''; p.pos.style.filter = ''; then(); });
            });
        }
        function ledge(el) {
            const r = el.getBoundingClientRect(), [lo, hi] = bounds();
            return { tx: Math.min(Math.max(r.right - 84, lo), hi), nb: Math.max(0, innerHeight - 10 - Math.min(r.bottom, innerHeight - 10)) };
        }
        function next(ms) { clearTimeout(fx.tickTimer); fx.tickTimer = setTimeout(tick, ms); }
        function tick() {
            const p = parts();
            if (fx.busy) { next(800); return; }
            if (!p || !p.m.classList.contains('show') || reducedMotion()) { next(1500); return; }
            const [lo, hi] = bounds();
            if (x === null) { x = Math.min(Math.max(p.pos.getBoundingClientRect().left, lo), hi); p.pos.classList.add('go'); p.pos.style.left = x + 'px'; face(p, FRONT); }
            clear(p);
            const r = Math.random();
            if (r < 0.32) {                                    // walk somewhere else
                let target = lo + Math.random() * (hi - lo);
                if (Math.abs(target - x) < 150) target = x < (lo + hi) / 2 ? Math.min(hi, x + 300) : Math.max(lo, x - 300);
                ghostTo(p, target, 0, () => next(500 + Math.random() * 1500));
            } else if (r < 0.44) {                             // visit a card: walk under it, hop up onto its edge, stay a moment, hop down
                const cards = Array.from(document.querySelectorAll('[class*="st-key-card_"]')).filter((c) => {
                    const q = c.getBoundingClientRect();
                    return q.width > 0 && q.top > 60 && q.bottom < innerHeight - 20 && q.bottom > 140;
                });
                if (!cards.length) { next(400); return; }
                const g = ledge(cards[Math.floor(Math.random() * cards.length)]);
                ghostTo(p, g.tx, g.nb, () => {
                    p.m.classList.add(['dance', 'look', 'wave'][Math.floor(Math.random() * 3)]);
                    later(2800, () => { clear(p); ghostTo(p, g.tx, 0, () => next(900)); });
                });
            } else if (r < 0.54) {                             // jump (twice)
                p.m.classList.add('jump');
                later(850, () => { p.m.classList.remove('jump'); void p.m.offsetWidth; p.m.classList.add('jump'); });
                later(1750, () => { clear(p); next(900); });
            } else if (r < 0.64) {                             // dance
                p.m.classList.add('dance');
                later(3200, () => { clear(p); next(700); });
            } else if (r < 0.72) {                             // look around
                p.m.classList.add('look');
                later(1900, () => { clear(p); next(600); });
            } else if (r < 0.80) {                             // wave hello
                p.m.classList.add('wave');
                say(p, 'สวัสดี!', 2400);
                later(2800, () => { clear(p); next(600); });
            } else if (r < 0.87) {                             // nap
                p.m.classList.add('sleep');
                say(p, 'Zzz…', 4200);
                later(4600, () => { clear(p); next(500); });
            } else {                                           // say a hint
                tipIdx = (tipIdx + 1) % TIPS.length;
                p.m.classList.remove('hop'); void p.m.offsetWidth; p.m.classList.add('hop');
                say(p, TIPS[tipIdx], 3800);
                later(4200, () => next(600));
            }
        }

        // ---- click a chart: the mascot vanishes and reappears on its edge, points at it and explains how to read it ----
        function chartKey(plot) {                                // the key the app gave this chart (st-key-<key> on its element container)
            for (let e = plot; e && e !== document.body; e = e.parentElement) {
                const m = (e.className || '').toString().match(/st-key-([\w-]+)/);
                if (m && !/^(card_|page_|hero|kpi)/.test(m[1])) return m[1];
            }
            return '';
        }
        function keyHelp(k) {
            if (!k) return '';
            if (fx.helpKey[k]) return fx.helpKey[k];
            const star = Object.keys(fx.helpKey).find((n) => n.endsWith('*') && k.startsWith(n.slice(0, -1)));
            return star ? fx.helpKey[star] : '';
        }
        function explainText(plot) {
            const card = plot.closest('[class*="st-key-card_"]');
            const ttl = card && card.querySelector('.card-title') ? card.querySelector('.card-title').textContent.trim() : '';
            const kh = keyHelp(chartKey(plot));
            if (kh) return (ttl ? ttl + ': ' : '') + kh;
            if (ttl && fx.help[ttl]) return ttl + ': ' + fx.help[ttl];
            const gd = plot.querySelector('.js-plotly-plot');
            const lay = gd && gd.layout ? gd.layout : {};
            const tx = (a) => (a && a.title && (a.title.text || (typeof a.title === 'string' ? a.title : ''))) || '';
            const y = tx(lay.yaxis), xx = tx(lay.xaxis);
            const names = (gd && gd.data ? gd.data : []).filter((d) => d.name && d.showlegend !== false && d.hoverinfo !== 'skip').map((d) => d.name);
            const uniq = Array.from(new Set(names)).slice(0, 5);
            let st = (ttl ? ttl + ': ' : '') + 'กราฟนี้แสดง';
            st += y ? ' ' + y : ' ค่าตามที่ระบุในกราฟ';
            if (xx) st += ' เทียบกับ ' + xx;
            if (uniq.length > 1) st += ' แยกเป็น ' + uniq.join(', ');
            return st + ' ชี้ที่จุดหรือแท่งเพื่อดูตัวเลข ช่องว่าง = ไม่มีข้อมูลที่เชื่อถือได้';
        }
        function endExplain() {
            const p = parts();
            clearTimeout(fx.explainTimer);
            if (!p) { fx.busy = false; return; }
            p.m.classList.remove('explain');
            p.bub.classList.remove('on', 'long', 'below');
            fx.arrived = false; fx.target = null;
            ghostTo(p, x, 0, () => { fx.busy = false; next(1200); }, (ms, fn) => setTimeout(fn, ms));
        }
        fx.aim = function() {                                  // the page scrolled while the mascot stands on a card: follow it
            const p = parts();
            if (!p || !fx.target || !fx.target.isConnected) { endExplain(); return; }
            if (!fx.arrived) return;
            const g = ledge(fx.target);
            p.pos.style.transition = 'left 220ms ease-out, bottom 220ms ease-out';
            p.pos.style.left = g.tx + 'px'; p.pos.style.bottom = g.nb + 'px'; x = g.tx;
        };
        fx.explain = function(plot, override, hold) {
            const p = parts();
            if (!p || reducedMotion()) return;
            const [lo] = bounds();
            if (x === null) { x = Math.min(Math.max(p.pos.getBoundingClientRect().left, lo), innerWidth - 84); p.pos.classList.add('go'); p.pos.style.left = x + 'px'; }
            clearTimeout(fx.explainTimer); clearTimeout(fx.bubTimer); clearTimeout(fx.tickTimer);
            fx.busy = true; fx.arrived = false; fx.target = plot;
            mascotState();
            clear(p);
            p.bub.classList.remove('on', 'long', 'below');
            p.pos.style.transition = '';
            fx.pick();
            const tm = (ms, fn) => setTimeout(() => { if (fx.busy && fx.target === plot) fn(); }, ms);   // not cancelled by the random actions
            const g = ledge(plot), text = override || explainText(plot);
            const arrive = () => {
                clear(p);
                face(p, FRONT);
                p.m.classList.add('explain');
                fx.arrived = true;
                p.bub.textContent = text;
                p.bub.classList.add('long', 'on');
                const bh = p.bub.offsetHeight, top = p.pos.getBoundingClientRect().top, bw = p.bub.offsetWidth, cx = x + 31;
                p.bub.classList.toggle('below', top < bh + 16);
                let center = 31;
                if (cx + bw / 2 > innerWidth - 12) center -= (cx + bw / 2) - (innerWidth - 12);
                if (cx - bw / 2 < lo) center += lo - (cx - bw / 2);
                place(p, bw, center);
                fx.explainTimer = setTimeout(endExplain, hold || 11000);
            };
            ghostTo(p, g.tx, g.nb, arrive, tm);           // it vanishes and shows up on the card's edge
        };
        document.addEventListener('click', (e) => {
            const tgt = e.target;
            if (!tgt || !tgt.closest || tgt.closest('.mascot-fixed')) return;
            const plot = tgt.closest('[data-testid="stPlotlyChart"]');
            if (plot) { fx.explain(plot); return; }
            const title = tgt.closest('.card-title') || tgt.closest('.rklist');
            if (title) { const c = title.closest('[class*="st-key-card_"]'); if (c) fx.explain(c); }
        }, true);
        fx.endExplain = endExplain;
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && fx.busy) endExplain(); });

        next(2500);
    }
    roam();
    syncMotion();
    if (!fx.motionBound) {
        fx.motionBound = true;
        document.addEventListener('click', (e) => {
            const b = e.target && e.target.closest ? e.target.closest('.lm-motion-btn') : null;
            if (!b) return;
            fx.motionSaved = !fx.motionSaved;
            try { localStorage.setItem('lm_motion', fx.motionSaved ? '1' : '0'); } catch (err) { /* ignore */ }
            syncMotion();
            queueReveal();
        }, true);
    }
    if (!fx.railBound) {
        fx.railBound = true;
        const blurRail = (e) => {
            const b = e.target && e.target.closest ? e.target.closest('.st-key-rail button') : null;
            if (b) setTimeout(() => { if (document.activeElement === b && !b.matches(':hover')) b.blur(); }, 30);
        };
        document.addEventListener('mouseout', blurRail, true);
        document.addEventListener('click', (e) => {
            const b = e.target && e.target.closest ? e.target.closest('.st-key-rail button') : null;
            if (b) { document.documentElement.classList.add('lm-notip'); setTimeout(() => b.blur(), 400); }   // a click leaves the button focused (and its tooltip open): hide tips until the next hover
        }, true);
        document.addEventListener('mouseover', (e) => {
            if (e.target && e.target.closest && e.target.closest('.st-key-rail button')) document.documentElement.classList.remove('lm-notip');
        }, true);
    }
    fx.scan = scan;
    scan();
    queueReveal();
    mascotState();
    if (!fx.revealObs) {                                       // the only observer: Streamlit changes the page a lot, so work is batched
        let busy = false;
        fx.revealObs = new MutationObserver(() => {
            if (busy) return;
            busy = true;
            setTimeout(() => { busy = false; scan(); syncMotion(); queueReveal(); mascotState(); }, 150);
        });
        w.addEventListener('resize', queueReveal);
        fx.revealObs.observe(document.body, { childList: true, subtree: true });
    }
}
"""

# What the mascot says when a chart is clicked. Only statements about how to read the chart (no numbers, no findings);
# charts that are not listed get a sentence built from their own axis titles and series names (see explainText in the script).
CHART_HELP = {
    "แผนที่ตลาดแรงงานรายภูมิภาค": "แต่ละสีคือหนึ่งภูมิภาค ตัวเลขอยู่ในรายการสีข้างแผนที่ คลิกที่ภาคเพื่อซูมและดูเฉพาะภาคนั้น",
    "แนวโน้มรายไตรมาส": "เส้นแสดงค่าของตัวชี้วัดที่เลือกในแต่ละไตรมาส ช่องว่างในเส้นคือไตรมาสที่ไม่มีค่าที่เชื่อถือได้ ระบบไม่เติมค่าให้",
    "ค่าจ้างชาย-หญิงตามกลุ่มอายุ": "แท่งทึบคือชาย แท่งลายคือหญิง เทียบค่าจ้างเฉลี่ยต่อเดือนในแต่ละกลุ่มอายุ เป็นข้อมูลระดับประเทศ",
    "ภูมิภาคที่อัตราการว่างงานสูงสุด": "เรียงอัตราการว่างงานของ 5 ภาคจากสูงไปต่ำ แท่งยาวเทียบกับภาคที่สูงที่สุด ภาคที่ไม่มีค่าที่ตรวจสอบแล้วจะไม่ถูกจัดอันดับ",
    "เหตุผลที่ผู้ว่างงานออกจากงานเดิม": "แต่ละแท่งคือหนึ่งไตรมาส แบ่งสีตามเหตุผลที่ผู้ว่างงานที่เคยทำงานออกจากงานเดิม ความสูงรวมคือผู้ว่างงานที่เคยทำงานทั้งหมดในไตรมาสนั้น ข้อมูลชุดนี้มีถึงปี 2565 เท่านั้น",
    "ความสัมพันธ์ระหว่างค่าจ้างกับการว่างงาน": "แต่ละจุดคือหนึ่งไตรมาส เส้นประคือแนวโน้มเชิงเส้น ค่า r บอกว่าสองค่าเคลื่อนไหวสัมพันธ์กันแค่ไหน ไม่ได้บอกว่าค่าหนึ่งเป็นสาเหตุของอีกค่า",
}

# Specific sentences for the charts on the other pages, by the key each chart is drawn with ("*" at the end = every key that starts so).
CHART_HELP_BY_KEY = {
    "bot_stack": "แต่ละแท่งคือหนึ่งไตรมาส แบ่งสีตามเหตุผลที่ผู้ว่างงานที่เคยทำงานออกจากงานเดิม ความสูงรวมคือผู้ว่างงานที่เคยทำงานทั้งหมด ข้อมูลชุดนี้มีถึงปี 2565 เท่านั้น",
    "dur_bar": "แต่ละแท่งคือสัดส่วน (ร้อยละ) ของผู้ว่างงานที่หางานมานานตามช่วงเวลานั้น คำนวณจากผลรวมทุกไตรมาสที่เลือก แท่งสูงกว่าคือสัดส่วนมากกว่า",
    "sso_bar": "แต่ละปีมีแท่งหนึ่งแท่งต่อเหตุผล ความสูงคือจำนวนกรณีที่ใช้สิทธิประกันสังคมกรณีว่างงานในปีนั้น",
    "eco_two": "สองกราฟซ้อนกันบนแกนไตรมาสเดียวกัน ได้แก่ อัตราการว่างงานและอัตราเติบโตของ GDP แยกแกนเพราะหน่วยต่างกัน",
    "eco_sc": "แต่ละจุดคือหนึ่งไตรมาส เส้นประคือแนวโน้มเชิงเส้น ใช้ดูว่าสองค่าเคลื่อนไหวไปทางเดียวกันหรือสวนกัน ไม่ได้บอกว่าค่าหนึ่งเป็นสาเหตุของอีกค่า",
    "ov_scatter": "แต่ละจุดคือหนึ่งไตรมาส เส้นประคือแนวโน้มเชิงเส้น ค่า r บอกว่าสองค่าเคลื่อนไหวสัมพันธ์กันแค่ไหน ไม่ได้บอกว่าค่าหนึ่งเป็นสาเหตุของอีกค่า",
    "lm_sc": "แต่ละจุดคือหนึ่งไตรมาส ดูว่าจุดเรียงไปทางเดียวกันหรือสวนกัน ไม่ได้บอกว่าค่าหนึ่งเป็นสาเหตุของอีกค่า",
    "lm_reg_sc": "แต่ละจุดคือข้อมูลหนึ่งรายการตามที่ระบุในแกน ใช้ดูความสัมพันธ์ ไม่ได้บอกสาเหตุ",
    "lm_pool": "แต่ละจุดคือข้อมูลหนึ่งรายการตามที่ระบุในแกน ใช้ดูความสัมพันธ์ ไม่ได้บอกสาเหตุ",
    "lm_trend": "แต่ละเส้นคือหนึ่งตัวชี้วัดรายไตรมาส ดูหน่วยจากชื่อแกนและคำอธิบายสี ช่องว่างหรือแถบเทาคือไตรมาสที่ไม่แสดงค่า เพราะไม่มีค่าที่เชื่อถือได้หรือตารางต้นทางขัดแย้งกัน",
    "lm_regtr_*": "แต่ละเส้นคือหนึ่งภาค ตามไตรมาส ช่องว่างหรือแถบเทาคือไตรมาสที่ไม่แสดงค่า เพราะไม่มีค่าที่เชื่อถือได้หรือตารางต้นทางขัดแย้งกัน",
    "reg_trend": "แต่ละเส้นคือหนึ่งภาค ตามไตรมาส ช่องว่างหรือแถบเทาคือไตรมาสที่ไม่แสดงค่า เพราะไม่มีค่าที่เชื่อถือได้หรือตารางต้นทางขัดแย้งกัน",
    "cmp_line_*": "แต่ละสีคือหนึ่งภาคที่เลือกเปรียบเทียบ เส้นขาดคือไตรมาสที่ไม่มีค่าที่เชื่อถือได้ ระบบไม่เติมค่าให้",
    "reg_bar_u": "แต่ละแท่งคือหนึ่งภาค แท่งยาวกว่าคือมีจำนวนผู้ว่างงานมากกว่าในไตรมาสที่ระบุ",
    "reg_bar_r": "แต่ละแท่งคือหนึ่งภาค แท่งยาวกว่าคืออัตราการว่างงานสูงกว่าในไตรมาสที่ระบุ",
    "edu_bar_cnt": "แต่ละแท่งคือหนึ่งระดับการศึกษา แท่งยาวกว่าคือมีผู้ว่างงานมากกว่า สีของแต่ละระดับเหมือนกันทุกกราฟ",
    "edu_bar_rate": "แต่ละแท่งคือหนึ่งระดับการศึกษา แท่งยาวกว่าคืออัตราการว่างงานสูงกว่า สีของแต่ละระดับเหมือนกันทุกกราฟ",
    "edu_trend": "แต่ละเส้นคือหนึ่งระดับการศึกษา ตามไตรมาส สีของแต่ละระดับเหมือนกับกราฟแท่งการศึกษา",
    "sex_bar": "แท่งทึบคือชาย แท่งลายคือหญิง ตามไตรมาส แท่งสูงกว่าคือจำนวนผู้ว่างงานมากกว่า",
    "lm_hc_age": "แท่งทึบคือชาย แท่งลายคือหญิง ในแต่ละกลุ่มอายุ แท่งสูงกว่าคือมีผู้มีงานทำมากกว่า",
}

_FX = st.components.v2.component("lm_fx", js=_JS)


def mount(sound: bool, dark: bool = False) -> None:
    """Call once per run (it draws nothing)."""
    _FX(data={"sound": bool(sound), "dark": bool(dark), "help": CHART_HELP, "help_key": CHART_HELP_BY_KEY}, key="lm_fx")
