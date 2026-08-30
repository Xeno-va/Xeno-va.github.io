#!/usr/bin/env python3
"""Build the static site: markdown in _src/content -> HTML at the repo root."""

import html
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import markdown
import yaml
from PIL import Image

SRC = Path(__file__).parent
ROOT = SRC.parent
CONTENT = SRC / "content"

MD = markdown.Markdown(
    extensions=["extra", "sane_lists", "toc", "attr_list", "smarty"],
    output_format="html5",
)


def render_md(text):
    MD.reset()
    return MD.convert(text)


def load_doc(path):
    """Split '---' YAML frontmatter from the markdown body."""
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw
    if raw.startswith("---"):
        _, fm, body = raw.split("---", 2)
        meta = yaml.safe_load(fm) or {}
    meta = dict(meta)
    meta["slug"] = meta.get("slug") or path.stem
    meta["body"] = body.strip()
    return meta


def fmt_date(value):
    if not value:
        return ""
    if isinstance(value, str):
        value = datetime.fromisoformat(value).date()
    return value.strftime("%d %B %Y")


def iso(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value).date()
    return value.isoformat()


def e(text):
    return html.escape(str(text or ""), quote=True)


KINDS = {
    "project": {"label": "Project", "dir": "projects"},
    "lab note": {"label": "Lab note", "dir": "lab-notes"},
}


def kind_of(p):
    k = (p.get("kind") or "project").strip().lower()
    if k not in KINDS:
        raise SystemExit(f"unknown kind {k!r} in {p['slug']} — use: {', '.join(KINDS)}")
    return KINDS[k]


def url_of(p):
    return f"/{kind_of(p)['dir']}/{p['slug']}/"


RASTER = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}


def strip_image(src, dst):
    """Re-encode an image so only pixels survive — no EXIF, no GPS, no ICC,
    no PNG text chunks, no camera serial, no timestamps."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    ext = src.suffix.lower()

    if ext == ".svg":
        text = src.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"(?is)<metadata\b.*?</metadata>", "", text)
        text = re.sub(r"(?is)<!--.*?-->", "", text)
        dst.write_text(text, encoding="utf-8")
        return

    if ext not in RASTER:
        raise SystemExit(f"refusing to publish {src.name}: unknown image type")

    with Image.open(src) as im:
        im.load()
        clean = Image.frombytes(im.mode, im.size, im.tobytes())
        if ext in {".jpg", ".jpeg"}:
            clean.save(dst, "JPEG", quality=92, optimize=True,
                       exif=b"", icc_profile=None)
        elif ext == ".png":
            clean.save(dst, "PNG", optimize=True, pnginfo=None, icc_profile=None)
        else:
            clean.save(dst, icc_profile=None)


def audit_images(root):
    """Refuse to finish a build if anything PUBLISHED still carries metadata.
    The source folder is skipped — originals keep their metadata on purpose."""
    bad = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in RASTER:
            continue
        if SRC in f.parents:
            continue
        with Image.open(f) as im:
            leftovers = {k: v for k, v in (im.info or {}).items()
                         if k not in {"dpi", "transparency", "gamma", "srgb",
                                      "aspect", "compression", "interlace",
                                      "jfif", "jfif_version", "jfif_unit",
                                      "jfif_density", "loop", "duration",
                                      "version", "background"}}
            if hasattr(im, "getexif") and dict(im.getexif()):
                leftovers["exif"] = "present"
        if leftovers:
            bad.append(f"{f.relative_to(root)}: {sorted(leftovers)}")
    if bad:
        raise SystemExit("METADATA STILL PRESENT — not publishing:\n  " + "\n  ".join(bad))


# hexagon with an inscribed X — inlined so it works without an extra request
MARK = (
    '<svg class="mark" viewBox="0 0 32 32" aria-hidden="true" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linejoin="round">'
    '<path d="M16 2.5 28 9.25v13.5L16 29.5 4 22.75V9.25Z"/>'
    '<path d="M11.5 11.5 20.5 20.5M20.5 11.5 11.5 20.5" stroke-linecap="round"/>'
    "</svg>"
)


# --------------------------------------------------------------------------
# templates
# --------------------------------------------------------------------------

def shell(site, *, title, description, body, path, extra_class=""):
    """Wrap page body in the site chrome. `path` is the page's URL path."""
    nav = "\n".join(
        '        <a href="{href}"{cur}>{label}</a>'.format(
            href=e(item["href"]),
            label=e(item["label"]),
            cur=' class="current"' if item["href"] == path else "",
        )
        for item in site["nav"]
    )
    canonical = site["url"].rstrip("/") + path
    full_title = title if title == site["name"] else f"{title} — {site['name']}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{e(full_title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:site_name" content="{e(site['name'])}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="/assets/mark.svg" type="image/svg+xml">
