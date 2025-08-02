import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ── DOM SELEKTORLAR ─────────────────────────────────────────────────
COMMENT_BTN = 'span[data-ad-rendering-role="comment_button"]'
COMMENT_TEXT_BTN = 'span:contains("Comment")'  # "Comment" button
MODAL_XPATH = '//div[@role="dialog" and @aria-labelledby]'
CLOSE_SELECTORS = [
    '[aria-label="Close"][role="button"]',
    'svg[aria-label="Close"]',
    '[data-visualcompletion="ignore-dynamic"][aria-label="Close"]',
]


def get_profile_posts(driver, profile_url, max_posts=50,
                      scroll_px=300, pause=1.0,
                      no_new_limit=5, max_steps=500):
    driver.get(profile_url)
    processed_ids, no_new, step = set(), 0, 0
    posts_count = 0
    recent_titles = []
    current_scroll_position = 0

    print(f" Postlar yig'ilayabdi (max: {max_posts})")

    while step < max_steps and no_new < no_new_limit and posts_count < max_posts:

        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, COMMENT_BTN)

            valid_buttons = []
            for btn in buttons:
                try:
                    if (btn.is_displayed() and
                            btn.location['y'] >= current_scroll_position and
                            id(btn) not in processed_ids):
                        valid_buttons.append(btn)
                except:
                    continue

            fresh = valid_buttons

        except Exception as e:
            print(f"\nButton topilmadi: {e}\n")
            fresh = []

        if fresh:
            no_new = 0
            for btn in fresh[:1]:
                if posts_count >= max_posts:
                    break
                processed_ids.add(id(btn))
                try:
                    btn_position = btn.location['y']
                    if btn_position < current_scroll_position:
                        continue

                    driver.execute_script("""
                        var element = arguments[0];
                        var elementRect = element.getBoundingClientRect();
                        var absoluteElementTop = elementRect.top + window.pageYOffset;
                        var middle = absoluteElementTop - (window.innerHeight / 2);
                        if (middle > window.pageYOffset) {
                            window.scrollTo(0, middle);
                        }
                    """, btn)
                    time.sleep(0.5)

                    WebDriverWait(driver, 2).until(EC.element_to_be_clickable(btn)).click()
                    time.sleep(1.5)

                    title = read_post_title(driver)

                    if title and title not in recent_titles:
                        posts_count += 1
                        recent_titles.append(title)
                        if len(recent_titles) > 15:
                            recent_titles.pop(0)
                        print(f"\nPost #{posts_count}: {title}\n")
                    elif title:
                        print(f"Takrorlanganlar: {title}")

                    close_modal(driver)

                    current_scroll_position = driver.execute_script("return window.pageYOffset")

                except Exception as e:
                    print(f"\nButton xato: {str(e)[:30]}...\n")
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(0.3)
                    except:
                        pass
                    continue
        else:
            current_height = driver.execute_script("return window.pageYOffset")
            max_height = driver.execute_script("return document.body.scrollHeight")

            if current_height >= max_height - 1500:
                no_new += 1
                print(f"Page tugaganga o'xshaydi {no_new}/{no_new_limit}")
                if no_new >= no_new_limit:
                    print("\nSahifa to'liq tugadi")
                    break
            else:
                print(f"Button topilmadi scroll qilinayabdi: ({scroll_px}px)")

        old_position = driver.execute_script("return window.pageYOffset")
        driver.execute_script(f"window.scrollBy(0, {scroll_px});")
        new_position = driver.execute_script("return window.pageYOffset")

        if new_position == old_position:
            no_new += 1
        else:
            current_scroll_position = new_position

        time.sleep(pause)
        step += 1

    if posts_count >= max_posts:
        print(f" Maksimal limitga yetdi {posts_count} ta post olindi!")
    elif no_new >= no_new_limit:
        print(f"Yangi postlar tugadi. Jami: {posts_count} ta post olindi")
    else:
        print(f"Maksimal step tugadi. Jami: {posts_count} ta post olindi")

    # print(f"Jami ko'rilgan postlar: {len(processed_ids)}")
    return recent_titles


def read_post_title(driver):
    try:
        modal = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, MODAL_XPATH))
        )

        for div in modal.find_elements(By.CSS_SELECTOR, 'div.x126k92a'):
            txt = div.text.strip()
            if txt and len(txt) >= 3 and len(txt) <= 500:
                print("➜", txt)
                return txt

        for div in modal.find_elements(By.CSS_SELECTOR, 'div[dir="auto"]'):
            txt = div.text.strip()
            if txt and len(txt) >= 3 and len(txt) <= 500:
                print("=>", txt)
                return txt

        print("=> Title topilmadi")
        return None
    except TimeoutException:
        print(" => Modal topilmadi")
        return None


def close_modal(driver):
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.3)
        try:
            modal = driver.find_element(By.XPATH, MODAL_XPATH)
            if modal.is_displayed():
                close_btn = modal.find_element(By.CSS_SELECTOR, 'div[aria-label="Close"][role="button"]')
                driver.execute_script("arguments[0].click();", close_btn)
                time.sleep(0.3)
        except:
            pass

    except Exception as e:
        print("Modal yopishda xato:\n", str(e))