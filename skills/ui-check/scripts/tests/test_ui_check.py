import importlib.util
import pathlib
import unittest

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent / "ui-check.py"
spec = importlib.util.spec_from_file_location("ui_check", SCRIPT)
ui_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_check)

DEFECT_FINDINGS = {"overflow-x", "clipped", "overlap", "edge", "row-height", "icon-centre", "gap", "off-centre", "table-column", "contrast", "drift", "numeric-align", "proximity"}
DEFECT_SMELLS = {"gradient-text", "gradient", "glass", "glow", "purple", "emoji", "card-in-card", "tinted-box", "accent-stripe", "pills", "eyebrow", "subtitles", "native-tooltip", "hues", "stock-copy", "helper-text"}


class Browser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()
        cls.page = cls.browser.new_page()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def measure_file(self, name, width, frame="none"):
        ui_check.load(self.page, (HERE / "pages" / name).as_uri(), width)
        return self.page.evaluate(ui_check.PROBE, {"frame": frame})

    def measure_html(self, html, width=800, frame="none"):
        self.page.set_viewport_size({"width": width, "height": 900})
        self.page.set_content(f"<!doctype html><html><head><style>body{{margin:0;font:16px/1.5 Arial,sans-serif}}</style></head><body>{html}</body></html>")
        return self.page.evaluate(ui_check.PROBE, {"frame": frame})


def kinds(report):
    return {f["kind"] for f in report["findings"]}


def smells(report):
    return {s["kind"] for s in report["smells"]}


class DefectPageTest(Browser):
    def test_every_planted_defect_is_found_at_phone_width(self):
        report = self.measure_file("defects.html", 390)
        self.assertEqual(kinds(report), DEFECT_FINDINGS)

    def test_every_planted_smell_is_found(self):
        report = self.measure_file("defects.html", 390)
        self.assertEqual(smells(report), DEFECT_SMELLS)

    def test_wide_panel_fits_at_desktop_width(self):
        report = self.measure_file("defects.html", 1280)
        self.assertNotIn("overflow-x", kinds(report))

    def test_near_miss_names_both_edges(self):
        report = self.measure_file("defects.html", 390)
        edge = next(f for f in report["findings"] if f["kind"] == "edge")
        self.assertIn("x=24", edge["message"])
        self.assertIn("x=26", edge["message"])
        self.assertTrue(any(e.startswith("p.lead") for e in edge["elements"]))


class CleanPageTest(Browser):
    def test_clean_page_has_no_findings_or_smells(self):
        for width in (390, 1280):
            with self.subTest(width=width):
                report = self.measure_file("clean.html", width)
                self.assertEqual(report["findings"], [])
                self.assertEqual(report["smells"], [])


class FalsePositiveTest(Browser):
    def test_screen_reader_label_is_ignored(self):
        report = self.measure_html('<label style="position:absolute;width:fit-content;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap">Email address</label><p>Sign in</p>')
        self.assertEqual(report["findings"], [])

    def test_ellipsis_cells_are_one_warning(self):
        cell = '<p style="width:80px;margin:0 0 8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">A very long file name.pdf</p>'
        report = self.measure_html(cell * 3)
        self.assertEqual([f["kind"] for f in report["findings"]], ["truncated"])
        self.assertIn("3 text", report["findings"][0]["message"])

    def test_scroll_container_content_is_not_clipped(self):
        report = self.measure_html('<div style="height:60px;overflow:auto"><p>one</p><p>two</p><p>three</p><p>four</p></div>')
        self.assertNotIn("clipped", kinds(report))

    def test_links_inside_a_paragraph_do_not_overlap_it(self):
        report = self.measure_html('<p style="text-align:center">Built by <a href="#">someone</a> at <a href="#">a place</a>. Source on <a href="#">a site</a>.</p>')
        self.assertNotIn("overlap", kinds(report))

    def test_centred_icons_of_different_sizes_are_not_edges(self):
        report = self.measure_html('<div style="width:40px;display:flex;flex-direction:column;align-items:center;gap:8px"><svg width="20" height="20"><rect width="20" height="20"/></svg><svg width="16" height="16"><rect width="16" height="16"/></svg></div>')
        self.assertNotIn("edge", kinds(report))