<link rel="alternate" type="application/atom+xml" href="/feed.xml" title="{e(site['name'])}">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body class="{e(extra_class)}">
<a class="skip" href="#main">Skip to content</a>
<header class="site-head">
  <div class="wrap head-inner">
    <a class="brand" href="/">
      {MARK}
      <span>{e(site['name'])}</span>
    </a>
    <input type="checkbox" id="navtoggle" hidden>
    <label class="burger" for="navtoggle" aria-label="Menu"><span></span></label>
    <nav>
{nav}
    </nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-foot">
  <div class="wrap foot-inner">
    <p>&copy; {datetime.now().year} {e(site['name'])}</p>
    <p><a href="/contact/">Make an enquiry</a></p>
  </div>
</footer>
</body>
</html>
"""


def home(site, posts):
    h = site["home"]
    if posts:
        work_band = f"""<section class="band alt">
  <div class="wrap">
    <h2 class="eyebrow">Recent</h2>
    <div class="teasers">
{chr(10).join(teaser(p) for p in posts[:3])}
    </div>
    <p class="more"><a href="/work/">Everything published &rarr;</a></p>
  </div>
</section>"""
    else:
        work_band = ""
    return f"""<section class="hero">
  <div class="wrap">
    <h1>{e(h['headline'])}</h1>
    <p class="lede">{e(h['subtext'])}</p>
    <p class="actions">
      <a class="btn primary" href="/contact/">Make an enquiry</a>
      <a class="btn" href="/services/">What gets built</a>
    </p>
  </div>
</section>

<section class="band">
  <div class="wrap narrow">
    <p class="standfirst">{e(h['summary'])}</p>
    <p class="more"><a href="/services/">What gets built, and who it is for &rarr;</a></p>
  </div>
</section>

{work_band}
"""


def teaser(p):
    tag = f'<span class="kind">{e(kind_of(p)["label"])}</span>'
    return f"""      <a class="teaser" href="{e(url_of(p))}">
        <div class="teaser-meta">{tag}<time datetime="{iso(p['date'])}">{fmt_date(p['date'])}</time></div>
        <h3>{e(p['title'])}</h3>
        <p>{e(p.get('summary', ''))}</p>
        <span class="go">Read &rarr;</span>
      </a>"""


def projects_index(site, projects):
    if projects:
        inner = f"""    <div class="teasers">
{chr(10).join(teaser(p) for p in projects)}
    </div>"""
    else:
        inner = """    <div class="empty">
      <p>Nothing published here yet.</p>
      <p>Work in progress is written up as it goes and posted when it stands on
      its own. Some systems are internal and stay that way.</p>
      <p><a href="/contact/">Ask about current work &rarr;</a></p>
    </div>"""
    return f"""<section class="page-head">
  <div class="wrap">
    <h1>Work</h1>
    <p class="lede">Finished builds and lab notes, newest first — including the routes that did not work out.</p>
  </div>
</section>
<section class="band">
  <div class="wrap narrow">
{inner}
  </div>
</section>
"""


def project_page(site, p):
    body = render_md(p["body"])
    tag = f'<span class="kind">{e(kind_of(p)["label"])}</span>'
    status = f'<span class="status">{e(p["status"])}</span>' if p.get("status") else ""
    repo = (f'<p class="repo"><a href="{e(p["repo"])}">Code and key files &rarr;</a></p>'
            if p.get("repo") else "")
    return f"""<article class="doc">
  <div class="wrap narrow">
    <div class="doc-meta">{tag}{status}<time datetime="{iso(p['date'])}">{fmt_date(p['date'])}</time></div>
    <h1>{e(p['title'])}</h1>
    <div class="prose">
{body}
    </div>
{repo}
    <p class="back"><a href="/work/">&larr; All work</a></p>
  </div>
</article>
"""


ENQUIRY_FORM = """
    <form class="enquiry" action="https://api.web3forms.com/submit" method="POST">
      <input type="hidden" name="access_key" value="{key}">
      <input type="hidden" name="subject" value="Enquiry from {name}">
      <input type="hidden" name="from_name" value="{name}">
      <input type="checkbox" name="botcheck" class="hp" tabindex="-1" autocomplete="off">

      <div class="row">
        <label>
          <span>Name</span>
          <input type="text" name="name" required autocomplete="name">
        </label>
        <label>
          <span>Email</span>
          <input type="email" name="email" required autocomplete="email">
        </label>
      </div>

      <label>
        <span>Organisation <em>optional</em></span>
        <input type="text" name="organisation" autocomplete="organization">
      </label>

      <label>
        <span>What is the enquiry about?</span>
        <select name="topic">
          <option>A system that needs building</option>
          <option>Something published here</option>
          <option>Partnership or investment</option>
          <option>Something else</option>
        </select>
      </label>

      <label>
        <span>What has to happen, and what constrains it?</span>
        <textarea name="message" rows="7" required
          placeholder="What the system has to do, where it has to do it, and what limits it — budget, timeline, environment, regulatory context. Rough is fine."></textarea>
      </label>

      <button type="submit" class="btn primary">Send enquiry</button>
      <p class="formnote">Goes straight to an inbox. Nothing is stored on this site.</p>
    </form>
