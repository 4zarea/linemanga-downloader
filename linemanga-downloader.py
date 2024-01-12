from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
import re
import base64
import shutil


def login_and_redirect(url):

    driver.get('https://manga.line.me/')

    cookie_file_path = os.path.join(os.getcwd(), 'cookie.txt') # cookieの取得

    with open(cookie_file_path, 'r') as json_open:
     cookies = json.load(json_open)

    for cookie in cookies:
        tmp = {"name": cookie["name"], "value": cookie["value"]}
        driver.add_cookie(tmp) # cookieの設定

    driver.get(url + '=page1') # cookieの設定をした後マンガの情報を取得するURLにリダイレクト


def get_manga_info(driver):
    option_info_script = """
    return {
        title: OPTION.title,
        authorName: OPTION.authorName,
        productName: OPTION.productName,
    };
    """# JavaScriptを実行してOPTIONオブジェクトの情報を取得

    manga_info = driver.execute_script(option_info_script)
    title = manga_info['title']
    author_name = manga_info['authorName']
    product_name = manga_info['productName']

    return title, author_name, product_name


def get_all_canvas(driver):
    canvas_elements = driver.find_elements(By.TAG_NAME, "canvas") # すべてのcanvasを取得

    page_class = "MangaPages_page__o8EKw"  # ページのクラスを指定して、要素を取得
    page_element = driver.find_elements(By.CLASS_NAME, page_class)
    end_page_class = "MangaPage_endGuideWrapper__HA-O_"  # なぜかendGuide(次の巻に行くかどうかの画面)が2つある場合があったので取得して数を確認する
    end_page_element = driver.find_elements(By.CLASS_NAME, end_page_class)

    total_pages = len(page_element) - len(end_page_element) # 実際のページ数を取得

    return canvas_elements, total_pages


def download_manga(driver):
    manga_folder = "manga" #デフォルトの漫画保存フォルダ
    os.makedirs(manga_folder, exist_ok=True)

    manga_product_folder = os.path.join(manga_folder, '[' + author_name + ']' + " " + product_name)
    os.makedirs(manga_product_folder, exist_ok=True) # 漫画保存フォルダに[作者] タイトルの形式でフォルダを作る

    formatted_volume = extract_volume_number(title)
    manga_title_folder = os.path.join(manga_product_folder, product_name + ' ' + '第' + formatted_volume + '巻')
    os.makedirs(manga_title_folder, exist_ok=True) # 作ったフォルダに タイトル 第00巻の形式でフォルダを作る(最終的に画像が保存される場所)

    print(title)
    for index in range(1, total_pages + 1): # 1ページ目から最後のページまでループする
            time.sleep(0.5)
            export_canvas_image(canvas_elements[total_pages - index], index, manga_title_folder)
            message = f"Downloading... {index}/{total_pages}"
            print(message, end='\r', flush=True)
            click_by_position(driver, 50, 50, canvas_elements[total_pages - index])
    print('ダウンロードが完了しました')

    if zip_after_download == True: # zip化するかどうか
        shutil.make_archive(manga_title_folder, 'zip', manga_title_folder)
        print(f"{manga_product_folder} に画像がzip化されました。")
        if delete_folder_after_zip == True:  # zip化した後にオリジナルのフォルダを消すかどうか
            shutil.rmtree(manga_title_folder)


def extract_volume_number(title): # タイトルから巻数だけ抜き出して桁数調整する
    match = re.search(r'(\d+)[^\d]*$', title)
    if match:
        volume = int(match.group(1))
        formatted_volume = f"{volume:02d}" # 3巻の場合03、12巻の場合12となる
        return formatted_volume
    else:
        formatted_volume = '01' # タイトルだけで巻数が含まれていない場合第01巻として扱う
        return formatted_volume

def export_canvas_image(canvas_element, index, folder):
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "canvas"))
    ) # キャンバスの読み込みを待機する

    canvas_data_url = driver.execute_script(
        "var canvas = arguments[0];"
        "return canvas.toDataURL('image/jpeg', 1.0).substring(23);", canvas_element
    ) # canvasをデータURLに変換
    
    filename = os.path.join(folder, f"{index}.jpg") # Base64デコードしてファイルに保存
    with open(filename, "wb") as file:
        file.write(base64.b64decode(canvas_data_url))


def click_by_position(driver, x, y , whole_page):
    from selenium.webdriver.common.action_chains import ActionChains
    actions = ActionChains(driver)

    actions.move_to_element_with_offset(whole_page, 0, 0)

    actions.move_by_offset(x, y)
    actions.click()
    actions.perform()


if __name__ == "__main__":
    chrome_options = webdriver.ChromeOptions() # Chromeのセキュリティ設定を変更
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=CrossSiteDocumentBlockingIfIsolating')
    chrome_options.add_argument('--headless')

    zip_after_download = True
    delete_folder_after_zip = True
    url = input("ダウンロードするURLを入力してください: ")
    
    driver = webdriver.Chrome(options=chrome_options)
    login_and_redirect(url)
    
    manga_info = get_manga_info(driver)
    title = manga_info[0]
    author_name = manga_info[1]
    product_name = manga_info[2]

    canvas_elements, total_pages = get_all_canvas(driver)

    download_manga(driver)

    driver.quit()
    
