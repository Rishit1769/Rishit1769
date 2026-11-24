"""Self-contained SVG renderers. All dynamic text is XML escaped."""
import base64
import hashlib
import html
import math
import textwrap
from datetime import date, timedelta
from xml.etree import ElementTree as ET

BG = "#060912"
CARD = "#101525"
TEXT = "#E6EDF3"
MUTED = "#94A3B8"
GOLD = "#FACC15"
SPACE = (4, 8, 12, 16, 24, 32)
PAD = SPACE[-1]
RADIUS = SPACE[3]
CARD_WIDTH = 900


def wrap_label(value, width, size, lines=None):
    # All cards use a fixed-pitch font. Allow extra room for wide glyphs.
    return textwrap.wrap(value, width=max(1, int(width / (size * .67))),
                         max_lines=lines, placeholder="…")


def orbit_axes(index, count):
    fraction = index / max(1, count - 1)
    return 166 + 302 * fraction, 110 + 97 * fraction


def esc(value):
    return html.escape(str(value or ""), quote=True)


def svg(width, height, contents, extra=""):
    value = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" role="img" {extra}>'
             f'<rect width="100%" height="100%" rx="{RADIUS}" fill="{BG}"/>{contents}</svg>')
    ET.fromstring(value)
    return value + "\n"


def label(x, y, value, size=16, color=TEXT, anchor="start", weight="normal", extra=""):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" text-anchor="{anchor}" '
            f'font-weight="{weight}" {extra}>{esc(value)}</text>')


def title(number, name, width=CARD_WIDTH):
    return label(PAD, 54, f"{number} / {name.upper()}", 18, GOLD, weight="bold", extra='letter-spacing="3"') + f'<path d="M{PAD} 72H{width-PAD}" stroke="#273044"/>'


def deterministic_stars(seed, count, width, height):
    pieces = []
    for i in range(count):
        digest = hashlib.sha256(f"{seed}:{i}".encode()).digest()
        x = 16 + int.from_bytes(digest[:2], "big") % (width-32)
        y = 16 + int.from_bytes(digest[2:4], "big") % (height-32)
        r = (0.6, 1, 1.5)[digest[4] % 3]
        opacity = (0.25, 0.4, 0.65)[digest[5] % 3]
        pieces.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#DDE9FF" opacity="{opacity}">'
                      f'<animate attributeName="opacity" values="{opacity};0.12;{opacity}" dur="{3+i%7}s" repeatCount="indefinite"/></circle>')
    return "".join(pieces)


def background_decorations():
    return ('<ellipse cx="250" cy="300" rx="215" ry="105" fill="#28436B" opacity=".075"/>'
            '<ellipse cx="970" cy="460" rx="180" ry="120" fill="#5B417C" opacity=".06"/>'
            '<g opacity=".3"><path d="M0 0L-38 14" stroke="#C7D8F5" stroke-width="1"/>'
            '<animateMotion path="M100 130L330 195" dur="19s" begin="5s" repeatCount="indefinite"/>'
            '<animate attributeName="opacity" values="0;.4;0" dur="19s" begin="5s" repeatCount="indefinite"/></g>'
            '<g opacity=".2"><path d="M0 0L-26 10" stroke="#C7D8F5" stroke-width="1"/>'
            '<animateMotion path="M970 95L1170 155" dur="23s" begin="12s" repeatCount="indefinite"/>'
            '<animate attributeName="opacity" values="0;.3;0" dur="23s" begin="12s" repeatCount="indefinite"/></g>')


