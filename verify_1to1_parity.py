#!/usr/bin/env python3
"""
Automated 1:1 Design Parity Auditor:
Compares live https://www.life.gov.sg/ against live http://127.0.0.1:8787/
via Chrome DevTools Protocol (CDP port 9222) and generates side-by-side
section proof crops using Pillow.
"""
import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw
import websockets

CDP_URL = os.getenv("CDP_URL", "http://127.0.0.1:9222/json")
ART_DIR = Path(os.getenv("PARITY_OUT_DIR", "./parity_proof"))
ART_DIR.mkdir(parents=True, exist_ok=True)

LIFESG_JS = r"""(() => {
  const gs = (el) => {
    if (!el) return null;
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {
      w: Math.round(r.width), h: Math.round(r.height),
      fs: s.fontSize, fw: s.fontWeight, lh: s.lineHeight, ls: s.letterSpacing,
      br: s.borderRadius, pad: s.padding, bg: s.backgroundColor,
      bt: s.borderTopWidth, bb: s.borderBottomWidth, bc: s.borderBottomColor,
      shadow: s.boxShadow, gap: s.gap,
      cols: s.gridTemplateColumns ? s.gridTemplateColumns.split(' ').length : 0
    };
  };
  const popLink = document.querySelector('.ll5rffu');
  const popText = popLink?.querySelector('span, p, div') || popLink;
  const momentCard = document.querySelector('.mtu900m');
  const topic1 = document.querySelector('.thwhats');
  const topic4 = document.querySelectorAll('.thwhats')[3];
  const headerBtn = document.querySelector('nav button[class*="mf6do54"]');
  const searchBtn = document.querySelector('button[class*="Buttonstyles"]');
  const chip1 = document.querySelector('a[class*="ts2ljtd"]');
  const footer = document.querySelector('footer');
  const footerTop = document.querySelector('footer section.t1nab4kr');
  const footerBottom = document.querySelector('footer section.b1ni5lnl');
  const storeImg = document.querySelector('img[alt*="App Store"]');
  return {
    masthead_h: Math.round((document.querySelector('sgds-masthead')?.getBoundingClientRect().height) || 0),
    header_h: Math.round((document.querySelector('nav')?.closest('section')?.parentElement?.getBoundingClientRect().height) || 0),
    header_cta: gs(headerBtn),
    hero_h: Math.round((document.querySelector('.ho0y8z1')?.getBoundingClientRect().height) || 0),
    hero_h1: gs(document.querySelector('.ho0y8z1 h1')),
    search_input: gs(document.querySelector('input')),
    search_btn: gs(searchBtn),
    chip1: gs(chip1),
    pop_count: document.querySelectorAll('.ll5rffu').length,
    pop_sec_h: Math.round((document.querySelectorAll('section.szyy60j.h1uj6h92')[0]?.getBoundingClientRect().height) || 0),
    pop_h2: gs(document.querySelectorAll('section.szyy60j.h1uj6h92')[0]?.querySelector('h2')),
    pop_grid: gs(popLink?.parentElement),
    pop_item: gs(popLink),
    pop_text: gs(popText),
    pop_chev_w: Math.round((popLink?.querySelector('svg')?.getBoundingClientRect().width) || 0),
    moments_count: document.querySelectorAll('.mtu900m').length,
    moment_card: gs(momentCard),
    moment_icon_w: Math.round((momentCard?.querySelector('img')?.getBoundingClientRect().width) || 0),
    moment_h5: gs(momentCard?.querySelector('h5')),
    moment_p: gs(momentCard?.querySelector('p')),
    topics_count: document.querySelectorAll('.thwhats').length,
    topics_sec_h: Math.round((document.querySelectorAll('section.szyy60j.h1uj6h92')[2]?.getBoundingClientRect().height) || 0),
    topics_grid: gs(topic1?.parentElement),
    topic_item0: gs(topic1),
    topic_item3: gs(topic4),
    topic_h5: gs(topic1?.querySelector('h5')),
    topic_p: gs(topic1?.querySelector('p')),
    topic_chev_w: Math.round((topic1?.querySelector('svg')?.getBoundingClientRect().width) || 0),
    footer_h: Math.round(footer?.getBoundingClientRect().height || 0),
    footer_bg: footer ? getComputedStyle(footer).backgroundColor : '',
    footer_top_h: Math.round(footerTop?.getBoundingClientRect().height || 0),
    footer_bottom_h: Math.round(footerBottom?.getBoundingClientRect().height || 0),
    store_badge: gs(storeImg),
    total_h: document.documentElement.scrollHeight
  };
})()"""

