import requests
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Environment o'zgaruvchilarini yuklash
load_dotenv(".env")
BASE_URL = os.getenv("BASE_URL")
CDN_URL = os.getenv("CDN_URL")

# Media papkasini yaratish
MEDIA_DIR = 'media'
os.makedirs(MEDIA_DIR, exist_ok=True)


def upload_to_cdn(file_url):
    """
    Faylni URL dan yuklab olib, CDN ga yuboradi va natijani qaytaradi.

    Args:
        file_url (str): Yuklab olinadigan faylning URL manzili

    Returns:
        str or None: CDN dan qaytgan file URL yoki None (xatolik bo'lsa)
    """
    if not file_url:
        return None

    try:
        # Fayl nomini aniqlash
        file_name = os.path.basename(file_url.split("?")[0])
        if not file_name or file_name == '/':
            file_name = f"image_{int(time.time())}.jpg"

        file_path = os.path.join(MEDIA_DIR, file_name)

        # Faylni yuklab olish
        print(f"Fayl yuklab olinmoqda: {file_url}")
        response = requests.get(file_url, timeout=30)
        response.raise_for_status()

        # Faylni vaqtincha saqlash
        with open(file_path, 'wb') as f:
            f.write(response.content)

        # CDN ga yuborish
        with open(file_path, 'rb') as f:
            files = {'file': f}
            cdn_response = requests.post(CDN_URL, files=files, timeout=30)

        # Vaqtincha faylni o'chirish
        os.remove(file_path)

        print(f'CDN javobi - Status: {cdn_response.status_code}')

        # Status code 200 yoki 201 bo'lsa muvaffaqiyatli
        if cdn_response.status_code in [200, 201]:
            try:
                cdn_data = cdn_response.json()
                return cdn_data.get('file')
            except json.JSONDecodeError:
                print("CDN javobini JSON sifatida parse qilib bo'lmadi")
                return None
        else:
            print(f'CDN xatoligi: {cdn_response.text}')
            return None

    except requests.RequestException as e:
        print(f"Network xatoligi: {e}")
        return None
    except Exception as e:
        print(f"Umumiy xatolik: {e}")
        return None


def process_media_urls(profile_data, media_fields):
    """
    Media URL larni CDN ga yuklaydi va yangi URL larni qaytaradi.

    Args:
        profile_data (dict): Profil ma'lumotlari
        media_fields (list): Media maydonlar ro'yxati

    Returns:
        dict: Yangilangan media URL lari
    """
    processed_data = {}

    for field in media_fields:
        original_url = profile_data.get(field)
        if original_url:
            print(f"\n{field.upper()} ishlanmoqda...")
            cdn_url = upload_to_cdn(original_url)
            processed_data[field] = cdn_url if cdn_url else original_url

            if cdn_url:
                print(f"{field.title()} muvaffaqiyatli CDN ga yuklandi: {cdn_url}")
            else:
                print(f"{field.title()} CDN ga yuklanmadi, asl URL ishlatiladi")
        else:
            print(f"{field.title()} mavjud emas")

    return processed_data


def process_friends_avatars(friends_list):
    """
    Do'stlarning avatar rasmlarini CDN ga yuklaydi.

    Args:
        friends_list (list): Do'stlar ro'yxati

    Returns:
        list: Yangilangan avatar URL lari bilan do'stlar ro'yxati
    """
    if not friends_list:
        return []

    processed_friends = []

    for friend in friends_list:
        if isinstance(friend, dict):
            processed_friend = friend.copy()
            avatar_url = friend.get('avatar')
            if avatar_url:
                print(f"\nDo'st avatari ishlanmoqda: {friend.get('name', 'Unknown')}")
                cdn_avatar = upload_to_cdn(avatar_url)
                processed_friend['avatar'] = cdn_avatar if cdn_avatar else avatar_url
                if not cdn_avatar:
                    print(f"Do'st avatari CDN ga yuklanmadi, asl URL ishlatildi")
            processed_friends.append(processed_friend)

    return processed_friends


def process_photo_albums(photo_albums):
    """
    Foto albumlaridagi rasmlarni CDN ga yuklaydi.

    Args:
        photo_albums (list): Foto albumlar ro'yxati

    Returns:
        list: Yangilangan URL lar bilan foto albumlar
    """
    if not photo_albums:
        return []

    processed_photos = []

    for i, photo_url in enumerate(photo_albums):
        if photo_url:
            print(f"\nAlbum rasmi ishlanmoqda: {i + 1}/{len(photo_albums)}")
            cdn_photo = upload_to_cdn(photo_url)
            processed_photos.append(cdn_photo if cdn_photo else photo_url)

    return processed_photos


