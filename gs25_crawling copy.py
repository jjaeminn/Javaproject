from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import pandas as pd
import os

class GS25EventCrawler:
    def __init__(self, url, crawl_all_pages=True, max_pages=20, wait_time=10):
        """
        GS25 행사상품 크롤러 초기화 (1+1, 2+1, 덤증정 행사 모두 크롤링)
        
        Args:
            url (str): 크롤링할 웹사이트 URL
            crawl_all_pages (bool): 모든 페이지를 크롤링할지 여부
            max_pages (int): crawl_all_pages가 False일 때 각 탭별 크롤링할 최대 페이지 수
            wait_time (int): 요소 로딩 대기 시간(초)
        """
        self.url = url
        self.crawl_all_pages = crawl_all_pages
        self.max_pages = max_pages  # crawl_all_pages가 False일 때만 사용
        self.wait_time = wait_time
        self.products = []
        self.product_names = set()  # 상품명 중복 체크를 위한 집합
        
        # 행사 탭 ID 목록 (전체 탭 제외)
        self.event_tabs = {
            "ONE_TO_ONE": "1+1 행사",
            "TWO_TO_ONE": "2+1 행사",
            "GIFT": "덤증정 행사"
        }
        
        # Chrome 옵션 설정
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 헤드리스 모드 (필요시 주석처리)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # WebDriver 초기화
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, wait_time)
    
    def start_crawling(self):
        """크롤링 시작 - 모든 행사 유형 크롤링"""
        try:
            # 웹사이트 접속
            self.driver.get(self.url)
            print(f"웹사이트 접속 완료: {self.url}")
            
            # 페이지 로딩 대기
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.myptab")))
            
            # 페이지가 완전히 로드될 때까지 추가 대기
            time.sleep(3)
            
            # 모든 행사 탭 목록 확인
            tabs_found = self.driver.find_elements(By.CSS_SELECTOR, "ul.myptab li span a")
            if not tabs_found:
                print("행사 탭 목록을 찾을 수 없습니다.")
                return []
                
            print(f"총 {len(tabs_found)}개의 행사 탭을 발견했습니다.")
            
            # 각 행사 탭별로 크롤링 진행
            for tab_id, tab_name in self.event_tabs.items():
                print(f"\n===== {tab_name} 크롤링 시작 =====")
                try:
                    self._crawl_event_tab(tab_id, tab_name)
                    # 탭 간 전환 시 페이지가 안정화될 시간 추가
                    time.sleep(3)
                except Exception as e:
                    print(f"{tab_name} 탭 크롤링 중 오류 발생: {str(e)}")
                    print(f"다음 탭으로 진행합니다.")
                    continue
            
            # 결과 저장
            self._save_results()
            
            return self.products
            
        except Exception as e:
            print(f"크롤링 중 오류 발생: {str(e)}")
            return []
            
        finally:
            # 드라이버 종료
            self.driver.quit()
    
    def _crawl_event_tab(self, tab_id, tab_name):
        """특정 행사 탭의 상품 정보 크롤링"""
        try:
            # 페이지 새로고침을 통해 초기 상태로 돌아가기
            self.driver.refresh()
            time.sleep(3)
            
            # 탭 요소 찾기 및 클릭
            tab_selector = f"a#" + tab_id
            tab_element = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, tab_selector))
            )
            
            # JavaScript로 강제 클릭 (더 안정적)
            self.driver.execute_script("arguments[0].click();", tab_element)
            print(f"{tab_name} 탭 클릭 완료")
            
            # 탭 변경 후 로딩 대기
            time.sleep(3)
            
            # 현재 활성화된 탭 확인
            tab_spans = self.driver.find_elements(By.CSS_SELECTOR, f"span.active a#" + tab_id)
            if not tab_spans:
                print(f"{tab_name} 탭이 활성화되지 않았습니다. 다시 시도합니다.")
                self.driver.execute_script("arguments[0].click();", tab_element)
                time.sleep(3)
            
            # 해당 탭의 상품 목록 표시 확인 (여러 개의 div.tblwrap 중 display: block인 것 찾기)
            tblwraps = self.driver.find_elements(By.CSS_SELECTOR, "div.tblwrap")
            visible_tblwrap = None
            
            for tblwrap in tblwraps:
                if tblwrap.value_of_css_property("display") == "block":
                    visible_tblwrap = tblwrap
                    break
            
            if not visible_tblwrap:
                print(f"{tab_name} 탭의 상품 목록이 표시되지 않았습니다. 다음 탭으로 이동합니다.")
                return
            
            print(f"{tab_name} 탭의 상품 목록 컨테이너 찾음")
            
            # 총 페이지 수 확인 (마지막 페이지 버튼이 있는 경우)
            total_pages = self.max_pages  # 기본값
            
            if self.crawl_all_pages:
                try:
                    last_page_buttons = visible_tblwrap.find_elements(By.CSS_SELECTOR, "a.next2")
                    if last_page_buttons:
                        last_page_button = last_page_buttons[0]
                        onclick_attr = last_page_button.get_attribute("onclick")
                        if onclick_attr and "movePage" in onclick_attr:
                            # "goodsPageController.movePage(80)" 같은 형식에서 숫자만 추출
                            import re
                            match = re.search(r'movePage\((\d+)\)', onclick_attr)
                            if match:
                                total_pages = int(match.group(1))
                                print(f"{tab_name} 탭의 총 페이지 수: {total_pages}페이지")
                except Exception as e:
                    print(f"총 페이지 수 확인 중 오류: {str(e)}")
                    print(f"설정된 기본값 {self.max_pages}페이지로 진행합니다.")
            
            # 현재 페이지 번호
            current_page = 1
            
            # 모든 페이지 순회
            while current_page <= total_pages:
                print(f"\n----- {tab_name}: 페이지 {current_page}/{total_pages} 크롤링 시작 -----")
                
                # 현재 페이지 크롤링
                products_on_page = self._crawl_current_page(tab_name)
                
                # 결과가 없으면 다음 탭으로 이동
                if not products_on_page:
                    print(f"{tab_name} 탭의 페이지 {current_page}에 상품이 없습니다. 다음 탭으로 이동합니다.")
                    break
                
                self._add_unique_products(products_on_page)
                print(f"{tab_name}: 페이지 {current_page}/{total_pages} 크롤링 완료 - {len(products_on_page)}개 상품 추출")
                
                # 다음 페이지로 이동
                if current_page < total_pages:
                    try:
                        # 다음 페이지 버튼 찾기 (표시된 tblwrap 내부에서)
                        next_buttons = visible_tblwrap.find_elements(By.CSS_SELECTOR, "a.next")
                        
                        if not next_buttons:
                            print("다음 페이지 버튼을 찾을 수 없습니다. 마지막 페이지로 판단합니다.")
                            break
                        
                        # JavaScript 클릭 이벤트 실행
                        self.driver.execute_script("goodsPageController.moveControl(1)")
                        print(f"다음 페이지로 이동 중...")
                        
                        # 페이지 로딩 대기
                        time.sleep(3)
                        
                        # 페이지 로드 확인
                        self.wait.until(
                            lambda driver: len(visible_tblwrap.find_elements(By.CSS_SELECTOR, "ul.prod_list li")) > 0
                        )
                        
                        current_page += 1
                    except Exception as e:
                        print(f"다음 페이지로 이동 중 오류 발생: {str(e)}")
                        print("마지막 페이지로 판단하고 이 탭의 크롤링을 종료합니다.")
                        break
                else:
                    print(f"마지막 페이지({total_pages})에 도달했습니다.")
                    break
                
        except Exception as e:
            print(f"{tab_name} 탭 크롤링 중 오류 발생: {str(e)}")
    
    def _add_unique_products(self, products_list):
        """중복되지 않은 상품만 추가"""
        for product in products_list:
            product_name = product["상품명"]
            # 이미 추가된 상품명이 아닌 경우에만 추가
            if product_name not in self.product_names:
                self.products.append(product)
                self.product_names.add(product_name)
            else:
                print(f"중복 상품 발견 - 제외: {product_name}")
    
    def _crawl_current_page(self, event_type):
        """현재 페이지의 상품 정보 추출"""
        products_on_page = []
        
        # 페이지가 완전히 로드될 때까지 기다립니다
        time.sleep(2)
        
        try:
            # 현재 보이는 div.tblwrap 찾기
            tblwraps = self.driver.find_elements(By.CSS_SELECTOR, "div.tblwrap")
            visible_tblwrap = None
            
            for tblwrap in tblwraps:
                if tblwrap.value_of_css_property("display") == "block":
                    visible_tblwrap = tblwrap
                    break
                    
            if not visible_tblwrap:
                print("현재 페이지에서 보이는 상품 목록 컨테이너를 찾을 수 없습니다.")
                return []
                
            # 보이는 컨테이너 내의 상품 목록 요소 찾기
            product_items = visible_tblwrap.find_elements(By.CSS_SELECTOR, "ul.prod_list li div.prod_box")
            
            if not product_items:
                print("현재 페이지에서 상품을 찾을 수 없습니다.")
                return []
                
            print(f"현재 페이지에서 {len(product_items)}개의 상품을 발견했습니다.")
            
            # 각 상품 정보 추출
            for item in product_items:
                try:
                    # 이미지 URL 추출
                    img_elements = item.find_elements(By.CSS_SELECTOR, "p.img img")
                    if not img_elements:
                        print("상품 이미지를 찾을 수 없습니다.")
                        continue
                        
                    img_url = img_elements[0].get_attribute("src")
                    
                    # 상품명 추출
                    name_elements = item.find_elements(By.CSS_SELECTOR, "p.tit")
                    if not name_elements:
                        print("상품명을 찾을 수 없습니다.")
                        continue
                        
                    name = name_elements[0].text.strip()
                    
                    # 가격 추출
                    price_elements = item.find_elements(By.CSS_SELECTOR, "p.price span.cost")
                    if not price_elements:
                        print(f"상품 '{name}'의 가격을 찾을 수 없습니다.")
                        continue
                        
                    price = price_elements[0].text.replace('원', '').strip()
                    
                    # 행사 유형 추출 (여러 종류의 행사 태그 확인)
                    promotion = ""
                    
                    # 1+1 행사 확인
                    one_to_one_elements = item.find_elements(By.CSS_SELECTOR, "div.flag_box.ONE_TO_ONE p.flg01 span")
                    if one_to_one_elements and len(one_to_one_elements) > 0:
                        promotion = one_to_one_elements[0].text.strip()
                    
                    # 2+1 행사 확인
                    if not promotion:
                        two_to_one_elements = item.find_elements(By.CSS_SELECTOR, "div.flag_box.TWO_TO_ONE p.flg01 span")
                        if two_to_one_elements and len(two_to_one_elements) > 0:
                            promotion = two_to_one_elements[0].text.strip()
                    
                    # 덤증정 행사 확인
                    if not promotion:
                        gift_elements = item.find_elements(By.CSS_SELECTOR, "div.flag_box.GIFT p.flg01 span")
                        if gift_elements and len(gift_elements) > 0:
                            promotion = "덤증정"
                    
                    # 행사 유형이 파악되지 않은 경우 기본 방식으로 한 번 더 시도
                    if not promotion:
                        all_span_elements = item.find_elements(By.CSS_SELECTOR, "div.flag_box p.flg01 span")
                        if all_span_elements and len(all_span_elements) > 0:
                            promotion = all_span_elements[0].text.strip()
                    
                    # 덤증정 상품 정보 추출 (있는 경우)
                    gift_info = ""
                    if "덤증정" in promotion or "덤" in promotion:
                        try:
                            dum_box = item.find_element(By.CSS_SELECTOR, "div.dum_box")
                            gift_name_element = dum_box.find_element(By.CSS_SELECTOR, "div.dum_txt p.name")
                            if gift_name_element:
                                gift_info = gift_name_element.text.strip()
                        except:
                            pass
                    
                    # 상품 정보 저장
                    product_info = {
                        "이미지URL": img_url,
                        "상품명": name,
                        "가격": price,
                        "행사유형": promotion,
                        "행사분류": event_type
                    }
                    
                    # 덤증정 상품 정보가 있으면 추가
                    if gift_info:
                        product_info["덤증정상품"] = gift_info
                    
                    products_on_page.append(product_info)
                    print(f"상품 정보 추출: {name} - {price}원 ({promotion})")
                    
                except Exception as e:
                    print(f"상품 정보 추출 중 오류: {str(e)}")
            
            return products_on_page
            
        except Exception as e:
            print(f"현재 페이지 크롤링 중 오류: {str(e)}")
            return []
    
    def _save_results(self):
        """크롤링 결과를 CSV 파일로 저장"""
        if not self.products:
            print("저장할 데이터가 없습니다.")
            return
        
        # 결과 디렉토리 생성
        output_dir = "gs25_results"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 파일명 생성 (현재 시간 포함)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(output_dir, f"GS25_행사상품_{timestamp}.csv")
        
        # DataFrame 생성 및 저장
        df = pd.DataFrame(self.products)
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"\n크롤링 결과 요약:")
        print(f"- 총 {len(self.products)}개의 상품 정보 수집 (중복 제거됨)")
        print(f"- 결과 저장 경로: {file_path}")
        
        # 행사 유형별 통계
        event_counts = df['행사분류'].value_counts().to_dict()
        for event_type, count in event_counts.items():
            print(f"- {event_type}: {count}개 상품")
        
        # 중복 제거 상태 보고
        duplicate_count = len(self.product_names) - len(self.products)
        if duplicate_count > 0:
            print(f"- {duplicate_count}개의 중복 상품이 제거되었습니다.")

    def crawl_single_event(self, event_type):
        """특정 행사 유형만 크롤링"""
        try:
            # 웹사이트 접속
            self.driver.get(self.url)
            print(f"웹사이트 접속 완료: {self.url}")
            
            # 페이지 로딩 대기
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.myptab")))
            
            # 지정된 행사 탭만 크롤링
            if event_type in self.event_tabs:
                tab_id = event_type
                tab_name = self.event_tabs[event_type]
                print(f"\n===== {tab_name} 크롤링 시작 =====")
                self._crawl_event_tab(tab_id, tab_name)
                
                # 결과 저장
                self._save_results()
                
                return self.products
            else:
                print(f"유효하지 않은 행사 유형: {event_type}")
                print(f"유효한 행사 유형: {list(self.event_tabs.keys())}")
                return []
                
        except Exception as e:
            print(f"크롤링 중 오류 발생: {str(e)}")
            return []
            
        finally:
            # 드라이버 종료
            self.driver.quit()

