# Saccade: read rendered text images through the real page (file input → pipeline → output box) and score them.
# python3 tests/saccade-read.py   (needs: pip install playwright; playwright's chromium)
import asyncio, base64, os, sys, tempfile, time, json
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); PAGE = "file://" + os.path.join(HERE, "..", "Saccade.html")
TEXT = ["The quick brown fox jumps over the lazy dog.", "PACK MY BOX WITH FIVE DOZEN LIQUOR JUGS!",
        "Saccade reads 0123456789 - and (some) symbols?", "It's offline, single-file, zero dependencies."]
CASES = [("sans-serif", 24, False), ("sans-serif", 16, False), ("sans-serif", 12, False), ("sans-serif", 32, False), ("serif", 24, False), ("serif", 16, False),
         ("monospace", 24, False), ("sans-serif", 24, True)]
def lev(a, b):
    p = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        c = [i]
        for j, cb in enumerate(b, 1): c.append(min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (ca != cb)))
        p = c
    return p[-1]
def score(got, want):
    g = [l.strip() for l in got.strip().split("\n") if l.strip()]; w = want
    nospace = lambda s: "".join(s.split())
    chars = 1 - lev(nospace("\n".join(g)), nospace("\n".join(w))) / max(1, len(nospace("\n".join(w))))
    full = 1 - lev(" ".join(" ".join(g).split()), " ".join(" ".join(w).split())) / max(1, len(" ".join(w)))
    return max(0, chars), max(0, full)
async def main():
    only = sys.argv[1:] and int(sys.argv[1])
    async with async_playwright() as p:
        b = await p.chromium.launch(); tmp = tempfile.mkdtemp(); out = []
        mk = await b.new_page()
        for k, (font, px, dark) in enumerate(CASES):
            if only is not None and only != "" and k != only and isinstance(only, int) and len(sys.argv) > 1: continue
            url = await mk.evaluate("""([lines, font, px, dark]) => { const c = document.createElement('canvas'), x = c.getContext('2d');
              x.font = `${px}px ${font}`; const w = Math.max(...lines.map(l => x.measureText(l).width)) + px * 2;
              c.width = Math.ceil(w); c.height = Math.ceil(px * 1.6 * lines.length + px * 2);
              x.fillStyle = dark ? '#1b1d22' : '#fff'; x.fillRect(0, 0, c.width, c.height);
              x.fillStyle = dark ? '#e8e8e8' : '#111'; x.font = `${px}px ${font}`; x.textBaseline = 'alphabetic';
              lines.forEach((l, i) => x.fillText(l, px, px * 1.6 * (i + 1) + px * 0.3)); return c.toDataURL('image/png'); }""", [TEXT, font, px, dark])
            f = os.path.join(tmp, f"case{k}.png"); open(f, "wb").write(base64.b64decode(url.split(",")[1]))
            pg = await b.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.goto(PAGE); await pg.evaluate("() => localStorage.clear()"); await pg.reload()
            t0 = time.time(); await pg.set_input_files("#file-input", f)
            # if the page asks for labels (older versions, or label mode on), just press DONE each time
            for _ in range(600):
                if await pg.evaluate("() => document.getElementById('st-emit')?.className.includes('done')"): break
                for sel in ("#btn-label-done", "#btn-gapfill-done"):
                    if await pg.evaluate(f"() => document.querySelector('{sel}')?.closest('.on, [class*=on]') && getComputedStyle(document.querySelector('{sel}')).display !== 'none' && document.querySelector('{sel}').offsetParent !== null"):
                        await pg.click(sel)
                await pg.wait_for_timeout(250)
            got = await pg.evaluate("() => document.getElementById('output').value")
            c, fl = score(got, TEXT)
            out.append(dict(case=f"{font} {px}px{' dark' if dark else ''}", chars=round(c, 3), full=round(fl, 3), secs=round(time.time() - t0, 1), got=got, errors=errs))
            print(f"{out[-1]['case']:<22} chars {c:.3f}  with spaces {fl:.3f}  {out[-1]['secs']:>5}s  {'ERR ' + str(errs) if errs else ''}")
            for l in got.split("\n")[:4]: print("    |", l)
            await pg.close()
        await b.close()
        m = sum(o["chars"] for o in out) / max(1, len(out)); print(f"mean char accuracy {m:.3f}")
        json.dump(out, open(os.path.join(tmp, "results.json"), "w"), indent=1)
asyncio.run(main())
