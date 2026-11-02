import re


def _header_tag(html, title):
    for match in re.finditer(
        r"<header[^>]*>(?:(?!</header>).)*?</header>", html, re.DOTALL
    ):
        if title in match.group(0):
            return match.group(0)
    raise AssertionError(f"header for {title!r} not found in response")


def _nav_item_tag(html, link_text):
    for match in re.finditer(r"<li[^>]*>(?:(?!</li>).)*?</li>", html, re.DOTALL):
        if link_text in match.group(0):
            return match.group(0)
    raise AssertionError(f"nav item for {link_text!r} not found in response")
