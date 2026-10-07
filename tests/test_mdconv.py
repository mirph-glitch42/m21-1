"""mdconv: rich HTML -> GFM converter (TDD per html-to-markdown-section-extraction.md).

All 56 TESTS cases are transcribed byte-exact from doc section 6 (G11
synthetic inputs shaped like live CMS output), plus the namespaced
(article_id) group of doc 6 (D6 named anchors; D8 T2 label hoisting).
Property tests P1-P4 follow doc 6.1 with the fixed seed 20261002.
"""

import random
import re
from collections import Counter

import pytest

from m21_crawl import mdconv
from m21_crawl.mdconv import HtmlConversionError, convert

BASE_URL = "https://www.knowva.ebenefits.va.gov"

# (name, input, expected) — doc section 6, cases 1-56, byte-exact expected.
CASES: list[tuple[str, str, str]] = [
    (
        "case01 minimal paragraph",
        "<p>Hello world</p>",
        "Hello world\n",
    ),
    (
        "case02 heading with emphasis",
        "<h2>Part <strong>1</strong>: Title</h2>",
        "## Part **1**: Title\n",
    ),
    (
        "case03 plain external link",
        '<p><a href="https://example.com/x">go</a></p>',
        "[go](https://example.com/x)\n",
    ),
    (
        "case04 eGain article link absolute with query",
        '<a class="eGainArticleLink" articleid="123" '
        'href="https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/123?portalId=999&usertype=customer">'
        "Section B</a>",
        "[Section B](https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/123)\n",
    ),
    (
        "case05 relative article link",
        '<a href="/system/ws/v11/ss/article/456?lang=en-US">X</a>',
        "[X](https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/456)\n",
    ),
    (
        "case06 2x2 table",
        "<table><thead><tr><th>A</th><th>B</th></tr></thead>"
        "<tbody><tr><td>1</td><td>2</td></tr></tbody></table>",
        "| A | B |\n| --- | --- |\n| 1 | 2 |\n",
    ),
    (
        "case07 ragged row padding",
        "<table><tr><th>A</th><th>B</th><th>C</th></tr><tr><td>1</td></tr></table>",
        "| A | B | C |\n| --- | --- | --- |\n| 1 |  |  |\n",
    ),
    (
        "case08 pipe escape",
        "<table><tr><th>K</th></tr><tr><td>a|b</td></tr></table>",
        "| K |\n| --- |\n| a\\|b |\n",
    ),
    (
        "case09 nested unordered list",
        "<ul><li>one<ul><li>sub</li></ul></li></ul>",
        "- one\n    - sub\n",
    ),
    (
        "case10 ordered list",
        "<ol><li>first</li><li>second</li></ol>",
        "1. first\n2. second\n",
    ),
    (
        "case11 span style stripping + nbsp",
        '<p><span style="color: red">red</span>&nbsp;text</p>',
        "red text\n",
    ),
    (
        "case12 adjacent emphasis disambiguation",
        "<p><strong>a</strong><em>b</em></p>",
        "**a** *b*\n",
    ),
    (
        "case13 layout frame with nested data table",
        "<table><tbody><tr><td><h3>In This Section</h3></td>"
        "<td><div>This section contains the following topics:</div>"
        "<table><tr><th>Topic</th><th>Name</th></tr>"
        "<tr><td>1</td><td>Alpha</td></tr></table></td></tr></tbody></table>",
        "### In This Section\n\nThis section contains the following topics:\n\n"
        "| Topic | Name |\n| --- | --- |\n| 1 | Alpha |\n",
    ),
    (
        "case14 javascript link dropped",
        '<a href="javascript:void(0)">click</a>',
        "click\n",
    ),
    (
        "case15 image with alt",
        '<p><img src="/img/x.png" alt="Figure 1"></p>',
        "![Figure 1](https://www.knowva.ebenefits.va.gov/img/x.png)\n",
    ),
    (
        "case16 br becomes space",
        "<p>line one<br>line two</p>",
        "line one line two\n",
    ),
    (
        "case17 horizontal rule (D9: dropped)",
        "<hr>",
        "",
    ),
    (
        "case18 blockquote",
        "<blockquote><p>note</p></blockquote>",
        "> note\n",
    ),
    (
        "case19 list inside a cell",
        "<table><tr><th>K</th></tr><tr><td><ul><li>a</li><li>b</li></ul></td></tr></table>",
        "| K |\n| --- |\n| a; b |\n",
    ),
    (
        "case20 inline code",
        "<p><code>x = 1</code></p>",
        "`x = 1`\n",
    ),
    (
        "case21 pre block with fence",
        "<pre><code>def f():\n    return 1</code></pre>",
        "```\ndef f():\n    return 1\n```\n",
    ),
    (
        "case22 heading clamp",
        "<h4>Deep</h4>",
        "#### Deep\n",
    ),
    (
        "case23a empty input",
        "",
        "",
    ),
    (
        "case23b whitespace-only input",
        "   \n  ",
        "",
    ),
    (
        "case24 nesting depth probe (50 divs)",
        "<div>" * 25 + "<p>deep</p>" + "</div>" * 25,
        "deep\n",
    ),
    (
        "case25 empty emphasis dropped",
        "<p>a<strong></strong>b</p>",
        "ab\n",
    ),
    (
        "case26 layout frame, spacer column",
        "<table><tr><td><h2>Overview</h2></td><td></td><td><p>Body text</p></td></tr></table>",
        "## Overview\n\nBody text\n",
    ),
    (
        "case27 section-mark label with named anchor",
        '<table><tr><td><h3>I.i.1.A.1.a<a id="1a" name="1a">.</a>'
        "&nbsp;Description of PL 106-475</h3></td>"
        "<td></td><td><p>Body text</p></td></tr></table>",
        '<a id="1a" name="1a"></a>\n\n### I.i.1.A.1.a. Description of PL 106-475\n\nBody text\n',
    ),
    (
        "case28 heading in non-leading cell falls back to GFM table",
        "<table><tr><th>K</th><th>Head</th></tr><tr><td><h3>Deep</h3></td><td>x</td></tr></table>",
        "| K | Head |\n| --- | --- |\n| Deep | x |\n",
    ),
    (
        "case29 one non-layout row falls back to GFM table",
        "<table><tr><td><h2>Head</h2></td><td>x</td></tr><tr><td>plain</td><td>y</td></tr></table>",
        "| Head | x |\n| --- | --- |\n| plain | y |\n",
    ),
    (
        "case30 nested layout frame dissolves recursively",
        "<table><tr><td><h2>Outer</h2></td><td></td>"
        "<td><table><tr><td><h3>Inner</h3></td><td></td><td><p>Deep</p></td></tr></table></td></tr></table>",
        "## Outer\n\n### Inner\n\nDeep\n",
    ),
    (
        "case31 top-level named anchor, standalone",
        '<p>Before</p><a name="top"></a><p>After</p>',
        'Before\n\n<a name="top"></a>\n\nAfter\n',
    ),
    (
        "case32 anchor wrapping text in a paragraph",
        '<p><a id="rm">the RM</a></p>',
        '<a id="rm"></a>the RM\n',
    ),
    (
        "case33 anchor with a usable link",
        '<p><a id="x" href="https://example.com/y">go</a></p>',
        "[go](https://example.com/y)\n",
    ),
    (
        "case34 null link href=#",
        '<p><a href="#">top</a></p>',
        "[top](#)\n",
    ),
    (
        "case35 id and name differ",
        '<p><a id="x" name="y">label</a></p>',
        '<a id="x" name="y"></a>label\n',
    ),
    (
        "case36 label cell anchor sibling of heading",
        '<table><tr><td><h3>Section</h3><a name="top"></a></td>'
        "<td></td><td><p>Body</p></td></tr></table>",
        '### Section\n\n<a name="top"></a>\n\nBody\n',
    ),
    (
        "case37 div wraps an emphasized run",
        "<div>An <em>initial claim</em> is a request for benefits.</div>",
        "An *initial claim* is a request for benefits.\n",
    ),
    (
        "case38 top-level emphasized run",
        "An <em>initial claim</em> is a request for benefits.",
        "An *initial claim* is a request for benefits.\n",
    ),
    (
        "case39 nested spans inside a div",
        "<div><span>An</span> <em>initial claim</em> <span>is a request.</span></div>",
        "An *initial claim* is a request.\n",
    ),
    (
        "case40 bold-emphasis hugging a parenthesis",
        "An <strong><em>independent medical opinion </em></strong>(IMO), "
        "as discussed in "
        '<a href="http://www.ecfr.gov/current/title-38/section-3.328">38 CFR 3.328</a>'
        ", is an independent assessment.",
        "An ***independent medical opinion***(IMO), as discussed in "
        "[38 CFR 3.328](http://www.ecfr.gov/current/title-38/section-3.328), "
        "is an independent assessment.\n",
    ),
    (
        "case41 italic label + link inside a div",
        "<div><i>Note</i>: As discussed in "
        '<a href="https://example.com/x">the guidance</a>, '
        "VA Central Office reviews the claim.</div>",
        "*Note*: As discussed in [the guidance](https://example.com/x), "
        "VA Central Office reviews the claim.\n",
    ),
    (
        "case42 div holding a real paragraph",
        "<div>An <em>initial claim</em> is a request.<p>Next block.</p></div>",
        "An *initial claim* is a request.\n\nNext block.\n",
    ),
    (
        "case43 named anchor inside a div run",
        '<div>See <a id="ref">the reference</a> for details.</div>',
        'See <a id="ref"></a>the reference for details.\n',
    ),
    (
        "case44 T2 section-mark frame, spacer + image",
        "<table><tr><td><span>II.i.2.B.4.c. Example of Outdated Form Determination</span></td>"
        '<td></td><td><img src="/img/form.png" alt="VA Form 21-526EZ"></td></tr></table>',
        "### II.i.2.B.4.c. Example of Outdated Form Determination\n\n"
        "![VA Form 21-526EZ](https://www.knowva.ebenefits.va.gov/img/form.png)\n",
    ),
    (
        "case45 T2 mark label + nested data table",
        "<table><tr><td>II.i.2.C.6.h. Rating Review of Undeliverable Mail</td>"
        "<td><table><tr><th>If</th><th>Then</th></tr>"
        "<tr><td>no EP</td><td>remand</td></tr></table></td></tr></table>",
        "### II.i.2.C.6.h. Rating Review of Undeliverable Mail\n\n"
        "| If | Then |\n| --- | --- |\n| no EP | remand |\n",
    ),
    (
        "case46 T2 Change Date bold label (B11)",
        "<table><tr><td><b>Change Date</b></td><td></td><td>November 18, 2020</td></tr></table>",
        "> **Change Date**\n> November 18, 2020\n",
    ),
    (
        "case47 T2 spacer-first Introduction",
        "<table><tr><td></td><td>Introduction</td>"
        "<td><p>This topic contains the following.</p></td></tr></table>",
        "### Introduction\n\nThis topic contains the following.\n",
    ),
    (
        "case48 two-cell letterhead stays GFM",
        "<table><tr><td>Department of Veterans Affairs</td>"
        "<td>Memorandum of Changes</td></tr></table>",
        "| Department of Veterans Affairs | Memorandum of Changes |\n| --- | --- |\n",
    ),
    (
        "case49 two-cell memo row stays GFM",
        "<table><tr><td>K-1</td><td>Form number for estate tax</td></tr></table>",
        "| K-1 | Form number for estate tax |\n| --- | --- |\n",
    ),
    (
        "case50 T2 4-cell spacer-first In This Section",
        "<table><tr><td></td><td><b>In This Section</b></td><td></td>"
        "<td><p>Topics listed below.</p></td></tr></table>",
        "### In This Section\n\nTopics listed below.\n",
    ),
    (
        "case51 T2 mark label with named anchor",
        '<table><tr><td>V.iii.5.3.g<a id="g5" name="g5">.</a> Granting a Subclass</td>'
        "<td><p>Body text</p></td></tr></table>",
        '<a id="g5" name="g5"></a>\n\n### V.iii.5.3.g. Granting a Subclass\n\nBody text\n',
    ),
    (
        "case52 T2 mark with space after a digit segment",
        "<table><tr><td>IX.i.2.4. b. Where to Find the Form</td>"
        "<td><p>Available online.</p></td></tr></table>",
        "### IX.i.2.4. b. Where to Find the Form\n\nAvailable online.\n",
    ),
    (
        "case53 T2 bold In This Section, two cells",
        "<table><tr><td><b>In This Section</b></td><td>content</td></tr></table>",
        "### In This Section\n\ncontent\n",
    ),
    (
        "case54 T3 all-empty table",
        "<table><tr><td></td></tr></table>",
        "",
    ),
    (
        "case55 three-cell rating row stays GFM",
        "<table><tr><td>7101</td><td>Hypertension</td><td>10</td></tr></table>",
        "| 7101 | Hypertension | 10 |\n| --- | --- | --- |\n",
    ),
    (
        "case56 T1 Change Date heading (B11)",
        "<table><tr><td><h3>Change Date</h3></td><td></td><td>August 22, 2024</td></tr></table>",
        "> **Change Date**\n> August 22, 2024\n",
    ),
    (
        "case57 hr-flanked frame renders without rules (D9/B13)",
        "<div><hr/></div><table><tr><td><h3>Change Date</h3></td>"
        "<td>&nbsp;</td><td>February 14, 2025</td></tr></table><div><hr/></div>",
        "> **Change Date**\n> February 14, 2025\n",
    ),
    (
        "case58 hr between paragraphs (D9)",
        "<p>A</p><hr><p>B</p>",
        "A\n\nB\n",
    ),
]


