"""Build static site from saved Luma HTML capture."""
from __future__ import annotations

import hashlib
import html as html_lib
import re
import ssl
from pathlib import Path
from urllib.parse import urlparse, unquote
import urllib.request

ROOT = Path(__file__).resolve().parent
HTM = ROOT / "Team1 Workshop - São Paulo · Luma.htm"
CHUNK = ROOT / "assets" / "_chunk_global.css"
OUT_CSS = ROOT / "style.css"
OUT_HTML = ROOT / "index.html"
ASSETS_FONTS = ROOT / "assets" / "fonts"
ASSETS_IMG = ROOT / "assets" / "images"

FACTORIA_HEADER = """/* Local Factoria (from Adobe Typekit; licensed for web via Luma) */
@font-face {
  font-family: "factoria";
  src: url("./assets/fonts/factoria-600.woff2") format("woff2");
  font-weight: 600;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: "factoria";
  src: url("./assets/fonts/factoria-500.woff2") format("woff2");
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}

"""

SSL = ssl.create_default_context()

FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Referer": "https://luma.com/",
}


def fetch(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers=FETCH_HEADERS)
        with urllib.request.urlopen(req, context=SSL, timeout=90) as r:
            dest.write_bytes(r.read())
        return True
    except Exception as e:
        print("fetch fail", url[:100], e)
        return False


def extract_style_blocks(html: str) -> list[str]:
    blocks = []
    for m in re.finditer(
        r'<style[^>]*id="__jsx-[^"]*"[^>]*>(.*?)</style>', html, re.DOTALL
    ):
        blocks.append(m.group(1).strip())
    return blocks