BTL_JS = r"""(() => {
  const gs = (el) => {
    if (!el) return null;
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {
      w: Math.round(r.width), h: Math.round(r.height),
      fs: s.fontSize, fw: s.fontWeight, lh: s.lineHeight, ls: s.letterSpacing,
      br: s.borderRadius, pad: s.padding, bg: s.backgroundColor,
      bt: s.borderTopWidth, bb: s.borderBottomWidth, bc: s.borderBottomColor,
      shadow: s.boxShadow, gap: s.gap,
      cols: s.gridTemplateColumns ? s.gridTemplateColumns.split(' ').length : 0
    };
  };
  const popLink = document.querySelector('.popular-item');
  const momentCard = document.querySelector('.moment-card');
  const topic1 = document.querySelector('.topic-item');
  const topic4 = document.querySelectorAll('.topic-item')[3];
  const footer = document.querySelector('.site-footer');
  return {
    masthead_h: Math.round(document.querySelector('.masthead-bar').getBoundingClientRect().height),
    header_h: Math.round(document.querySelector('.site-header').getBoundingClientRect().height),
    header_cta: gs(document.querySelector('.btn-header-cta')),
    hero_h: Math.round(document.querySelector('.hero-section').getBoundingClientRect().height),
    hero_h1: gs(document.querySelector('.hero-h1')),
    search_input: gs(document.querySelector('.hero-search-input')),
    search_btn: gs(document.querySelector('.hero-search-btn')),
    chip1: gs(document.querySelector('.hero-chip')),
    pop_count: document.querySelectorAll('.popular-item').length,
    pop_sec_h: Math.round(document.querySelector('.popular-section').getBoundingClientRect().height),
    pop_h2: gs(document.querySelector('.popular-section .sec-h2')),
    pop_grid: gs(document.querySelector('.popular-grid')),
    pop_item: gs(popLink),
    pop_text: gs(popLink),
    pop_chev_w: Math.round(popLink.querySelector('svg').getBoundingClientRect().width),
    moments_count: document.querySelectorAll('.moment-card').length,
    moment_card: gs(momentCard),
    moment_icon_w: Math.round(momentCard.querySelector('svg').getBoundingClientRect().width),
    moment_h5: gs(momentCard.querySelector('.moment-h5')),
    moment_p: gs(momentCard.querySelector('.moment-p')),
    topics_count: document.querySelectorAll('.topic-item').length,
    topics_sec_h: Math.round(document.querySelector('.topics-section').getBoundingClientRect().height),
    topics_grid: gs(document.querySelector('.topics-grid')),
    topic_item0: gs(topic1),
    topic_item3: gs(topic4),
    topic_h5: gs(topic1.querySelector('.topic-h5')),
    topic_p: gs(topic1.querySelector('.topic-p')),
    topic_chev_w: Math.round(topic1.querySelector('svg').getBoundingClientRect().width),
    footer_h: Math.round(footer.getBoundingClientRect().height),
    footer_bg: getComputedStyle(footer).backgroundColor,
    footer_top_h: Math.round(document.querySelector('.footer-top').getBoundingClientRect().height),
    footer_bottom_h: Math.round(document.querySelector('.footer-bottom').getBoundingClientRect().height),
    store_badge: gs(document.querySelector('.store-badge')),
    total_h: document.documentElement.scrollHeight,
    zero_overflow: document.documentElement.scrollWidth <= window.innerWidth
  };
})()"""

async def eval_tab(ws_url: str, expr: str):
    async with websockets.connect(ws_url, max_size=16_000_000) as ws:
        await ws.send(json.dumps({"id": 10, "method": "Emulation.setDeviceMetricsOverride", "params": {"width": 1280, "height": 800, "deviceScaleFactor": 2, "mobile": False}}))
        while True:
            if json.loads(await ws.recv()).get("id") == 10:
                break
        await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}}))
        val = None
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                val = msg["result"]["result"]["value"]
                break
        await ws.send(json.dumps({"id": 11, "method": "Emulation.clearDeviceMetricsOverride"}))
        while True:
            if json.loads(await ws.recv()).get("id") == 11:
                break
        return val