@pytest.mark.parametrize(
    ("name", "html", "expected"),
    CASES,
    ids=[case[0] for case in CASES],
)
def test_doc_cases_byte_exact(name: str, html: str, expected: str) -> None:
    assert convert(html, base_url=BASE_URL) == expected


# --- doc 6, namespaced (article_id) group (D6) --------------------------------


def test_namespaced_marker_in_heading() -> None:
    html = (
        '<table><tr><td><h3>Sec<a id="1a" name="1a">.</a> Title</h3></td>'
        "<td></td><td><p>Body</p></td></tr></table>"
    )
    assert (
        convert(html, base_url=BASE_URL, article_id="123")
        == '<a id="art_123_1a" name="art_123_1a"></a>\n\n### Sec. Title\n\nBody\n'
    )


def test_namespaced_marker_in_t2_label() -> None:
    html = (
        '<table><tr><td>II.i.2.B.4.b<a id="4b" name="4b">.</a> '
        "Determining the Date a Form Becomes Outdated</td>"
        "<td><p>Body</p></td></tr></table>"
    )
    assert (
        convert(html, base_url=BASE_URL, article_id="554400000174859")
        == '<a id="art_554400000174859_4b" name="art_554400000174859_4b"></a>\n\n'
        "### II.i.2.B.4.b. Determining the Date a Form Becomes Outdated\n\nBody\n"
    )