if __name__ == "__main__":
    # 크롤링할 웹사이트 URL
    website_url = "http://gs25.gsretail.com/gscvs/ko/products/event-goods#;"
    
    # 크롤러 객체 생성 - wait_time 증가 및 최대 페이지 조정
    crawler = GS25EventCrawler(website_url, max_pages=50, wait_time=15)
    
    # 모든 탭 크롤링
    print("모든 행사 상품 크롤링 시작...")
    products = crawler.start_crawling()
    
    # 또는 각 탭을 개별적으로 크롤링할 수 있습니다
    # print("1+1 행사 상품만 크롤링...")
    # products = crawler.crawl_single_event("ONE_TO_ONE")  # 1+1 행사만 크롤링
    
    # print("2+1 행사 상품만 크롤링...")
    # products = crawler.crawl_single_event("TWO_TO_ONE")  # 2+1 행사만 크롤링
    
    # print("덤증정 행사 상품만 크롤링...")
    # products = crawler.crawl_single_event("GIFT")  # 덤증정 행사만 크롤링
    
    # print("전체 행사 상품만 크롤링...")
    # products = crawler.crawl_single_event("TOTAL")  # 전체 행사만 크롤링
    
    print(f"\n크롤링이 완료되었습니다. 총 {len(products)}개의 상품 정보가 수집되었습니다.")
    
    # print("2+1 행사 상품만 크롤링...")
    # products = crawler.crawl_single_event("TWO_TO_ONE")  # 2+1 행사만 크롤링
    
    # print("덤증정 행사 상품만 크롤링...")
    # products = crawler.crawl_single_event("GIFT")  # 덤증정 행사만 크롤링
    
    # print("전체 행사 상품만 크롤링...")
    # products = crawler.crawl_single_event("TOTAL")  # 전체 행사만 크롤링
    
    print(f"\n크롤링이 완료되었습니다. 총 {len(products)}개의 상품 정보가 수집되었습니다.")

























