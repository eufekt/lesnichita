#!/usr/bin/env python3
"""Write static project pages from public/projects.json and Are.na.

Are.na's docs ask sites to fetch channel data ahead of time instead of calling
the API on every visit: https://www.are.na/developers/explore

Usage: python3 scripts/sync-projects.py
"""

import html
import json
import re
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CATALOG = PUBLIC / "projects.json"
HOME = PUBLIC / "index.html"
API = "https://api.are.na/v3"
ORIGIN = "https://lesnichita.info"
# Are.na serves this channel's gif at its original size for every rendition.
HEAVY_BYTES = 2_000_000

HEADER = """\
  <header>
    <a class="home" href="/">Nichita Hariton</a>
    <nav aria-label="Social links">
      <ul>
        <li><a href="https://www.are.na/la-src/blocks" rel="me">are.na</a></li>
        <li><a href="https://www.instagram.com/lesnichita/" rel="me">instagram</a></li>
      </ul>
    </nav>
  </header>"""


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "lesnichita-sync", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def download(url, dest):
    request = urllib.request.Request(url, headers={"User-Agent": "lesnichita-sync"})
    with urllib.request.urlopen(request, timeout=120) as response, dest.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)


def channel_slug(value):
    if not value:
        return None
    try:
        parts = [part for part in urllib.parse.urlparse(value).path.split("/") if part]
        return parts[-1] if parts else value
    except ValueError:
        return value


def block_id(value):
    match = re.search(r"are\.na/block/(\d+)", str(value or ""))
    return match.group(1) if match else None


def channel_blocks(slug):
    page = 1
    blocks = []
    while True:
        url = f"{API}/channels/{urllib.parse.quote(slug)}/contents?per=100&sort=position_desc&page={page}"
        body = fetch_json(url)
        blocks.extend(body.get("data") or [])
        meta = body.get("meta") or {}
        if not meta.get("has_more_pages"):
            return blocks
        page = meta.get("next_page") or page + 1
        time.sleep(0.4)


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def is_heavy(image):
    """True when the file we would embed is large.

    Are.na's file_size is the original upload. Stills have small and medium
    renditions of a few dozen kilobytes, so those stay hotlinked. GIFs are
    served at the original size for every rendition.
    """
    if not image:
        return False
    src = image.get("src") or ""
    content_type = image.get("content_type") or ""
    if content_type == "image/gif" or src.lower().split("?", 1)[0].endswith(".gif"):
        return True
    if version_src(image, "medium") or version_src(image, "small"):
        return False
    return (image.get("file_size") or 0) > HEAVY_BYTES


def version_src(image, name):
    version = image.get(name) or {}
    return version.get("src")


def picture(image):
    """Small and medium Are.na renditions. The browser picks from srcset."""
    small = image.get("small") or {}
    medium = image.get("medium") or {}
    src = medium.get("src") or small.get("src") or image.get("src")
    candidates = []
    if small.get("src"):
        candidates.append((small["src"], small.get("width") or 400))
    if medium.get("src") and medium.get("src") != small.get("src"):
        candidates.append((medium["src"], medium.get("width") or 1200))
    width = medium.get("width") or image.get("width")
    height = medium.get("height") or image.get("height")
    return src, candidates, width, height


def jpeg_size(path):
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        return None
    index = 2
    while index < len(data) - 8:
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(data[index + 5:index + 7], "big")
            width = int.from_bytes(data[index + 7:index + 9], "big")
            return width, height
        if marker in (0xD8, 0xD9):
            index += 2
            continue
        length = int.from_bytes(data[index + 2:index + 4], "big")
        index += 2 + length
    return None