def test_namespaced_inline_marker() -> None:
    assert (
        convert('<p><a id="rm">the RM</a></p>', base_url=BASE_URL, article_id="123")
        == '<a id="art_123_rm"></a>the RM\n'
    )


def test_namespaced_fragment_link() -> None:
    assert (
        convert('<p><a href="#1a">see</a></p>', base_url=BASE_URL, article_id="123")
        == "[see](#art_123_1a)\n"
    )


def test_null_link_stays_hash() -> None:
    assert (
        convert('<p><a href="#">top</a></p>', base_url=BASE_URL, article_id="123") == "[top](#)\n"
    )


def test_none_input_returns_empty() -> None:
    assert convert(None, base_url=BASE_URL) == ""


def test_parse_failure_raises_html_conversion_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*args: object, **kwargs: object) -> object:
        raise ValueError("synthetic parser failure")

    monkeypatch.setattr(mdconv, "BeautifulSoup", boom)
    with pytest.raises(HtmlConversionError) as excinfo:
        convert("<p>x</p>", base_url=BASE_URL, article_id="ART123")
    err = excinfo.value
    assert err.article_id == "ART123"
    assert isinstance(err.cause, ValueError)


# --- doc 6.1 property tests (fixed seed, generated fragments) -----------------

TOKENS = ("alpha", "bravo", "charlie", "delta")
_TOKEN_RE = re.compile("|".join(TOKENS))
SEED = 20261002