import mysql.connector
from mysql.connector import Error
import pandas as pd
import os

class GS25DatabaseManager:
    def __init__(self, host="localhost", user="root", password="2741", database="gs25_db"):
        """
        GS25 행사상품 데이터베이스 관리자 초기화
        
        Args:
            host (str): MySQL 서버 호스트명
            user (str): MySQL 사용자 이름
            password (str): MySQL 비밀번호
            database (str): 사용할 데이터베이스 이름
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """데이터베이스 연결"""
        try:
            # 데이터베이스 연결
            print(f"MySQL 서버({self.host})에 연결 중...")
            self.conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            
            if self.conn.is_connected():
                print("MySQL 서버에 연결되었습니다.")
                self.cursor = self.conn.cursor()
                
                # 데이터베이스 생성 (없는 경우)
                self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                print(f"데이터베이스 {self.database} 준비 완료")
                
                # 데이터베이스 선택
                self.cursor.execute(f"USE {self.database}")
                
                # 행사 상품 테이블 생성
                self.create_tables()
                
                return True
        except Error as e:
            print(f"데이터베이스 연결 중 오류 발생: {e}")
            return False
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.cursor:
            self.cursor.close()
        if self.conn and self.conn.is_connected():
            self.conn.close()
            print("데이터베이스 연결이 종료되었습니다.")
    
    def create_tables(self):
        """필요한 테이블 생성"""
        try:
            # 행사 유형 테이블 생성
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_types (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_id VARCHAR(20) UNIQUE,
                event_name VARCHAR(50) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 행사 상품 테이블 생성
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_name VARCHAR(255) NOT NULL,
                price INT,
                image_url VARCHAR(500),
                promotion_type VARCHAR(20),
                event_type_id INT,
                gift_product VARCHAR(255),
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_product (product_name, promotion_type),
                FOREIGN KEY (event_type_id) REFERENCES event_types(id)
            )
            ''')
            
            print("필요한 테이블이 생성되었습니다.")
            
            # 기본 행사 유형 데이터 삽입
            self.seed_event_types()
            
        except Error as e:
            print(f"테이블 생성 중 오류 발생: {e}")
    
    def seed_event_types(self):
        """행사 유형 기본 데이터 삽입"""
        try:
            # 행사 유형 데이터
            event_types = [
                ('ONE_TO_ONE', '1+1 행사', '동일 상품 하나 더 증정'),
                ('TWO_TO_ONE', '2+1 행사', '동일 상품 2개 구매 시 하나 더 증정'),
                ('GIFT', '덤증정 행사', '상품 구매 시 다른 상품 증정')
            ]
            
            # 이미 데이터가 있는지 확인
            self.cursor.execute("SELECT COUNT(*) FROM event_types")
            count = self.cursor.fetchone()[0]
            
            if count == 0:
                # 데이터 삽입
                insert_query = "INSERT INTO event_types (event_id, event_name, description) VALUES (%s, %s, %s)"
                self.cursor.executemany(insert_query, event_types)
                self.conn.commit()
                print(f"{len(event_types)}개의 행사 유형 데이터가 등록되었습니다.")
            else:
                print("행사 유형 데이터가 이미 등록되어 있습니다.")
                
        except Error as e:
            print(f"행사 유형 데이터 등록 중 오류 발생: {e}")
    
    def save_products(self, products):
        """행사 상품 데이터 저장"""
        if not self.conn or not self.conn.is_connected():
            print("데이터베이스에 연결되어 있지 않습니다.")
            return 0
        
        if not products:
            print("저장할 상품 데이터가 없습니다.")
            return 0
        
        inserted_count = 0
        updated_count = 0
        
        try:
            # 행사 유형 ID 가져오기
            event_type_mapping = {}
            self.cursor.execute("SELECT id, event_id FROM event_types")
            for id, event_id in self.cursor.fetchall():
                event_type_mapping[event_id] = id
            
            # 상품 정보 저장
            for product in products:
                try:
                    # 이벤트 타입 ID 찾기
                    event_type = None
                    event_name = product.get('행사분류', '')
                    
                    if '1+1' in event_name:
                        event_type = event_type_mapping.get('ONE_TO_ONE')
                    elif '2+1' in event_name:
                        event_type = event_type_mapping.get('TWO_TO_ONE')
                    elif '덤증정' in event_name:
                        event_type = event_type_mapping.get('GIFT')
                    
                    # 가격을 숫자만 남기기
                    price_str = product.get('가격', '0')
                    price = int(''.join(filter(str.isdigit, price_str))) if price_str else 0
                    
                    # 덤증정 상품 정보
                    gift_product = product.get('덤증정상품', '')
                    
                    # 중복 확인 (같은 상품명과 행사 유형)
                    check_query = """
                    SELECT id FROM event_products 
                    WHERE product_name = %s AND promotion_type = %s
                    """
                    self.cursor.execute(check_query, (product.get('상품명', ''), product.get('행사유형', '')))
                    existing_id = self.cursor.fetchone()
                    
                    if existing_id:
                        # 이미 존재하는 상품 업데이트
                        update_query = """
                        UPDATE event_products SET 
                          price = %s,
                          image_url = %s,
                          event_type_id = %s,
                          gift_product = %s,
                          updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """
                        self.cursor.execute(update_query, (
                            price,
                            product.get('이미지URL', ''),
                            event_type,
                            gift_product,
                            existing_id[0]
                        ))
                        updated_count += 1
                    else:
                        # 새 상품 등록
                        insert_query = """
                        INSERT INTO event_products 
                        (product_name, price, image_url, promotion_type, event_type_id, gift_product)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        self.cursor.execute(insert_query, (
                            product.get('상품명', ''),
                            price,
                            product.get('이미지URL', ''),
                            product.get('행사유형', ''),
                            event_type,
                            gift_product
                        ))
                        inserted_count += 1
                        
                except Error as e:
                    print(f"상품 '{product.get('상품명', '')}' 저장 중 오류 발생: {e}")
            
            # 변경사항 저장
            self.conn.commit()
            print(f"\n데이터베이스 저장 완료: 새로 추가된 상품 {inserted_count}개, 업데이트된 상품 {updated_count}개")
            
        except Error as e:
            print(f"상품 데이터 저장 중 오류 발생: {e}")
            return 0
        
        return inserted_count + updated_count
    
    def load_products_from_csv(self, csv_file):
        """CSV 파일에서 상품 정보 로드 후 DB에 저장"""
        try:
            if not os.path.exists(csv_file):
                print(f"파일을 찾을 수 없습니다: {csv_file}")
                return 0
                
            # CSV 파일 읽기
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            print(f"CSV 파일 '{csv_file}'에서 {len(df)}개의 상품 정보를 로드했습니다.")
            
            # DataFrame을 리스트로 변환
            products = df.to_dict('records')
            
            # DB에 저장
            return self.save_products(products)
            
        except Exception as e:
            print(f"CSV 파일 로드 중 오류 발생: {e}")
            return 0
    
    def get_product_count(self):
        """DB에 저장된 상품 수 확인"""
        try:
            if not self.conn or not self.conn.is_connected():
                print("데이터베이스에 연결되어 있지 않습니다.")
                return 0
                
            self.cursor.execute("SELECT COUNT(*) FROM event_products")
            count = self.cursor.fetchone()[0]
            return count
            
        except Error as e:
            print(f"상품 수 확인 중 오류 발생: {e}")
            return 0
    
    def get_event_type_stats(self):
        """행사 유형별 상품 통계"""
        try:
            if not self.conn or not self.conn.is_connected():
                print("데이터베이스에 연결되어 있지 않습니다.")
                return {}
                
            query = """
            SELECT et.event_name, COUNT(ep.id) as product_count
            FROM event_types et
            LEFT JOIN event_products ep ON et.id = ep.event_type_id
            GROUP BY et.id, et.event_name
            """
            self.cursor.execute(query)
            
            stats = {}
            for event_name, count in self.cursor.fetchall():
                stats[event_name] = count
                
            return stats
            
        except Error as e:
            print(f"행사 유형별 통계 확인 중 오류 발생: {e}")
            return {}