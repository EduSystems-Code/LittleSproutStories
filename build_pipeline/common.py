"""
Shared helpers for the LittleSprout build pipeline: balanced-tag extraction
(regex alone can't safely match nested <div>...</div> like a helper-slot's
inner label div), used by both extract_spec.py and render.py so the two
stay in lockstep on what counts as "the stage" or "the page".
"""

import re


def find_balanced(html: str, open_tag_start: int, tag: str) -> tuple[int, int]:
    """Given the index of a '<tag ...>' opening tag, return (content_start,
    content_end) spanning up to (not including) its matching '</tag>',
    correctly skipping over nested same-name tags."""
    open_re = re.compile(r"<%s(?:\s[^>]*)?>" % re.escape(tag))
    close_re = re.compile(r"</%s>" % re.escape(tag))

    m = open_re.match(html, open_tag_start)
    if not m:
        raise ValueError(f"No <{tag}> at index {open_tag_start}")
    content_start = m.end()
    depth = 1
    pos = content_start
    while depth > 0:
        next_open = open_re.search(html, pos)
        next_close = close_re.search(html, pos)
        if not next_close:
            raise ValueError(f"Unbalanced <{tag}> starting at {open_tag_start}")
        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            pos = next_close.end()
    content_end = pos - len(f"</{tag}>")
    return content_start, content_end


def extract_all_balanced(html: str, open_marker_re: str, tag: str):
    """Find every top-level occurrence of open_marker_re, return list of
    (full_match_start, full_match_end_exclusive_of_close_tag_included, inner_html)."""
    out = []
    for m in re.finditer(open_marker_re, html):
        start = m.start()
        cstart, cend = find_balanced(html, start, tag)
        full_end = cend + len(f"</{tag}>")
        out.append((start, full_end, html[cstart:cend]))
    return out