def strip_next_from_head(html: str) -> str:
    html = re.sub(
        r'<script[^>]+src="/_next/static/[^"]+"[^>]*>\s*</script>',
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<script[^>]+src="/_next/static/[^"]+"[^>]*></script>',
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<link[^>]+href="/_next/static/chunks/09cd7f69d306d41c\.css"[^>]*/?>',
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(r'<noscript data-n-css=""></noscript>', "", html)
    html = re.sub(
        r'<meta name="sentry-trace"[^>]*/?>',
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(r'<meta name="baggage"[^>]*/?>', "", html, flags=re.IGNORECASE)
    html = re.sub(r'\s*data-next-head=""', "", html)
    html = re.sub(r'\s*data-n-g=""', "", html)
    return html


def remove_next_data(html: str) -> str:
    return re.sub(
        r'<script id="__NEXT_DATA__" type="application/json">.*?</script>',
        "",
        html,
        flags=re.DOTALL,
    )


def clean_lumacdn_url(raw: str) -> str | None:
    """Normalize a captured Luma CDN URL."""
    u = html_lib.unescape(raw.strip())
    for sep in ('"', "'", ")", "&quot;", "&#34;", "<", " ", "\n"):
        if sep in u:
            u = u.split(sep)[0]
    u = u.rstrip(",;")
    if not u.startswith("https://images.lumacdn.com"):
        return None
    return u


def collect_lumacdn_urls(html: str) -> list[str]:
    """Order-preserving unique list of image CDN URLs."""
    seen: set[str] = set()
    ordered: list[str] = []
    for m in re.finditer(r"https://images\.lumacdn\.com[^\s\"'<>]*", html):
        c = clean_lumacdn_url(m.group(0))
        if c and c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def local_image_path(url: str) -> str:
    """Stable local path under assets/images (no entity garbage)."""
    h = hashlib.sha256(url.encode()).hexdigest()[:10]
    p = Path(unquote(urlparse(url).path))
    stem = re.sub(r"[^\w\-]", "_", (p.stem or "img"))[:60]
    suffix = p.suffix or ".bin"
    return f"./assets/images/{stem}_{h}{suffix}"


def rewrite_css_urls_for_legacy_fonts(css: str) -> str:
    """Map /fonts/... in chunk to ./assets/fonts/ if we add files later."""

    def repl(m: re.Match[str]) -> str:
        raw = m.group(1).strip().strip('"').strip("'")
        if raw.startswith("/fonts/"):
            name = Path(raw).name
            return f"url(./assets/fonts/{name})"
        return m.group(0)

    return re.sub(r"url\(\s*([^)]+)\s*\)", repl, css)


def main() -> None:
    html_raw = HTM.read_text(encoding="utf-8")
    chunk = CHUNK.read_text(encoding="utf-8")
    chunk = rewrite_css_urls_for_legacy_fonts(chunk)

    lumas = collect_lumacdn_urls(html_raw)
    img_map: dict[str, str] = {u: local_image_path(u) for u in lumas}

    for remote, rel in img_map.items():
        dest = ROOT / rel.lstrip("./")
        if not dest.exists():
            print("img", remote[:90])
            fetch(remote, dest)

    style_blocks = extract_style_blocks(html_raw)
    merged = FACTORIA_HEADER + "/* === luma global chunk === */\n" + chunk + "\n\n"
    merged += "/* === inline jsx styles from capture === */\n"
    merged += "\n\n".join(style_blocks) + "\n"

    for remote, local in sorted(img_map.items(), key=lambda x: -len(x[0])):
        merged = merged.replace(remote, local)

    OUT_CSS.write_text(merged, encoding="utf-8")
    print("Wrote", OUT_CSS.name, OUT_CSS.stat().st_size)

    h = strip_next_from_head(html_raw)
    h = remove_next_data(h)
    h = re.sub(
        r'<style[^>]*id="__jsx-[^"]*"[^>]*>.*?</style>',
        "",
        h,
        flags=re.DOTALL,
    )

    for remote, local in sorted(img_map.items(), key=lambda x: -len(x[0])):
        h = h.replace(remote, local)

    h = h.replace('href="/favicon.ico"', 'href="./favicon.ico"')
    h = h.replace('href="/apple-touch-icon.png"', 'href="./apple-touch-icon.png"')
    h = re.sub(
        r'<link href="/fonts/factoria\.css"[^>]*/?>',
        "",
        h,
        flags=re.IGNORECASE,
    )
    h = re.sub(
        r'<link rel="manifest" href="/pwa\.webmanifest"/>',
        "",
        h,
        flags=re.IGNORECASE,
    )

    anti = """    <script>
(function(){var r=document.documentElement;function s(t){window.__theme=t;r.classList.remove("dark","light");r.classList.add(t);}var q=window.matchMedia("(prefers-color-scheme: dark)");s(q.matches?"dark":"light");})();
    </script>
"""
    if "<head>" in h and anti.strip() not in h:
        h = h.replace("<head>", "<head>\n" + anti, 1)

    if '<link rel="stylesheet" href="./style.css"' not in h:
        h = h.replace(
            "</head>",
            '    <link rel="stylesheet" href="./style.css" />\n</head>',
            1,
        )

    h = re.sub(
        r"<body>\s*<script data-cfasync=\"false\">.*?</script>",
        "<body>\n",
        h,
        count=1,
        flags=re.DOTALL,
    )

    def fix_preload(m: re.Match[str]) -> str:
        block = m.group(0)
        sm = re.search(r'imageSrcSet="([^"]+)"', block)
        if not sm:
            return ""
        parts = []
        for seg in sm.group(1).split(","):
            seg = seg.strip()
            if not seg:
                continue
            bits = seg.split()
            url = bits[0]
            desc = bits[1] if len(bits) > 1 else ""
            cu = clean_lumacdn_url(url)
            if cu and cu in img_map:
                url = img_map[cu]
            parts.append(f"{url} {desc}".strip())
        srcset = ", ".join(parts)
        sizes_m = re.search(r'imageSizes="([^"]*)"', block)
        sizes = sizes_m.group(1) if sizes_m else ""
        first = parts[0].split()[0] if parts else ""
        return (
            f'<link rel="preload" as="image" href="{first}" '
            f'imagesrcset="{srcset}" imagesizes="{sizes}" />'
        )

    h = re.sub(
        r'<link rel="preload" as="image"[^>]+/>',
        fix_preload,
        h,
        flags=re.IGNORECASE,
    )

    h = h.replace("<meta charSet=", "<meta charset=")

    if "script.js" not in h:
        h = h.replace(
            "</body>",
            '    <script defer src="./script.js"></script>\n</body>',
            1,
        )

    h = re.sub(
        r"\.(png|jpe?g|webp|gif)_quot;",
        r".\1&quot;",
        h,
        flags=re.IGNORECASE,
    )

    OUT_HTML.write_text(h, encoding="utf-8")
    print("Wrote", OUT_HTML.name, OUT_HTML.stat().st_size)


if __name__ == "__main__":
    main()