class TokenTest(Browser):
    TOKENS = "<style>:root{--background:#ffffff;--foreground:#111111;--muted:#f4f4f5;--border:#e4e4e7;--primary:#2563eb}</style>"

    def test_colour_outside_the_tokens_is_reported(self):
        report = self.measure_html(self.TOKENS + '<p style="color:#111111">Plain</p><p style="color:#0f766e">Teal</p>')
        messages = [f["message"] for f in report["findings"] if f["kind"] == "off-token"]
        self.assertEqual(len(messages), 1)
        self.assertIn("#0f766e", messages[0])

    def test_token_with_opacity_is_still_a_token(self):
        report = self.measure_html(self.TOKENS + '<p style="color:#111111">Plain</p><div style="height:40px;border:1px solid rgb(228 228 231 / 0.5)"></div>')
        self.assertNotIn("off-token", kinds(report))


class FrameTest(Browser):
    def test_all_mode_outlines_every_box(self):
        report = self.measure_file("clean.html", 1280, frame="all")
        outlines = self.page.evaluate("document.getElementById('__uicheck').children.length")
        self.assertGreaterEqual(outlines, len(report["snapshot"]))

    def test_issues_mode_labels_each_finding(self):
        report = self.measure_file("defects.html", 390, frame="issues")
        labels = self.page.evaluate("[...document.getElementById('__uicheck').children].map(d => d.textContent).filter(Boolean)")
        for finding in report["findings"]:
            with self.subTest(finding=finding["id"]):
                self.assertIn(finding["id"], labels)


class CompareTest(Browser):
    def test_baseline_lists_a_restyled_button(self):
        before = self.measure_file("clean.html", 1280)
        self.page.add_style_tag(content=".btn{padding:0 24px}")
        after = self.page.evaluate(ui_check.PROBE, {"frame": "none"})
        lines = ui_check.baseline_changes(after, before)
        self.assertIn("1 restyled", lines[0])
        self.assertTrue(any("restyled  button.btn" in line and "padding" in line for line in lines))

    def test_unchanged_page_has_no_changes(self):
        before = self.measure_file("clean.html", 1280)
        after = self.measure_file("clean.html", 1280)
        self.assertEqual(ui_check.baseline_changes(after, before), ["  0 restyled, 0 resized, 0 moved sideways, 0 moved up or down, 0 added, 0 removed"])

    def test_pages_with_different_layout_are_listed(self):
        a = self.measure_file("clean.html", 390)
        b = self.measure_file("defects.html", 390)
        lines = ui_check.page_differences([a, b])
        self.assertTrue(any("controlHeight" in line for line in lines))

    def test_recoloured_variant_shares_the_layout(self):
        base = "<header style='height:56px;background:{c}'></header><main style='display:flex;gap:24px;padding:24px'><nav style='width:200px;height:400px;background:{c}'></nav><section style='flex:1;height:400px;border:1px solid {c}'><h2>Files</h2></section></main>"
        a = self.measure_html(base.format(c="#ddd"))
        b = self.measure_html(base.format(c="#0a7"))
        c = self.measure_html("<main style='padding:24px'><section style='height:300px;border:1px solid #ddd'><h2>Files</h2></section><div style='display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px'><div style='height:120px;background:#eee'></div><div style='height:120px;background:#eee'></div></div></main>")
        self.assertEqual(len(ui_check.shared_layouts([a, b])), 1)
        self.assertEqual(ui_check.shared_layouts([a, c]), [])


if __name__ == "__main__":
    unittest.main()


ICON = '<svg viewBox="0 0 16 16" width="16" height="16"><path d="M2 8h12" stroke="#111" stroke-width="2"/></svg>'
CARD = f'<div style="width:200px;height:160px;padding:16px;border:1px solid #ddd">{ICON}<h3 style="margin:8px 0">Fast</h3><p style="margin:0">Text</p></div>'


