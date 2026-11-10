#!/usr/bin/env python3
"""
Graba el video demo del simulador "¿Cuándo me pensiono si soy contratista del Estado?".

Método: captura cuadro por cuadro (30 fps) con Playwright + Chromium y ensambla con ffmpeg.
Cada cuadro se calcula de forma determinista a partir del tiempo t (cámara, cursor, slider,
anotaciones), así que el video sale fluido aunque el screenshot sea lento.

Uso:
    python3 grabar_demo.py                      # usa la carpeta de este script
    python3 grabar_demo.py --html ruta/simulador_pension.html --out ruta/salida

Requisitos: playwright (python) con Chromium instalado, ffmpeg con libx264.
No modifica simulador_pension.html: trabaja sobre una copia con <!doctype html>.
"""
import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

FPS = 30
W, H = 1920, 1080
DURACION = 40.0  # segundos

# ---------------------------------------------------------------------------
# Planos de cámara (coordenadas de página a escala 1, viewport 1920x1080)
#   s = zoom, (cx, cy) = punto de la página que queda en el centro de la pantalla
# ---------------------------------------------------------------------------
CAM_A = (1.25, 960, 462)    # vista general: título, casos, veredicto, cuadrícula
CAM_B = (2.05, 1152, 527)   # acercamiento a la edad, veredicto y cuadrícula
CAM_C = (1.25, 960, 737)    # slider + resultados + grupo (se recalcula con el alto real del formulario)
CAM_D = (1.25, 960, 676)    # botones de casos + resultados

# Línea de tiempo (segundos)
T_A_END = 4.0           # fin de la vista general
T_B_IN = (4.0, 6.2)     # zoom a la cuadrícula
T_RING1 = (6.6, 10.6)   # resalta "800 de 1.000 semanas"
T_C_IN = (11.0, 12.8)   # paneo al slider
T_CUR_IN = (11.6, 13.1)  # el cursor entra hasta el control del slider
T_PRESS = 13.25
T_DRAG = (13.45, 20.65)  # 5,75 -> 9 meses (7,2 s)
T_RING2 = (20.9, 23.4)  # resalta edad y grupo "Estables"
T_D_IN = (23.4, 24.9)   # paneo a los botones de casos
T_CUR_OCA = (23.7, 25.0)
T_CLICK_OCA = 25.15
T_RING3 = (26.2, 30.4)  # resalta "348 de 1.000 semanas"
T_CUR_TIP = (30.9, 31.9)
T_CLICK_TIP = 32.05
T_RING4 = (33.2, 38.0)  # resalta el veredicto del contratista típico
T_CUR_OUT = (33.4, 34.8)

