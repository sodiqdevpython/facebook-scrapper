from selenium.webdriver.common.by import By
from utils.parser import parse_count_to_int
from utils.selenium_utils import get_element_or_none
from selenium.common.exceptions import NoSuchElementException


def get_banner_image_url(driver):
    try:
        img = driver.find_element(By.CSS_SELECTOR, 'img[data-imgperflogname="profileCoverPhoto"]')
        return img.get_attribute("src")
    except NoSuchElementException:
        return None

def get_avatar_img_url(driver):
    try:
        img = driver.find_elements(By.CSS_SELECTOR, 'image[preserveAspectRatio="xMidYMid slice"]')
        return img[1].get_attribute("xlink:href")
    except NoSuchElementException:
        return None

def get_overview(driver):
    work = get_element_or_none(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[4]/div/div/div/div[1]/div/div/div/div/div[2]/div/div/div/div/div[2]/div/div/div[2]")

    studied = get_element_or_none(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[4]/div/div/div/div[1]/div/div/div/div/div[2]/div/div/div/div/div[3]/div/div/div[2]")

    lives = get_element_or_none(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[4]/div/div/div/div[1]/div/div/div/div/div[2]/div/div/div/div/div[4]/div/div/div[2]/div/span")

    born_in = get_element_or_none(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[4]/div/div/div/div[1]/div/div/div/div/div[2]/div/div/div/div/div[5]/div/div/div[2]")

    married = get_element_or_none(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[4]/div/div/div/div[1]/div/div/div/div/div[2]/div/div/div/div/div[6]/div/div/div[2]")

    data = {
        "work": work,
        "studied": studied,
        "lives": lives,
        "from": born_in,
        "married": married
    }

    return data

def get_profile_full_info(driver, profile_url):
    if "profile.php?id=" in profile_url:
        driver.get(profile_url + "&sk=about")
    else:
        driver.get(profile_url + "/about")

    full_name = get_element_or_none(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[1]/div[2]/div/div/div/div[3]/div/div/div[1]/div/div/span/h1")

    followers = get_element_or_none(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[1]/div[2]/div/div/div/div[3]/div/div/div[2]/span/a[1]/strong")
    followers = parse_count_to_int(followers) if followers else 0

    following = get_element_or_none(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[1]/div[2]/div/div/div/div[3]/div/div/div[2]/span/a[2]/strong")
    following = parse_count_to_int(following) if following else 0

    banner = get_banner_image_url(driver)

    avatar = get_avatar_img_url(driver)

    overview = get_overview(driver)

    photo_albums = get_latest_photo_urls(driver, profile_url)

    return {
        "full_name": full_name,
        "followers": followers,
        "following": following,
        "banner": banner,
        "avatar": avatar,
        "overview": overview,
        "photo_albums": photo_albums,
    }

def get_latest_photo_urls(driver, url, limit=10):
    if "profile.php?id=" in url:
        driver.get(url + "&sk=photos_albums")
    else:
        driver.get(url + "/photos_albums")

    album_imgs = driver.find_elements(
        By.CSS_SELECTOR,
        'a[href*="/media/set/"] img'
    )
    urls = [img.get_attribute("src") for img in album_imgs if img.get_attribute("src")]
    return urls[:limit]