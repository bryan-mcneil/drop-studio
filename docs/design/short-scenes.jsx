// GadgetDrop Short — scene components for the drop-studio review video.
// Built on animations-v2.jsx (SceneStage/scene-clock) + tweaks-panel.jsx.
// All motion is driven by the per-scene clock (localTime/progress) so the
// host timeline can time-stretch and the video export stays frame-exact.

const { SceneStage, Easing, clamp } = window;
const {
  useTweaks, TweaksPanel, TweakSection, TweakSlider,
  TweakToggle, TweakRadio, TweakColor, TweakText,
} = window;

const W = 1080, H = 1920;
const FONT = "'Figtree', ui-sans-serif, system-ui, -apple-system, sans-serif";

// ── GadgetDrop palette (verbatim token values) ──────────────────────────────
const C = {
  studioTop: '#0b0a1c', studioBottom: '#1b1740',
  indigo900: '#312e81', indigo700: '#4338ca', indigo600: '#4f46e5',
  indigo500: '#6366f1', indigo400: '#818cf8', indigo200: '#c7d2fe',
  indigo100: '#e0e7ff', indigo50: '#eef2ff',
  orange: '#f97316',
  amber400: '#fbbf24',
  emerald600: '#059669', emerald500: '#10b981', emerald400: '#34d399',
  sky500: '#0ea5e9', sky300: '#7dd3fc',
  rose600: '#e11d48', rose400: '#fb7185',
  white: '#ffffff', gray900: '#111827', gray700: '#374151', gray600: '#4b5563',
  gray500: '#6b7280', gray400: '#9ca3af', gray300: '#d1d5db', gray200: '#e5e7eb',
  gray100: '#f3f4f6', gray50: '#f9fafb',
  amazon: 'linear-gradient(135deg,#FFB84D,#FF9900)',
  violet: 'linear-gradient(160deg,#312e81 0%,#4338ca 44%,#6d28d9 100%)',
};

// ── small helpers ───────────────────────────────────────────────────────────
function hexA(hex, a) {
  const s = hex.replace('#', '');
  const x = s.length === 3 ? s.replace(/./g, (c) => c + c) : s;
  const n = parseInt(x, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}
const num = (s) => parseFloat(String(s).replace(/[^0-9.]/g, '')) || 0;
const money = (n) =>
  '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
// single-segment tween on a clock value
const tw = (t, from, to, s, e, ease = Easing.easeOutCubic) =>
  window.animate({ from, to, start: s, end: e, ease })(t);

const ContentCtx = React.createContext(null);
const useContent = () => React.useContext(ContentCtx);

// ── shared chrome ────────────────────────────────────────────────────────────
function Studio({ children, glow = C.indigo500, localTime = 0 }) {
  const pulse = 0.28 + 0.06 * Math.sin(localTime * 1.4);
  const drift = 14 * Math.sin(localTime * 0.6);
  return (
    <div style={{
      position: 'absolute', inset: 0, overflow: 'hidden', fontFamily: FONT,
      background: `linear-gradient(to bottom, ${C.studioTop}, ${C.studioBottom})`,
    }}>
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: `radial-gradient(${hexA(glow, 0.14)} 2px, transparent 2px)`,
        backgroundSize: '46px 46px', opacity: 0.6,
      }} />
      <div style={{
        position: 'absolute', top: -360 + drift, left: '50%',
        transform: 'translateX(-50%)', width: 1600, height: 860, borderRadius: '50%',
        background: `radial-gradient(closest-side, ${hexA(glow, pulse)}, transparent 70%)`,
      }} />
      <div style={{
        position: 'absolute', bottom: -420 - drift, left: '30%',
        width: 900, height: 700, borderRadius: '50%',
        background: `radial-gradient(closest-side, ${hexA(C.indigo700, 0.34)}, transparent 70%)`,
      }} />
      {children}
    </div>
  );
}

function Wordmark({ size = 46, drop = C.indigo400, gadget = C.gray400, weight = 800 }) {
  return (
    <div style={{ fontFamily: FONT, fontWeight: weight, fontSize: size, letterSpacing: '-0.02em', lineHeight: 1 }}>
      <span style={{ color: gadget }}>Gadget</span><span style={{ color: drop }}>Drop</span>
    </div>
  );
}

function Watermark({ opacity = 1 }) {
  return (
    <div style={{
      position: 'absolute', bottom: 70, left: 0, right: 0, textAlign: 'center',
      fontFamily: FONT, fontWeight: 600, fontSize: 34, letterSpacing: '0.04em',
      color: C.gray500, opacity,
    }}>gadgetdrop.tech</div>
  );
}

function Eyebrow({ children, color = C.indigo400, top, localTime, at = 0.1 }) {
  const o = tw(localTime, 0, 1, at, at + 0.4);
  const y = tw(localTime, 18, 0, at, at + 0.4, Easing.easeOutBack);
  return (
    <div style={{
      position: 'absolute', top, left: 0, right: 0, textAlign: 'center',
      fontFamily: FONT, fontWeight: 800, fontSize: 34, letterSpacing: '0.28em',
      textTransform: 'uppercase', color, opacity: o, transform: `translateY(${y}px)`,
    }}>{children}</div>
  );
}

// tag-shaped chip (discount / verdict)
function Tag({ children, bg = C.emerald600, color = C.white, size = 42, style = {} }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 16,
      padding: '16px 34px 16px 44px', borderRadius: 22,
      background: bg, color, fontFamily: FONT, fontWeight: 800, fontSize: size,
      letterSpacing: '0.01em', whiteSpace: 'nowrap',
      clipPath: 'polygon(24px 0,100% 0,100% 100%,24px 100%,0 50%)', ...style,
    }}>
      <span style={{ width: 16, height: 16, borderRadius: '50%', background: 'rgba(255,255,255,0.9)' }} />
      {children}
    </div>
  );
}

function Stars({ rating = 4, appear = 1, size = 66, gap = 12 }) {
  return (
    <div style={{ display: 'flex', gap, justifyContent: 'center' }}>
      {[0, 1, 2, 3, 4].map((i) => {
        const filled = i < Math.round(rating);
        const p = clamp(appear * 5.5 - i, 0, 1);
        const e = Easing.easeOutBack(p);
        return (
          <span key={i} style={{
            fontSize: size, lineHeight: 1, color: filled ? C.amber400 : C.gray200,
            transform: `scale(${0.2 + 0.8 * e}) rotate(${(1 - e) * -25}deg)`,
            opacity: clamp(p * 1.5, 0, 1), display: 'inline-block',
          }}>★</span>
        );
      })}
    </div>
  );
}

// kinetic word-by-word caption band
function Kinetic({ words, hi = [], accent, localTime, start = 0.2, per = 0.14, y = 1520, size = 72 }) {
  return (
    <div style={{
      position: 'absolute', left: 70, right: 70, top: y,
      display: 'flex', flexWrap: 'wrap', gap: '8px 20px',
      justifyContent: 'center', alignItems: 'flex-end',
    }}>
      {words.map((w, i) => {
        const t0 = start + i * per;
        const p = clamp((localTime - t0) / 0.26, 0, 1);
        const e = Easing.easeOutBack(p);
        const on = hi.includes(i);
        return (
          <span key={i} style={{
            fontFamily: FONT, fontWeight: 800, fontSize: size, lineHeight: 1.02,
            letterSpacing: '-0.01em', color: on ? accent : C.white,
            opacity: clamp(p * 1.8, 0, 1),
            transform: `translateY(${(1 - e) * 26}px) scale(${0.7 + 0.3 * e})`,
            transformOrigin: 'center bottom', display: 'inline-block',
            textShadow: '0 6px 30px rgba(0,0,0,0.6)',
          }}>{w}</span>
        );
      })}
    </div>
  );
}

