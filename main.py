import os, json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

from components.get_profile_info import get_profile_full_info
from components.get_profile_posts import get_profile_posts
from components.get_user_friends import get_friends_list

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
user_data_dir = os.path.join(BASE_DIR, "selenium_profile")
profile_name = "Profile 1"

options = webdriver.ChromeOptions()
options.add_argument(f"--user-data-dir={user_data_dir}")
options.add_argument(f"--profile-directory={profile_name}")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

profile_url = "https://www.facebook.com/kunuznews"

# data = get_profile_full_info(driver, profile_url)

# friends = get_friends_list(driver, profile_url)

# friends olish uchun
# print(json.dumps(friends, indent=4, ensure_ascii=False))

# umumiy data larni olish uchun
# print(json.dumps(data, indent=4, ensure_ascii=False))

# profile_posts ni olish uchun
get_profile_posts(driver, profile_url)

# result = {
#     'profile': data,
#     'friends': friends,
# }

# print(json.dumps(result, indent=4, ensure_ascii=False))

time.sleep(10000)
driver.quit()