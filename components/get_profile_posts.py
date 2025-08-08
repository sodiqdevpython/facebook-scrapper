import time
import json
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from utils.parser import parse_facebook_date
from components.api import save_and_send_post_data

COMMENT_BTN = 'span[data-ad-rendering-role="comment_button"]'
COMMENT_TEXT_BTN = 'span:contains("Comment")'  # "Comment" button
MODAL_XPATH = '//div[@role="dialog" and @aria-labelledby]'
CLOSE_SELECTORS = [
    '[aria-label="Close"][role="button"]',
    'svg[aria-label="Close"]',
    '[data-visualcompletion="ignore-dynamic"][aria-label="Close"]',
]


def save_to_json(post_data, profile_name="unknown_profile"):
    try:
        json_dir = f"scraped_posts/{datetime.now().strftime('%Y%m%d')}"
        os.makedirs(json_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        post_id = post_data.get('post_id', f'post_{timestamp}')
        filename = f"{json_dir}/{post_id}_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, ensure_ascii=False, indent=2, default=str)

        print(f"Post ma'lumotlari saqlandi: {filename}")
        return filename

    except Exception as e:
        print(f"JSON saqlashda xato: {str(e)}")
        return None


def get_profile_posts(driver, profile_url, max_posts=20,
                      scroll_px=300, pause=1.0,
                      no_new_limit=5, max_steps=5000):
    driver.get(profile_url)
    processed_ids, no_new, step = set(), 0, 0
    posts_count = 0
    recent_titles = []
    current_scroll_position = 0
    saved_posts = []

    profile_name = profile_url.split('/')[-1] or profile_url.split('/')[-2]

    # Agar max_posts <= 0 bo'lsa, barcha postlarni olish uchun limitlarni oshirish
    if max_posts <= 0:
        print("Count <= 0, BARCHA postlar yig'iladi (unlimited)")
        max_posts = 99999  # Juda katta son
        no_new_limit = 15  # Ko'proq urinish
        max_steps = 20000  # Ko'proq scroll
        print(f"Yangi limitlar: max_posts={max_posts}, no_new_limit={no_new_limit}, max_steps={max_steps}")
    else:
        print(f"Postlar yig'ilayabdi (max: {max_posts})")

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
                    post_data = read_post_data(driver, posts_count + 1)
                    posts_count += 1
                    if post_data:
                        post_data['profile_url'] = profile_url
                        post_data['profile_name'] = profile_name
                        post_data['scraped_at'] = datetime.now().isoformat()

                        # JSON ga saqlash VA API ga yuborish
                        saved_file, api_result = save_and_send_post_data(post_data, profile_name)

                        if saved_file:
                            saved_posts.append(saved_file)

                        if api_result:
                            print(f"✓ Post #{posts_count} API ga muvaffaqiyatli yuborildi!")
                        else:
                            print(f"✗ Post #{posts_count} API ga yuborishda xatolik")

                        title = post_data.get('title', '')
                        if title and title not in recent_titles:
                            recent_titles.append(title)
                            if len(recent_titles) > 15:
                                recent_titles.pop(0)
                            print(f"Post #{posts_count}: {title}\n")
                        elif title:
                            print(f"Post #{posts_count}: {title} (takrorlangan)\n")
                        else:
                            print(f"Post #{posts_count}: title yo'q\n")
                    else:
                        print(f"Post #{posts_count}: olinmadi\n")

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
                if max_posts <= 0:
                    print(f"Sahifa tugaganga o'xshaydi (unlimited mode) {no_new}/{no_new_limit}")
                else:
                    print(f"Page tugaganga o'xshaydi {no_new}/{no_new_limit}")

                if no_new >= no_new_limit:
                    if max_posts <= 0:
                        print(f"\nUnlimited mode: Sahifa to'liq tugadi, jami {posts_count} ta post olindi")
                    else:
                        print("\nSahifa to'liq tugadi")
                    break
            else:
                if max_posts <= 0:
                    print(
                        f"Unlimited mode: Button topilmadi scroll qilinayabdi: ({scroll_px}px) - Step: {step}/{max_steps}")
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

    # Xulosa
    if max_posts <= 0:
        print(f"UNLIMITED MODE tugadi: Jami {posts_count} ta post olindi")
        print(f"Steps ishlatildi: {step}/{max_steps}")
        print(f"No new attempts: {no_new}/{no_new_limit}")
    elif posts_count >= max_posts:
        print(f"Maksimal limitga yetdi {posts_count} ta post olindi")
    elif no_new >= no_new_limit:
        print(f"Jami: {posts_count} ta post olindi")
    else:
        print(f"Jami: {posts_count} ta post olindi")

    print(f"JSON fayllar soni: {len(saved_posts)}")
    print(f"Saqlangan fayllar: {saved_posts}")

    return recent_titles


def read_post_data(driver, post_number):
    try:
        modal = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, MODAL_XPATH))
        )

        post_data = {
            'post_id': f'post_{post_number}_{int(time.time())}',
            'post_number': post_number,
            'title': None,
            'location': None,
            'reactions_count': None,
            'comments_count': None,
            'images': [],
            'comments': []
        }

        try:
            location = modal.find_element(By.XPATH,
                                          "/html/body/div[1]/div/div[1]/div/div[4]/div/div/div[1]/div/div[2]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[1]/div/div/div/div/div/div/div/div/div/div/div[13]/div/div/div[2]/div/div[2]/div/div[1]/span/div/h3/span")
            post_data['location'] = location.text
            print("Location:", location.text)
        except:
            print("Location topilmadi")

        try:
            reactions_count = modal.find_element(By.XPATH,
                                                 "/html/body/div[1]/div/div[1]/div/div[4]/div/div/div[1]/div/div[2]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div/div[1]/div/div[1]/div/div[1]/div/span/div/span[2]/span/span")
            post_data['reactions_count'] = reactions_count.text
            print(f"Reactions count: {reactions_count.text}")
        except:
            print("Reactions count topilmadi")
        try:
            comments_count = modal.find_element(By.CSS_SELECTOR,
                                                'span.xdj266r.x14z9mp.xat24cr.x1lziwak.xexx8yu.xyri2b.x18d9i69.x1c1uobl.x1hl2dhg.x16tdsg8.x1vvkbs.xkrqix3.x1sur9pj')
            post_data['comments_count'] = comments_count.text
            print(f"Comments count: {comments_count.text}")
        except Exception as e:
            print(f"Comments count xato: {str(e)[:30]}...")

        try:
            target_div = modal.find_element(By.CSS_SELECTOR,
                                            'div.x14z9mp.xat24cr.x1lziwak.xexx8yu.xyri2b.x18d9i69.x1c1uobl.x1gslohp')
            try:
                title_div = modal.find_element(By.CSS_SELECTOR,
                                               'div.xdj266r.x14z9mp.xat24cr.x1lziwak.xexx8yu.xyri2b.x18d9i69.x1c1uobl')
                all_images = title_div.find_elements(By.TAG_NAME, 'img')

                for i, img in enumerate(all_images):
                    try:
                        src = img.get_attribute('src')
                        if src and src.startswith('https://') and not src.startswith('https://static'):
                            post_data['images'].append({
                                'src': src,
                                'index': len(post_data['images']) + 1
                            })
                            print(f"Rasm {len(post_data['images'])}: {src[:50]}...")
                    except:
                        pass

            except Exception as e:
                print(f"Title div topilmadi: {str(e)[:30]}...")

            try:
                comments = target_div.find_elements(By.CSS_SELECTOR, 'div.x78zum5.xdt5ytf')
                print(f"{len(comments)} ta comment topildi")

                for i, comment in enumerate(comments[:50]):  # ! boshidagi 50 ta comment uchun
                    try:
                        comment_data = {}

                        try:
                            comment_data['author_url'] = comment.find_element(By.CSS_SELECTOR,
                                                                              'a[aria-hidden="false"]').get_attribute(
                                'href')
                        except:
                            comment_data['author_url'] = None
                        try:
                            comment_data['author_image'] = comment.find_element(By.CSS_SELECTOR,
                                                                                'image[preserveAspectRatio="xMidYMid slice"').get_attribute(
                                'xlink:href')
                        except:
                            comment_data['author_image'] = None

                        try:
                            comment_data['author_name'] = comment.find_element(By.CSS_SELECTOR,
                                                                               'span[class="x3nfvp2"]').text
                        except:
                            comment_data['author_name'] = None

                        try:
                            comment_data['text'] = comment.find_element(By.CSS_SELECTOR, 'div[dir="auto"]').text
                        except:
                            comment_data['text'] = None

                        try:
                            comment_date_element = comment.find_element(By.CSS_SELECTOR,
                                                                        'a[class="x1i10hfl xjbqb8w x1ejq31n x18oe1m7 x1sy0etr xstzfhl x972fbf x10w94by x1qhh985 x14e42zd x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x14z9mp xat24cr x1lziwak xexx8yu xyri2b x18d9i69 x1c1uobl x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz xkrqix3 x1sur9pj xi81zsa x1s688f"]')
                            parsed_date = parse_facebook_date(comment_date_element.text)
                            if parsed_date and hasattr(parsed_date, 'isoformat'):
                                comment_data['date'] = parsed_date.isoformat()
                            else:
                                comment_data['date'] = str(parsed_date) if parsed_date else None
                        except:
                            comment_data['date'] = None

                        if any([comment_data.get('author_name'), comment_data.get('text')]):
                            post_data['comments'].append(comment_data)
                            print(
                                f"Comment {len(post_data['comments'])}: {comment_data.get('author_name', 'Unknown')} - {(comment_data.get('text', 'No text')[:50])}...")

                    except Exception as e:
                        print(f"Comment {i + 1} xato: {str(e)[:50]}...")
                        continue

            except Exception as e:
                print(f"Comments xato: {str(e)[:30]}...")

        except Exception as e:
            print(f"target_div xato: {str(e)[:30]}...")

        try:
            title_div = modal.find_element(By.CSS_SELECTOR,
                                           'div.xdj266r.x14z9mp.xat24cr.x1lziwak.x1vvkbs.x126k92a')
            title_text = title_div.text.strip()
            if title_text and len(title_text) >= 3 and len(title_text) <= 500:
                post_data['title'] = title_text
                print(f"Title: {title_text}")
            else:
                print("Title matn topilmadi yoki noto'g'ri uzunlik")

        except Exception as e:
            print(f"Title div topilmadi: {str(e)[:30]}...")

        return post_data

    except TimeoutException:
        print("Modal topilmadi")
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
        print("Modal yopishda xato berdi:\n", str(e))