// ── HOOK ─────────────────────────────────────────────────────────────────────
function Hook(props) {
  const c = useContent();
  if (c.hookStyle === 'question') return <HookQuestion {...props} />;
  return <HookSlam {...props} />;
}

function HookSlam({ localTime }) {
  const c = useContent();
  // deal price slam + breathe
  const slam = Easing.easeOutBack(clamp((localTime - 0.55) / 0.55, 0, 1));
  const breathe = localTime > 1.15 ? 1 + 0.014 * Math.sin((localTime - 1.15) * 2.4) : 1;
  const priceScale = (0.55 + 0.45 * slam) * breathe;
  const priceO = clamp((localTime - 0.5) / 0.3, 0, 1);
  // strike on the list price
  const strike = tw(localTime, 0, 1, 0.9, 1.4, Easing.easeInOutCubic);
  const wasO = tw(localTime, 0, 1, 0.7, 1.0);
  const tagP = Easing.easeOutBack(clamp((localTime - 1.35) / 0.4, 0, 1));
  const saveO = tw(localTime, 0, 1, 1.6, 2.0);
  const chipY = tw(localTime, 40, 0, 1.95, 2.35, Easing.easeOutBack);
  const chipO = tw(localTime, 0, 1, 1.95, 2.3);

  return (
    <Studio localTime={localTime} glow={C.indigo500}>
      <div style={{ position: 'absolute', top: 118, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
        <Wordmark size={44} />
      </div>
      <Eyebrow top={500} localTime={localTime} at={0.15}>Today's Drop</Eyebrow>

      {/* was $xxx, struck */}
      <div style={{
        position: 'absolute', top: 620, left: 0, right: 0, textAlign: 'center',
        opacity: wasO, fontFamily: FONT, fontWeight: 700, fontSize: 60, color: C.gray400,
      }}>
        <span style={{ position: 'relative', display: 'inline-block' }}>
          was {c.listPrice}
          <span style={{
            position: 'absolute', left: -8, right: -8, top: '52%', height: 6, borderRadius: 4,
            background: C.rose400, transform: `scaleX(${strike})`, transformOrigin: 'left center',
          }} />
        </span>
      </div>

      {/* deal price slam */}
      <div style={{
        position: 'absolute', top: 700, left: 0, right: 0, textAlign: 'center',
        opacity: priceO, transform: `scale(${priceScale})`, transformOrigin: 'center top',
      }}>
        <div style={{
          fontFamily: FONT, fontWeight: 800, fontSize: 260, lineHeight: 0.95, color: C.white,
          letterSpacing: '-0.03em', textShadow: `0 20px 80px ${hexA(C.indigo500, 0.55)}`,
        }}>{c.dealPrice}</div>
      </div>

      {/* discount tag + savings */}
      <div style={{
        position: 'absolute', top: 1030, left: 0, right: 0,
        display: 'flex', gap: 26, justifyContent: 'center', alignItems: 'center',
      }}>
        <div style={{ transform: `scale(${tagP})`, transformOrigin: 'center' }}>
          <Tag bg={C.emerald600} size={52}>{c.pct}% OFF</Tag>
        </div>
        <div style={{
          opacity: saveO, fontFamily: FONT, fontWeight: 800, fontSize: 52, color: C.emerald400,
          letterSpacing: '-0.01em',
        }}>Save ${c.save}</div>
      </div>

      {/* product chip */}
      <div style={{
        position: 'absolute', top: 1200, left: 0, right: 0, display: 'flex', justifyContent: 'center',
        opacity: chipO, transform: `translateY(${chipY}px)`,
      }}>
        <div style={{
          background: C.indigo100, color: C.indigo700, fontFamily: FONT, fontWeight: 800,
          fontSize: 46, padding: '20px 44px', borderRadius: 999, letterSpacing: '-0.01em',
        }}>{c.productName}</div>
      </div>

      {c.captions && (
        <Kinetic words={[`${c.pct}%`, 'OFF', 'RIGHT', 'NOW']} hi={[0]} accent={C.indigo200}
          localTime={localTime} start={2.4} y={1480} />
      )}
      <Watermark />
    </Studio>
  );
}

function HookQuestion({ localTime }) {
  const c = useContent();
  const q = tw(localTime, 0, 1, 0.2, 0.7);
  const qy = tw(localTime, 30, 0, 0.2, 0.7, Easing.easeOutBack);
  const priceScale = Easing.easeOutBack(clamp((localTime - 0.9) / 0.5, 0, 1));
  const priceO = tw(localTime, 0, 1, 0.9, 1.2);
  const chipO = tw(localTime, 0, 1, 1.6, 2.0);
  const chipY = tw(localTime, 34, 0, 1.6, 2.0, Easing.easeOutBack);
  return (
    <Studio localTime={localTime} glow={C.indigo500}>
      <div style={{ position: 'absolute', top: 118, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
        <Wordmark size={44} />
      </div>
      <div style={{
        position: 'absolute', top: 560, left: 80, right: 80, textAlign: 'center',
        opacity: q, transform: `translateY(${qy}px)`,
        fontFamily: FONT, fontWeight: 800, fontSize: 108, lineHeight: 1.04, color: C.white,
        letterSpacing: '-0.02em',
      }}>Is <span style={{ color: C.indigo200 }}>{c.dealPrice}</span> a good deal?</div>

      <div style={{
        position: 'absolute', top: 940, left: 0, right: 0, display: 'flex', justifyContent: 'center',
        opacity: priceO, transform: `scale(${0.6 + 0.4 * priceScale})`,
      }}>
        <div style={{
          background: C.indigo100, color: C.indigo700, fontFamily: FONT, fontWeight: 800,
          fontSize: 48, padding: '22px 48px', borderRadius: 999,
        }}>{c.productName}</div>
      </div>

      <div style={{
        position: 'absolute', top: 1120, left: 0, right: 0, textAlign: 'center',
        opacity: chipO, transform: `translateY(${chipY}px)`,
        fontFamily: FONT, fontWeight: 700, fontSize: 46, color: C.gray400,
      }}>We tracked it for 90 days ↓</div>

      {c.captions && (
        <Kinetic words={['LET', 'US', 'CHECK']} hi={[2]} accent={C.indigo200}
          localTime={localTime} start={2.2} y={1470} />
      )}
      <Watermark />
    </Studio>
  );
}

// ── PRODUCT ────────────────────────────────────────────────────────────────
function Product({ localTime, dur }) {
  const c = useContent();
  const cardO = tw(localTime, 0, 1, 0.05, 0.5);
  const cardScale = tw(localTime, 0.9, 1, 0.05, 0.6, Easing.easeOutCubic);
  const cardFloat = 8 * Math.sin(localTime * 1.1);
  // ken burns on photo
  const kb = clamp((localTime - 0.4) / (dur - 0.4), 0, 1);
  const photoScale = 1 + 0.08 * kb;
  const photoO = tw(localTime, 0, 1, 0.35, 0.9);
  const nameO = tw(localTime, 0, 1, 0.6, 1.0);
  const nameY = tw(localTime, 20, 0, 0.6, 1.0, Easing.easeOutBack);
  const starsAppear = clamp((localTime - 1.0) / 0.9, 0, 1);
  const priceSlam = Easing.easeOutBack(clamp((localTime - 1.5) / 0.5, 0, 1));
  const priceO = tw(localTime, 0, 1, 1.5, 1.85);
  const tagP = Easing.easeOutBack(clamp((localTime - 1.95) / 0.4, 0, 1));

  return (
    <Studio localTime={localTime} glow={C.indigo500}>
      <Eyebrow top={150} localTime={localTime} at={0.1}>Today's Drop</Eyebrow>
      <div style={{
        position: 'absolute', top: 300, left: 80, right: 80,
        background: C.white, borderRadius: 52, padding: '64px 56px 72px',
        boxShadow: `0 40px 90px ${hexA('#000000', 0.45)}`,
        opacity: cardO, transform: `translateY(${cardFloat}px) scale(${cardScale})`,
        transformOrigin: 'center top',
      }}>
        {/* photo panel */}
        <div style={{
          height: 620, borderRadius: 36, background: `radial-gradient(circle at 50% 40%, ${C.gray50}, ${C.gray100})`,
          overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center',
          border: `1px solid ${C.gray100}`,
        }}>
          <img src={window.PRODUCT_IMG} alt="" style={{
            width: '92%', height: '92%', objectFit: 'contain', opacity: photoO,
            transform: `scale(${photoScale})`, transformOrigin: 'center 55%',
            filter: 'drop-shadow(0 30px 40px rgba(0,0,0,0.28))',
          }} />
        </div>

        <div style={{
          marginTop: 48, textAlign: 'center', fontFamily: FONT, fontWeight: 800, fontSize: 78,
          color: C.gray900, letterSpacing: '-0.02em', opacity: nameO, transform: `translateY(${nameY}px)`,
        }}>{c.productName}</div>

        <div style={{ marginTop: 30 }}>
          <Stars rating={c.rating} appear={starsAppear} size={72} />
        </div>

        <div style={{
          marginTop: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 34,
        }}>
          <div style={{
            fontFamily: FONT, fontWeight: 800, fontSize: 150, lineHeight: 0.9, color: C.gray900,
            letterSpacing: '-0.03em', opacity: priceO, transform: `scale(${0.7 + 0.3 * priceSlam})`,
            transformOrigin: 'center',
          }}>{c.dealPrice}</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'flex-start' }}>
            <div style={{
              fontFamily: FONT, fontWeight: 700, fontSize: 54, color: C.gray400,
              textDecoration: 'line-through', opacity: priceO,
            }}>{c.listPrice}</div>
            <div style={{ transform: `scale(${tagP})`, transformOrigin: 'left center' }}>
              <Tag bg={C.emerald600} size={40}>{c.pct}% OFF</Tag>
            </div>
          </div>
        </div>
      </div>
      <Watermark />
    </Studio>
  );
}

// ── FEATURE (x3) ──────────────────────────────────────────────────────────
function Feature({ scene, localTime, dur }) {
  const c = useContent();
  const accent = c.accent;
  const step = scene.step || 1, steps = 3;
  const kickerO = tw(localTime, 0, 1, 0.2, 0.6);
  const target = num(scene.metric);
  const hasCount = /\d/.test(scene.metric || '') && target > 0;
  const countP = tw(localTime, 0, 1, 0.25, 1.15, Easing.easeOutExpo);
  const shown = hasCount ? Math.round(target * countP).toLocaleString('en-US') : scene.metric;
  const heroScale = Easing.easeOutBack(clamp((localTime - 0.2) / 0.5, 0, 1));
  const heroO = tw(localTime, 0, 1, 0.2, 0.55);
  const cardY = tw(localTime, 50, 0, 0.45, 0.95, Easing.easeOutCubic);
  const cardO = tw(localTime, 0, 1, 0.45, 0.9);
  const checkP = Easing.easeOutBack(clamp((localTime - 0.7) / 0.45, 0, 1));

  return (
    <Studio localTime={localTime} glow={C.indigo500}>
      {/* progress dots */}
      <div style={{
        position: 'absolute', top: 210, left: 0, right: 0, display: 'flex', gap: 16,
        justifyContent: 'center', alignItems: 'center',
      }}>
        {[1, 2, 3].map((s) => {
          const done = s < step, active = s === step;
          const fill = active ? tw(localTime, 0, 1, 0.1, 0.6) : done ? 1 : 0;
          return (
            <div key={s} style={{
              width: active ? 96 : 30, height: 18, borderRadius: 999,
              background: done ? accent : hexA(C.white, 0.14),
              border: `2px solid ${done || active ? accent : hexA(C.white, 0.25)}`,
              overflow: 'hidden', position: 'relative',
            }}>
              {active && <div style={{ position: 'absolute', inset: 0, background: accent, transform: `scaleX(${fill})`, transformOrigin: 'left' }} />}
            </div>
          );
        })}
      </div>

      <div style={{
        position: 'absolute', top: 300, left: 0, right: 0, textAlign: 'center',
        fontFamily: FONT, fontWeight: 800, fontSize: 34, letterSpacing: '0.28em',
        textTransform: 'uppercase', color: C.emerald400, opacity: kickerO,
      }}>{scene.kicker}</div>

      {/* hero metric */}
      <div style={{ position: 'absolute', top: 400, left: 0, right: 0, height: 360, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {scene.viz === 'scan' && (
          <div style={{ position: 'absolute', width: 380, height: 380, borderRadius: '50%', opacity: heroO }}>
            <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: `3px solid ${hexA(accent, 0.35)}` }} />
            <div style={{ position: 'absolute', inset: 70, borderRadius: '50%', border: `2px solid ${hexA(accent, 0.25)}` }} />
            <div style={{ position: 'absolute', inset: 140, borderRadius: '50%', border: `2px solid ${hexA(accent, 0.2)}` }} />
            <div style={{
              position: 'absolute', inset: 0, borderRadius: '50%',
              background: `conic-gradient(from ${localTime * 130}deg, ${hexA(accent, 0)} 0deg, ${hexA(accent, 0.5)} 55deg, ${hexA(accent, 0)} 120deg)`,
            }} />
          </div>
        )}
        <div style={{
          position: 'relative', fontFamily: FONT, fontWeight: 800, fontSize: 210, lineHeight: 0.9,
          color: C.white, letterSpacing: '-0.03em', opacity: heroO,
          transform: `scale(${0.6 + 0.4 * heroScale})`, textShadow: `0 16px 60px ${hexA(accent, 0.5)}`,
        }}>
          {shown}<span style={{ fontSize: scene.unit === '°' ? 96 : 96, color: accent, verticalAlign: scene.unit === '°' ? 'super' : 'baseline', marginLeft: scene.unit === '°' ? 4 : 0 }}>{scene.unit}</span>
        </div>
      </div>

      {/* feature card */}
      <div style={{
        position: 'absolute', top: 900, left: 80, right: 80, background: C.white, borderRadius: 44,
        padding: '56px 52px', boxShadow: `0 34px 80px ${hexA('#000000', 0.4)}`,
        opacity: cardO, transform: `translateY(${cardY}px)`,
        display: 'flex', gap: 40, alignItems: 'center',
      }}>
        <div style={{
          width: 128, height: 128, borderRadius: '50%', background: accent, flex: 'none',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transform: `scale(${checkP})`, boxShadow: `0 12px 30px ${hexA(accent, 0.5)}`,
        }}>
          <svg width="74" height="74" viewBox="0 0 24 24" fill="none">
            <path d="M4 12.5l5 5L20 6.5" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"
              style={{ strokeDasharray: 40, strokeDashoffset: 40 * (1 - clamp((localTime - 0.85) / 0.4, 0, 1)) }} />
          </svg>
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 62, lineHeight: 1.08, color: C.gray900, letterSpacing: '-0.02em' }}>{scene.title}</div>
          <div style={{ fontFamily: FONT, fontWeight: 500, fontSize: 40, lineHeight: 1.32, color: C.gray500, marginTop: 18 }}>{scene.sub}</div>
        </div>
      </div>

      {c.captions && scene.cap && (
        <Kinetic words={scene.cap} hi={scene.capHi || []} accent={accent} localTime={localTime} start={1.2} y={1560} />
      )}
      <Watermark />
    </Studio>
  );
}

