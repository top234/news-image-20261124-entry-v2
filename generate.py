#!/usr/bin/env python3
"""news-image-20261124 v2 "The World in One Day" — deterministic render.
Draws a 1024x1024 one-page newspaper from FACTS.md only. No clock, no
network, no randomness: identical input bytes -> identical PNG bytes.
"""
import hashlib
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W = H = 1024
M = 22                      # outer margin
CW = W - 2 * M              # 980 content width

PAPER = (250, 244, 230)
INK = (18, 32, 66)          # navy
INK_SOFT = (52, 66, 102)
RED = (178, 34, 30)
RULE = (150, 140, 120)
GREY = (110, 104, 90)
CARD_BG = (255, 252, 246)
CARD_BORDER = (196, 186, 166)

BADGE_COLORS = {
    "CONFIRMED": (26, 122, 58),
    "OFFICIAL": (27, 58, 107),
    "REPORTED": (176, 118, 8),
    "CLAIM": (178, 34, 30),
}

REGION_COLORS = {
    "EUROPE": (27, 58, 107),
    "MIDDLE EAST": (178, 34, 30),
    "AFRICA": (140, 90, 10),
    "EAST ASIA": (150, 40, 90),
    "SOUTH ASIA": (200, 90, 20),
    "SE ASIA": (20, 130, 110),
    "OCEANIA": (30, 110, 160),
    "N. AMERICA": (90, 60, 140),
    "LATIN AMERICA": (40, 130, 60),
    "WORLD": (90, 90, 90),
}

FDIR = "/usr/share/fonts/truetype/dejavu"


def font(name, size):
    return ImageFont.truetype(os.path.join(FDIR, name), size)


SERIF = "DejaVuSerif.ttf"
SERIF_B = "DejaVuSerif-Bold.ttf"
SANS = "DejaVuSans.ttf"
SANS_B = "DejaVuSans-Bold.ttf"


def tw(draw, text, f):
    """Text width in px."""
    return draw.textlength(text, font=f)


