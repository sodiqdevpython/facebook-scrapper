from selenium.common.exceptions import NoSuchElementException

def get_element_or_none(driver, by, xpath, get_text=True):
    try:
        element = driver.find_element(by, xpath)
        if get_text:
            return element.text.strip().replace('\n', '')
        return element
    except NoSuchElementException:
        return None
