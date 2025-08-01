# import time
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.common.by import By
#
# def get_profile_posts(driver, profile_url):
#     driver.get(profile_url)
#     time.sleep(3)
#     posts = driver.find_elements(By.CSS_SELECTOR, 'span[data-ad-rendering-role="comment_button"]')
#
#     for post in posts:  #Postlarni topib olishga
#         time.sleep(2)
#         post.click() # post comment ni bosdik
#         time.sleep(3) #comment yuklanishini kutish uchun
#
#         get_post_title(driver)
#
#         close_button = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Close"]') #close button ni topib olish uchun
#         close_button.click() #postni yopdim boshqaisga o'tish uchun
#         time.sleep(2)
#         driver.execute_script("window.scrollBy(0, 900);") # 1300px pastga srudim
#
#     time.sleep(3)
#     return posts
#
#
#
#
# def get_post_title(driver):
#     try:
#         modal = driver.find_element(By.XPATH, '//div[@aria-label="Close"]/ancestor::div[starts-with(@class,"x1n2onr6")]')
#         title_divs = modal.find_elements(By.CSS_SELECTOR, 'div.x126k92a')
#         for div in title_divs:
#             text = div.text.strip()
#             if text:
#                 print(text)
#                 return text
#
#         print("Post title yozilmagan")
#     except Exception as e:
#         print("Xato: ", str(e))


import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, StaleElementReferenceException,
    ElementClickInterceptedException,
)

COMMENT_BTN      = 'span[data-ad-rendering-role="comment_button"]'
MODAL_XPATH      = '//div[@role="dialog" and @aria-labelledby]'
CLOSE_CANDIDATES = [
    '[aria-label="Close"]',                # div yoki button
    'svg[aria-label="Close"]',             # svg ikonka
    '[data-visualcompletion="ignore-dynamic"][aria-label="Close"]',
]

def get_profile_posts(driver, profile_url,
                      scroll_px=1400, pause=1.5,
                      no_new_limit=15, max_steps=1500):

    driver.get(profile_url)
    processed_ids, no_new, step = set(), 0, 0

    while step < max_steps and no_new < no_new_limit:

        buttons = driver.find_elements(By.CSS_SELECTOR, COMMENT_BTN)
        fresh   = [b for b in buttons if id(b) not in processed_ids]
        no_new  = 0 if fresh else no_new + 1

        for btn in fresh:
            processed_ids.add(id(btn))
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                WebDriverWait(driver, 4).until(EC.element_to_be_clickable(btn)).click()

                read_post_title(driver)
                close_modal(driver)       # ❌ faqat Close tugmasi
            except (TimeoutException, StaleElementReferenceException,
                    ElementClickInterceptedException):
                continue

        driver.execute_script(f"window.scrollBy(0, {scroll_px});")
        time.sleep(pause)
        step += 1

    print(f"🔚  Jami ko‘rilgan postlar: {len(processed_ids)}")

def read_post_title(driver):
    try:
        modal = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, MODAL_XPATH))
        )
        for div in modal.find_elements(By.CSS_SELECTOR, 'div.x126k92a'):
            txt = div.text.strip()
            if txt:
                print("➜", txt)
                return txt
        print("➜ (Sarlavha topilmadi)")
    except TimeoutException:
        print("➜ (Modal topilmadi)")

def close_modal(driver):
    try:
        modal = WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((By.XPATH, MODAL_XPATH))
        )
    except TimeoutException:
        print("⚠️  Modal topilmadi — yopib bo‘lmadi")
        return

    for css in CLOSE_CANDIDATES:
        try:
            close_btn = modal.find_element(By.CSS_SELECTOR, css)
            # 1) Oddiy click
            try:
                close_btn.click()
                WebDriverWait(driver, 2).until(EC.staleness_of(modal))
                return
            except ElementClickInterceptedException:
                pass

            # 2) Agar to‘sildi → JS orqali “real” click
            driver.execute_script(
                "arguments[0].dispatchEvent(new MouseEvent('click', {bubbles:true}));",
                close_btn
            )
            WebDriverWait(driver, 2).until(EC.staleness_of(modal))
            return
        except Exception:
            continue

    print("⚠️  Close tugmasi topilmadi yoki bosilmadi")

