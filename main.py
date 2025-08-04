import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from components.api import send_profile_data, save_and_send_post_data
from components.get_profile_info import get_profile_full_info
from components.get_profile_posts import get_profile_posts

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

profile_url = "https://www.facebook.com/abror.muhtor.alij.2025"

print("=== PROFIL MA'LUMOTLARI OLISH ===")
# Profil ma'lumotlarini olish va API ga yuborish
data = get_profile_full_info(driver, profile_url)
profile_result = send_profile_data(data)

if profile_result:
    print("✓ Profil ma'lumotlari muvaffaqiyatli API ga yuborildi!")
else:
    print("✗ Profil ma'lumotlarini API ga yuborishda xatolik")

print("\n=== POSTLAR OLISH ===")
# Postlarni olish va API ga yuborish (har bir post avtomatik CDN va API ga yuboriladi)
posts = get_profile_posts(driver, profile_url, max_posts=5)  # 5 ta post olish

print(f"\n=== YAKUNIY NATIJA ===")
print(f"Profil yuborildi: {'✓' if profile_result else '✗'}")
print(f"Postlar jarayoni yakunlandi")

# Brauzer yopish
time.sleep(5)
driver.quit()
print("Brauzer yopildi.")