// ── PRICE (90-day chart) ─────────────────────────────────────────────────
function Price({ localTime }) {
  const c = useContent();
  const accent = c.accent;
  const lowV = num(c.low), highV = num(c.high), avgV = num(c.avg), nowV = c.deal;
  const span = Math.max(1, highV - lowV);

  const titleO = tw(localTime, 0, 1, 0.05, 0.5);
  const titleY = tw(localTime, 26, 0, 0.05, 0.5, Easing.easeOutCubic);
  const cardO = tw(localTime, 0, 1, 0.3, 0.7);
  const cardScale = tw(localTime, 0.96, 1, 0.3, 0.75, Easing.easeOutCubic);

  // chart geometry (viewBox 780 x 300)
  const vals = [359.99, 352, 344, 300, 300, 358, 306, 250, 244, 262, 238, nowV];
  const n = vals.length;
  const X = (i) => 12 + (i / (n - 1)) * 756;
  const Y = (v) => 252 - ((v - lowV) / span) * 236;
  const line = vals.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ');
  const areaPts = `12,268 ${line} 768,268`;

  const drawT = tw(localTime, 0, 1, 0.6, 2.9, Easing.easeInOutCubic);
  const xDraw = 12 + drawT * 756;
  const valAt = (f) => {
    const pos = f * (n - 1), i = Math.floor(pos), fr = pos - i;
    return vals[i] + (vals[Math.min(i + 1, n - 1)] - vals[i]) * fr;
  };
  const dotY = Y(valAt(drawT));
  const drawDone = drawT > 0.999;
  const ping = drawDone ? (Math.sin(localTime * 4) + 1) / 2 : 0;
  const avgO = tw(localTime, 0, 1, 1.0, 1.5);

  const nowCount = money(tw(localTime, lowV, nowV, 0.6, 2.9, Easing.easeOutCubic) * 0 + tw(localTime, 0, nowV, 0.6, 2.9, Easing.easeOutExpo));
  const stat = (v, s, e) => money(tw(localTime, 0, v, s, e, Easing.easeOutExpo));

  // verdict
  let vTxt = 'Typical price', vBg = C.amber400, vCol = C.gray900;
  if (nowV <= lowV * 1.015) { vTxt = 'Lowest tracked price'; vBg = C.emerald600; vCol = C.white; }
  else if (nowV < avgV * 0.99) { vTxt = 'Below typical price'; vBg = C.emerald600; vCol = C.white; }
  else if (nowV > avgV * 1.03) { vTxt = 'Higher than usual'; vBg = C.rose600; vCol = C.white; }
  const vP = Easing.easeOutBack(clamp((localTime - 3.5) / 0.5, 0, 1));
  const vShow = clamp((localTime - 3.5) / 0.3, 0, 1);
  const dateO = tw(localTime, 0, 1, 4.0, 4.5);

  return (
    <Studio localTime={localTime} glow={C.indigo500}>
      <div style={{
        position: 'absolute', top: 210, left: 80, right: 80, textAlign: 'center',
        fontFamily: FONT, fontWeight: 800, fontSize: 82, lineHeight: 1.06, color: C.white,
        letterSpacing: '-0.02em', opacity: titleO, transform: `translateY(${titleY}px)`,
      }}>Is the price good <span style={{ color: C.indigo200 }}>right now?</span></div>

      <div style={{
        position: 'absolute', top: 470, left: 70, right: 70, background: C.white, borderRadius: 48,
        padding: '54px 52px 60px', boxShadow: `0 40px 90px ${hexA('#000000', 0.45)}`,
        opacity: cardO, transform: `scale(${cardScale})`, transformOrigin: 'center top',
      }}>
        {/* header row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontFamily: FONT, fontWeight: 700, fontSize: 32, letterSpacing: '0.14em', color: C.gray500, textTransform: 'uppercase', paddingTop: 12 }}>
            <span style={{ width: 20, height: 20, borderRadius: '50%', background: accent }} />90-day tracked price
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 30, letterSpacing: '0.14em', color: accent, textTransform: 'uppercase' }}>Now</div>
            <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 92, lineHeight: 1, color: C.gray900, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>{nowCount}</div>
          </div>
        </div>

        {/* chart */}
        <div style={{ marginTop: 30 }}>
          <svg viewBox="0 0 780 300" width="100%" style={{ display: 'block', overflow: 'visible' }}>
            <defs>
              <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor={hexA(accent, 0.28)} />
                <stop offset="1" stopColor={hexA(accent, 0.03)} />
              </linearGradient>
            </defs>
            {/* avg dashed reference */}
            <line x1="12" y1={Y(avgV)} x2="768" y2={Y(avgV)} stroke={C.gray300} strokeWidth="3" strokeDasharray="10 10" opacity={avgO} />
            <text x="760" y={Y(avgV) - 12} textAnchor="end" fontFamily={FONT} fontWeight="700" fontSize="26" fill={C.gray400} opacity={avgO}>AVG</text>
            <polygon points={areaPts} fill="url(#areaFill)" />
            <polyline points={line} fill="none" stroke={accent} strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
            {/* reveal mask: white cover over undrawn portion */}
            <rect x={xDraw} y="-20" width={Math.max(0, 800 - xDraw)} height="340" fill={C.white} />
            {/* leading / now dot */}
            <circle cx={drawDone ? X(n - 1) : xDraw} cy={drawDone ? Y(nowV) : dotY} r={13 + ping * 5} fill={accent} />
            <circle cx={drawDone ? X(n - 1) : xDraw} cy={drawDone ? Y(nowV) : dotY} r="7" fill="#fff" />
            {drawDone && <circle cx={X(n - 1)} cy={Y(nowV)} r={16 + ping * 26} fill="none" stroke={accent} strokeWidth="3" opacity={0.6 - ping * 0.6} />}
          </svg>
        </div>

        {/* stats */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 44, textAlign: 'center' }}>
          {[['90-day low', stat(lowV, 2.4, 2.9), C.emerald600], ['Average', stat(avgV, 2.6, 3.1), C.gray900], ['90-day high', stat(highV, 2.8, 3.3), C.gray900]].map((s, i) => (
            <div key={i} style={{ flex: 1 }}>
              <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 28, letterSpacing: '0.1em', color: C.gray400, textTransform: 'uppercase' }}>{s[0]}</div>
              <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 56, color: s[2], letterSpacing: '-0.01em', marginTop: 10, fontVariantNumeric: 'tabular-nums' }}>{s[1]}</div>
            </div>
          ))}
        </div>

        {/* verdict */}
        <div style={{ marginTop: 46, display: 'flex', justifyContent: 'center', opacity: vShow, transform: `scale(${0.7 + 0.3 * vP})` }}>
          <Tag bg={vBg} color={vCol} size={46}>{vTxt}</Tag>
        </div>
        <div style={{ marginTop: 30, textAlign: 'center', fontFamily: FONT, fontWeight: 500, fontSize: 32, color: C.gray400, opacity: dateO }}>
          Price checked {c.checkedDate}. Confirm at checkout.
        </div>
      </div>
      <Watermark />
    </Studio>
  );
}