def ensure_poster(slug, block):
    dest_dir = PUBLIC / "projects" / slug / "posters"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{block['id']}.jpg"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as handle:
        temp = Path(handle.name)
    try:
        download(block["image"]["src"], temp)
        subprocess.check_call(
            [
                "ffmpeg", "-y", "-i", str(temp),
                "-frames:v", "1",
                "-vf", "scale='min(1200,iw)':-2",
                "-q:v", "6",
                str(dest),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        temp.unlink(missing_ok=True)
    return dest


def img_tag(src, candidates, alt, width, height, class_name, lazy):
    attributes = [f'src="{esc(src)}"', f'alt="{esc(alt)}"', 'decoding="async"']
    if class_name:
        attributes.append(f'class="{class_name}"')
    if len(candidates) > 1:
        srcset = ", ".join(f"{url} {width_hint}w" for url, width_hint in candidates)
        attributes.append(f'srcset="{esc(srcset)}"')
        attributes.append('sizes="(min-width: 48rem) 48rem, 100vw"')
    if width and height:
        attributes.append(f'width="{int(width)}"')
        attributes.append(f'height="{int(height)}"')
    if lazy:
        attributes.append('loading="lazy"')
    else:
        attributes.append('fetchpriority="high"')
    return "<img " + " ".join(attributes) + ">"


def gallery_item(slug, block):
    image = block.get("image") or {}
    alt = image.get("alt_text") or block.get("title") or ""
    href = f"https://www.are.na/block/{block['id']}"
    if is_heavy(image):
        poster = ensure_poster(slug, block)
        size = jpeg_size(poster)
        width, height = size if size else (None, None)
        src = f"/projects/{slug}/posters/{poster.name}"
        # The animation stays on Are.na and loads only if the still is opened.
        href = image.get("src") or href
        tag = img_tag(src, [], alt, width, height, None, lazy=True)
        return f'        <li><a class="image-link" href="{esc(href)}">{tag}</a></li>'
    src, candidates, width, height = picture(image)
    if not src:
        return ""
    tag = img_tag(src, candidates, alt, width, height, None, lazy=True)
    return f'        <li><a class="image-link" href="{esc(href)}">{tag}</a></li>'


def meta_block(project, blocks):
    identifier = block_id(project.get("meta_image"))
    if identifier:
        for block in blocks:
            if str(block.get("id")) == identifier and block.get("image"):
                return block
        body = fetch_json(f"{API}/blocks/{identifier}")
        if body.get("image"):
            return body
    return None


def project_page(project, blocks):
    slug = project["slug"]
    title = project.get("title") or slug
    description = project.get("description") or ""
    date = project.get("date")
    tags = [tag for tag in (project.get("tags") or []) if tag]
    channel = project.get("arena_channel")
    meta = meta_block(project, blocks)
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        f"  <title>{esc(title)} — Nichita Hariton</title>",
    ]
    if description:
        parts.append(f'  <meta name="description" content="{esc(description)}">')
    canonical = f"{ORIGIN}/projects/{slug}/"
    parts.extend([
        f'  <link rel="canonical" href="{esc(canonical)}">',
        f'  <meta property="og:title" content="{esc(title)}">',
        f'  <meta property="og:url" content="{esc(canonical)}">',
        '  <meta property="og:type" content="article">',
    ])
    if description:
        parts.append(f'  <meta property="og:description" content="{esc(description)}">')
    if meta and meta.get("image") and not is_heavy(meta["image"]):
        src, _, _, _ = picture(meta["image"])
        if src:
            parts.append(f'  <meta property="og:image" content="{esc(src)}">')
    parts.extend([
        '  <link rel="stylesheet" href="/style.css">',
        "</head>",
        "<body>",
        HEADER,
        '  <main class="project" lang="fr">',
        f"    <h1>{esc(title)}</h1>",
    ])
    if date:
        parts.append(f'    <p class="project-date">{esc(date)}</p>')
    if description:
        parts.append(f'    <p class="project-description">{esc(description)}</p>')
    if tags:
        parts.append(f'    <p class="project-tags">{esc(", ".join(tags))}</p>')
    if meta and meta.get("image") and not is_heavy(meta["image"]):
        src, candidates, width, height = picture(meta["image"])
        tag = img_tag(src, candidates, title, width, height, "meta-image", lazy=False)
        href = f"https://www.are.na/block/{meta['id']}"
        parts.append(f'    <a class="image-link" href="{esc(href)}">{tag}</a>')
    elif project.get("meta_image") and not block_id(project.get("meta_image")):
        tag = img_tag(project["meta_image"], [], title, None, None, "meta-image", lazy=False)
        parts.append(f'    <a class="image-link" href="{esc(project["meta_image"])}">{tag}</a>')
    if channel:
        parts.append(f'    <p><a href="{esc(channel)}">are.na</a></p>')
    items = [gallery_item(slug, block) for block in blocks if block.get("image")]
    items = [item for item in items if item]
    if items:
        parts.append('    <ul class="images" aria-label="Channel images">')
        parts.extend(items)
        parts.append("    </ul>")
    parts.extend(["  </main>", "</body>", "</html>", ""])
    return "\n".join(parts)


def work_item(project, blocks):
    slug = project["slug"]
    title = project.get("title") or slug
    href = f"/projects/{slug}/"
    lines = ["        <li>"]
    meta = meta_block(project, blocks)
    image = (meta or {}).get("image") or {}
    thumb = (image.get("small") or {}).get("src")
    if thumb and not is_heavy(image):
        width = (image.get("small") or {}).get("width")
        height = (image.get("small") or {}).get("height")
        tag = img_tag(thumb, [], "", width, height, "project-thumb", lazy=False)
        lines.append(f'          <a class="image-link" href="{esc(href)}" aria-label="{esc(title)}">{tag}</a>')
    elif project.get("meta_image") and not block_id(project.get("meta_image")):
        tag = img_tag(project["meta_image"], [], "", None, None, "project-thumb", lazy=False)
        lines.append(f'          <a class="image-link" href="{esc(href)}" aria-label="{esc(title)}">{tag}</a>')
    line = f'          <p class="project-line"><a href="{esc(href)}">{esc(title)}</a>'
    if project.get("date"):
        line += f'<span class="subtitle">{esc(project["date"])}</span>'
    line += "</p>"
    lines.append(line)
    if project.get("description"):
        lines.append(f'          <p class="project-description">{esc(project["description"])}</p>')
    if project.get("tags"):
        tags = [tag for tag in project["tags"] if tag]
        if tags:
            lines.append(f'          <p class="project-tags">{esc(", ".join(tags))}</p>')
    lines.append("        </li>")
    return "\n".join(lines)


def write_home(sections):
    html_text = HOME.read_text()
    pattern = re.compile(r"<!-- work:start -->.*?<!-- work:end -->", re.S)
    block = "<!-- work:start -->\n" + "\n".join(sections) + "\n      <!-- work:end -->"
    updated, count = pattern.subn(block, html_text, count=1)
    if count != 1:
        raise SystemExit("public/index.html is missing <!-- work:start --> and <!-- work:end -->")
    HOME.write_text(updated)


def main():
    projects = json.loads(CATALOG.read_text())
    sections = []
    for project in projects:
        slug = project.get("slug") or ""
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            raise SystemExit(f"slug must be lowercase letters, numbers, and hyphens: {slug!r}")
        slug_name = channel_slug(project.get("arena_channel"))
        blocks = channel_blocks(slug_name) if slug_name else []
        page = PUBLIC / "projects" / slug / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(project_page(project, blocks))
        sections.append(work_item(project, blocks))
        images = [block for block in blocks if block.get("image")]
        heavy = [block for block in images if is_heavy(block.get("image"))]
        print(f"{slug}: {len(images)} images, {len(heavy)} linked instead of embedded")
    write_home(["      <ul>", *sections, "      </ul>"])


if __name__ == "__main__":
    main()