def send_profile_data(profile_data):
    """
    Profil ma'lumotlarini BASE_URL ga yuboradi.
    Barcha media fayllarni avval CDN ga yuklaydi.

    Args:
        profile_data (dict): Profil ma'lumotlari
    """
    print("Profil ma'lumotlari ishlanmoqda...")

    # Asosiy profil media fayllarini ishlov berish
    media_fields = ['banner', 'avatar']
    processed_media = process_media_urls(profile_data, media_fields)

    # Do'stlarning avatarlarini ishlov berish
    processed_friends = process_friends_avatars(profile_data.get('friends', []))

    # Photo albumlarni ishlov berish
    processed_photos = process_photo_albums(profile_data.get('photo_albums', []))

    # API ga yuborish uchun ma'lumotlarni tayyorlash
    api_data = {
        "profile_url": profile_data.get('profile_url'),
        "full_name": profile_data.get('full_name'),
        "followers": profile_data.get('followers', 0),
        "following": profile_data.get('following', 0),
        "overview": profile_data.get('overview', {}),
        "photo_albums": processed_photos,
        "friends": processed_friends,
    }

    # Processed media URL larni qo'shish
    api_data.update(processed_media)

    # Debug: API data ni ko'rish
    print(f"\nAPI ga yuboriladigan ma'lumotlar:")
    print(f"Profile URL: {api_data.get('profile_url')}")
    print(f"Full name: {api_data.get('full_name')}")
    print(f"Followers: {api_data.get('followers')}")
    print(f"Following: {api_data.get('following')}")
    print(f"Banner: {api_data.get('banner', 'None')}")
    print(f"Avatar: {api_data.get('avatar', 'None')}")
    print(f"Friends count: {len(api_data.get('friends', []))}")
    print(f"Photos count: {len(api_data.get('photo_albums', []))}")

    try:
        # API ga POST so'rov yuborish
        url = f"{BASE_URL}/profiles/"
        print(f"\nAPI URL: {url}")

        response = requests.post(url, json=api_data, timeout=30)

        print(f"API javobi - Status: {response.status_code}")
        print(f"API javob matni: {response.text}")

        response.raise_for_status()

        print("Profil muvaffaqiyatli yuborildi!")
        return response.json()

    except requests.HTTPError as e:
        print(f"HTTP xatoligi: {e}")
        print(f"Javob matni: {response.text}")
        return None
    except requests.RequestException as e:
        print(f"API ga yuborishda xatolik: {e}")
        return None
    except Exception as e:
        print(f"Umumiy xatolik: {e}")
        return None


def process_post_images(images_list):
    """
    Post rasmlari ro'yxatini CDN ga yuklaydi.

    Args:
        images_list (list): Rasm ob'ektlari ro'yxati

    Returns:
        list: CDN URL lari bilan yangilangan rasm ro'yxati
    """
    if not images_list:
        return []

    processed_images = []

    for image in images_list:
        if isinstance(image, dict) and image.get('src'):
            print(f"\nPost rasmi ishlanmoqda: {image.get('index', '?')}")
            cdn_url = upload_to_cdn(image['src'])

            processed_image = {
                'src': cdn_url if cdn_url else image['src'],
                'index': image.get('index', len(processed_images) + 1)
            }

            if cdn_url:
                print(f"Rasm {image.get('index', '?')} muvaffaqiyatli CDN ga yuklandi")
            else:
                print(f"Rasm {image.get('index', '?')} CDN ga yuklanmadi, asl URL ishlatiladi")

            processed_images.append(processed_image)

    return processed_images


def process_comments_avatars(comments_list):
    """
    Commentlar ichidagi author_image larni CDN ga yuklaydi.

    Args:
        comments_list (list): Comment ob'ektlari ro'yxati

    Returns:
        list: CDN URL lari bilan yangilangan comment ro'yxati
    """
    if not comments_list:
        return []

    processed_comments = []

    for i, comment in enumerate(comments_list):
        if isinstance(comment, dict):
            processed_comment = comment.copy()

            author_image = comment.get('author_image')
            if author_image:
                print(f"\nComment {i + 1} avatar rasmi ishlanmoqda...")
                cdn_url = upload_to_cdn(author_image)
                processed_comment['author_image'] = cdn_url if cdn_url else author_image

                if cdn_url:
                    print(f"Comment {i + 1} avatari muvaffaqiyatli CDN ga yuklandi")
                else:
                    print(f"Comment {i + 1} avatari CDN ga yuklanmadi, asl URL ishlatiladi")

            processed_comments.append(processed_comment)

    return processed_comments