// ── CTA ────────────────────────────────────────────────────────────────────
function CTA({ localTime }) {
  const c = useContent();
  const wmScale = Easing.easeOutBack(clamp((localTime - 0.1) / 0.55, 0, 1));
  const wmO = tw(localTime, 0, 1, 0.1, 0.5);
  const tagO = tw(localTime, 0, 1, 0.55, 0.95);
  const tagY = tw(localTime, 28, 0, 0.55, 0.95, Easing.easeOutBack);
  const btnP = Easing.easeOutBack(clamp((localTime - 1.0) / 0.5, 0, 1));
  const btnO = tw(localTime, 0, 1, 1.0, 1.35);
  const btnPulse = localTime > 1.5 ? 1 + 0.02 * Math.sin((localTime - 1.5) * 3) : 1;
  const urlO = tw(localTime, 0, 1, 1.4, 1.8);
  const linkO = tw(localTime, 0, 1, 1.8, 2.2);
  const bounce = Math.abs(Math.sin(localTime * 2.6)) * 18;
  const glowDrift = 20 * Math.sin(localTime * 0.7);

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', background: C.violet, fontFamily: FONT }}>
      <div style={{
        position: 'absolute', top: 200 + glowDrift, left: '50%', transform: 'translateX(-50%)',
        width: 1200, height: 900, borderRadius: '50%',
        background: `radial-gradient(closest-side, ${hexA('#a78bfa', 0.4)}, transparent 70%)`,
      }} />
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: `radial-gradient(${hexA('#c4b5fd', 0.16)} 2px, transparent 2px)`, backgroundSize: '46px 46px', opacity: 0.5,
      }} />

      <div style={{ position: 'absolute', top: 560, left: 0, right: 0, display: 'flex', justifyContent: 'center', opacity: wmO, transform: `scale(${0.7 + 0.3 * wmScale})` }}>
        <Wordmark size={124} gadget={C.white} drop={C.indigo200} />
      </div>

      <div style={{
        position: 'absolute', top: 760, left: 80, right: 80, textAlign: 'center', opacity: tagO, transform: `translateY(${tagY}px)`,
        fontFamily: FONT, fontWeight: 700, fontSize: 56, color: hexA('#ffffff', 0.92), letterSpacing: '-0.01em',
      }}>Full review + live price history</div>

      {/* Amazon CTA — the one place orange lives */}
      <div style={{ position: 'absolute', top: 920, left: 0, right: 0, display: 'flex', justifyContent: 'center', opacity: btnO, transform: `scale(${(0.7 + 0.3 * btnP) * btnPulse})` }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 22, background: C.amazon, color: C.gray900,
          fontFamily: FONT, fontWeight: 800, fontSize: 54, padding: '34px 66px', borderRadius: 26,
          boxShadow: `0 22px 60px ${hexA('#FF9900', 0.5)}`,
        }}>See it on Amazon <span style={{ fontSize: 56 }}>→</span></div>
      </div>

      <div style={{ position: 'absolute', top: 1120, left: 0, right: 0, display: 'flex', justifyContent: 'center', opacity: urlO }}>
        <div style={{ background: C.white, color: C.indigo700, fontFamily: FONT, fontWeight: 800, fontSize: 48, padding: '22px 52px', borderRadius: 999 }}>gadgetdrop.tech</div>
      </div>

      <div style={{ position: 'absolute', top: 1290, left: 0, right: 0, textAlign: 'center', opacity: linkO }}>
        <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 42, color: hexA('#ffffff', 0.8) }}>Link in the description</div>
        <div style={{ marginTop: 20, transform: `translateY(${bounce}px)`, fontSize: 64, color: C.white, lineHeight: 1 }}>↓</div>
      </div>
    </div>
  );
}