"""


def page_page(site, pg):
    body = render_md(pg["body"])
    lede = f'<p class="lede">{e(pg["lede"])}</p>' if pg.get("lede") else ""
    if pg.get("form"):
        body += ENQUIRY_FORM.format(
            key=e(site.get("form_key", "")), name=e(site["name"]))
    return f"""<article class="doc">
  <div class="wrap narrow">
    <h1>{e(pg['title'])}</h1>
    {lede}
    <div class="prose">
{body}
    </div>
  </div>
</article>
"""


# --------------------------------------------------------------------------
# feed / sitemap
# --------------------------------------------------------------------------

def atom(site, projects):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = []
    for p in projects:
        url = site['url'].rstrip('/') + url_of(p)
        entries.append(f"""  <entry>
    <title>{e(p['title'])}</title>
    <link href="{e(url)}"/>
    <id>{e(url)}</id>
    <updated>{iso(p['date'])}T00:00:00Z</updated>
    <summary>{e(p.get('summary', ''))}</summary>
  </entry>""")
    body = "\n".join(entries)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{e(site['name'])}</title>
  <link href="{e(site['url'])}"/>
  <link rel="self" href="{e(site['url'].rstrip('/'))}/feed.xml"/>
  <id>{e(site['url'])}</id>
  <updated>{now}</updated>
{body}
</feed>
"""


def sitemap(site, paths):
    urls = "\n".join(
        f"  <url><loc>{e(site['url'].rstrip('/') + p)}</loc></url>" for p in paths
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
"""


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def main():
    site = yaml.safe_load((CONTENT / "site.yml").read_text(encoding="utf-8"))

    projects = sorted(
        (load_doc(f) for f in (CONTENT / "posts").glob("*.md")),
        key=lambda p: iso(p["date"]),
        reverse=True,
    )
    pages = [load_doc(f) for f in sorted((CONTENT / "pages").glob("*.md"))]

    # remove everything the previous build wrote, so renamed or deleted
    # content cannot leave an orphaned page live on the site
    manifest = SRC / "manifest.txt"
    if manifest.exists():
        for line in manifest.read_text().splitlines():
            old = ROOT / line
            if old.exists():
                old.unlink()
            parent = old.parent
            while parent != ROOT and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
    if (ROOT / "assets").exists():
        shutil.rmtree(ROOT / "assets")

    written = []
    paths = ["/"]

    written.append(write(ROOT / "index.html", shell(
        site, title=site["name"], description=site["description"],
        body=home(site, projects), path="/", extra_class="home")))

    written.append(write(ROOT / "work/index.html", shell(
        site, title="Work",
        description="Finished builds and lab notes.",
        body=projects_index(site, projects), path="/work/")))
    paths.append("/work/")

    for p in projects:
        u = url_of(p)
        written.append(write(ROOT / f"{u.strip('/')}/index.html", shell(
            site, title=p["title"], description=p.get("summary", ""),
            body=project_page(site, p), path=u)))
        paths.append(u)

    for pg in pages:
        written.append(write(ROOT / f"{pg['slug']}/index.html", shell(
            site, title=pg["title"], description=pg.get("description", ""),
            body=page_page(site, pg), path=f"/{pg['slug']}/")))
        paths.append(f"/{pg['slug']}/")

    written.append(write(ROOT / "feed.xml", atom(site, projects)))
    written.append(write(ROOT / "sitemap.xml", sitemap(site, paths)))
    written.append(write(ROOT / "robots.txt",
                         f"User-agent: *\nAllow: /\nSitemap: {site['url'].rstrip('/')}/sitemap.xml\n"))
    if site.get("custom_domain", True):
        written.append(write(ROOT / "CNAME", site["domain"] + "\n"))
    elif (ROOT / "CNAME").exists():
        (ROOT / "CNAME").unlink()
    written.append(write(ROOT / ".nojekyll", ""))

    # 404
    written.append(write(ROOT / "404.html", shell(
        site, title="Not found", description="Page not found.",
        body='<section class="page-head"><div class="wrap"><h1>404</h1>'
             '<p class="lede">That page does not exist. '
             '<a href="/">Back to the front page</a>.</p></div></section>',
        path="/404.html")))

    shutil.copytree(SRC / "assets", ROOT / "assets", dirs_exist_ok=True)
    written += sorted((ROOT / "assets").rglob("*"))

    # every image is re-encoded on the way out — pixels only
    src_images = SRC / "images"
    if (ROOT / "images").exists():
        shutil.rmtree(ROOT / "images")
    n_img = 0
    if src_images.exists():
        for f in sorted(src_images.rglob("*")):
            if f.is_file():
                strip_image(f, ROOT / "images" / f.relative_to(src_images))
                n_img += 1
        written += sorted((ROOT / "images").rglob("*"))
    audit_images(ROOT)

    manifest.write_text(
        "\n".join(str(w.relative_to(ROOT)) for w in written if w.is_file()) + "\n")

    print(f"built {len(written)} files, {len(projects)} posts, {len(pages)} pages, "
          f"{n_img} images stripped and audited clean")
    for w in written:
        print("  ", w.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
