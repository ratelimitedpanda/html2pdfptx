import re

from playwright.sync_api import TimeoutError, sync_playwright

SLIDE_SELECTORS = [".slide", "section", "article"]


def capture_slides(url, settings):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": settings["width"], "height": settings["height"]},
            device_scale_factor=settings["scale"],
        )
        _open(page, url, settings["freeze_animations"])

        mode = settings["mode"]
        if mode == "auto":
            mode = _detect_engine(page)

        def progress(slides, total=None):
            print(f"[{len(slides)}{f'/{total}' if total else ''}] Слайд снят ({mode})")
            settings["on_mode"](mode)
            settings["on_progress"](slides, total)

        slides = _capture(page, mode, settings, progress)

        if settings["mode"] == "auto" and mode == "keyboard" and len(slides) < 2:
            mode = "scroll"
            slides = _capture(page, mode, settings, progress)

        browser.close()

    if not slides:
        raise RuntimeError("Не удалось снять ни одного слайда")
    return mode, slides


def _open(page, url, freeze_animations):
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
    except TimeoutError:
        pass

    page.add_style_tag(content="::-webkit-scrollbar { display: none; }")
    if freeze_animations:
        page.add_style_tag(content="* { animation-duration: 0s !important; transition-duration: 0s !important; }")
    page.wait_for_timeout(1000)


def _detect_engine(page):
    return page.evaluate("""() => {
        if (window.Reveal) return "reveal";
        if (window.impress) return "impress";
        if (window.remark && window.slideshow) return "remark";
        if (document.querySelector(".swiper")?.swiper) return "swiper";
        return "keyboard";
    }""")


def _capture(page, mode, settings, progress):
    capture = {
        "reveal": _capture_reveal,
        "impress": _capture_impress,
        "remark": _capture_remark,
        "swiper": _capture_swiper,
        "keyboard": _capture_keyboard,
        "scroll": _capture_scroll,
    }[mode]
    return capture(page, settings, progress)


def _screenshot(page, settings):
    page.wait_for_timeout(settings["settle_ms"])
    shot = page.screenshot()
    for _ in range(15):
        page.wait_for_timeout(150)
        new_shot = page.screenshot()
        if new_shot == shot:
            break
        shot = new_shot
    return shot


def _capture_reveal(page, settings, progress):
    page.wait_for_function("Reveal.isReady()")
    page.evaluate("""Reveal.configure({
        transition: "none",
        backgroundTransition: "none",
        controls: false,
        progress: false,
        fragments: false,
    })""")
    page.evaluate("Reveal.slide(0, 0)")

    total = page.evaluate("Reveal.getTotalSlides()")
    slides = []
    for _ in range(total):
        notes = page.evaluate("Reveal.getSlideNotes() || ''")
        slides.append({"png": _screenshot(page, settings), "text": "", "notes": _strip_tags(notes)})
        progress(slides, total)
        page.evaluate("Reveal.next()")
    return slides


def _capture_impress(page, settings, progress):
    page.add_style_tag(content=".hint, #impress-toolbar, .impress-progressbar { display: none !important; }")

    total = page.evaluate("document.querySelectorAll('.step').length")
    slides = []
    for i in range(total):
        page.evaluate(f"impress().goto({i}, 0)")
        slides.append({"png": _screenshot(page, settings), "text": "", "notes": ""})
        progress(slides, total)
    return slides


def _capture_remark(page, settings, progress):
    total = page.evaluate("slideshow.getSlideCount()")
    slides = []
    for i in range(1, total + 1):
        page.evaluate(f"slideshow.gotoSlide({i})")
        _screenshot(page, settings)
        png = page.locator(".remark-visible .remark-slide-scaler").screenshot()
        slides.append({"png": png, "text": "", "notes": ""})
        progress(slides, total)
    return slides


def _capture_swiper(page, settings, progress):
    total = page.evaluate("document.querySelector('.swiper').swiper.slides.length")
    slides = []
    for i in range(total):
        page.evaluate(f"document.querySelector('.swiper').swiper.slideTo({i}, 0)")
        slides.append({"png": _screenshot(page, settings), "text": "", "notes": ""})
        progress(slides, total)
    return slides


def _capture_keyboard(page, settings, progress):
    key = " " if settings["key"] == "Space" else settings["key"]
    slides = []

    while len(slides) < settings["max_slides"]:
        png = _screenshot(page, settings)
        if slides and png in (slides[0]["png"], slides[-1]["png"]):
            break

        slides.append({"png": png, "text": "", "notes": ""})
        progress(slides)

        if key == "click":
            page.mouse.click(settings["width"] * 0.75, settings["height"] / 2)
        else:
            page.keyboard.press(key)
    return slides


def _capture_scroll(page, settings, progress):
    page.evaluate("window.scrollTo(0, 0)")
    elements = _find_slide_elements(page, settings["height"] / 2)
    slides = []

    if elements:
        for element in elements[: settings["max_slides"]]:
            element.scroll_into_view_if_needed()
            page.wait_for_timeout(settings["settle_ms"])
            slides.append({"png": element.screenshot(), "text": element.inner_text().strip(), "notes": ""})
            progress(slides, len(elements))
        return slides

    page_height = page.evaluate("document.documentElement.scrollHeight")
    for y in range(0, page_height, settings["height"]):
        page.evaluate(f"window.scrollTo(0, {y})")
        png = _screenshot(page, settings)
        if slides and png == slides[-1]["png"]:
            continue
        slides.append({"png": png, "text": "", "notes": ""})
        progress(slides)
    return slides[: settings["max_slides"]]


def _find_slide_elements(page, min_height):
    for selector in SLIDE_SELECTORS:
        found = []
        for element in page.query_selector_all(selector):
            box = element.bounding_box()
            nested = element.evaluate("(el, selector) => !!el.parentElement.closest(selector)", selector)
            if box and box["height"] >= min_height and not nested:
                found.append((box["y"], element))

        if len({round(y) for y, _ in found}) >= 2:
            return [element for _, element in found]
    return []


def _strip_tags(html):
    return re.sub(r"<[^>]+>", "", html.replace("<br>", "\n")).strip()