// ── LANDSCAPE (16:9) scenes — hero embed, CTA dropped ────────────────────────
const WL = 1920, HL = 1080;

function HookLandscape(props) {
  const c = useContent();
  if (c.hookStyle === 'question') return <HookLandscapeQuestion {...props} />;
  return <HookLandscapeSlam {...props} />;
}

function HookLandscapeSlam({ localTime }) {
  const c = useContent();
  const slam = Easing.easeOutBack(clamp((localTime - 0.55) / 0.55, 0, 1));
  const breathe = localTime > 1.15 ? 1 + 0.012 * Math.sin((localTime - 1.15) * 2.4) : 1;
  const priceScale = (0.55 + 0.45 * slam) * breathe;
  const priceO = clamp((localTime - 0.5) / 0.3, 0, 1);
  const strike = tw(localTime, 0, 1, 0.9, 1.4, Easing.easeInOutCubic);
  const wasO = tw(localTime, 0, 1, 0.7, 1.0);
  const tagP = Easing.easeOutBack(clamp((localTime - 1.35) / 0.4, 0, 1));
  const saveO = tw(localTime, 0, 1, 1.6, 2.0);
  const saveY = tw(localTime, 24, 0, 1.6, 2.0, Easing.easeOutBack);
  const chipO = tw(localTime, 0, 1, 2.0, 2.35);
  const chipY = tw(localTime, 38, 0, 2.0, 2.4, Easing.easeOutBack);
  return (
    <Studio localTime={localTime} glow={C.indigo500}>
      <div style={{ position: 'absolute', top: 80, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
        <Wordmark size={40} />
      </div>
      <Eyebrow top={200} localTime={localTime} at={0.15}>Today's Drop</Eyebrow>
      <div style={{ position: 'absolute', top: 340, left: 0, right: 0, height: 420, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 72 }}>
        <div style={{ opacity: priceO, transform: `scale(${priceScale})`, transformOrigin: 'center' }}>
          <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 280, lineHeight: 0.9, color: C.white, letterSpacing: '-0.03em', textShadow: `0 20px 80px ${hexA(C.indigo500, 0.55)}` }}>{c.dealPrice}</div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 26, alignItems: 'flex-start' }}>
          <div style={{ opacity: wasO, fontFamily: FONT, fontWeight: 700, fontSize: 64, color: C.gray400 }}>
            <span style={{ position: 'relative', display: 'inline-block' }}>
              was {c.listPrice}
              <span style={{ position: 'absolute', left: -6, right: -6, top: '52%', height: 6, borderRadius: 4, background: C.rose400, transform: `scaleX(${strike})`, transformOrigin: 'left center' }} />
            </span>
          </div>
          <div style={{ transform: `scale(${tagP})`, transformOrigin: 'left center' }}>
            <Tag bg={C.emerald600} size={52}>{c.pct}% OFF</Tag>
          </div>
          <div style={{ opacity: saveO, transform: `translateY(${saveY}px)`, fontFamily: FONT, fontWeight: 800, fontSize: 60, color: C.emerald400, letterSpacing: '-0.01em' }}>Save ${c.save}</div>
        </div>
      </div>
      <div style={{ position: 'absolute', top: 820, left: 0, right: 0, display: 'flex', justifyContent: 'center', opacity: chipO, transform: `translateY(${chipY}px)` }}>
        <div style={{ background: C.indigo100, color: C.indigo700, fontFamily: FONT, fontWeight: 800, fontSize: 48, padding: '20px 48px', borderRadius: 999, letterSpacing: '-0.01em' }}>{c.productName}</div>
      </div>
      {c.captions && (
        <Kinetic words={[`${c.pct}%`, 'OFF', 'RIGHT', 'NOW']} hi={[0]} accent={C.indigo200} localTime={localTime} start={2.4} y={956} size={52} />
      )}
    </Studio>
  );
}

