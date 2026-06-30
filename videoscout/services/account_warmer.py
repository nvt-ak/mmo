"""
YouTube Account Warmer
Dùng Playwright + Chrome profile để:
1. Follow channels (train algorithm)
2. Watch videos 30-60s (signal interest)
3. Scroll homepage (simulate human)
"""
import time
import random
from pathlib import Path
from utils.logger import get_logger

log = get_logger("warmer")

# Human-like delays
def _sleep(min_s: float, max_s: float):
    t = random.uniform(min_s, max_s)
    time.sleep(t)


def warm_account(
    chrome_profile_path: str,
    channels_to_follow: list[dict],
    watch_videos: int = 3,
    on_status=None,           # callback(str) for UI updates
) -> dict:
    """
    Main entry point.
    chrome_profile_path: path to Chrome user data dir
        e.g. C:/Users/you/AppData/Local/Google/Chrome/User Data/Profile 1
    channels_to_follow: list of {id, name, url}
    watch_videos: how many homepage videos to watch per session
    Returns: {followed: int, watched: int, errors: list}
    """
    result = {"followed": 0, "watched": 0, "errors": []}

    def status(msg: str):
        log.info(msg)
        if on_status:
            on_status(msg)

    status("Launching Chrome with profile…")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=chrome_profile_path,
                headless=False,          # visible so user can handle captcha
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
                ignore_default_args=["--enable-automation"],
            )

            page = browser.pages[0] if browser.pages else browser.new_page()

            # ── Step 1: Follow channels ───────────────────────────────
            for ch in channels_to_follow:
                try:
                    status(f"Following: {ch['name']}")
                    page.goto(ch["url"], timeout=30_000)
                    _sleep(2, 4)

                    # click Subscribe button
                    sub_btn = page.query_selector(
                        "#subscribe-button button, "
                        "ytd-subscribe-button-renderer button"
                    )
                    if sub_btn:
                        text = (sub_btn.text_content() or "").strip().lower()
                        if "subscri" in text:
                            sub_btn.click()
                            _sleep(1, 2)
                            result["followed"] += 1
                            status(f"✅ Followed: {ch['name']}")
                        else:
                            status(f"Already following: {ch['name']}")
                    else:
                        status(f"⚠️ Subscribe button not found: {ch['name']}")

                    # scroll channel page a bit (signal interest)
                    page.mouse.wheel(0, random.randint(300, 800))
                    _sleep(1, 3)

                except Exception as e:
                    msg = f"Error following {ch['name']}: {e}"
                    log.error(msg)
                    result["errors"].append(msg)

            # ── Step 2: Browse homepage + watch videos ────────────────
            status("Opening YouTube homepage…")
            page.goto("https://www.youtube.com", timeout=30_000)
            _sleep(3, 5)

            # scroll homepage a few times
            for _ in range(random.randint(3, 6)):
                page.mouse.wheel(0, random.randint(400, 900))
                _sleep(1, 2)

            # click and watch some videos
            watched = 0
            video_links = page.query_selector_all(
                "ytd-rich-item-renderer a#thumbnail"
            )
            random.shuffle(video_links)

            for link in video_links[:watch_videos]:
                try:
                    href = link.get_attribute("href") or ""
                    if "/watch?v=" not in href:
                        continue

                    url = f"https://www.youtube.com{href}"
                    status(f"Watching: {url}")
                    page.goto(url, timeout=30_000)
                    _sleep(2, 4)

                    # watch 30-60 seconds
                    watch_time = random.randint(30, 60)
                    status(f"  Watching {watch_time}s…")
                    _sleep(watch_time, watch_time + 5)

                    # scroll down comments a bit
                    page.mouse.wheel(0, random.randint(300, 600))
                    _sleep(1, 2)

                    watched += 1
                    result["watched"] += 1

                except Exception as e:
                    log.warning(f"Error watching video: {e}")

            # ── Step 3: Back to homepage, final scroll ────────────────
            page.goto("https://www.youtube.com", timeout=30_000)
            _sleep(2, 4)
            for _ in range(3):
                page.mouse.wheel(0, random.randint(400, 700))
                _sleep(1, 2)

            status(
                f"Session done — followed={result['followed']} "
                f"watched={result['watched']} errors={len(result['errors'])}"
            )
            browser.close()

    except Exception as e:
        msg = f"Warmer crashed: {e}"
        log.error(msg, exc_info=True)
        result["errors"].append(msg)

    return result


def harvest_feed(
    chrome_profile_path: str,
    view_min: int = 150_000,
    view_max: int = 200_000,
    on_status=None,
) -> list[dict]:
    """
    Open YouTube homepage with existing profile,
    parse video cards from feed,
    return videos matching view criteria.
    ponytail: view_count parsed from aria-label; upgrade to yt-dlp metadata if needed
    """
    videos = []

    def status(msg: str):
        log.info(msg)
        if on_status:
            on_status(msg)

    status("Harvesting feed…")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=chrome_profile_path,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"],
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://www.youtube.com", timeout=30_000)
            _sleep(3, 5)

            # scroll to load more cards
            for _ in range(5):
                page.mouse.wheel(0, 800)
                _sleep(1, 2)

            cards = page.query_selector_all("ytd-rich-item-renderer")
            status(f"Found {len(cards)} video cards in feed")

            for card in cards:
                try:
                    title_el = card.query_selector("#video-title")
                    link_el  = card.query_selector("a#thumbnail")
                    meta_el  = card.query_selector(
                        "#metadata-line span:first-child"
                    )
                    channel_el = card.query_selector(
                        "#channel-name a, #channel-info #channel-name"
                    )

                    if not title_el or not link_el:
                        continue

                    title   = (title_el.text_content() or "").strip()
                    href    = link_el.get_attribute("href") or ""
                    meta    = (meta_el.text_content() or "").strip() if meta_el else ""
                    channel = (channel_el.text_content() or "").strip() if channel_el else ""

                    if "/watch?v=" not in href:
                        continue

                    vid_id = href.split("v=")[1].split("&")[0]
                    view_count = _parse_view_count(meta)

                    if view_count and (view_min <= view_count <= view_max):
                        videos.append({
                            "id":          vid_id,
                            "title":       title,
                            "channel":     channel,
                            "view_count":  view_count,
                            "youtube_url": f"https://www.youtube.com{href}",
                            "source":      "feed",
                        })
                        log.info(
                            f"FEED MATCH: {view_count:,} views — {title[:50]}"
                        )

                except Exception as e:
                    log.debug(f"Card parse error: {e}")
                    continue

            browser.close()
            status(f"Harvest done — {len(videos)} videos match criteria")

    except Exception as e:
        log.error(f"harvest_feed crashed: {e}", exc_info=True)

    return videos


def _parse_view_count(text: str) -> int | None:
    """
    Parse '178K views' or '1.2M views' → int.
    Returns None if unparseable.
    """
    import re
    text = text.lower().replace(",", "")
    m = re.search(r"([\d.]+)\s*([km]?)\s*view", text)
    if not m:
        return None
    num = float(m.group(1))
    suffix = m.group(2)
    if suffix == "k":
        num *= 1_000
    elif suffix == "m":
        num *= 1_000_000
    return int(num)