def _gen_inline(rng: random.Random, depth: int, parent: str | None = None) -> str:
    if depth <= 0 or rng.random() < 0.5:
        return rng.choice(TOKENS)
    options = (
        ("strong", "em") if parent is None else tuple(t for t in ("strong", "em") if t != parent)
    )
    tag = rng.choice(options)
    return f"<{tag}>{_gen_inline(rng, depth - 1, tag)}</{tag}>"


def _gen_block(rng: random.Random) -> str:
    roll = rng.random()
    if roll < 0.35:
        return f"<p>{_gen_inline(rng, 2)}</p>"
    if roll < 0.55:
        tag = rng.choice(("ul", "ol"))
        items = "".join(f"<li>{_gen_inline(rng, 1)}</li>" for _ in range(rng.randint(1, 3)))
        return f"<{tag}>{items}</{tag}>"
    if roll < 0.70:
        level = rng.randint(2, 4)
        return f"<h{level}>{_gen_inline(rng, 1)}</h{level}>"
    if roll < 0.82:
        return f"<span>{_gen_inline(rng, 1)}</span>"
    if roll < 0.92:
        return f"<blockquote><p>{_gen_inline(rng, 1)}</p></blockquote>"
    if roll < 0.98:
        return f"<p><code>{rng.choice(TOKENS)}</code></p>"
    return "<hr>"


def _gen_html(rng: random.Random) -> str:
    return "".join(_gen_block(rng) for _ in range(rng.randint(1, 5)))


def _samples(n: int) -> list[str]:
    rng = random.Random(SEED)
    return [_gen_html(rng) for _ in range(n)]


def test_p1_determinism() -> None:
    for html in _samples(25):
        assert convert(html, base_url=BASE_URL) == convert(html, base_url=BASE_URL)


def test_p2_shape_exactly_one_trailing_newline() -> None:
    for html in _samples(25):
        out = convert(html, base_url=BASE_URL)
        assert out == "" or (out.endswith("\n") and not out.endswith("\n\n"))


def test_p3_no_empty_markers() -> None:
    for html in _samples(25):
        out = convert(html, base_url=BASE_URL)
        assert "****" not in out
        assert "``" not in out


def test_p4_word_preservation() -> None:
    for html in _samples(25):
        out = convert(html, base_url=BASE_URL)
        assert Counter(_TOKEN_RE.findall(out)) == Counter(_TOKEN_RE.findall(html))