class DesignRuleTest(Browser):
    def test_small_targets_close_together(self):
        buttons = '<button style="width:16px;height:16px;padding:0;border:0">a</button>'
        self.assertIn("target-size", kinds(self.measure_html(f'<div style="display:flex;gap:2px">{buttons * 3}</div>')))
        self.assertNotIn("target-size", kinds(self.measure_html(f'<div style="display:flex;gap:40px">{buttons * 3}</div>')))

    def test_long_lines(self):
        text = "word " * 120
        self.assertIn("line-length", kinds(self.measure_html(f"<p style='width:1100px'>{text}</p>", width=1280)))
        self.assertNotIn("line-length", kinds(self.measure_html(f"<p style='width:560px'>{text}</p>", width=1280)))

    def test_small_text(self):
        self.assertIn("small-text", kinds(self.measure_html("<p>Body</p><span style='font-size:10px'>tiny</span>")))

    def test_skipped_heading_level(self):
        report = self.measure_html("<h1>A</h1><h3>B</h3>")
        self.assertIn("headings", kinds(report))
        self.assertNotIn("headings", kinds(self.measure_html("<h1>A</h1><h2>B</h2><h3>C</h3>")))

    def test_border_with_wide_shadow(self):
        box = "<div style='width:300px;height:100px;border:1px solid #ddd;box-shadow:0 10px 30px rgba(0,0,0,.2)'>x</div>"
        self.assertIn("border-shadow", smells(self.measure_html(box)))

    def test_icon_tile_above_a_heading(self):
        tile = f"<div style='width:40px;height:40px;background:#eef;display:grid;place-items:center'>{ICON}</div><h3 style='margin:12px 0 0'>Secure</h3>"
        self.assertIn("icon-tile", smells(self.measure_html(tile)))

    def test_row_of_identical_icon_cards(self):
        row = f"<div style='display:flex;gap:16px'>{CARD * 3}</div>"
        self.assertIn("card-grid", smells(self.measure_html(row)))
        self.assertNotIn("card-grid", smells(self.measure_html(f"<div style='display:flex;gap:16px'>{CARD * 2}</div>")))


class ConsistencyTest(Browser):
    def test_chips_in_a_row_with_different_sizes(self):
        chip = "<span style='display:inline-block;padding:2px 8px;border-radius:999px;background:#eee;font-size:{s}px'>tag</span>"
        report = self.measure_html(f"<div style='display:flex;gap:8px'>{chip.format(s=12)}{chip.format(s=12)}{chip.format(s=14)}</div>")
        found = [f for f in report["findings"] if f["kind"] == "inconsistent"]
        self.assertTrue(found and "font size 12 vs 14" in found[0]["message"], report["findings"])
        same = self.measure_html(f"<div style='display:flex;gap:8px'>{chip.format(s=12) * 3}</div>")
        self.assertNotIn("inconsistent", kinds(same))

    def test_same_class_in_two_places_with_different_size(self):
        html = "<style>.chip{display:inline-block;padding:2px 8px;border:1px solid #ccc;border-radius:6px}</style><p style='font-size:12px'><span class='chip'>a</span></p><p style='font-size:16px'><span class='chip'>b</span></p>"
        self.assertIn("inconsistent", kinds(self.measure_html(html)))

    def test_too_many_font_sizes(self):
        html = "".join(f"<p style='font-size:{s}px'>t</p>" for s in [11, 12, 13, 14, 15, 16, 18, 20])
        self.assertIn("scale", kinds(self.measure_html(html)))


class HardNoAndTableTest(Browser):
    def test_button_pushed_out_of_a_clipped_dialog(self):
        html = "<div style='width:300px;overflow:hidden;border:1px solid #ddd'><div style='display:flex;white-space:nowrap;gap:8px'><code>docker run -p 8080:80 --name web registry/app:latest</code><button>Copy</button></div></div>"
        self.assertIn("control-cut", kinds(self.measure_html(html)))

    def test_button_in_a_scroll_container_is_not_cut(self):
        html = "<div style='width:300px;overflow-x:auto'><div style='display:flex;white-space:nowrap;gap:8px'><code>docker run -p 8080:80 --name web registry/app:latest</code><button>Copy</button></div></div>"
        self.assertNotIn("control-cut", kinds(self.measure_html(html)))

    def test_broken_image(self):
        self.page.set_content("<img src='missing-file.png' width='40' height='40' alt='x'>")
        self.page.wait_for_load_state("load")
        report = self.page.evaluate(ui_check.PROBE, {"frame": "none"})
        self.assertIn("broken-image", kinds(report))

    def test_number_column_and_missing_values(self):
        rows = "".join(f"<tr><td>f{k}</td><td>{v}</td></tr>" for k, v in enumerate(["12 MB", "3 MB", "—", "N/A", "140 MB"]))
        report = self.measure_html(f"<table><thead><tr><th>Name</th><th>Size</th></tr></thead><tbody>{rows}</tbody></table>")
        self.assertTrue({"numeric-align", "empty-cell"} <= kinds(report))
        right = "".join(f"<tr><td>f{k}</td><td style='text-align:right;font-variant-numeric:tabular-nums'>{v}</td></tr>" for k, v in enumerate(["12", "3", "140"]))
        self.assertFalse({"numeric-align", "empty-cell"} & kinds(self.measure_html(f"<table><tbody>{right}</tbody></table>")))

    def test_long_table_without_pagination(self):
        rows = "".join(f"<tr><td>row {k}</td></tr>" for k in range(60))
        self.assertIn("long-table", kinds(self.measure_html(f"<table><tbody>{rows}</tbody></table>")))
        self.assertNotIn("long-table", kinds(self.measure_html(f"<table><tbody>{rows}</tbody></table><nav aria-label='pagination'><button>Next</button></nav>")))

    def test_stress_finds_a_layout_that_breaks_with_long_text(self):
        fragile = "<div style='width:300px;overflow:hidden'><div style='display:flex;white-space:nowrap;gap:8px'><code>registry.io/team/web:1.2</code><button>Copy</button></div></div>"
        robust = "<div style='width:300px'><div style='display:flex;gap:8px'><code style='min-width:0;overflow-wrap:anywhere'>registry.io/team/web:1.2</code><button style='flex:none'>Copy</button></div></div>"
        results = []
        for html in [fragile, robust]:
            before = self.measure_html(html)
            self.page.evaluate(ui_check.STRESS)
            results.append(ui_check.stress_failures(before, self.page.evaluate(ui_check.PROBE, {"frame": "none"})))
        self.assertTrue(results[0])
        self.assertEqual(results[1], [])


