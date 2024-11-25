import time
import random


class Solver:
    def __init__(self, playwright, proxy=None, headless=True):
        self.playwright = playwright
        self.proxy = proxy
        self.headless = headless
        self.current_x = 0
        self.current_y = 0
        self.start_browser()

    def start_browser(self):
        # Proxy setup
        if self.proxy:
            try:
                username, password_and_host = self.proxy.split(":")
                password, host = password_and_host.split("@")
                self.browser = self.playwright.chromium.launch(
                    headless=self.headless,
                    proxy={"server": f"http://{host}", "username": username, "password": password},
                )
            except Exception as e:
                raise ValueError(f"Invalid proxy format: {self.proxy}. Error: {e}")
        else:
            self.browser = self.playwright.chromium.launch(headless=self.headless)

    def terminate(self):
        if hasattr(self, "browser"):
            self.browser.close()

    def build_page_data(self):
        # Build custom page
        with open("utils/page.html") as f:
            self.page_data = f.read()
        stub = f'<div class="cf-turnstile" data-sitekey="{self.sitekey}"></div>'
        self.page_data = self.page_data.replace("<!-- cf turnstile -->", stub)

    def get_mouse_path(self, x1, y1, x2, y2):
        path = []
        x, y = x1, y1

        while abs(x - x2) > 3 or abs(y - y2) > 3:
            diff = abs(x - x2) + abs(y - y2)
            speed = random.uniform(0.5, 2) * (diff / 45 if diff > 20 else 1)

            if abs(x - x2) > 3:
                x += speed if x < x2 else -speed
            if abs(y - y2) > 3:
                y += speed if y < y2 else -speed

            path.append((round(x), round(y)))

        return path

    def move_to(self, x, y):
        for px, py in self.get_mouse_path(self.current_x, self.current_y, x, y):
            self.page.mouse.move(px, py)
            time.sleep(random.uniform(0.002, 0.01))
        self.current_x, self.current_y = x, y

    def find_element_value(self, selector):
        elem = self.page.query_selector(selector)
        return elem.get_attribute("value") if elem else None

    def solve_invisible(self):
        for _ in range(10):
            self.move_to(random.randint(0, self.window_width), random.randint(0, self.window_height))
            value = self.find_element_value("[name=cf-turnstile-response]")
            if value:
                return value
            time.sleep(random.uniform(0.005, 0.015))
        return "failed"

    def solve_visible(self):
        iframe = self.page.query_selector("iframe")
        while not iframe:
            time.sleep(0.1)
            iframe = self.page.query_selector("iframe")

        while not iframe.bounding_box():
            time.sleep(0.1)

        iframe_box = iframe.bounding_box()
        self.move_to(
            iframe_box["x"] + random.randint(5, 12),
            iframe_box["y"] + random.randint(5, 12),
        )
        framepage = iframe.content_frame()
        checkbox = framepage.query_selector("input")
        while not checkbox:
            time.sleep(0.1)
            checkbox = framepage.query_selector("input")

        checkbox_box = checkbox.bounding_box()
        if checkbox_box:
            x = checkbox_box["x"] + random.uniform(checkbox_box["width"] * 0.2, checkbox_box["width"] * 0.8)
            y = checkbox_box["y"] + random.uniform(checkbox_box["height"] * 0.2, checkbox_box["height"] * 0.8)
            self.move_to(x, y)
            time.sleep(random.uniform(0.1, 0.3))
            self.page.mouse.click(x, y)

        return self.solve_invisible()

    def solve(self, url, sitekey, invisible=False):
        self.url = url if url.endswith("/") else url + "/"
        self.sitekey = sitekey
        self.invisible = invisible
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

        self.build_page_data()
        self.page.route(self.url, lambda route: route.fulfill(body=self.page_data, status=200))
        self.page.goto(self.url)

        self.window_width = self.page.evaluate("window.innerWidth")
        self.window_height = self.page.evaluate("window.innerHeight")

        try:
            return self.solve_invisible() if invisible else self.solve_visible()
        finally:
            self.context.close()