def solar(snapshot, config):
    w, h, cx, cy = 1200, 720, 600, 360
    languages = list(snapshot["languages"])
    supported = {lang["name"] for lang in languages}
    if any((r.get("language") or "Other") not in supported for r in snapshot["repos"]):
        languages.append({"name": "Other", "percent": max(0, 100-sum(l["percent"] for l in languages)), "color": MUTED})
    avatar = snapshot["avatar"]
    mime = "image/png" if avatar.startswith(b"\x89PNG") else "image/jpeg"
    uri = f"data:{mime};base64,{base64.b64encode(avatar).decode()}"
    out = [f'<defs><radialGradient id="sun-glow"><stop stop-color="{GOLD}" stop-opacity=".48"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>'
           f'<clipPath id="avatar-clip"><circle cx="0" cy="0" r="47"/></clipPath>'
           f'<linearGradient id="planet-shade"><stop stop-color="#fff" stop-opacity=".4"/><stop offset="1" stop-color="#000" stop-opacity=".45"/></linearGradient></defs>',
           background_decorations(), deterministic_stars(config["username"], config["star_density"], w, h), title("01", "Developer universe", w),
           label(36, 103, "LIVE GITHUB ECOSYSTEM", 12, MUTED, extra='letter-spacing="2"')]
    for i in range(len(languages)):
        rx, ry = orbit_axes(i, len(languages))
        out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="#273044" stroke-width="1.3" stroke-dasharray="3 6"/>')
    out += [f'<circle cx="{cx}" cy="{cy}" r="114" fill="url(#sun-glow)"><animate attributeName="r" values="108;123;108" dur="5s" repeatCount="indefinite"/></circle>',
            f'<path d="M{cx-78} {cy-20}Q{cx-100} {cy-38} {cx-69} {cy-56}" fill="none" stroke="{GOLD}" stroke-width="2" opacity=".3"><animate attributeName="opacity" values=".1;.45;.1" dur="7s" repeatCount="indefinite"/></path>',
            f'<g transform="translate({cx} {cy})"><circle r="57" fill="#151722" stroke="{GOLD}" stroke-width="5"/>'
            f'<image href="{uri}" x="-47" y="-47" width="94" height="94" clip-path="url(#avatar-clip)"/>'
            f'<circle r="60" fill="none" stroke="{GOLD}" opacity=".4"><animate attributeName="r" values="59;72;59" dur="4s" repeatCount="indefinite"/>'
            '<animate attributeName="opacity" values=".55;0;.55" dur="4s" repeatCount="indefinite"/></circle></g>',
            f'<title>{esc(snapshot["profile"].get("name") or config["username"])}</title>']
    by_language = {}
    for repo in snapshot["repos"]:
        by_language.setdefault(repo.get("language") or "Other", []).append(repo)
    pinned_names = {p["name"] for p in snapshot["pinned"]}
    for i, lang in enumerate(languages):
        # Each carrier moves around a sun-centered ellipse. Its child moons inherit that motion.
        rx, ry = orbit_axes(i, len(languages))
        size = max(config["planet_radius_min"], min(config["planet_radius_max"], 12+lang["percent"]*.36))
        dur = config["orbital_base_seconds"] + i*config["orbital_step_seconds"]
        color = esc(lang["color"])
        phase = i * 2*math.pi / max(1, len(languages))
        x0, y0 = rx*math.cos(phase), ry*math.sin(phase)
        path = "M0 0 " + " ".join(f'L{rx*math.cos(phase+2*math.pi*k/72)-x0:.2f} {ry*math.sin(phase+2*math.pi*k/72)-y0:.2f}' for k in range(1, 73))
        out.append(f'<g transform="translate({cx+x0:.2f} {cy+y0:.2f})"><animateMotion path="{path}" dur="{dur}s" repeatCount="indefinite"/>'
                   f'<circle r="{size+10:.1f}" fill="{color}" opacity=".09"/>'
                   f'<circle r="{size:.1f}" fill="{color}"/>'
                   f'<g><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="{6+i*2}s" repeatCount="indefinite"/>'
                   f'<path d="M{-size*.8:.1f} {-size*.3:.1f} Q0 {-size*.7:.1f} {size*.9:.1f} 0" stroke="white" stroke-opacity=".38" fill="none" stroke-width="2"/>'
                   f'<path d="M{-size*.9:.1f} {size*.35:.1f} Q0 {size*.7:.1f} {size*.7:.1f} {size*.25:.1f}" stroke="#111" stroke-opacity=".2" fill="none" stroke-width="3"/></g>'
                   f'<circle r="{size:.1f}" fill="url(#planet-shade)"/>')
        moons = sorted(by_language.get(lang["name"], []), key=lambda r: (r["name"] not in pinned_names, -r.get("stargazers_count", 0), r["name"]))[:config["max_moons_per_planet"]]
        for j, repo in enumerate(moons):
            distance = size + 14 + j*5
            mdur = 7+j*3+i
            moon_size = 5 if repo["name"] in pinned_names else 2.8
            pinned = repo["name"] in pinned_names
            caption = f'<title>{esc(repo["name"])}</title>'
            out.append(f'<g transform="translate({distance} 0)"><animateMotion path="M0 0 A{distance} {distance*.42:.1f} 0 1 1 {-2*distance} 0 A{distance} {distance*.42:.1f} 0 1 1 0 0" dur="{mdur}s" repeatCount="indefinite"/>'
                       f'<circle r="{moon_size}" fill="{GOLD if pinned else MUTED}"/>{caption}</g>')
        out.append(label(0, size+23, lang["name"], 13, TEXT, "middle", "bold", 'paint-order="stroke" stroke="#060912" stroke-width="4" stroke-linejoin="round"') + label(0, size+40, f'{lang["percent"]:.1f}%', 11, MUTED, "middle") + '</g>')
    out.append('<defs><linearGradient id="comet-tail"><stop stop-color="#59B8FF" stop-opacity="0"/>'
               '<stop offset="1" stop-color="#91D4FF" stop-opacity=".85"/></linearGradient></defs>')
    for i, event in enumerate(snapshot["pushes"]):
        name = event["repo"]["name"]
        # Reserve lanes above and below the planet labels and keep the caption upright.
        y = (114 if i % 2 == 0 else 642) + (i // 2 - 1) * 12
        control_y = y + (-18 if i % 2 == 0 else 16)
        begin = 1 + i * 4
        out.append(
            f'<g opacity="0"><path d="M-96 0L0 -3V3Z" fill="url(#comet-tail)"/>'
            f'<circle r="8" fill="#59B8FF" opacity=".22"/><circle r="3" fill="#CDEAFF"/>'
            f'{label(-8, -10, name, 15, "#BFE9FF", "end")}'
            f'<animateMotion path="M110 {y} Q600 {control_y} 1090 {y}" dur="24s" keyPoints="0;1;1" keyTimes="0;.25;1" calcMode="linear" '
            f'begin="{begin}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;.04;.16;.25;1" '
            f'dur="24s" begin="{begin}s" repeatCount="indefinite"/></g>'
        )
    out.append(label(36, 686, "SUN  DEVELOPER    PLANETS  LANGUAGES    MOONS  REPOSITORIES    COMETS  RECENT PUSHES", 11, MUTED))
    return svg(w, h, "".join(out))


def profile_card(snapshot, config):
    p = snapshot["profile"]
    bio = config["professional"]["bio"]
    avatar = snapshot["avatar"]
    mime = "image/png" if avatar.startswith(b"\x89PNG") else "image/jpeg"
    uri = f"data:{mime};base64,{base64.b64encode(avatar).decode()}"
    out = [title("02", "The sun"), '<defs><clipPath id="pclip"><circle cx="103" cy="147" r="49"/></clipPath></defs>',
           f'<image href="{uri}" x="54" y="98" width="98" height="98" clip-path="url(#pclip)"/>',
           '<circle cx="103" cy="147" r="52" fill="none" stroke="#FACC15" stroke-width="2"/>',
           label(180, 125, p.get("name") or config["professional"]["name"], 25, TEXT, weight="bold"),
           label(180, 153, config["professional"]["headline"], 17, GOLD),
           *(label(180, 184 + i * 20, line, 15, MUTED)
             for i, line in enumerate(wrap_label(bio, CARD_WIDTH-180-PAD, 15, 2))),
           label(54, 243, f'LOCATION  {p.get("location") or config["professional"]["location"]}', 14, MUTED),
           *[label(54 + i * 202, 278, f"{name}  {value}", 14, TEXT)
             for i, (name, value) in enumerate((
                 ("FOLLOWERS", p["followers"]),
                 ("FOLLOWING", p["following"]),
                 ("PUBLIC REPOS", p["public_repos"]),
                 ("PUBLIC STARS", snapshot["public_stars"]),
             ))]]
    return svg(CARD_WIDTH, 316, "".join(out))


def project_card(repo, index):
    lang = repo.get("primaryLanguage") or {}
    color = esc(lang.get("color") or MUTED)
    description = repo.get("description") or "No description provided on GitHub."
    name = repo["name"]
    width, height = 450, 264
    padding = SPACE[4]
    right = width - padding
    out = [
        f'<circle cx="396" cy="40" r="22" fill="{color}" opacity=".13"/>',
        f'<ellipse cx="396" cy="40" rx="29" ry="9" fill="none" stroke="{color}" '
        'opacity=".55" transform="rotate(-22 396 40)"/>',
        f'<circle cx="396" cy="40" r="12" fill="{color}"><animate attributeName="opacity" '
        'values=".75;1;.75" dur="5s" repeatCount="indefinite"/></circle>',
        label(padding, 44, f"MOON {index:02d}", 16, GOLD, weight="bold", extra='letter-spacing="2"'),
    ]
    for i, line in enumerate(wrap_label(name, width-2*padding, 23, 2)):
        out.append(label(padding, 81+i*26, line, 23, TEXT, weight="bold"))
    for i, line in enumerate(wrap_label(description, width-2*padding, 19, 3)):
        out.append(label(padding, 140+i*23, line, 19, MUTED))
    out += [
        f'<path d="M{padding} 210H{right}" stroke="#273044"/>',
        f'<circle cx="{padding+5}" cy="235" r="5" fill="{color}"/>',
        label(padding+18, 241, wrap_label(lang.get("name") or "Unspecified", 185, 17, 1)[0], 17, MUTED),
        label(317, 241, f'★ {repo["stargazerCount"]}', 17, TEXT, "end"),
        label(right, 241, f'⑂ {repo["forkCount"]}', 17, TEXT, "end"),
    ]
    return svg(width, height, "".join(out))


def languages_card(snapshot):
    langs = snapshot["languages"]
    height = max(195, 111+len(langs)*54)
    out = [title("04", "Planetary composition")]
    if not langs:
        out.append(label(36, 125, "No language bytes in included repositories.", 14, MUTED))
    for i, lang in enumerate(langs):
        y = 111+i*54
        width = 510*lang["percent"]/100
        out += [f'<circle cx="45" cy="{y-5}" r="7" fill="{esc(lang["color"])}"/>',
                label(64, y, lang["name"], 15, TEXT), label(CARD_WIDTH-PAD, y, f'{lang["percent"]:.1f}%', 14, MUTED, "end"),
                f'<rect x="247" y="{y-12}" width="510" height="12" rx="6" fill="#273044"/>',
                f'<rect x="247" y="{y-12}" width="{width:.1f}" height="12" rx="6" fill="{esc(lang["color"])}"><animate attributeName="width" from="0" to="{width:.1f}" dur="1.6s" fill="freeze"/></rect>']
    out.append(label(36, height-23, "Share of language bytes across included public repositories", 11, MUTED))
    return svg(CARD_WIDTH, height, "".join(out))


def contributions_card(snapshot):
    days = snapshot["days"]
    metrics = snapshot["metrics"]
    out = [title("05", "Orbit log"), label(36, 106, f'{metrics["year_total"]} CONTRIBUTIONS THIS CALENDAR YEAR', 17, TEXT, weight="bold"),
           label(36, 138, f'CURRENT STREAK  {metrics["current_streak"]} DAYS', 13, GOLD),
           label(355, 138, f'LONGEST STREAK  {metrics["longest_streak"]} DAYS', 13, GOLD),
           label(680, 138, f'ACTIVE  {metrics["active_days"]}/{metrics["period_days"]} DAYS', 12, MUTED)]
    max_count = max((d["contributionCount"] for d in days), default=0)
    days = sorted(days, key=lambda day: day["date"])
    if days:
        first = date.fromisoformat(days[0]["date"])
        start = first - timedelta(days=(first.weekday()+1) % 7)
        end = date.fromisoformat(days[-1]["date"])
        columns = (end-start).days // 7 + 1
        left, top, step_y = 92, 184, 24
        step_x = min(32, (CARD_WIDTH-PAD-left) / columns)
        previous_month = None
        for index in range(columns):
            week = start + timedelta(weeks=index)
            if week.month != previous_month:
                out.append(label(left+index*step_x, top-12, week.strftime("%b"), 13, MUTED))
                previous_month = week.month
        for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
            out.append(label(PAD, top+row*step_y+14, name, 13, MUTED))
        for day in days:
            col, row = divmod((date.fromisoformat(day["date"])-start).days, 7)
            count = day["contributionCount"]
            color = "#192237" if count == 0 else "#214D7B" if count < max_count*.35 else "#357FC2" if count < max_count*.7 else GOLD
            out.append(f'<rect x="{left+col*step_x:.2f}" y="{top+row*step_y}" '
                       f'width="{step_x-SPACE[0]:.2f}" height="18" rx="3" fill="{color}">'
                       f'<title>{esc(day["date"])}: {count} contributions</title></rect>')
    out.append(label(PAD, 370, f'Calendar ending {snapshot["as_of"]}', 14, MUTED))
    return svg(CARD_WIDTH, 394, "".join(out))


def pending_contributions():
    return svg(CARD_WIDTH, 210, title("05", "Orbit log") + label(36, 125, "Contribution data awaits the first authenticated GitHub Actions run.", 15, MUTED))