class InteractTest(Browser):
    def interact_html(self, html):
        self.measure_html(html)
        return ui_check.interact(self.page)

    def test_invisible_focus(self):
        findings = self.interact_html('<button style="outline:none">Save</button>')
        self.assertEqual([f['kind'] for f in findings], ['focus-invisible'])
        self.assertEqual(findings[0]['severity'], 'fail')
        self.assertEqual(len(findings[0]['boxes'][0]), 4)

    def test_visible_focus_outline(self):
        self.assertEqual(self.interact_html('<style>button:focus{outline:2px solid blue}</style><button>Save</button>'), [])

    def test_clipped_focus_outline(self):
        findings = self.interact_html('<style>button:focus{outline:2px solid blue;outline-offset:3px}</style><div style="overflow:hidden;width:100px"><button>Save</button></div>')
        self.assertIn('focus-clipped', {f['kind'] for f in findings})

    def test_fixed_header_covers_focus(self):
        findings = self.interact_html('<header style="position:fixed;inset:0 0 auto;height:60px;background:white;z-index:2">Header</header><a href="#">Covered link</a>')
        self.assertIn('focus-covered', {f['kind'] for f in findings})

    def test_hover_border_moves_layout(self):
        findings = self.interact_html('<style>button{border:0}button:hover{border:2px solid black}</style><button>Save</button>')
        self.assertIn('hover-shift', {f['kind'] for f in findings})
        self.assertTrue(all(f['severity'] == 'warn' for f in findings))

    def test_stable_button(self):
        self.assertEqual(self.interact_html('<button>Save</button>'), [])

    def test_focus_moves_sibling(self):
        findings = self.interact_html('<style>button:focus + span{margin-left:3px}</style><button>Save</button><span>Text</span>')
        self.assertIn('focus-shift', {f['kind'] for f in findings})

    def test_pseudo_element_focus_paint(self):
        self.assertEqual(self.interact_html('<style>button{outline:none}button::after{content:"!";color:black}button:focus::after{color:blue}</style><button>Save</button>'), [])

    def test_repeated_findings_are_grouped(self):
        findings = self.interact_html('<button style="outline:none">Save</button>' * 6)
        self.assertEqual(len(findings), 1)
        self.assertEqual(len(findings[0]['elements']), 4)
        self.assertIn('6 element(s)', findings[0]['message'])

    def test_tab_scroll_does_not_count_as_movement(self):
        self.assertEqual(self.interact_html('<div style="height:1200px"></div><button>Save</button>'), [])

    def test_viewport_height(self):
        ui_check.load(self.page, 'about:blank', 320, 480)
        self.assertEqual(self.page.viewport_size, {'width': 320, 'height': 480})


LONG = 2 * "This paragraph explains the feature in detail so that the reader knows what it does, why it exists, how the team built it and what it will do next quarter when the new plan starts for every customer in every region of the world today. "


