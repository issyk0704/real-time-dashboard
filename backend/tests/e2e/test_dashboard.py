from playwright.sync_api import Page, expect


def open_dashboard(page: Page, base_url):
    page.goto(base_url)
    expect(page.locator(".tile")).to_have_count(3)


def tile(page: Page, name):
    return page.locator(".tile", has=page.locator(".tile-label", has_text=name))


def test_tiles_show_price_change_and_sparkline(page: Page, base_url, api):
    open_dashboard(page, base_url)

    nq = tile(page, "NQ")
    expect(nq.locator(".tile-value")).to_have_text("31,515.50")
    expect(nq.locator(".tile-delta")).to_have_text("▲ +0.56%")
    expect(nq.locator(".sparkline polyline")).to_have_count(1)
    expect(tile(page, "ES").locator(".tile-delta")).to_have_text("▼ -0.25%")
    expect(tile(page, "EURUSD").locator(".tile-value")).to_have_text("1.12663")


def test_lost_connection_is_reported(page: Page, base_url):
    page.route("**/api/stream?**", lambda route: route.abort())
    page.goto(base_url)

    expect(page.get_by_test_id("connection-status")).to_have_text("Reconnecting…")


def test_clock_shows_active_killzone_and_macro(page: Page, base_url, api):
    open_dashboard(page, base_url)

    expect(page.get_by_test_id("ny-clock")).to_have_text("Tue 09:00:00 NY")
    expect(page.get_by_test_id("killzone-status")).to_have_text("NY AM killzone · 2h 0m left")
    expect(page.get_by_test_id("macro-status")).to_have_text("Macro 08:50–09:10 · 10m left")
    expect(page.locator("#killzone-table thead th.active")).to_have_text("NY AM (08:30–11:00)")


def test_news_banner_shows_for_imminent_high_impact_event(page: Page, base_url, api):
    api.calendar = [{"time": "2026-10-06T09:10:00-04:00", "currency": "USD", "impact": "High",
                     "title": "CPI m/m", "forecast": "0.3%", "previous": "0.2%"}]
    open_dashboard(page, base_url)

    expect(page.get_by_role("alert")).to_have_text("⚠ High-impact news: USD CPI m/m in 10m")
    expect(page.locator("#calendar-table tbody tr")).to_have_count(1)


def test_no_news_banner_when_event_is_far_away(page: Page, base_url, api):
    api.calendar = [{"time": "2026-10-06T14:00:00-04:00", "currency": "USD", "impact": "High",
                     "title": "FOMC", "forecast": "", "previous": ""}]
    open_dashboard(page, base_url)

    expect(page.locator("#news-banner")).to_be_hidden()


def test_levels_killzones_and_smt_are_rendered(page: Page, base_url, api):
    open_dashboard(page, base_url)

    nq_levels = page.locator("#levels-table tbody tr", has_text="NQ")
    expect(nq_levels.locator("td").nth(0)).to_contain_text("31,516.00")
    expect(nq_levels.locator("td").nth(0).locator(".tag")).to_have_text("swept")
    expect(nq_levels.locator("td").nth(1)).to_contain_text("31,515.00")
    expect(nq_levels.locator("td").nth(1).locator(".tag")).to_have_count(0)
    nq_asia = page.locator("#killzone-table tbody tr", has_text="NQ").locator("td").nth(0)
    expect(nq_asia).to_contain_text("H 31,515.75")
    expect(nq_asia).to_contain_text("L 31,515.25")
    expect(page.locator("#smt-list li")).to_contain_text("ES swept, NQ failed")
    expect(page.locator("#smt-list li .smt-bias")).to_have_text("▼ Bearish NQ")


def test_adding_a_symbol_reconnects_and_persists(page: Page, base_url, api):
    open_dashboard(page, base_url)

    page.get_by_label("Add Yahoo symbol").fill("gc=f")
    page.get_by_role("button", name="Add").click()

    expect(page.locator(".tile")).to_have_count(4)
    assert api.stream_requests[-1] == ["NQ=F", "ES=F", "EURUSD=X", "GC=F"]
    page.reload()
    expect(page.locator(".tile")).to_have_count(4)


def test_removing_a_symbol(page: Page, base_url, api):
    open_dashboard(page, base_url)

    page.get_by_role("button", name="Remove ES").click()

    expect(page.locator(".tile")).to_have_count(2)
    expect(tile(page, "ES")).to_have_count(0)


def test_unknown_symbol_shows_error_tile(page: Page, base_url, api):
    open_dashboard(page, base_url)

    page.get_by_label("Add Yahoo symbol").fill("NOTREAL")
    page.get_by_role("button", name="Add").click()

    expect(tile(page, "NOTREAL").locator(".tile-delta")).to_have_text("No data for this symbol")
    expect(tile(page, "NOTREAL").locator(".tile-open")).to_be_disabled()


def test_clicking_a_tile_opens_chart_with_levels(page: Page, base_url, api):
    open_dashboard(page, base_url)

    page.get_by_role("button", name="Open NQ chart").click()

    dialog = page.locator("#chart-dialog")
    expect(dialog).to_be_visible()
    expect(dialog.locator("#chart-title")).to_have_text("NQ")
    expect(dialog.locator("#chart canvas").first).to_be_visible()
    page.get_by_role("button", name="Close chart").click()
    expect(dialog).to_be_hidden()