MESES_INI, MESES_FIN, PASO = 5.75, 9.0, 0.05


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def prog(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


def lerp(a, b, k):
    return a + (b - a) * k


def lerp_cam(c1, c2, k):
    # interpolamos el zoom en escala logarítmica para que el movimiento se sienta uniforme
    s = math.exp(lerp(math.log(c1[0]), math.log(c2[0]), k))
    return (s, lerp(c1[1], c2[1], k), lerp(c1[2], c2[2], k))


def camera(t):
    if t < T_B_IN[0]:
        return CAM_A
    if t < T_B_IN[1]:
        return lerp_cam(CAM_A, CAM_B, ease(prog(t, *T_B_IN)))
    if t < T_C_IN[0]:
        return CAM_B
    if t < T_C_IN[1]:
        return lerp_cam(CAM_B, CAM_C, ease(prog(t, *T_C_IN)))
    if t < T_D_IN[0]:
        return CAM_C
    if t < T_D_IN[1]:
        return lerp_cam(CAM_C, CAM_D, ease(prog(t, *T_D_IN)))
    return CAM_D


def meses_en(t):
    k = ease(prog(t, *T_DRAG))
    v = MESES_INI + (MESES_FIN - MESES_INI) * k
    return round(round(v / PASO) * PASO, 2)


def fade(t, a, b, d=0.35):
    """Opacidad 0->1->0 en el intervalo [a, b] con rampas de d segundos."""
    if t <= a or t >= b:
        return 0.0
    return ease(min((t - a) / d, (b - t) / d, 1.0))


def ripple(t, tc, dur=0.55):
    if tc <= t <= tc + dur:
        k = (t - tc) / dur
        return {"k": ease_out(k)}
    return None


def press_scale(t, tc):
    d = t - tc
    if -0.06 <= d <= 0.16:
        return 0.82
    return 1.0


def preparar_posiciones(P):
    """Ajusta el plano del slider y la anotación al alto real del formulario."""
    global CAM_C
    fl, ft, fr, fb = P["form"]
    top, bottom = ft - 15, fb + 175          # edad grande arriba; grupo y anotación abajo
    s = min(1080 / (bottom - top), 1.4)
    CAM_C = (s, 960, (top + bottom) / 2)
    return {"oca": tuple(P["oca"]), "tip": tuple(P["tip"]), "sl_x": P["sl_x"], "sl_w": P["sl_w"],
            "sl_cy": P["sl_cy"], "n2_at": (fl + 2, fb + 16)}


def build_state(t, P):
    """Estado completo del cuadro en el tiempo t. P = posiciones (coordenadas de página)."""
    st = {"cam": camera(t)}

    # ---- cursor (coordenadas de página) ----
    thumb = lambda v: (P["sl_x"] + 8 + v / 12 * (P["sl_w"] - 16), P["sl_cy"])
    entrada = (1560.0, 1180.0)
    cur = None
    scale = 1.0
    rip = None
    if T_CUR_IN[0] <= t < T_DRAG[0]:
        k = ease(prog(t, *T_CUR_IN))
        tx, ty = thumb(MESES_INI)
        cur = (lerp(entrada[0], tx, k), lerp(entrada[1], ty, k))
        scale = press_scale(t, T_PRESS)
        if t >= T_PRESS:
            scale = 0.82
        rip = ripple(t, T_PRESS)
    elif T_DRAG[0] <= t < T_DRAG[1] + 0.2:
        cur = thumb(meses_en(t))
        scale = 0.82 if t < T_DRAG[1] else 1.0
    elif T_DRAG[1] + 0.2 <= t < T_CUR_OCA[0]:
        cur = thumb(MESES_FIN)
    elif T_CUR_OCA[0] <= t < T_CUR_TIP[0]:
        k = ease(prog(t, *T_CUR_OCA))
        a = thumb(MESES_FIN)
        b = P["oca"]
        # pequeño arco para que el movimiento se vea natural
        arc = math.sin(math.pi * k) * -40
        cur = (lerp(a[0], b[0], k), lerp(a[1], b[1], k) + arc)
        scale = press_scale(t, T_CLICK_OCA)
        rip = ripple(t, T_CLICK_OCA)
    elif T_CUR_TIP[0] <= t < T_CUR_OUT[0]:
        k = ease(prog(t, *T_CUR_TIP))
        a, b = P["oca"], P["tip"]
        cur = (lerp(a[0], b[0], k), lerp(a[1], b[1], k))
        scale = press_scale(t, T_CLICK_TIP)
        rip = ripple(t, T_CLICK_TIP)
    elif T_CUR_OUT[0] <= t < T_CUR_OUT[1]:
        k = ease(prog(t, *T_CUR_OUT))
        a = P["tip"]
        cur = (lerp(a[0], 1240, k), lerp(a[1], 236, k))
    elif t >= T_CUR_OUT[1]:
        cur = (1240, 236)
    # opacidad del cursor
    cop = 0.0
    if cur is not None:
        cop = ease(prog(t, T_CUR_IN[0], T_CUR_IN[0] + 0.4))
        if t >= T_CUR_OUT[0]:
            cop = 1 - ease(prog(t, T_CUR_OUT[0] + 0.6, T_CUR_OUT[1]))
    st["cursor"] = {"x": cur[0] if cur else 0, "y": cur[1] if cur else 0,
                    "o": cop, "s": scale, "rip": rip}

    # ---- slider ----
    if T_DRAG[0] <= t <= T_DRAG[1] + 0.05:
        st["meses"] = meses_en(t)

    # ---- clics ----
    st["click"] = None
    for tc, bid in ((T_CLICK_OCA, "p-ocasional"), (T_CLICK_TIP, "p-tipico")):
        if tc <= t < tc + 1 / FPS:
            st["click"] = bid

    # ---- anotaciones ----
    st["n2_at"] = P["n2_at"]
    st["notes"] = {
        "n1": fade(t, 0.35, 3.85, 0.4),
        "n2": fade(t, 12.9, 23.3, 0.4),
    }

    # ---- resaltados ----
    rings = []
    o = fade(t, *T_RING1, d=0.4)
    if o:
        rings.append({"id": "ledger-count", "o": o, "c": "bad", "pad": [10, 3]})
    o = fade(t, *T_RING2, d=0.35)
    if o:
        rings.append({"id": "age-big", "o": o, "c": "ok", "pad": [10, 6]})
        rings.append({"id": "g-name", "o": o, "c": "ok", "pad": [8, 2]})
    o = fade(t, *T_RING3, d=0.4)
    if o:
        rings.append({"id": "ledger-count", "o": o, "c": "bad", "pad": [10, 3]})
    o = fade(t, *T_RING4, d=0.4)
    if o:
        rings.append({"id": "verdict-line", "o": o, "c": "bad", "pad": [12, 4]})
    st["rings"] = rings
    return st


# ---------------------------------------------------------------------------
# JS inyectado: cámara, cursor, anotaciones y anillos de resaltado
# ---------------------------------------------------------------------------
SETUP_JS = r"""
() => {
  const css = document.createElement('style');
  css.textContent = `
    html{overflow:hidden}
    .tl-fill{transition:none!important}
    #demo-layer{position:fixed;inset:0;pointer-events:none;z-index:99999}
    #demo-cursor{position:absolute;left:0;top:0;width:38px;height:46px;transform-origin:4px 3px;
      filter:drop-shadow(0 3px 5px rgba(0,0,0,.35))}
    #demo-rip{position:absolute;left:0;top:0;border-radius:50%;border:4px solid #0d6e6a;opacity:0}
    .demo-note{position:absolute;left:0;top:0;background:#ffffff;border:1px solid #d9dee6;border-left:6px solid #0d6e6a;
      border-radius:12px;padding:16px 22px 18px;box-shadow:0 10px 30px rgba(21,35,58,.16);opacity:0;color:#15233a}
    .demo-note .e{font-family:"IBM Plex Mono",ui-monospace,monospace;font-weight:500;font-size:17px;letter-spacing:.08em;
      text-transform:uppercase;color:#0d6e6a;margin-bottom:6px}
    .demo-note .b{font-family:"Archivo","Helvetica Neue",Arial,sans-serif;font-weight:700;font-size:28px;line-height:1.2}
    .demo-ring{position:absolute;border-radius:12px;border:4px solid;opacity:0;box-shadow:0 0 0 6px rgba(255,255,255,.55)}
  `;
  document.head.appendChild(css);
  const L = document.createElement('div'); L.id = 'demo-layer';
  L.innerHTML = `
    <div class="demo-note" id="n1" style="width:500px">
      <div class="e">Caso real anonimizado</div>
      <div class="b">Mujer de 25 años, sin semanas cotizadas</div>
    </div>
    <div class="demo-note" id="n2" style="width:470px">
      <div class="e">Mismo caso, otro ritmo</div>
      <div class="b">¿Y si tuviera contrato 9 meses al año en vez de 5,75?</div>
    </div>
    <div class="demo-ring" id="r0"></div><div class="demo-ring" id="r1"></div>
    <div id="demo-rip"></div>
    <svg id="demo-cursor" viewBox="0 0 26 32" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 2 L2 25 L8 19.5 L12.2 29 L16.4 27.2 L12.3 17.9 L20.5 17.9 Z"
        fill="#15233a" stroke="#ffffff" stroke-width="2" stroke-linejoin="round"/>
    </svg>`;
  document.documentElement.appendChild(L);

  const body = document.body;
  const br = body.getBoundingClientRect();
  body.style.transformOrigin = '0 0';
  const B = {x: br.left, y: br.top};
  let cam = {s:1, tx:0, ty:0};
  const toView = (x, y) => ({x: B.x + cam.s*(x - B.x) + cam.tx, y: B.y + cam.s*(y - B.y) + cam.ty});
  const COL = {ok:'#177245', bad:'#b4431c'};

  window.__demo = {
    frame(st){
      // cámara
      const [s, cx, cy] = st.cam;
      cam = {s, tx: 960 - B.x - s*(cx - B.x), ty: 540 - B.y - s*(cy - B.y)};
      body.style.transform = `translate(${cam.tx}px, ${cam.ty}px) scale(${s})`;
      // slider
      if (st.meses !== undefined && st.meses !== null){
        const el = document.getElementById('meses');
        const v = st.meses.toFixed(2);
        if (el.value !== String(+v) && (+el.value).toFixed(2) !== v){
          el.value = v; el.dispatchEvent(new Event('input', {bubbles:true}));
        }
      }
      // clic
      if (st.click){ document.getElementById(st.click).click(); }
      // anotaciones (ancladas a la página)
      const n1 = document.getElementById('n1'), n2 = document.getElementById('n2');
      let p = toView(1078, 52);
      n1.style.transform = `translate(${p.x}px, ${p.y + (1-st.notes.n1)*12}px)`; n1.style.opacity = st.notes.n1;
      p = toView(st.n2_at[0], st.n2_at[1]);
      n2.style.transform = `translate(${p.x}px, ${p.y + (1-st.notes.n2)*12}px)`; n2.style.opacity = st.notes.n2;
      // anillos
      for (let i = 0; i < 2; i++){
        const r = document.getElementById('r'+i), g = st.rings[i];
        if (!g){ r.style.opacity = 0; continue; }
        const e = document.getElementById(g.id), rc = e.getBoundingClientRect();
        let x = rc.left, w = rc.width;
        if (g.id === 'age-big'){ // el número + "años"
          const sm = e.querySelector('small'); if (sm){ w = sm.getBoundingClientRect().right - rc.left; }
        }
        const px = g.pad[0] * cam.s / 1.25, py = g.pad[1] * cam.s / 1.25;
        Object.assign(r.style, {left:(x-px)+'px', top:(rc.top-py)+'px', width:(w+2*px)+'px',
          height:(rc.height+2*py)+'px', borderColor:COL[g.c], opacity:g.o});
      }
      // cursor
      const c = st.cursor, cur = document.getElementById('demo-cursor'), rip = document.getElementById('demo-rip');
      const v = toView(c.x, c.y);
      cur.style.opacity = c.o;
      cur.style.transform = `translate(${v.x - 4}px, ${v.y - 3}px) scale(${c.s})`;
      if (c.rip){
        const R = 14 + 34*c.rip.k;
        Object.assign(rip.style, {width:2*R+'px', height:2*R+'px', opacity:(1-c.rip.k)*0.9,
          transform:`translate(${v.x - R}px, ${v.y - R}px)`});
      } else { rip.style.opacity = 0; }
      return document.getElementById('age-big').textContent;
    }
  };
  // posiciones en coordenadas de página (sin transformación)
  const rc = id => document.getElementById(id).getBoundingClientRect();
  const c = id => { const r = rc(id); return [r.left + r.width*0.5, r.top + r.height*0.55]; };
  const sl = rc('meses');
  const fm = rc('form');
  return {oca: c('p-ocasional'), tip: c('p-tipico'), sl_x: sl.left, sl_w: sl.width, sl_cy: sl.top + sl.height/2,
          form: [fm.left, fm.top, fm.right, fm.bottom]};
}
"""

# Cifras esperadas en momentos clave (t, texto de #age-big)
CHECKS = [(2.0, "65,0años"), (9.0, "65,0años"), (22.0, "50,6años"), (28.0, "117,0años"), (38.0, "62,8años")]


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(here / "simulador_pension.html"))
    ap.add_argument("--out", default=str(here))
    ap.add_argument("--work", default=None, help="carpeta temporal para la copia y los cuadros")
    args = ap.parse_args()

    work = Path(args.work or tempfile.mkdtemp(prefix="demo_simulador_"))
    work.mkdir(parents=True, exist_ok=True)
    frames = work / "frames"
    if frames.exists():
        shutil.rmtree(frames)
    frames.mkdir()

    src = Path(args.html).read_text(encoding="utf-8")
    copia = work / "simulador_grabacion.html"
    copia.write_text('<!doctype html><html lang="es"><head><meta charset="utf-8">'
                     '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>'
                     + src + "</body></html>", encoding="utf-8")

    launch = {}
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        launch["proxy"] = {"server": proxy}

    n_frames = int(round(DURACION * FPS))
    checks = {int(round(t * FPS)): (t, exp) for t, exp in CHECKS}
    errores = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch)
        ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1,
                                  color_scheme="light", ignore_https_errors=True)
        page = ctx.new_page()
        page.goto(copia.as_uri() + "#intermitente", wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(1200)
        P = page.evaluate(SETUP_JS)
        P = preparar_posiciones(P)
        # calentamiento: renderiza el primer cuadro dos veces para que fuentes y capas estén listas
        page.evaluate("st => window.__demo.frame(st)", build_state(0.0, P))
        page.wait_for_timeout(500)

        for i in range(n_frames):
            t = i / FPS
            st = build_state(t, P)
            age = page.evaluate("st => window.__demo.frame(st)", st)
            if st["click"]:
                page.wait_for_timeout(30)
            page.screenshot(path=str(frames / f"f{i:05d}.png"), type="png")
            if i in checks:
                tt, exp = checks[i]
                ok = age == exp
                print(f"  t={tt:5.1f}s  #age-big = {age!r:14} esperado {exp!r:14} {'OK' if ok else 'ERROR'}")
                if not ok:
                    errores.append((tt, age, exp))
            if i % 150 == 0:
                print(f"cuadro {i}/{n_frames}", flush=True)
        browser.close()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    mp4 = out / "demo_simulador.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "f%05d.png"),
           "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-level", "4.1",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(mp4)]
    subprocess.run(cmd, check=True)
    # portada: caso Intermitente con 65,0 (t = 3,0 s)
    shutil.copy(frames / f"f{int(3.0 * FPS):05d}.png", out / "demo_simulador_poster.png")
    print("Video:", mp4)
    print("Portada:", out / "demo_simulador_poster.png")
    if errores:
        print("CIFRAS INCORRECTAS:", errores)
        sys.exit(1)


if __name__ == "__main__":
    main()