function HookLandscapeQuestion({ localTime }) {
  const c = useContent();
  const q = tw(localTime, 0, 1, 0.2, 0.7);
  const qy = tw(localTime, 28, 0, 0.2, 0.7, Easing.easeOutBack);
  const chipP = Easing.easeOutBack(clamp((localTime - 1.0) / 0.5, 0, 1));
  const chipO = tw(localTime, 0, 1, 1.0, 1.35);
  const subO = tw(localTime, 0, 1, 1.6, 2.0);
  const bounce = Math.abs(Math.sin(localTime * 2.4)) * 12;
  return (
    <Studio localTime={localTime} glow={C.indigo500}>
      <div style={{ position: 'absolute', top: 80, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
        <Wordmark size={40} />
      </div>
      <div style={{ position: 'absolute', top: 400, left: 120, right: 120, textAlign: 'center', opacity: q, transform: `translateY(${qy}px)`, fontFamily: FONT, fontWeight: 800, fontSize: 128, lineHeight: 1.04, color: C.white, letterSpacing: '-0.02em' }}>Is <span style={{ color: C.indigo200 }}>{c.dealPrice}</span> a good deal?</div>
      <div style={{ position: 'absolute', top: 640, left: 0, right: 0, display: 'flex', justifyContent: 'center', opacity: chipO, transform: `scale(${0.7 + 0.3 * chipP})` }}>
        <div style={{ background: C.indigo100, color: C.indigo700, fontFamily: FONT, fontWeight: 800, fontSize: 48, padding: '20px 48px', borderRadius: 999 }}>{c.productName}</div>
      </div>
      <div style={{ position: 'absolute', top: 820, left: 0, right: 0, textAlign: 'center', opacity: subO, fontFamily: FONT, fontWeight: 700, fontSize: 46, color: C.gray400 }}>We tracked it for 90 days</div>
      <div style={{ position: 'absolute', top: 902, left: 0, right: 0, textAlign: 'center', opacity: subO, transform: `translateY(${bounce}px)`, fontSize: 56, color: C.indigo200, lineHeight: 1 }}>↓</div>
    </Studio>
  );
}

function ProductLandscape({ localTime, dur }) {
  const c = useContent();
  const cardO = tw(localTime, 0, 1, 0.05, 0.5);
  const cardScale = tw(localTime, 0.94, 1, 0.05, 0.6, Easing.easeOutCubic);
  const kb = clamp((localTime - 0.4) / ((dur || 6) - 0.4), 0, 1);
  const photoScale = 1 + 0.08 * kb;
  const photoO = tw(localTime, 0, 1, 0.35, 0.9);
  const detO = tw(localTime, 0, 1, 0.6, 1.0);
  const detX = tw(localTime, 40, 0, 0.6, 1.05, Easing.easeOutCubic);
  const starsAppear = clamp((localTime - 1.0) / 0.9, 0, 1);
  const priceSlam = Easing.easeOutBack(clamp((localTime - 1.5) / 0.5, 0, 1));
  const priceO = tw(localTime, 0, 1, 1.5, 1.85);
  const tagP = Easing.easeOutBack(clamp((localTime - 1.95) / 0.4, 0, 1));
  const float = 6 * Math.sin(localTime * 1.1);
  return (
    <Studio localTime={localTime} glow={C.indigo500}>
      <Eyebrow top={86} localTime={localTime} at={0.1}>Today's Drop</Eyebrow>
      <div style={{ position: 'absolute', top: 176, left: 110, right: 110, bottom: 104, background: C.white, borderRadius: 52, padding: 54, boxShadow: `0 40px 90px ${hexA('#000000', 0.45)}`, opacity: cardO, transform: `translateY(${float}px) scale(${cardScale})`, display: 'flex', gap: 56 }}>
        <div style={{ flex: '1.12', borderRadius: 36, background: `radial-gradient(circle at 50% 45%, ${C.gray50}, ${C.gray100})`, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${C.gray100}` }}>
          <img src={window.PRODUCT_IMG} alt="" style={{ width: '90%', height: '90%', objectFit: 'contain', opacity: photoO, transform: `scale(${photoScale})`, transformOrigin: 'center 55%', filter: 'drop-shadow(0 30px 40px rgba(0,0,0,0.28))' }} />
        </div>
        <div style={{ flex: '1', display: 'flex', flexDirection: 'column', justifyContent: 'center', opacity: detO, transform: `translateX(${detX}px)` }}>
          <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 88, lineHeight: 1.05, color: C.gray900, letterSpacing: '-0.02em' }}>{c.productName}</div>
          <div style={{ marginTop: 34, alignSelf: 'flex-start' }}>
            <Stars rating={c.rating} appear={starsAppear} size={66} />
          </div>
          <div style={{ marginTop: 52, display: 'flex', alignItems: 'flex-end', gap: 30 }}>
            <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 168, lineHeight: 0.85, color: C.gray900, letterSpacing: '-0.03em', opacity: priceO, transform: `scale(${0.7 + 0.3 * priceSlam})`, transformOrigin: 'left bottom' }}>{c.dealPrice}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'flex-start', paddingBottom: 14 }}>
              <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 52, color: C.gray400, textDecoration: 'line-through', opacity: priceO }}>{c.listPrice}</div>
              <div style={{ transform: `scale(${tagP})`, transformOrigin: 'left center' }}>
                <Tag bg={C.emerald600} size={40}>{c.pct}% OFF</Tag>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Studio>
  );
}

function FeatureLandscape({ scene, localTime }) {
  const c = useContent();
  const accent = c.accent;
  const step = scene.step || 1;
  const kickerO = tw(localTime, 0, 1, 0.2, 0.6);
  const target = num(scene.metric);
  const hasCount = /\d/.test(scene.metric || '') && target > 0;
  const countP = tw(localTime, 0, 1, 0.25, 1.15, Easing.easeOutExpo);
  const shown = hasCount ? Math.round(target * countP).toLocaleString('en-US') : scene.metric;
  const heroScale = Easing.easeOutBack(clamp((localTime - 0.2) / 0.5, 0, 1));
  const heroO = tw(localTime, 0, 1, 0.2, 0.55);
  const cardX = tw(localTime, 60, 0, 0.45, 0.95, Easing.easeOutCubic);
  const cardO = tw(localTime, 0, 1, 0.45, 0.9);
  const checkP = Easing.easeOutBack(clamp((localTime - 0.7) / 0.45, 0, 1));
  return (
    <Studio localTime={localTime} glow={C.indigo500}>
      <div style={{ position: 'absolute', top: 108, left: 0, right: 0, display: 'flex', gap: 16, justifyContent: 'center', alignItems: 'center' }}>
        {[1, 2, 3].map((s) => {
          const done = s < step, active = s === step;
          const fill = active ? tw(localTime, 0, 1, 0.1, 0.6) : done ? 1 : 0;
          return (
            <div key={s} style={{ width: active ? 96 : 30, height: 18, borderRadius: 999, background: done ? accent : hexA(C.white, 0.14), border: `2px solid ${done || active ? accent : hexA(C.white, 0.25)}`, overflow: 'hidden', position: 'relative' }}>
              {active && <div style={{ position: 'absolute', inset: 0, background: accent, transform: `scaleX(${fill})`, transformOrigin: 'left' }} />}
            </div>
          );
        })}
      </div>
      <div style={{ position: 'absolute', top: 200, left: 0, right: 0, textAlign: 'center', fontFamily: FONT, fontWeight: 800, fontSize: 34, letterSpacing: '0.28em', textTransform: 'uppercase', color: C.emerald400, opacity: kickerO }}>{scene.kicker}</div>
      <div style={{ position: 'absolute', left: 120, width: 800, top: 320, height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {scene.viz === 'scan' && (
          <div style={{ position: 'absolute', width: 440, height: 440, borderRadius: '50%', opacity: heroO }}>
            <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: `3px solid ${hexA(accent, 0.35)}` }} />
            <div style={{ position: 'absolute', inset: 80, borderRadius: '50%', border: `2px solid ${hexA(accent, 0.25)}` }} />
            <div style={{ position: 'absolute', inset: 160, borderRadius: '50%', border: `2px solid ${hexA(accent, 0.2)}` }} />
            <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: `conic-gradient(from ${localTime * 130}deg, ${hexA(accent, 0)} 0deg, ${hexA(accent, 0.5)} 55deg, ${hexA(accent, 0)} 120deg)` }} />
          </div>
        )}
        <div style={{ position: 'relative', fontFamily: FONT, fontWeight: 800, fontSize: 230, lineHeight: 0.9, color: C.white, letterSpacing: '-0.03em', opacity: heroO, transform: `scale(${0.6 + 0.4 * heroScale})`, textShadow: `0 16px 60px ${hexA(accent, 0.5)}` }}>
          {shown}<span style={{ fontSize: 96, color: accent, verticalAlign: scene.unit === '°' ? 'super' : 'baseline', marginLeft: scene.unit === '°' ? 4 : 0 }}>{scene.unit}</span>
        </div>
      </div>
      <div style={{ position: 'absolute', left: 1010, right: 120, top: 358, background: C.white, borderRadius: 44, padding: '54px 50px', boxShadow: `0 34px 80px ${hexA('#000000', 0.4)}`, opacity: cardO, transform: `translateX(${cardX}px)`, display: 'flex', gap: 40, alignItems: 'flex-start' }}>
        <div style={{ width: 122, height: 122, borderRadius: '50%', background: accent, flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${checkP})`, boxShadow: `0 12px 30px ${hexA(accent, 0.5)}` }}>
          <svg width="70" height="70" viewBox="0 0 24 24" fill="none">
            <path d="M4 12.5l5 5L20 6.5" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ strokeDasharray: 40, strokeDashoffset: 40 * (1 - clamp((localTime - 0.85) / 0.4, 0, 1)) }} />
          </svg>
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 64, lineHeight: 1.08, color: C.gray900, letterSpacing: '-0.02em' }}>{scene.title}</div>
          <div style={{ fontFamily: FONT, fontWeight: 500, fontSize: 42, lineHeight: 1.32, color: C.gray500, marginTop: 20 }}>{scene.sub}</div>
        </div>
      </div>
      {c.captions && scene.cap && (
        <Kinetic words={scene.cap} hi={scene.capHi || []} accent={accent} localTime={localTime} start={1.2} y={946} size={52} />
      )}
    </Studio>
  );
}