def send_post_data(post_data):
    """
    Bitta post ma'lumotlarini API ga yuboradi.
    Barcha rasm va avatar larni avval CDN ga yuklaydi.

    Args:
        post_data (dict): Post ma'lumotlari

    Returns:
        dict or None: API javabi yoki None (xatolik bo'lsa)
    """
    print(f"\n=== POST {post_data.get('post_number', '?')} ISHLANMOQDA ===")
    print(f"Post ID: {post_data.get('post_id')}")
    print(f"Title: {post_data.get('title', 'No title')[:50]}...")

    # Post rasmlarini CDN ga yuklash
    processed_images = process_post_images(post_data.get('images', []))

    # Comment avatarlarini CDN ga yuklash
    processed_comments = process_comments_avatars(post_data.get('comments', []))

    # Helper funksiya - string dan raqam chiqarish
    def extract_number(text):
        if not text:
            return 0
        if isinstance(text, int):
            return text
        if isinstance(text, str):
            # Faqat raqamlarni ajratib olish
            import re
            numbers = re.findall(r'\d+', text.replace(',', ''))
            return int(numbers[0]) if numbers else 0
        return 0

    # API ga yuborish uchun ma'lumotlarni tayyorlash
    api_data = {
        "post_id": post_data.get('post_id'),
        "post_number": post_data.get('post_number'),
        "title": post_data.get('title'),
        "location": post_data.get('location'),
        "reactions_count": extract_number(post_data.get('reactions_count')),
        "comments_count": extract_number(post_data.get('comments_count')),
        "images": processed_images,
        "comments": processed_comments,
        "profile_url": post_data.get('profile_url'),
        "profile_name": post_data.get('profile_name'),
        "scraped_at": post_data.get('scraped_at')
    }

    # Debug: API data ni ko'rish
    print(f"\nAPI ga yuboriladigan ma'lumotlar:")
    print(f"Post ID: {api_data.get('post_id')}")
    print(f"Title: {api_data.get('title', 'None')}")
    print(f"Images count: {len(api_data.get('images', []))}")
    print(f"Comments count: {len(api_data.get('comments', []))}")
    print(f"Profile: {api_data.get('profile_name')}")

    try:
        # API ga POST so'rov yuborish
        url = f"{BASE_URL}/posts/"  # posts endpoint
        print(f"\nAPI URL: {url}")

        response = requests.post(url, json=api_data, timeout=30)

        print(f"API javobi - Status: {response.status_code}")

        if response.status_code not in [200, 201]:
            print(f"API javob matni: {response.text}")

        response.raise_for_status()

        print(f"Post {post_data.get('post_number')} muvaffaqiyatli yuborildi!")
        return response.json()

    except requests.HTTPError as e:
        print(f"HTTP xatoligi: {e}")
        if hasattr(response, 'text'):
            print(f"Javob matni: {response.text}")
        return None
    except requests.RequestException as e:
        print(f"API ga yuborishda xatolik: {e}")
        return None
    except Exception as e:
        print(f"Umumiy xatolik: {e}")
        return None


def send_posts_batch(posts_data_list):
    """
    Bir nechta postni ketma-ket API ga yuboradi.

    Args:
        posts_data_list (list): Post ma'lumotlari ro'yxati

    Returns:
        list: Muvaffaqiyatli yuborilgan postlar natijalari
    """
    results = []

    print(f"\n=== JAMI {len(posts_data_list)} TA POST API GA YUBORILMOQDA ===")

    for i, post_data in enumerate(posts_data_list):
        print(f"\n--- Post {i + 1}/{len(posts_data_list)} ---")

        result = send_post_data(post_data)
        if result:
            results.append(result)
            print(f"✓ Post {i + 1} muvaffaqiyatli yuborildi")
        else:
            print(f"✗ Post {i + 1} yuborishda xatolik")

        # Postlar orasida biroz kutish
        if i < len(posts_data_list) - 1:
            time.sleep(2)

    print(f"\n=== YAKUNIY NATIJA ===")
    print(f"Jami postlar: {len(posts_data_list)}")
    print(f"Muvaffaqiyatli yuborildi: {len(results)}")
    print(f"Xatolik bo'ldi: {len(posts_data_list) - len(results)}")

    return results


def load_and_send_posts_from_json_files(json_files_list):
    """
    JSON fayllardan postlarni o'qib, API ga yuboradi.

    Args:
        json_files_list (list): JSON fayl yo'llari ro'yxati

    Returns:
        list: API natijalari
    """
    posts_data = []

    for json_file in json_files_list:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                post_data = json.load(f)
                posts_data.append(post_data)
                print(f"✓ {json_file} fayli o'qildi")
        except Exception as e:
            print(f"✗ {json_file} faylini o'qishda xatolik: {e}")

    if posts_data:
        return send_posts_batch(posts_data)
    else:
        print("Hech qanday post ma'lumoti topilmadi")
        return []


# Scraper kodingiz bilan integratsiya uchun
def save_and_send_post_data(post_data, profile_name="unknown_profile"):
    """
    Post ma'lumotlarini JSON ga saqlaydi va API ga yuboradi.
    Bu funksiyani scraper kodingizda ishlatishingiz mumkin.

    Args:
        post_data (dict): Post ma'lumotlari
        profile_name (str): Profil nomi

    Returns:
        tuple: (json_filename, api_result)
    """
    # JSON ga saqlash
    try:
        json_dir = f"scraped_posts/{datetime.now().strftime('%Y%m%d')}"
        os.makedirs(json_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        post_id = post_data.get('post_id', f'post_{timestamp}')
        filename = f"{json_dir}/{post_id}_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, ensure_ascii=False, indent=2, default=str)

        print(f"Post ma'lumotlari saqlandi: {filename}")

        # API ga yuborish
        api_result = send_post_data(post_data)

        return filename, api_result

    except Exception as e:
        print(f"JSON saqlash/API yuborishda xato: {str(e)}")
        return None, None