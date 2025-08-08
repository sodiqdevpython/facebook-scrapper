import os
import requests
import time
import json
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import signal
import sys

from components.api import send_profile_data
from components.get_profile_info import get_profile_full_info
from components.get_profile_posts import get_profile_posts

# Environment o'zgaruvchilarni yuklash
load_dotenv(".env")
BASE_URL = os.getenv("BASE_URL")
AGENT_CHECK_INTERVAL = int(os.getenv("AGENT_CHECK_INTERVAL", "10"))  # soniyalarda
UPDATED_TIMEOUT_MINUTES = int(os.getenv("UPDATED_TIMEOUT_MINUTES", "5"))  # daqiqalarda
AGENT_ID = os.getenv("AGENT_ID", "Agent-1")  # agent nomi

# Global o'zgaruvchilar - signal handler uchun
current_channel_id = None
driver = None

# Selenium sozlamalari
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
user_data_dir = os.path.join(BASE_DIR, "selenium_profile")
profile_name = "Profile 1"


def setup_driver():
    """Selenium driver ni sozlash"""
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_name}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def get_available_channels():
    """
    is_checking=false bo'lgan va updated vaqti timeout dan oshgan channellarni olish
    """
    try:
        url = f"{BASE_URL}/channels/"
        params = {
            'is_checking': 'false'
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        channels = response.json()
        available_channels = []

        current_time = datetime.now()

        for channel in channels:
            # Updated vaqtini tekshirish
            updated_str = channel.get('updated')
            if updated_str:
                try:
                    # ISO format da parse qilish
                    updated_time = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
                    # Timezone info ni olib tashlash (local time bilan solishtirish uchun)
                    updated_time = updated_time.replace(tzinfo=None)

                    # Oxirgi UPDATED_TIMEOUT_MINUTES daqiqada update bo'lganlarni skip qilish
                    time_diff = current_time - updated_time
                    if time_diff.total_seconds() < (UPDATED_TIMEOUT_MINUTES * 60):
                        print(
                            f"  > Channel {channel.get('id')} - oxirgi {UPDATED_TIMEOUT_MINUTES} daqiqada update bo'lgan, skip")
                        continue

                except ValueError as e:
                    print(f"  > Vaqt parse qilishda xatolik: {e}")

            available_channels.append(channel)

        return available_channels

    except requests.RequestException as e:
        print(f"Channellarni olishda network xatoligi: {e}")
        return []
    except Exception as e:
        print(f"Channellarni olishda umumiy xatolik: {e}")
        return []


def claim_channel(channel_id):
    """
    Channelni band qilish (is_checking=true qilish)
    """
    try:
        url = f"{BASE_URL}/channels/{channel_id}/"
        data = {
            'is_checking': True
        }

        response = requests.patch(url, json=data, timeout=30)

        if response.status_code in [200, 201]:
            print(f"✓ Channel {channel_id} muvaffaqiyatli band qilindi")
            return True
        else:
            print(f"✗ Channel {channel_id} band qilishda xatolik: Status {response.status_code}")
            print(f"  Response: {response.text}")
            return False

    except requests.RequestException as e:
        print(f"Channel {channel_id} band qilishda network xatoligi: {e}")
        return False
    except Exception as e:
        print(f"Channel {channel_id} band qilishda umumiy xatolik: {e}")
        return False


def release_channel(channel_id):
    """
    Channelni bo'shatish (is_checking=false qilish)
    """
    if not channel_id:
        return True

    try:
        url = f"{BASE_URL}/channels/{channel_id}/"
        data = {
            'is_checking': False
        }

        response = requests.patch(url, json=data, timeout=30)

        if response.status_code in [200, 201]:
            print(f"✓ Channel {channel_id} muvaffaqiyatli bo'shatildi")
            return True
        else:
            print(f"✗ Channel {channel_id} bo'shatishda xatolik: Status {response.status_code}")
            print(f"  Response: {response.text}")
            return False

    except requests.RequestException as e:
        print(f"Channel {channel_id} bo'shatishda network xatoligi: {e}")
        return False
    except Exception as e:
        print(f"Channel {channel_id} bo'shatishda umumiy xatolik: {e}")
        return False


def signal_handler(signum, frame):
    """
    Signal handler - dastur to'xtatilganda channelni bo'shatish
    """
    global current_channel_id, driver

    print(f"\n⚠️  Signal qabul qilindi: {signum}")
    print("Dastur to'xtatilmoqda, channelni bo'shatish...")

    # Hozirgi channelni bo'shatish
    if current_channel_id:
        print(f"Channel {current_channel_id} ni bo'shatish...")
        release_success = release_channel(current_channel_id)
        if release_success:
            print("✓ Channel muvaffaqiyatli bo'shatildi")
        else:
            print("✗ Channel bo'shatishda xatolik!")

    # Driver ni yopish
    if driver:
        try:
            print("Driver yopilmoqda...")
            driver.quit()
            print("✓ Driver yopildi")
        except Exception as e:
            print(f"Driver yopishda xatolik: {e}")

    print("Dastur tugadi")
    sys.exit(0)


def process_channel(driver_instance, channel_data):
    """
    Bitta channelni to'liq ishlov berish
    """
    channel_id = channel_data.get('id')
    channel_url = channel_data.get('channel_username')
    post_count = channel_data.get('count', 10)

    print(f"\n{'=' * 60}")
    print(f"CHANNEL {channel_id} ISHLANMOQDA")
    print(f"URL: {channel_url}")
    print(f"Post count: {post_count}")
    print(f"{'=' * 60}")

    success_profile = False
    success_posts = False

    try:
        # 1. Profil ma'lumotlarini olish va yuborish
        print("\n=== PROFIL MA'LUMOTLARI OLISH ===")
        try:
            profile_data = get_profile_full_info(driver_instance, channel_url)

            if profile_data:
                profile_result = send_profile_data(profile_data)
                if profile_result:
                    print("✓ Profil ma'lumotlari muvaffaqiyatli API ga yuborildi!")
                    success_profile = True
                else:
                    print("✗ Profil ma'lumotlarini API ga yuborishda xatolik")
            else:
                print("✗ Profil ma'lumotlarini olishda xatolik")

        except Exception as e:
            print(f"✗ Profil ma'lumotlari olishda xatolik: {e}")

        # 2. Postlarni olish va yuborish
        print(f"\n=== POSTLAR OLISH (count: {post_count}) ===")

        try:
            # Agar count 0 dan kichik bo'lsa, unlimited post yig'ish
            if post_count <= 0:
                print("Count <= 0, barcha postlar yig'iladi")
                max_posts = 1000  # Maksimal limit
                max_steps = 10000  # Ko'proq scroll
            else:
                max_posts = post_count
                max_steps = 5000

            posts_result = get_profile_posts(
                driver_instance,
                channel_url,
                max_posts=max_posts,
                max_steps=max_steps
            )

            if posts_result is not None:
                print(f"✓ Postlar jarayoni yakunlandi. Natija: {len(posts_result)} ta post")
                success_posts = True
            else:
                print("✗ Postlar olishda xatolik")

        except Exception as e:
            print(f"✗ Postlar olishda xatolik: {e}")

        # Umumiy natija
        if success_profile or success_posts:
            print(f"\n✓ Channel {channel_id} qisman yoki to'liq muvaffaqiyatli ishlov berildi")
            print(f"  - Profil: {'✓' if success_profile else '✗'}")
            print(f"  - Postlar: {'✓' if success_posts else '✗'}")
            return True
        else:
            print(f"\n✗ Channel {channel_id} ishlov berishda to'liq xatolik")
            return False

    except Exception as e:
        print(f"\n✗ Channel {channel_id} ishlov berishda umumiy xatolik: {e}")
        return False


def main_agent_loop():
    """
    Asosiy agent loop - doimiy ishlab turadi
    """
    global current_channel_id, driver

    print(f"\n{'=' * 80}")
    print(f"FACEBOOK SCRAPER AGENT - {AGENT_ID}")
    print(f"Base URL: {BASE_URL}")
    print(f"Check interval: {AGENT_CHECK_INTERVAL} soniya")
    print(f"Timeout minutes: {UPDATED_TIMEOUT_MINUTES} daqiqa")
    print(f"{'=' * 80}")

    # Signal handler o'rnatish
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Terminate signal

    try:
        # Selenium driver ni ishga tushirish
        print("\nSelenium driver ishga tushirilmoqda...")
        driver = setup_driver()
        print("✓ Driver tayyor")

        print(f"\n🚀 Agent ishga tushdi. Har {AGENT_CHECK_INTERVAL} soniyada channellar tekshiriladi...")

        while True:
            try:
                current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"\n[{current_time_str}] Mavjud channellarni tekshirish...")

                # Mavjud channellarni olish
                available_channels = get_available_channels()

                if not available_channels:
                    print("❌ Hech qanday mavjud channel topilmadi")
                    print(f"⏳ {AGENT_CHECK_INTERVAL} soniya kutish...")
                    time.sleep(AGENT_CHECK_INTERVAL)
                    continue

                # Birinchi channelni olish
                channel = available_channels[0]
                channel_id = channel.get('id')
                current_channel_id = channel_id  # Global o'zgaruvchiga saqlash

                print(f"🎯 Channel topildi: {channel_id} - {channel.get('channel_username')}")

                # Channelni band qilish
                print(f"🔒 Channel {channel_id} ni band qilish...")
                if not claim_channel(channel_id):
                    print("❌ Channel band qilishda xatolik, keyingisiga o'tish...")
                    current_channel_id = None
                    time.sleep(5)
                    continue

                # Channelni ishlov berish
                print(f"⚙️  Channel {channel_id} ni ishlov berish boshlandi...")
                success = process_channel(driver, channel)

                # Channelni bo'shatish
                print(f"🔓 Channel {channel_id} ni bo'shatish...")
                release_success = release_channel(channel_id)

                if not release_success:
                    print("❌ Channel bo'shatishda xatolik!")

                # Global o'zgaruvchini tozalash
                current_channel_id = None

                # Natijani ko'rsatish
                if success:
                    print(f"✅ Channel {channel_id} muvaffaqiyatli tugallandi")
                else:
                    print(f"❌ Channel {channel_id} ishlov berishda xatolik bo'ldi")

                # Keyingi channelga o'tishdan oldin biroz kutish
                print("⏳ Keyingi channelga o'tish uchun 3 soniya kutish...")
                time.sleep(3)

            except KeyboardInterrupt:
                print("\n⚠️  Keyboard interrupt (Ctrl+C)")
                break
            except Exception as e:
                print(f"❌ Agent loop da xatolik: {e}")
                print(f"⏳ 5 soniya kutib qayta urinish...")

                # Agar xatolik bo'lsa, hozirgi channelni bo'shatish
                if current_channel_id:
                    print(f"🔓 Xatolik tufayli channel {current_channel_id} ni bo'shatish...")
                    release_channel(current_channel_id)
                    current_channel_id = None

                time.sleep(5)
                continue

    except Exception as e:
        print(f"❌ Agent ishga tushirishda umumiy xatolik: {e}")

    finally:
        # Oxirgi channelni bo'shatish
        if current_channel_id:
            print(f"🔓 Dastur tugashi: channel {current_channel_id} ni bo'shatish...")
            release_channel(current_channel_id)

        # Driver ni yopish
        if driver:
            try:
                print("🔒 Driver yopilmoqda...")
                driver.quit()
                print("✓ Driver yopildi")
            except Exception as e:
                print(f"Driver yopishda xatolik: {e}")


if __name__ == "__main__":
    try:
        main_agent_loop()
    except KeyboardInterrupt:
        print("\n⚠️  Dastur foydalanuvchi tomonidan to'xtatildi")
    except Exception as e:
        print(f"❌ Dastur umumiy xatoligi: {e}")

    print("\n👋 Dastur tugadi")