function PriceLandscape({ localTime }) {
  const c = useContent();
  const accent = c.accent;
  const lowV = num(c.low), highV = num(c.high), avgV = num(c.avg), nowV = c.deal;
  const span = Math.max(1, highV - lowV);
  const titleO = tw(localTime, 0, 1, 0.05, 0.5);
  const titleY = tw(localTime, 24, 0, 0.05, 0.5, Easing.easeOutCubic);
  const cardO = tw(localTime, 0, 1, 0.3, 0.7);
  const cardScale = tw(localTime, 0.97, 1, 0.3, 0.75, Easing.easeOutCubic);
  const vals = [359.99, 352, 344, 300, 300, 358, 306, 250, 244, 262, 238, nowV];
  const n = vals.length;
  const X = (i) => 20 + (i / (n - 1)) * 1640;
  const Y = (v) => 252 - ((v - lowV) / span) * 236;
  const line = vals.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ');
  const areaPts = `20,268 ${line} 1660,268`;
  const drawT = tw(localTime, 0, 1, 0.6, 2.9, Easing.easeInOutCubic);
  const xDraw = 20 + drawT * 1640;
  const valAt = (f) => { const pos = f * (n - 1), i = Math.floor(pos), fr = pos - i; return vals[i] + (vals[Math.min(i + 1, n - 1)] - vals[i]) * fr; };
  const dotY = Y(valAt(drawT));
  const drawDone = drawT > 0.999;
  const ping = drawDone ? (Math.sin(localTime * 4) + 1) / 2 : 0;
  const avgO = tw(localTime, 0, 1, 1.0, 1.5);
  const nowCount = money(tw(localTime, 0, nowV, 0.6, 2.9, Easing.easeOutExpo));
  const stat = (v, s, e) => money(tw(localTime, 0, v, s, e, Easing.easeOutExpo));
  let vTxt = 'Typical price', vBg = C.amber400, vCol = C.gray900;
  if (nowV <= lowV * 1.015) { vTxt = 'Lowest tracked price'; vBg = C.emerald600; vCol = C.white; }
  else if (nowV < avgV * 0.99) { vTxt = 'Below typical price'; vBg = C.emerald600; vCol = C.white; }
  else if (nowV > avgV * 1.03) { vTxt = 'Higher than usual'; vBg = C.rose600; vCol = C.white; }
  const vP = Easing.easeOutBack(clamp((localTime - 3.5) / 0.5, 0, 1));
  const vShow = clamp((localTime - 3.5) / 0.3, 0, 1);
  const dateO = tw(localTime, 0, 1, 4.2, 4.7);
  return (
    <Studio localTime={localTime} glow={C.indigo500}>
      <div style={{ position: 'absolute', top: 96, left: 0, right: 0, textAlign: 'center', fontFamily: FONT, fontWeight: 800, fontSize: 76, lineHeight: 1.05, color: C.white, letterSpacing: '-0.02em', opacity: titleO, transform: `translateY(${titleY}px)` }}>Is the price good <span style={{ color: C.indigo200 }}>right now?</span></div>
      <div style={{ position: 'absolute', top: 236, left: 90, right: 90, background: C.white, border: 'none', borderRadius: 48, padding: '44px 56px 38px', boxShadow: `0 40px 90px ${hexA('#000000', 0.45)}`, opacity: cardO, transform: `scale(${cardScale})`, transformOrigin: 'center top' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontFamily: FONT, fontWeight: 700, fontSize: 32, letterSpacing: '0.14em', color: C.gray500, textTransform: 'uppercase', paddingTop: 16 }}>
            <span style={{ width: 20, height: 20, borderRadius: '50%', background: accent }} />90-day tracked price
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 30, letterSpacing: '0.14em', color: accent, textTransform: 'uppercase' }}>Now</div>
            <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 96, lineHeight: 1, color: C.gray900, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>{nowCount}</div>
          </div>
        </div>
        <div style={{ marginTop: 10, height: 300 }}>
          <svg viewBox="0 0 1680 300" width="100%" height="300" preserveAspectRatio="xMidYMid meet" style={{ display: 'block', overflow: 'visible' }}>
            <defs>
              <linearGradient id="areaFillL" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor={hexA(accent, 0.28)} />
                <stop offset="1" stopColor={hexA(accent, 0.03)} />
              </linearGradient>
            </defs>
            <line x1="20" y1={Y(avgV)} x2="1660" y2={Y(avgV)} stroke={C.gray300} strokeWidth="3" strokeDasharray="10 10" opacity={avgO} />
            <text x="1652" y={Y(avgV) - 12} textAnchor="end" fontFamily={FONT} fontWeight="700" fontSize="26" fill={C.gray400} opacity={avgO}>AVG</text>
            <polygon points={areaPts} fill="url(#areaFillL)" />
            <polyline points={line} fill="none" stroke={accent} strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
            <rect x={xDraw} y="-20" width={Math.max(0, 1720 - xDraw)} height="340" fill={C.white} />
            <circle cx={drawDone ? X(n - 1) : xDraw} cy={drawDone ? Y(nowV) : dotY} r={13 + ping * 5} fill={accent} />
            <circle cx={drawDone ? X(n - 1) : xDraw} cy={drawDone ? Y(nowV) : dotY} r="7" fill="#fff" />
            {drawDone && <circle cx={X(n - 1)} cy={Y(nowV)} r={16 + ping * 26} fill="none" stroke={accent} strokeWidth="3" opacity={0.6 - ping * 0.6} />}
          </svg>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 22 }}>
          <div style={{ display: 'flex', gap: 76 }}>
            {[['90-day low', stat(lowV, 2.4, 2.9), C.emerald600], ['Average', stat(avgV, 2.6, 3.1), C.gray900], ['90-day high', stat(highV, 2.8, 3.3), C.gray900]].map((s, i) => (
              <div key={i}>
                <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 28, letterSpacing: '0.1em', color: C.gray400, textTransform: 'uppercase' }}>{s[0]}</div>
                <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 58, color: s[2], letterSpacing: '-0.01em', marginTop: 8, fontVariantNumeric: 'tabular-nums' }}>{s[1]}</div>
              </div>
            ))}
          </div>
          <div style={{ opacity: vShow, transform: `scale(${0.7 + 0.3 * vP})`, transformOrigin: 'right center' }}>
            <Tag bg={vBg} color={vCol} size={44}>{vTxt}</Tag>
          </div>
        </div>
        <div style={{ marginTop: 22, textAlign: 'center', fontFamily: FONT, fontWeight: 500, fontSize: 30, color: C.gray400, opacity: dateO }}>
          Price checked {c.checkedDate}. Confirm at checkout.
        </div>
      </div>
    </Studio>
  );
}

