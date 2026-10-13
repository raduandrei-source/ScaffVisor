"""Links and constants shown to the user."""

DOCS_URL = "https://raduandrei-source.github.io/ScaffVisor/"
REPO_URL = "https://github.com/raduandrei-source/ScaffVisor"

# page -> (file, anchor) in the documentation site; "" is the home page
PAGES = {
    "": "",
    "layout": "panel.html#layout",
    "ground": "panel.html#ground",
    "parts": "panel.html#parts",
    "result": "panel.html#result",
    "presets": "presets.html",
    "philosophy": "philosophy.html",
}


def docs_url(page=""):
    return DOCS_URL + PAGES.get(page, "")