class CopyTest(Browser):
    def test_heading_restated_below(self):
        html = "<table><tr><td>x</td></tr></table><h2 style='font-size:20px'>Settings</h2><p style='margin:4px 0;font-size:14px;color:#777'>Manage your settings here.</p>"
        self.assertIn("restates", kinds(self.measure_html(html)))

    def test_helper_sentence_in_an_app(self):
        html = "<table><tr><td>x</td></tr></table><h2 style='font-size:20px'>Upload</h2><p style='margin:4px 0;font-size:14px;color:#777'>Share files with expiry, download limits and a password.</p>"
        self.assertIn("helper-text", smells(self.measure_html(html)))

    def test_alerts_and_sticky_headers_are_not_smells(self):
        report = self.measure_html("<header style='position:sticky;top:0;backdrop-filter:blur(8px);height:56px'>Files</header><div role='alert' style='background:#fde8e8;border:1px solid #f5b5b5;padding:16px;width:300px;height:60px'>Upload failed. Try again.</div>")
        self.assertNotIn("glass", smells(report))
        self.assertNotIn("tinted-box", smells(report))

    def test_long_button_label_and_filler(self):
        report = self.measure_html("<p>Just to confirm: here you can simply upload.</p><button>Click here to save all your changes</button>")
        self.assertIn("long-label", kinds(report))
        self.assertIn("filler", smells(report))
        self.assertNotIn("long-label", kinds(self.measure_html("<button>Save</button><button>Send password reset email</button>")))

    def test_long_paragraph_and_text_book_page(self):
        page = "".join(f"<h2>Part {k}</h2><p style='max-width:700px'>{LONG}</p>" for k in range(12))
        report = self.measure_html(page, width=1280)
        self.assertTrue({"long-paragraph", "wall-of-text", "text-heavy"} <= kinds(report), kinds(report))
        short = "".join(f"<h2>Part {k}</h2><p>Short line.</p><img src='data:image/gif;base64,R0lGODlhAQABAAAAACw=' style='width:600px;height:300px'>" for k in range(4))
        self.assertFalse({"long-paragraph", "wall-of-text", "text-heavy"} & kinds(self.measure_html(short, width=1280)))

    def test_docs_pages_are_not_text_heavy(self):
        page = "<article class='prose'>" + "".join(f"<h2>Part {k}</h2><p style='max-width:700px'>{LONG}</p>" for k in range(12)) + "</article>"
        self.assertFalse({"long-paragraph", "wall-of-text", "text-heavy"} & kinds(self.measure_html(page, width=1280)))


class DetailTest(Browser):
    def test_double_border(self):
        html = "<div style='border:1px solid #999;width:300px'><div style='border-top:1px solid #999;border-bottom:1px solid #999;padding:8px'>row</div></div>"
        self.assertIn("double-border", kinds(self.measure_html(html)))
        self.assertNotIn("double-border", kinds(self.measure_html("<div style='border:1px solid #999;width:300px;padding:8px'><div style='border-bottom:1px solid #999;padding:8px'>row</div></div>")))

    def test_cramped_badge(self):
        bad = "<span style='display:inline-block;padding:6px 2px;border-radius:4px;background:#eee'>Beta tester</span>"
        good = "<span style='display:inline-block;padding:2px 8px;border-radius:4px;background:#eee'>Beta tester</span>"
        self.assertIn("cramped-padding", kinds(self.measure_html(bad)))
        self.assertNotIn("cramped-padding", kinds(self.measure_html(good)))

    def test_control_with_browser_font(self):
        self.assertIn("control-font", kinds(self.measure_html("<input value='a'><button>Go</button>")))
        self.assertNotIn("control-font", kinds(self.measure_html("<input value='a' style='font:inherit'><button style='font:inherit'>Go</button>")))

    def test_stretched_image(self):
        gif = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        self.page.set_content(f"<img src='{gif}' style='width:200px;height:50px'><img src='{gif}' style='width:60px;height:60px'>")
        self.page.wait_for_load_state("load")
        found = [f for f in self.page.evaluate(ui_check.PROBE, {"frame": "none"})["findings"] if f["kind"] == "image-distorted"]
        self.assertEqual(len(found), 1)
        self.assertIn("1 image", found[0]["message"])

    def test_checkbox_centred_on_a_long_label(self):
        label = "<label style='display:flex;align-items:{a};gap:8px;width:220px'><input type='checkbox' style='margin:0;width:16px;height:16px'><span>Send me a weekly digest email when the workspace changes</span></label>"
        self.assertIn("choice-centre", kinds(self.measure_html(label.format(a="center"))))
        self.assertNotIn("choice-centre", kinds(self.measure_html(label.format(a="flex-start"))))

    def test_heading_closer_to_the_section_above(self):
        bad = "<div><p style='margin:0'>Earlier text</p><h2 style='margin:4px 0 24px'>Billing</h2><p style='margin:0'>Plan</p></div>"
        good = "<div><p style='margin:0'>Earlier text</p><h2 style='margin:32px 0 8px'>Billing</h2><p style='margin:0'>Plan</p></div>"
        self.assertIn("proximity", kinds(self.measure_html(bad)))
        self.assertNotIn("proximity", kinds(self.measure_html(good)))

    def test_ellipsis_with_free_space(self):
        html = "<div style='display:flex;width:600px;gap:8px'><span style='width:120px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>quarterly-report-final-version.pdf</span><button>Open</button></div>"
        self.assertIn("early-ellipsis", kinds(self.measure_html(html)))

    def test_fixed_bar_covers_the_end(self):
        bar = "<div style='position:fixed;left:0;right:0;bottom:0;height:64px;background:#fff;border-top:1px solid #ccc'>Save</div>"
        self.assertIn("covered-end", kinds(self.measure_html(f"<div style='height:1200px'></div><button>Next page</button>{bar}")))
        self.assertNotIn("covered-end", kinds(self.measure_html(f"<div style='height:1200px'></div><button>Next page</button><div style='height:80px'></div>{bar}")))

    def test_cursor_rules(self):
        report = self.measure_html("<div style='cursor:pointer;padding:8px'>Card</div><button style='cursor:pointer'>A</button><button>B</button>")
        self.assertTrue({"cursor-lie", "cursor-mixed"} <= kinds(report))
        zoo = self.measure_html("<div style='cursor:grab'>a</div><div style='cursor:help'>b</div><div style='cursor:crosshair'>c</div>")
        self.assertIn("cursor-zoo", smells(zoo))