// ── shared content model + control panel ─────────────────────────────────────
function buildContent(t) {
  const list = num(t.listPrice), deal = num(t.dealPrice);
  const pct = list > 0 ? Math.round((1 - deal / list) * 100) : 0;
  const save = Math.max(0, Math.round(list - deal));
  return { ...t, accent: t.accent || C.indigo600, list, deal, pct, save };
}

function ControlPanel({ t, setTweak, title }) {
  return (
    <TweaksPanel title={title}>
      <TweakSection label="Video" />
      <TweakRadio label="Hook" value={t.hookStyle}
        options={[{ value: 'slam', label: 'Price slam' }, { value: 'question', label: 'Question' }]}
        onChange={(v) => setTweak('hookStyle', v)} />
      <TweakColor label="Accent" value={t.accent}
        options={[C.indigo600, C.emerald600, C.rose600, C.sky500]}
        onChange={(v) => setTweak('accent', v)} />
      <TweakToggle label="Kinetic captions" value={t.captions} onChange={(v) => setTweak('captions', v)} />
      <TweakSection label="Product" />
      <TweakText label="Name" value={t.productName} onChange={(v) => setTweak('productName', v)} />
      <TweakSlider label="Rating" value={t.rating} min={1} max={5} step={0.5} onChange={(v) => setTweak('rating', v)} />
      <TweakSection label="Pricing" />
      <TweakText label="Deal price" value={t.dealPrice} onChange={(v) => setTweak('dealPrice', v)} />
      <TweakText label="List price" value={t.listPrice} onChange={(v) => setTweak('listPrice', v)} />
      <TweakSection label="Price history" />
      <TweakText label="90-day low" value={t.low} onChange={(v) => setTweak('low', v)} />
      <TweakText label="Average" value={t.avg} onChange={(v) => setTweak('avg', v)} />
      <TweakText label="90-day high" value={t.high} onChange={(v) => setTweak('high', v)} />
    </TweaksPanel>
  );
}

// ── top-level components ──────────────────────────────────────────────────────
function GadgetDropShort() {
  const [t, setTweak] = useTweaks(window.OM_TWEAKS);
  return (
    <ContentCtx.Provider value={buildContent(t)}>
      <SceneStage width={W} height={H} scenes={window.OM_SCENES} playback={window.OM_PLAYBACK} bg={C.studioTop}>
        {{ Hook, Product, Feature, Price, CTA }}
      </SceneStage>
      <ControlPanel t={t} setTweak={setTweak} title="Short (9:16)" />
    </ContentCtx.Provider>
  );
}

function GadgetDropHero() {
  const [t, setTweak] = useTweaks(window.OM_TWEAKS);
  return (
    <ContentCtx.Provider value={buildContent(t)}>
      <SceneStage width={WL} height={HL} scenes={window.OM_SCENES} playback={window.OM_PLAYBACK} bg={C.studioTop}>
        {{ Hook: HookLandscape, Product: ProductLandscape, Feature: FeatureLandscape, Price: PriceLandscape }}
      </SceneStage>
      <ControlPanel t={t} setTweak={setTweak} title="Hero (16:9)" />
    </ContentCtx.Provider>
  );
}

window.GadgetDropShort = GadgetDropShort;
window.GadgetDropHero = GadgetDropHero;
