import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import argparse
import logging
import re
import pandas as pd
import os

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_apartment_details(driver, url):
    driver.get(url)
    time.sleep(2)
    data = {}

    try:
        price_element = WebDriverWait(driver,2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span[itemprop="price"]'))
        )
        price_content = price_element.get_attribute("content")

        if price_content:
            data["Цена"] = int(price_content)
            logger.info(f"Найдена цена: {data['Цена']} руб.")
        else:
            data["Цена"] = None
            logger.warning("Атрибут content пустой")

    except (TimeoutException, NoSuchElementException):
        logger.warning("Элемент с ценой не найден")

    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "params__paramsList___XzY3MG")
            )
        )

        script = """
        var results = [];
        var uls = document.getElementsByClassName('params__paramsList___XzY3MG');
        for (var i = 0; i < uls.length; i++) {
            var lis = uls[i].getElementsByTagName('li');
            for (var j = 0; j < lis.length; j++) {
                var li = lis[j];
                // Получаем только видимый текст
                var text = li.innerText || li.textContent;
                // Удаляем не-breaking spaces и trim
                text = text.replace(/\\u00A0/g, ' ').trim();
                // Проверяем, не пустой ли элемент
                if (text && !/^[\\s\\xa0]*$/.test(text)) {
                    results.push(text);
                }
            }
        }
        return results;
        """

        texts = driver.execute_script(script)
        logger.info(f"Найдено {len(texts)} параметров для объявления")

        for text in texts:
            if ":" in text:
                parts = text.split(":", 1)
                param = parts[0].strip()
                value = parts[1].strip()

                if param and value:
                    data[param] = value
            else:
                logger.warning(f"Не собрана информация")

        logger.info(f"Успешно собрано {len(data)} параметров")

    except TimeoutException:
        logger.error(f"Таймаут при загрузке деталей")
    except Exception as e:
        logger.error(f"Ошибка при парсинге деталей: {str(e)}")

    data["Ссылка"] = url

    return data


def get_city_from_url(url):
    """Извлекает название города из URL"""
    pattern = r"https://www\.avito\.ru/([^/]+)/kvartiry/prodam"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return "unknown_city"


def process_city(driver, base_url, num_pages, city_name):
    """Обрабатывает один город и возвращает DataFrame"""
    all_data = []

    for page in range(1, num_pages + 1):
        page_url = f"{base_url}?p={page}"
        logger.info(f"Обработка страницы {page}/{num_pages} для города {city_name}")
        driver.get(page_url)

        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'a[data-marker="item-title"]')
                )
            )

            link_elements = driver.find_elements(
                By.CSS_SELECTOR, 'a[data-marker="item-title"]'
            )
            links = []
            for elem in link_elements:
                href = elem.get_attribute("href")
                if href and "kvartiry" in href:
                    links.append(href)

            links = list(set(links))

            logger.info(f"На странице {page} найдено {len(links)} объявлений")

            for i, link in enumerate(links, 1):
                logger.info(f"Парсинг объявления {i}/{len(links)} для города {city_name}")
                details = parse_apartment_details(driver, link)
                if details:
                    all_data.append(details)
                time.sleep(1)

            logger.info(f"Страница {page} обработана, собрано {len(links)} объявлений")

        except TimeoutException:
            logger.error(f"Таймаут при загрузке страницы {page} для города {city_name}")
            continue

    if all_data:
        df = pd.DataFrame(all_data)

        preferred_columns = ["Цена", "Ссылка"]
        other_columns = [col for col in df.columns if col not in preferred_columns]
        ordered_columns = preferred_columns + other_columns

        df = df[ordered_columns]

        return df
    else:
        logger.warning(f"Для города {city_name} данные не собраны")
        return pd.DataFrame()


def main(urls, num_pages):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--blink-settings=imagesEnabled=false")

    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)

    try:
        for url in urls:
            city_name = get_city_from_url(url)
            logger.info(f"Обработка города: {city_name}")
            
            df_city = process_city(driver, url, num_pages, city_name)
            
            if not df_city.empty:
                csv_filename = f"avito_apartments{city_name}.csv"
                df_city.to_csv(csv_filename, index=False, encoding="utf-8")
                logger.info(f"Данные для города {city_name} в {csv_filename}")
                logger.info(f"Собрано {len(df_city)} объявлений для города {city_name}")

                if "Цена" in df_city.columns:
                    successful_prices = df_city["Цена"].notna().sum()
                    logger.info(f"Успешно извлечено цен: {successful_prices} из {len(df_city)} для города {city_name}")
            else:
                logger.warning(f"Нет данных для сохранения города {city_name}")
            time.sleep(2)

    finally:
        driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Парсер квартир с Avito")
    parser.add_argument(
        "--pages", type=int, default=50, help="Количество страниц для парсинга"
    )
    args = parser.parse_args()

    urls_to_parse = [
        'https://www.avito.ru/nizhniy_novgorod/kvartiry/prodam'
    ]

    main(urls_to_parse, args.pages)