MENU = """<button aria-haspopup="menu" onclick="document.getElementById('m').style.display='block'">Open</button>
<div id="m" role="menu" style="display:none;position:absolute;{where}width:160px;height:120px;background:#fff;border:1px solid #ccc">
<div role="menuitem">One</div></div>"""


class PopupTest(Browser):
    def popup_kinds(self, html):
        self.page.set_viewport_size({"width": 800, "height": 600})
        self.page.set_content(f"<!doctype html><html><head><style>body{{margin:0;font:16px/1.5 Arial,sans-serif}}</style></head><body>{html}</body></html>")
        return {f["kind"] for f in ui_check.popups(self.page)}

    def test_menu_cut_off_by_its_card(self):
        html = f"<div style='position:relative;overflow:hidden;width:300px;height:80px;border:1px solid #ddd'>{MENU.format(where='top:40px;left:0;')}</div>"
        self.assertIn("popup-clipped", self.popup_kinds(html))

    def test_menu_with_room(self):
        html = f"<div style='position:relative;width:300px'>{MENU.format(where='top:40px;left:0;')}</div>"
        self.assertEqual(self.popup_kinds(html), set())

    def test_menu_under_a_sticky_header(self):
        html = f"<div style='position:relative;z-index:1'>{MENU.format(where='top:40px;left:0;')}</div><div style='position:fixed;top:30px;left:0;width:800px;height:200px;background:#eee;z-index:5'></div>"
        self.assertIn("popup-covered", self.popup_kinds(html))

    def test_dialog_taller_than_the_screen(self):
        dialog = """<button aria-haspopup="dialog" onclick="document.getElementById('d').style.display='block'">Open</button>
<div id="d" role="dialog" style="display:none;position:fixed;top:40px;left:100px;width:400px;height:900px;{scroll}background:#fff;border:1px solid #ccc"><div style="height:880px">Form</div><button>Save</button></div>"""
        self.assertIn("dialog-unreachable", self.popup_kinds(dialog.format(scroll="")))
        self.assertNotIn("dialog-unreachable", self.popup_kinds(dialog.format(scroll="max-height:500px;overflow:auto;")))


class WrapTest(Browser):
    def test_one_item_alone_on_the_last_line(self):
        chip = "<span style='display:inline-block;width:90px;padding:4px;border:1px solid #ccc'>tag</span>"
        self.assertIn("orphan-wrap", kinds(self.measure_html(f"<div style='display:flex;flex-wrap:wrap;gap:8px;width:330px'>{chip * 4}</div>")))
        self.assertNotIn("orphan-wrap", kinds(self.measure_html(f"<div style='display:flex;flex-wrap:wrap;gap:8px;width:330px'>{chip * 6}</div>")))
