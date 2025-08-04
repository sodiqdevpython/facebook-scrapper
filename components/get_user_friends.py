from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time

def get_friends_list(driver, url, limit=10):
    # Friends sahifasiga o‘tish
    if "profile.php?id=" in url:
        driver.get(url + "&sk=friends")
    else:
        driver.get(url + "/friends")

    time.sleep(3)

    # Scroll qilish: do‘stlar to‘liq yuklanishi uchun
    last_height = driver.execute_script("return document.body.scrollHeight")
    friends_data = set()
    attempts = 0

    while len(friends_data) < limit and attempts < 10:
        # Topilgan do‘st bloklarini ajratish
        cards = driver.find_elements(By.CSS_SELECTOR, 'div.x1yztbdb div.x1iyjqo2 a[href*="facebook.com"]')

        for card in cards:
            href = card.get_attribute("href")
            name = card.text.strip()
            if href and name:
                friends_data.add((name, href))
            if len(friends_data) >= limit:
                break

        # Scroll pastga
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(2)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            attempts += 1
        else:
            attempts = 0
            last_height = new_height

    friends = []
    for name, href in list(friends_data)[:limit]:
        try:
            img_el = driver.find_element(By.XPATH, f'//a[@href="{href}"]//img')
            img_url = img_el.get_attribute("src")
        except:
            img_url = None
        friends.append({
            "name": name,
            "profile_url": href,
            "avatar": img_url
        })

    return friends