def wrap(draw, text, f, max_w):
    """Greedy word wrap; returns list of lines (never empty)."""
    words = text.split()
    lines, cur = [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if tw(draw, trial, f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines or [""]


def fit_lines(draw, text, f, max_w, max_lines):
    """Wrap and truncate with an ellipsis to max_lines."""
    lines = wrap(draw, text, f, max_w)
    if len(lines) <= max_lines:
        return lines
    lines = lines[:max_lines]
    while lines and tw(draw, lines[-1] + " ...", f) > max_w:
        lines[-1] = lines[-1][:-1].rstrip()
    if lines:
        lines[-1] = (lines[-1] + " ...").strip()
    return lines


def draw_centered(draw, y, text, f, fill, x0=M, x1=W - M):
    w_ = tw(draw, text, f)
    draw.text(((x0 + x1 - w_) / 2, y), text, font=f, fill=fill)
    return y


def italic_text(base, xy, text, f, fill):
    """Render text with a slight rightward slant (fake italic)."""
    x, y = xy
    tmp = Image.new("RGBA", (int(tw(ImageDraw.Draw(base), text, f)) + 30,
                             f.size + 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((4, 2), text, font=f, fill=fill + (255,))
    sheared = tmp.transform(tmp.size, Image.AFFINE,
                            (1, -0.16, 0.16 * tmp.size[1], 0, 1, 0),
                            resample=Image.BICUBIC)
    base.paste(sheared, (int(x), int(y)), sheared)


# ---------------------------------------------------------------- data
CARDS = [
    dict(n=1, place="STRAIT OF HORMUZ", region="MIDDLE EAST", field="SHIPPING",
         badge="CLAIM",
         head="Iran says mines set three tankers ablaze in Hormuz",
         body="The IRGC Navy's claim was still unverified on Tuesday. Two ships had US air escort, it says. Qatar's PM: \u201ccannot withstand another escalation\u201d.",
         src="Al Jazeera \u00b7 Anadolu \u00b7 Iran International", scene="hormuz"),
    dict(n=2, place="NEW YORK", region="N. AMERICA", field="MARKETS",
         badge="CONFIRMED",
         head="Markets roar back as Nvidia founder returns",
         body="Wall Street recovers about half of last week's losses; Nvidia stock jumps ~30% a day after the board reinstated Jensen Huang as CEO.",
         src="AP \u00b7 BBC \u00b7 Axios", scene="markets"),
    dict(n=3, place="ZAPORIZHZHIA, UKRAINE", region="EUROPE", field="WAR",
         badge="OFFICIAL",
         head="Russia fires 96 drones; Zaporizhzhia flats hit",
         body="Ukraine's air force says 73 were downed or jammed by 08:00. A late-Monday strike tore open a five-storey block: two dead, 40 hurt.",
         src="Ukrainian Air Force \u00b7 Ukrinform \u00b7 Kyiv Independent", scene="drones"),
    dict(n=4, place="TAPLEJUNG, NEPAL", region="SOUTH ASIA", field="DISASTER",
         badge="CONFIRMED",
         head="Magnitude-5.6 quake jolts eastern Nepal",
         body="Hit near the Tibet border at 07:17; felt in India, Bhutan and Bangladesh. No deaths. Nepal centre: 5.6; EMSC/USGS: 5.3.",
         src="Kathmandu Post \u00b7 Xinhua \u00b7 The Hindu", scene="quake"),
    dict(n=5, place="CANBERRA", region="OCEANIA", field="TECHNOLOGY",
         badge="CONFIRMED",
         head="Australia deal: tech fines up to 5%",
         body="Labor-Greens deal on a \u201cdigital duty of care\u201d ties fines to global revenue; users may sue. Google, Meta in scope.",
         src="Reuters \u00b7 ABC \u00b7 AAP", scene="parliament"),
    dict(n=6, place="KHAN YOUNIS, GAZA", region="MIDDLE EAST", field="WAR",
         badge="REPORTED",
         head="Drone strike kills 3 at Gaza police post",
         body="Israeli strikes in Al-Mawasi also wound five, a hospital source says. Three more killed near the Netzarim corridor.",
         src="Reuters \u00b7 Times of Israel \u00b7 Anadolu", scene="gaza"),
    dict(n=7, place="VILLAVICENCIO, COLOMBIA", region="LATIN AMERICA", field="SECURITY",
         badge="OFFICIAL",
         head="Car bomb wrecks Colombian state HQ",
         body="Blast late Monday at the Meta governor's office. At least 23 hurt. President blames ex-FARC dissidents.",
         src="UPI \u00b7 Reuters \u00b7 Meta health secretariat", scene="blast"),
    dict(n=8, place="BENGHAZI, LIBYA", region="AFRICA", field="WAR",
         badge="CLAIM",
         head="Ukraine says its drones sank a Russian warship",
         body="Kyiv says seven drones sank the Merkury at the Benghazi naval base on 23 November, carrying the Black Sea fight to the Med.",
         src="Middle East Eye \u00b7 Kyiv Independent", scene="ship"),
    dict(n=9, place="ULLEUNG, S. KOREA", region="EAST ASIA", field="SECURITY",
         badge="OFFICIAL",
         head="Russian jets trip Korean air-raid alert",
         body="F-15Ks scramble; no airspace breach, Seoul says. Russian jets were in the KADIZ.",
         src="Yonhap \u00b7 AP \u00b7 SBS", scene="jets"),
    dict(n=10, place="ANTALYA, TURKEY", region="WORLD", field="CLIMATE",
         badge="CONFIRMED",
         head="COP31 collapses with no deal",
         body="Talks ran 50 hours, then 90+ nations rejected a draft that never said \u201cfossil fuels\u201d. First big COP failure since 2009.",
         src="Grist \u00b7 AP \u00b7 UNFCCC", scene="cop"),
    dict(n=11, place="SINGAPORE", region="SE ASIA", field="TRADE",
         badge="CONFIRMED",
         head="US blacklists Megaspeed over chips",
         body="Commerce Dept puts the firm on the Entity List after months of bipartisan pressure; US firms now need a licence to sell it chips.",
         src="Politico \u00b7 Federal Register", scene="chip"),
    dict(n=12, place="CARTAGENA, COLOMBIA", region="LATIN AMERICA", field="CRIME",
         badge="REPORTED",
         head="25 hostages in supermarket siege",
         body="A failed armoured-car hijack ends with gunmen holding shoppers at an Exito store; airport halts landings. Five freed.",
         src="Reuters \u00b7 AP", scene="siege"),
    dict(n=13, place="MADRID, SPAIN", region="EUROPE", field="SPORT",
         badge="CONFIRMED",
         head="Real Madrid hit five on Champions League night",
         body="Arsenal held 1-1 by Dortmund; Man City draw 2-2 with Napoli. Nine games, 25 goals.",
         src="UEFA \u00b7 Flashscore", scene="football"),
]

ALSO = [
    (14, "BERLIN", "Germany first to get Ukraine's Delta combat system", "EUROPE \u00b7 DEFENCE \u00b7 OFFICIAL"),
    (15, "BRUSSELS", "NATO chief Rutte vows defence against space threat", "EUROPE \u00b7 DEFENCE \u00b7 OFFICIAL"),
    (16, "LONDON", "UK sanctions 5 Myanmar generals after ICJ genocide ruling", "EUROPE \u00b7 LAW \u00b7 CONFIRMED"),
    (17, "WARSAW", "Poland: peace deal won't end Russian sabotage of Europe", "EUROPE \u00b7 SECURITY \u00b7 OFFICIAL"),
    (18, "RIGA", "Latvia: Ukraine war may hit a tipping point next year", "EUROPE \u00b7 WAR \u00b7 OFFICIAL"),
    (19, "OSLO", "Norway in dialogue with Ukraine on \u201cstability in our near areas\u201d", "EUROPE \u00b7 DEFENCE \u00b7 OFFICIAL"),
    (20, "BRUSSELS", "7 countries back EU limits on Russian tourist and sports visas", "EUROPE \u00b7 DIPLOMACY \u00b7 REPORTED"),
    (21, "ITURI, DRC", "Fighting near hospital traps Ebola responders for 24 hours", "AFRICA \u00b7 HEALTH \u00b7 OFFICIAL"),
    (22, "TIGRAY", "Amnesty: Ethiopian strikes on towns may be war crimes", "AFRICA \u00b7 RIGHTS \u00b7 REPORTED"),
    (23, "TRIPOLI", "UN mission urges probe into Benghazi port attacks", "AFRICA \u00b7 DIPLOMACY \u00b7 OFFICIAL"),
    (24, "BAGHDAD", "Iraq PM orders ministry to run oilfields in Kurdish-held areas", "MIDDLE EAST \u00b7 ENERGY \u00b7 REPORTED"),
    (25, "WASHINGTON", "Huckabee doubts US will end $3.8bn Israel aid this year", "MIDDLE EAST \u00b7 DIPLOMACY \u00b7 REPORTED"),
    (26, "DAMASCUS", "US weighs training Syrian soldiers in demining", "MIDDLE EAST \u00b7 DEFENCE \u00b7 REPORTED"),
    (27, "RAS AL KHAIMAH", "UAE bus crash kills 13, injures 14", "MIDDLE EAST \u00b7 ACCIDENT \u00b7 REPORTED"),
    (28, "DHAKA", "Hasina plans return 16 Dec; minister: \u201cbrought back in handcuffs\u201d", "SOUTH ASIA \u00b7 POLITICS \u00b7 REPORTED"),
    (29, "TOKYO", "Japan to pay full 2027 ICC bill early, before US sanctions bite", "EAST ASIA \u00b7 LAW \u00b7 CONFIRMED"),
    (30, "TAIPEI", "AI-powered Chinese campaign targets Taiwan vote, study finds", "EAST ASIA \u00b7 AI \u00b7 REPORTED"),
    (31, "SEOUL", "Korea offers $375,000 to catch AI cheats in college exam", "EAST ASIA \u00b7 AI \u00b7 CONFIRMED"),
    (32, "KUALA LUMPUR", "Malaysia to send 6,500 Rohingya refugees back to Myanmar", "SE ASIA \u00b7 MIGRATION \u00b7 REPORTED"),
    (33, "CANBERRA", "Australia, Singapore deepen AI ties; Wong in town", "OCEANIA \u00b7 AI \u00b7 CONFIRMED"),
    (34, "BRASILIA", "Latin America opens science-cooperation talks (ECLAC)", "LATIN AMERICA \u00b7 SCIENCE \u00b7 OFFICIAL"),
    (35, "WASHINGTON", "Rep. Jimmy Gomez resigns after ethics finding", "N. AMERICA \u00b7 POLITICS \u00b7 CONFIRMED"),
    (36, "WASHINGTON", "Pentagon: Canada falling short as a defence partner", "N. AMERICA \u00b7 DEFENCE \u00b7 OFFICIAL"),
    (37, "WASHINGTON", "Trump to order DOJ to fast-track federal death sentences", "N. AMERICA \u00b7 LAW \u00b7 REPORTED"),
    (38, "NEW YORK", "Super Bowl LXI to be shown in IMAX theatres", "N. AMERICA \u00b7 CULTURE \u00b7 CONFIRMED"),
]

TIMELINE = [
    ("01:32 UTC", "Nepal quake M5.6 (07:17 local)"),
    ("04:09 UTC", "Australia tech-fines deal (Reuters)"),
    ("16:59 UTC", "Cartagena hostages (Reuters)"),
    ("17:45 UTC", "Champions League early games"),
    ("20:00 UTC", "Champions League late games"),
]

NUMBERS = [
    ("3", "tankers ablaze, Iran claims"),
    ("96", "drones at Ukraine overnight"),
    ("5.6", "magnitude, east Nepal quake"),
    ("5%", "max tech fine in Australia"),
    ("23", "hurt in Villavicencio blast"),
    ("6,500", "Rohingya to be sent back"),
]

CHIPS = [("EUROPE", 9), ("MIDDLE EAST", 6), ("AFRICA", 4), ("EAST ASIA", 4),
         ("SOUTH ASIA", 2), ("SE ASIA", 2), ("OCEANIA", 2), ("N. AMERICA", 5),
         ("LATIN AMERICA", 3), ("WORLD", 1)]

PINS = [  # (card n, lon, lat)
    (1, 56.0, 26.5), (2, -74.0, 40.7), (3, 35.2, 47.8), (4, 87.9, 27.6),
    (5, 149.1, -35.3), (6, 34.45, 31.35), (7, -73.6, 4.15), (8, 20.1, 32.1),
    (9, 130.9, 37.5), (10, 30.7, 36.9), (11, 103.8, 1.35), (12, -75.5, 10.4),
    (13, -3.7, 40.4),
]

DATE_CHECK = ("Every story here happened, or was first reported, on Tuesday "
              "24 November 2026 (any time zone). Left out as Monday's news: "
              "Jensen Huang's reinstatement was announced Monday \u2014 only "
              "Tuesday's market reaction is counted; Zelensky's NATO call "
              "was Monday 23 Nov; Maduro's birthday behind bars was Monday. "
              "Pictures and map: drawn for this page; no photographs.")

FOOTER = ("Sources: Reuters \u00b7 AP \u00b7 BBC \u00b7 AFP \u00b7 NYT \u00b7 WSJ \u00b7 "
          "Politico \u00b7 Kyiv Independent \u00b7 UN News \u00b7 UEFA \u00b7 Xinhua \u00b7 "
          "The Hindu \u00b7 ABC \u00b7 UPI \u2014 Press time 23:59 UTC, Tue 24 Nov 2026.")

# Coarse equirectangular land mask: 72 cols (5 deg lon) x 24 rows (6 deg lat,
# lat 84..-60). Intervals are (first_col, last_col) inclusive per row.
LAND_ROWS = [
    [(18, 21), (24, 30)],
    [(12, 24), (24, 32), (38, 42), (54, 58)],
    [(2, 8), (10, 24), (25, 31), (39, 42), (44, 71)],
    [(3, 7), (9, 25), (31, 33), (37, 42), (42, 71)],
    [(10, 25), (35, 36), (37, 42), (42, 71)],
    [(11, 25), (35, 36), (36, 42), (42, 71)],
    [(11, 23), (35, 42), (45, 51), (51, 63), (64, 65)],
    [(11, 22), (34, 42), (42, 46), (46, 51), (51, 61), (62, 64)],
    [(12, 21), (34, 42), (42, 48), (48, 54), (54, 60)],
    [(13, 20), (34, 43), (43, 47), (49, 53), (55, 57), (57, 60)],
    [(14, 19), (33, 43), (44, 47), (50, 53), (55, 57)],
    [(15, 19), (32, 44), (51, 52), (55, 57)],
    [(17, 20), (32, 44), (55, 57)],
    [(20, 26), (34, 44), (55, 60)],
    [(20, 29), (37, 44), (56, 60), (62, 65)],
    [(20, 29), (38, 44), (57, 60), (63, 66)],
    [(20, 28), (38, 44), (44, 46), (62, 64)],
    [(21, 28), (38, 43), (44, 46), (61, 66)],
    [(22, 27), (38, 43), (44, 45), (59, 66)],
    [(21, 26), (39, 42), (59, 66), (69, 71)],
    [(21, 24), (39, 41), (64, 66), (69, 71)],
    [(21, 23), (69, 70)],
    [(21, 22)],
    [(22, 23)],
]

# ---------------------------------------------------------------- scenes

def scene(draw, kind, x, y, w, h):
    """Draw a small vector scene inside (x, y, w, h)."""
    sky = (214, 228, 240)
    sea = (168, 196, 220)
    draw.rectangle([x, y, x + w, y + h], fill=sky)
    cx, cy = x + w / 2, y + h / 2
    if kind == "hormuz":
        draw.rectangle([x, y + h * 0.55, x + w, y + h], fill=sea)
        for i, tx in enumerate((0.12, 0.42, 0.70)):
            hx, hy = x + w * tx, y + h * 0.62
            draw.polygon([(hx, hy), (hx + w * 0.20, hy), (hx + w * 0.17, hy - 9),
                          (hx + w * 0.03, hy - 9)], fill=(30, 40, 60))
            draw.rectangle([hx + w * 0.05, hy - 20, hx + w * 0.09, hy - 9],
                           fill=(60, 70, 90))
            fx = hx + w * 0.10
            draw.polygon([(fx - 5, hy - 20), (fx, hy - 34), (fx + 5, hy - 20)],
                         fill=(230, 120, 20))
            draw.polygon([(fx - 3, hy - 18), (fx, hy - 27), (fx + 3, hy - 18)],
                         fill=(250, 210, 60))
        draw.line([x, y + h * 0.55, x + w, y + h * 0.55], fill=(255, 255, 255), width=1)
    elif kind == "markets":
        base = y + h - 8
        vals = (0.25, 0.38, 0.33, 0.55, 0.5, 0.72, 0.95)
        bw = w / len(vals)
        for i, v in enumerate(vals):
            bx = x + i * bw + 2
            draw.rectangle([bx, base - v * (h - 18), bx + bw - 4, base],
                           fill=INK if i < 5 else RED)
        draw.line([x + 4, base - 0.25 * (h - 18), x + w - 4, base - 0.95 * (h - 18)],
                  fill=RED, width=2)
        draw.polygon([(x + w - 13, base - 0.98 * (h - 18)), (x + w - 4, base - 0.95 * (h - 18)),
                      (x + w - 13, base - 0.88 * (h - 18))], fill=RED)
    elif kind == "drones":
        for i, (bx, bh) in enumerate(((0.08, 0.62), (0.26, 0.78), (0.46, 0.55),
                                      (0.64, 0.85), (0.82, 0.68))):
            bx0 = x + w * bx
            draw.rectangle([bx0, y + h - bh * h, bx0 + w * 0.14, y + h], fill=(70, 80, 100))
            draw.rectangle([bx0 + w * 0.03, y + h - bh * h - 7, bx0 + w * 0.11,
                            y + h - bh * h], fill=(70, 80, 100))
        for dx, dy in ((0.30, 0.18), (0.55, 0.10), (0.78, 0.22)):
            px, py = x + w * dx, y + h * dy
            draw.ellipse([px - 2, py - 2, px + 2, py + 2], fill=INK)
            draw.line([px - 6, py, px + 6, py], fill=INK, width=1)
            draw.line([px, py - 6, px, py + 6], fill=INK, width=1)
    elif kind == "quake":
        draw.polygon([(x, y + h), (x + w * 0.30, y + h * 0.25), (x + w * 0.52, y + h),
                      (x + w * 0.72, y + h * 0.35), (x + w, y + h)], fill=(120, 130, 150))
        draw.polygon([(x + w * 0.22, y + h * 0.38), (x + w * 0.30, y + h * 0.25),
                      (x + w * 0.38, y + h * 0.38)], fill=(255, 255, 255))
        draw.polygon([(x + w * 0.65, y + h * 0.46), (x + w * 0.72, y + h * 0.35),
                      (x + w * 0.79, y + h * 0.46)], fill=(255, 255, 255))
        pts = []
        px = x + 4
        while px < x + w - 4:
            pts.append((px, cy + (6 if (px // 7) % 2 else -6)))
            px += 7
        draw.line(pts, fill=RED, width=2)
    elif kind == "parliament":
        draw.rectangle([x + w * 0.18, y + h * 0.55, x + w * 0.82, y + h * 0.92],
                       fill=(200, 190, 170))
        draw.polygon([(x + w * 0.12, y + h * 0.55), (x + w * 0.5, y + h * 0.18),
                      (x + w * 0.88, y + h * 0.55)], fill=(150, 140, 125))
        for i in range(5):
            cx0 = x + w * (0.24 + i * 0.13)
            draw.rectangle([cx0, y + h * 0.62, cx0 + 5, y + h * 0.92], fill=(250, 244, 230))
        draw.text((x + w - 5, y + 4), "5%", font=font(SANS_B, 15),
                  fill=RED, anchor="ra")
    elif kind == "gaza":
        for i, (bx, bh) in enumerate(((0.06, 0.55), (0.24, 0.72), (0.44, 0.5),
                                      (0.62, 0.8), (0.80, 0.6))):
            bx0 = x + w * bx
            draw.rectangle([bx0, y + h - bh * h, bx0 + w * 0.15, y + h], fill=(90, 95, 110))
        px, py = x + w * 0.68, y + h * 0.16
        draw.ellipse([px - 2, py - 2, px + 2, py + 2], fill=INK)
        draw.line([px - 6, py, px + 6, py], fill=INK, width=1)
        draw.line([px, py - 6, px, py + 6], fill=INK, width=1)
        draw.ellipse([x + w * 0.30, y + h * 0.10, x + w * 0.42, y + h * 0.30],
                     fill=(200, 200, 200))
    elif kind == "blast":
        draw.rectangle([x + w * 0.15, y + h * 0.45, x + w * 0.85, y + h * 0.92],
                       fill=(150, 145, 135))
        draw.rectangle([x + w * 0.30, y + h * 0.62, x + w * 0.42, y + h * 0.92],
                       fill=(90, 85, 75))
        draw.rectangle([x + w * 0.58, y + h * 0.62, x + w * 0.70, y + h * 0.92],
                       fill=(90, 85, 75))
        bx, by = x + w * 0.5, y + h * 0.30
        pts = []
        for i in range(12):
            r = 16 if i % 2 == 0 else 8
            import math
            a = i * math.pi / 6
            pts.append((bx + r * math.cos(a), by + r * math.sin(a)))
        draw.polygon(pts, fill=(250, 180, 40))
        draw.ellipse([bx - 5, by - 5, bx + 5, by + 5], fill=RED)
    elif kind == "ship":
        draw.rectangle([x, y + h * 0.6, x + w, y + h], fill=sea)
        draw.polygon([(x + w * 0.15, y + h * 0.55), (x + w * 0.55, y + h * 0.42),
                      (x + w * 0.85, y + h * 0.55), (x + w * 0.75, y + h * 0.72),
                      (x + w * 0.25, y + h * 0.72)], fill=(40, 50, 70))
        draw.rectangle([x + w * 0.45, y + h * 0.28, x + w * 0.55, y + h * 0.45],
                       fill=(40, 50, 70))
        draw.arc([x + w * 0.10, y + h * 0.62, x + w * 0.30, y + h * 0.82],
                 180, 360, fill=(255, 255, 255), width=2)
        draw.arc([x + w * 0.65, y + h * 0.66, x + w * 0.85, y + h * 0.86],
                 180, 360, fill=(255, 255, 255), width=2)
    elif kind == "jets":
        draw.polygon([(x, y + h), (x + w * 0.35, y + h * 0.55), (x + w * 0.55, y + h),
                      (x + w * 0.75, y + h * 0.6), (x + w, y + h)], fill=(140, 150, 165))
        for jx, jy in ((0.30, 0.20), (0.62, 0.12)):
            px, py = x + w * jx, y + h * jy
            draw.polygon([(px, py - 6), (px + 12, py + 3), (px, py + 2), (px - 3, py + 5)],
                         fill=INK)
            draw.line([px - 12, py + 2, px, py + 2], fill=INK, width=1)
        draw.arc([x + w * 0.42, y + h * 0.30, x + w * 0.58, y + h * 0.55],
                 0, 360, fill=RED, width=2)
    elif kind == "cop":
        draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], outline=INK, width=2)
        draw.ellipse([cx - 20, cy - 8, cx + 20, cy + 8], outline=INK, width=1)
        draw.line([cx - 20, cy, cx + 20, cy], fill=INK, width=1)
        draw.line([cx - 26, cy - 26, cx + 26, cy + 26], fill=RED, width=3)
        draw.line([cx - 26, cy + 26, cx + 26, cy - 26], fill=RED, width=3)
    elif kind == "chip":
        for i, (bx, bh) in enumerate(((0.08, 0.6), (0.26, 0.8), (0.44, 0.55),
                                      (0.62, 0.88), (0.80, 0.7))):
            bx0 = x + w * bx
            draw.rectangle([bx0, y + h - bh * h, bx0 + w * 0.14, y + h], fill=(80, 90, 110))
        sq = 18
        sx, sy = x + w - sq - 6, y + 5
        draw.rectangle([sx, sy, sx + sq, sy + sq], fill=INK)
        draw.rectangle([sx + 5, sy + 5, sx + sq - 5, sy + sq - 5], outline=(250, 210, 60), width=1)
        for i in range(3):
            draw.line([sx + 2 + i * 6, sy, sx + 2 + i * 6, sy - 3], fill=INK, width=1)
    elif kind == "siege":
        draw.rectangle([x + w * 0.12, y + h * 0.35, x + w * 0.88, y + h * 0.92],
                       fill=(190, 180, 165))
        draw.polygon([(x + w * 0.08, y + h * 0.35), (x + w * 0.92, y + h * 0.35),
                      (x + w * 0.84, y + h * 0.55), (x + w * 0.16, y + h * 0.55)],
                     fill=RED)
        draw.rectangle([x + w * 0.42, y + h * 0.62, x + w * 0.58, y + h * 0.92],
                       fill=(90, 85, 75))
        draw.rectangle([x + w * 0.20, y + h * 0.62, x + w * 0.34, y + h * 0.80],
                       outline=INK, width=1)
        draw.rectangle([x + w * 0.66, y + h * 0.62, x + w * 0.80, y + h * 0.80],
                       outline=INK, width=1)
    elif kind == "football":
        draw.arc([x + w * 0.08, y + h * 0.30, x + w * 0.92, y + h * 1.15],
                 180, 360, fill=(90, 100, 115), width=2)
        for i in range(5):
            bx0 = x + w * (0.14 + i * 0.16)
            draw.line([bx0, y + h * 0.62, bx0, y + h * 0.78], fill=(90, 100, 115), width=1)
        bx, by = cx, y + h * 0.32
        draw.ellipse([bx - 11, by - 11, bx + 11, by + 11], fill=(255, 255, 255),
                     outline=INK, width=1)
        draw.polygon([(bx, by - 5), (bx + 5, by - 1), (bx + 3, by + 5),
                      (bx - 3, by + 5), (bx - 5, by - 1)], fill=INK)
        draw.text((x + w - 4, y + h - 4), "5\u20131", font=font(SANS_B, 12),
                  fill=RED, anchor="rb")


# ---------------------------------------------------------------- render

def render():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # ---- masthead
    y = 12
    draw_centered(d, y, "ONE DAY OF WORLD NEWS ON ONE PAGE", font(SANS_B, 11), INK)
    y = 28
    draw_centered(d, y, "38 STORIES \u00b7 9 REGIONS \u00b7 21 FIELDS \u00b7 EVERY ONE DATED "
                        "TUESDAY 24 NOVEMBER 2026", font(SANS, 10), INK_SOFT)
    d.line([M, 44, W - M, 44], fill=RULE, width=1)
    d.line([M, 46, W - M, 46], fill=INK, width=2)

    # ---- giant title
    y = 52
    draw_centered(d, y, "Tuesday 24 November 2026", font(SERIF_B, 52), INK)

    # ---- kicker (red, slanted serif, 2 lines)
    kicker = ("Three tankers ablaze in Hormuz \u00b7 Wall Street roars back as "
              "Nvidia's founder returns \u00b7 96 drones over Ukraine overnight")
    klines = wrap(d, kicker, font(SERIF, 16), CW - 40)
    ky = 112
    for ln in klines[:2]:
        w_ = tw(d, ln, font(SERIF, 16))
        italic_text(img, ((W - w_) / 2, ky), ln, font(SERIF, 16), RED)
        ky += 20

    # ---- region chips
    y = 156
    chip_w = (CW - 9 * 6) / 10
    cx = M
    for name, n in CHIPS:
        col = REGION_COLORS[name]
        d.rounded_rectangle([cx, y, cx + chip_w, y + 20], radius=10, fill=col)
        label = "%s %d" % (name, n)
        f = font(SANS_B, 9)
        while tw(d, label, f) > chip_w - 8 and f.size > 7:
            f = font(SANS_B, f.size - 1)
        lw = tw(d, label, f)
        d.text((cx + (chip_w - lw) / 2, y + 10), label, font=f, fill=(255, 255, 255),
               anchor="lm")
        cx += chip_w + 6

    # ---- UTC timeline strip
    y = 182
    d.rectangle([M, y, W - M, y + 34], fill=INK)
    cell_w = CW / 5
    for i, (t, txt) in enumerate(TIMELINE):
        ex = M + i * cell_w
        if i:
            d.line([ex, y + 5, ex, y + 29], fill=(90, 105, 140), width=1)
        d.text((ex + 8, y + 4), t, font=font(SANS_B, 10), fill=(250, 210, 60))
        for j, ln in enumerate(wrap(d, txt, font(SANS, 9), cell_w - 16)[:2]):
            d.text((ex + 8, y + 16 + j * 10), ln, font=font(SANS, 9),
                   fill=(235, 238, 245))

    # ---- numbers strip
    y = 220
    cell_w = CW / 6
    for i, (num, label) in enumerate(NUMBERS):
        ex = M + i * cell_w
        if i:
            d.line([ex, y + 4, ex, y + 42], fill=RULE, width=1)
        nf = font(SERIF_B, 26)
        d.text((ex + cell_w / 2, y + 2), num, font=nf, fill=RED, anchor="ma")
        for j, ln in enumerate(wrap(d, label, font(SANS, 9), cell_w - 12)):
            d.text((ex + cell_w / 2, y + 30 + j * 10), ln, font=font(SANS, 9),
                   fill=INK_SOFT, anchor="ma")
            if j >= 1:
                break
    d.line([M, y + 46, W - M, y + 46], fill=INK, width=2)

    # ---- 13 cards
    cards_y = 270
    hero_h, small_h, gap = 150, 126, 6
    hero_w = (CW - 2 * gap) / 3
    small_w = (CW - 4 * gap) / 5

    def card(c, x, y, w, h, hero):
        d.rectangle([x, y, x + w, y + h], fill=CARD_BG, outline=CARD_BORDER, width=1)
        ill_h = 52 if hero else 34
        scene(d, c["scene"], x + 1, y + 1, w - 2, ill_h)
        # number badge over the illustration corner
        bx, by = x + 8, y + 8
        d.ellipse([bx, by, bx + 18, by + 18], fill=RED, outline=(255, 255, 255), width=1)
        nf = font(SANS_B, 11)
        d.text((bx + 9, by + 9), str(c["n"]), font=nf, fill=(255, 255, 255), anchor="mm")
        ty = y + ill_h + 4
        # place + verification badge
        bf = font(SANS_B, 8 if hero else 7)
        bcol = BADGE_COLORS[c["badge"]]
        bw_ = tw(d, c["badge"], bf) + 8
        d.rounded_rectangle([x + w - 6 - bw_, ty, x + w - 6, ty + 12], radius=6, fill=bcol)
        d.text((x + w - 6 - bw_ / 2, ty + 6), c["badge"], font=bf,
               fill=(255, 255, 255), anchor="mm")
        pf = font(SANS_B, 9 if hero else 8)
        place_lines = fit_lines(d, c["place"], pf, w - 14 - bw_, 1)
        d.text((x + 6, ty + 1), place_lines[0], font=pf, fill=INK)
        ty += 13 if hero else 12
        # headline
        hf = font(SANS_B, 13 if hero else 11)
        hl = fit_lines(d, c["head"], hf, w - 12, 2)
        for ln in hl:
            d.text((x + 6, ty), ln, font=hf, fill=INK)
            ty += 14 if hero else 12
        ty += 1
        # body
        bodyf = font(SANS, 10 if hero else 8)
        bl = fit_lines(d, c["body"], bodyf, w - 12, 3)
        for ln in bl:
            d.text((x + 6, ty), ln, font=bodyf, fill=INK_SOFT)
            ty += 11 if hero else 9.5
        # bottom line: tag + source
        sf = font(SANS, 8 if hero else 7)
        tag = "%s \u00b7 %s" % (c["region"], c["field"])
        src = c["src"]
        if hero:
            line = tag + "  \u2014  " + src
            lines = fit_lines(d, line, sf, w - 12, 1)
            d.text((x + 6, y + h - 13), lines[0], font=sf, fill=GREY)
        else:
            d.text((x + 6, y + h - 21), tag, font=sf, fill=GREY)
            sl = fit_lines(d, src, sf, w - 12, 1)
            d.text((x + 6, y + h - 11), sl[0], font=sf, fill=GREY)

    for i, c in enumerate(CARDS[:3]):
        card(c, M + i * (hero_w + gap), cards_y, hero_w, hero_h, True)
    row2_y = cards_y + hero_h + gap
    for i, c in enumerate(CARDS[3:8]):
        card(c, M + i * (small_w + gap), row2_y, small_w, small_h, False)
    row3_y = row2_y + small_h + gap
    for i, c in enumerate(CARDS[8:13]):
        card(c, M + i * (small_w + gap), row3_y, small_w, small_h, False)
    cards_end = row3_y + small_h

    # ---- ALSO list
    y = cards_end + 8
    d.text((M, y), "ALSO ON TUESDAY 24 NOVEMBER", font=font(SANS_B, 11), fill=INK)
    d.line([M + 218, y + 6, W - M, y + 6], fill=RULE, width=1)
    y += 18
    also_top = y
    also_bottom = 912
    col_w = (CW - 2 * 12) / 3
    cols = [ALSO[0:9], ALSO[9:17], ALSO[17:25]]
    # pick a font size that fits all three columns in the budget
    for size in (9, 8.5, 8, 7.5):
        hf = font(SANS_B, size)
        tf = font(SANS, size - 1)
        heights = []
        for col in cols:
            hh = 0
            for n, place, head, tag in col:
                text = "%d. %s \u2014 %s" % (n, place, head)
                hh += len(wrap(d, text, hf, col_w)) * (size + 2) + size + 2
            heights.append(hh)
        if max(heights) <= also_bottom - also_top:
            break
    for ci, col in enumerate(cols):
        cx = M + ci * (col_w + 12)
        cy = also_top
        for n, place, head, tag in col:
            text = "%d. %s \u2014 %s" % (n, place, head)
            lines = wrap(d, text, hf, col_w)
            for ln in lines:
                d.text((cx, cy), ln, font=hf, fill=INK)
                cy += size + 2
            d.text((cx, cy), tag, font=tf, fill=GREY)
            cy += size + 2

    # ---- bottom row: dotted world map + DATE CHECK box
    y = 918
    map_x, map_w, map_h = M, 620, 66
    d.rectangle([map_x, y, map_x + map_w, y + map_h], outline=CARD_BORDER, width=1)
    d.text((map_x + 6, y + 2), "WHERE IT HAPPENED \u2014 1\u201313 pictured \u00b7 14\u201338 listed",
           font=font(SANS_B, 8), fill=INK)
    # dotted land: lat 84..-60 mapped onto the strip below the label
    my0, my1 = y + 12, y + map_h - 2
    lat_top, lat_bot = 84.0, -60.0
    rows, cols_n = len(LAND_ROWS), 72
    dot_step_x = map_w / cols_n
    dot_step_y = (my1 - my0) / rows
    for r, intervals in enumerate(LAND_ROWS):
        for c0, c1 in intervals:
            for cc in range(c0, c1 + 1):
                px = map_x + cc * dot_step_x + dot_step_x / 2
                py = my0 + r * dot_step_y + dot_step_y / 2
                d.ellipse([px - 1, py - 1, px + 1, py + 1], fill=(120, 130, 150))
    for n, lon, lat in PINS:
        px = map_x + (lon + 180) / 360 * map_w
        py = my0 + (lat_top - lat) / (lat_top - lat_bot) * (my1 - my0)
        d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=RED, outline=(255, 255, 255), width=1)
        d.text((px, py), str(n), font=font(SANS_B, 7), fill=(255, 255, 255), anchor="mm")
    # legend under the map is inside the strip: badge key at bottom-right
    # DATE CHECK box
    dc_x, dc_w = map_x + map_w + 10, W - M - (map_x + map_w + 10)
    d.rectangle([dc_x, y, dc_x + dc_w, y + map_h], outline=INK, width=1)
    d.text((dc_x + 6, y + 3), "DATE CHECK", font=font(SANS_B, 9), fill=RED)
    dcf = font(SANS, 7.5)
    dl = wrap(d, DATE_CHECK, dcf, dc_w - 12)
    ly = y + 14
    for ln in dl[:5]:
        d.text((dc_x + 6, ly), ln, font=dcf, fill=INK_SOFT)
        ly += 9

    # ---- badge legend line + footer
    y = 988
    leg = ("CONFIRMED = two or more outlets, or a final official result  \u00b7  "
           "OFFICIAL = on record from an authority  \u00b7  REPORTED = carried by "
           "the outlets named  \u00b7  CLAIM = one side's account, not yet verified")
    lf = font(SANS, 8)
    lw = tw(d, leg, lf)
    d.text(((W - lw) / 2, y), leg, font=lf, fill=GREY)
    y = 998
    ff = font(SANS, 8)
    fw = tw(d, FOOTER, ff)
    d.text(((W - fw) / 2, y), FOOTER, font=ff, fill=INK_SOFT)

    # thin outer frame
    d.rectangle([8, 8, W - 9, H - 9], outline=INK, width=1)
    return img


def main():
    out_dir = os.environ.get("OUTPUT_DIR", ".")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    img = render()
    img.save(path, format="PNG", optimize=True)
    data = open(path, "rb").read()
    print("WROTE %s %d bytes sha256=%s" % (path, len(data), hashlib.sha256(data).hexdigest()))


if __name__ == "__main__":
    main()