def make_comparison_strips():
    ref_path = ART_DIR / "lifesg_full_ref.png"
    btl_path = ART_DIR / "btl_1to1_full.png"
    if not (ref_path.exists() and btl_path.exists()):
        print("WARN: Full-page images missing for comparison crops")
        return

    ref = Image.open(ref_path).convert("RGB")
    btl = Image.open(btl_path).convert("RGB")
    # Normalize widths to match
    w = min(ref.width, btl.width)
    scale_r = w / ref.width
    scale_b = w / btl.width
    if ref.width != w:
        ref = ref.resize((w, int(ref.height * scale_r)), Image.LANCZOS)
    if btl.width != w:
        btl = btl.resize((w, int(btl.height * scale_b)), Image.LANCZOS)

    # DPR factor (screenshots on Retina Mac are 2x)
    dpr = round(w / 1280) or 1

    # Full side-by-side image
    gap = 24 * dpr
    out_h = max(ref.height, btl.height)
    combo = Image.new("RGB", (w * 2 + gap, out_h), (230, 234, 240))
    combo.paste(ref, (0, 0))
    combo.paste(btl, (w + gap, 0))
    combo_small = combo.resize((combo.width // 2, combo.height // 2), Image.LANCZOS)
    combo_small.save(ART_DIR / "proof_full_side_by_side.png")

    # Section-by-section crops (in CSS pixels * dpr)
    crops = [
        ("proof_sec1_header_hero.png", 0, 710),
        ("proof_sec2_popular.png", 695, 1080),
        ("proof_sec3_moments.png", 1065, 1480),
        ("proof_sec4_topics.png", 1465, 2130),
        ("proof_sec5_footer.png", 2130, 2655),
    ]
    for fname, y1_css, y2_css in crops:
        y1, y2 = y1_css * dpr, y2_css * dpr
        c_ref = ref.crop((0, min(y1, ref.height - 10), w, min(y2, ref.height)))
        c_btl = btl.crop((0, min(y1, btl.height - 10), w, min(y2, btl.height)))
        ch = max(c_ref.height, c_btl.height)
        strip = Image.new("RGB", (w * 2 + gap, ch), (225, 230, 236))
        strip.paste(c_ref, (0, 0))
        strip.paste(c_btl, (w + gap, 0))
        strip = strip.resize((strip.width // 2, strip.height // 2), Image.LANCZOS)
        strip.save(ART_DIR / fname)
    print(f"Saved 6 visual proof images to {ART_DIR}")

async def main():
    tabs = json.loads(urllib.request.urlopen(CDP_URL).read().decode())
    life_tab = next((t for t in tabs if "life.gov.sg" in t.get("url", "")), None)
    btl_tab = next((t for t in tabs if "127.0.0.1:8787" in t.get("url", "")), None)
    if not life_tab or not btl_tab:
        print(f"ERROR: Tabs not found (life={bool(life_tab)}, btl={bool(btl_tab)})")
        sys.exit(1)

    L = await eval_tab(life_tab["webSocketDebuggerUrl"], LIFESG_JS)
    B = await eval_tab(btl_tab["webSocketDebuggerUrl"], BTL_JS)

    checks = [
        ("1. Masthead Height", L["masthead_h"], B["masthead_h"], 0),
        ("2. Header/Navbar Height", L["header_h"], B["header_h"], 0),
        ("3. Header CTA Height", L["header_cta"]["h"], B["header_cta"]["h"], 0),
        ("4. Header CTA Border-Radius", L["header_cta"]["br"], B["header_cta"]["br"], None),
        ("5. Header CTA Font-Size/Weight", f'{L["header_cta"]["fs"]}/{L["header_cta"]["fw"]}', f'{B["header_cta"]["fs"]}/{B["header_cta"]["fw"]}', None),
        ("6. Hero Section Height", L["hero_h"], B["hero_h"], 0),
        ("7. Hero H1 Font-Size/Weight/LH", f'{L["hero_h1"]["fs"]}/{L["hero_h1"]["fw"]}/{L["hero_h1"]["lh"]}', f'{B["hero_h1"]["fs"]}/{B["hero_h1"]["fw"]}/{B["hero_h1"]["lh"]}', None),
        ("8. Search Input Height", L["search_input"]["h"], B["search_input"]["h"], 0),
        ("9. Search Button Size (W×H)", f'{L["search_btn"]["w"]}x{L["search_btn"]["h"]}', f'{B["search_btn"]["w"]}x{B["search_btn"]["h"]}', None),
        ("10. Search Button Font (FS/FW)", f'{L["search_btn"]["fs"]}/{L["search_btn"]["fw"]}', f'{B["search_btn"]["fs"]}/{B["search_btn"]["fw"]}', None),
        ("11. Hero Chip Height & Radius", f'{L["chip1"]["h"]}px / {L["chip1"]["br"]}', f'{B["chip1"]["h"]}px / {B["chip1"]["br"]}', None),
        ("12. Popular Item Count", L["pop_count"], B["pop_count"], 0),
        ("13. Popular Section Height", L["pop_sec_h"], B["pop_sec_h"], 2),
        ("14. Popular Grid Columns", L["pop_grid"]["cols"], B["pop_grid"]["cols"], 0),
        ("15. Popular Link Font (FS/FW/LH)", f'{L["pop_text"]["fs"]}/{L["pop_text"]["fw"]}/{L["pop_text"]["lh"]}', f'{B["pop_text"]["fs"]}/{B["pop_text"]["fw"]}/{B["pop_text"]["lh"]}', None),
        ("16. Popular Chevron Size", L["pop_chev_w"], B["pop_chev_w"], 0),
        ("17. Life Moments Card Count", L["moments_count"], B["moments_count"], 0),
        ("18. Life Moment Card Size (W×H)", f'{L["moment_card"]["w"]}x{L["moment_card"]["h"]}', f'{B["moment_card"]["w"]}x{B["moment_card"]["h"]}', None),
        ("19. Life Moment Card Radius", L["moment_card"]["br"], B["moment_card"]["br"], None),
        ("20. Life Moment Icon Size", L["moment_icon_w"], B["moment_icon_w"], 0),
        ("21. Life Moment H5 & P Typography", f'{L["moment_h5"]["fs"]}/{L["moment_p"]["fs"]}', f'{B["moment_h5"]["fs"]}/{B["moment_p"]["fs"]}', None),
        ("22. Topics Item Count", L["topics_count"], B["topics_count"], 0),
        ("23. Topics Grid Columns", L["topics_grid"]["cols"], B["topics_grid"]["cols"], 0),
        ("24. Topics Top/Bottom Hairlines", f'r1:{L["topic_item0"]["bt"]}/{L["topic_item0"]["bb"]} r2:{L["topic_item3"]["bt"]}/{L["topic_item3"]["bb"]}', f'r1:{B["topic_item0"]["bt"]}/{B["topic_item0"]["bb"]} r2:{B["topic_item3"]["bt"]}/{B["topic_item3"]["bb"]}', None),
        ("25. Topics H5/P/Chevron", f'{L["topic_h5"]["fs"]}/{L["topic_p"]["fs"]}/{L["topic_chev_w"]}px', f'{B["topic_h5"]["fs"]}/{B["topic_p"]["fs"]}/{B["topic_chev_w"]}px', None),
        ("26. Footer Total Height & BG", f'{L["footer_h"]}px / {L["footer_bg"]}', f'{B["footer_h"]}px / {B["footer_bg"]}', None),
        ("27. Footer Top & Bottom Heights", f'{L["footer_top_h"]}px / {L["footer_bottom_h"]}px', f'{B["footer_top_h"]}px / {B["footer_bottom_h"]}px', None),
        ("28. Store Badge Size (W×H)", f'{L["store_badge"]["w"]}x{L["store_badge"]["h"]}', f'{B["store_badge"]["w"]}x{B["store_badge"]["h"]}', None),
    ]

    passed = 0
    print(f"{'CHECK':<35} | {'LIFE.GOV.SG':<26} | {'BTL 2.0 (OURS)':<26} | STATUS")
    print("-" * 102)
    for name, lv, bv, tol in checks:
        if tol is None:
            ok = (lv == bv)
        else:
            ok = abs(lv - bv) <= tol
        passed += int(ok)
        print(f"{name:<35} | {str(lv):<26} | {str(bv):<26} | {'PASS' if ok else 'FAIL'}")
    print("-" * 102)
    print(f"SCORE: {passed}/{len(checks)} EXACT 1:1 CHECKS PASSED | Zero Horizontal Overflow: {B['zero_overflow']} | Total Height: LifeSG={L['total_h']}px vs BTL={B['total_h']}px")

    make_comparison_strips()
    if passed != len(checks) or not B["zero_overflow"]:
        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())
