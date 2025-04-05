import pandas as pd
import mysql.connector
from mysql.connector import Error

def csv_to_mysql(csv_file, host='localhost', user='root', password='', database='gs25_db'):
    conn = None
    cursor = None
    
    try:
        # CSV 파일 읽기
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        print(f"CSV 파일에서 {len(df)}개 상품 정보를 읽었습니다.")
        
        # MySQL 연결
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password
        )
        
        if conn.is_connected():
            cursor = conn.cursor()
            
            # 데이터베이스 생성 (없는 경우)
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
            cursor.execute(f"USE {database}")
            print(f"데이터베이스 '{database}'에 연결되었습니다.")
            
            # 기존 테이블 삭제 (필요한 경우)
            # cursor.execute("DROP TABLE IF EXISTS event_products")
            # print("기존 테이블 삭제 완료")
            
            # 테이블 생성 - 컬럼 이름을 CSV와 정확히 일치시킴
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS gs25_products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                이미지URL VARCHAR(500),
                상품명 VARCHAR(255) NOT NULL,
                가격 VARCHAR(50),
                행사유형 VARCHAR(50),
                행사분류 VARCHAR(50)
            )
            ''')
            print("테이블 생성 완료")
            
            # 데이터 삽입
            for _, row in df.iterrows():
                insert_query = """
                INSERT INTO gs25_products 
                (이미지URL, 상품명, 가격, 행사유형, 행사분류)
                VALUES (%s, %s, %s, %s, %s)
                """
                
                cursor.execute(insert_query, (
                    row['이미지URL'],
                    row['상품명'],
                    row['가격'],
                    row['행사유형'],
                    row['행사분류']
                ))
            
            # 변경사항 저장
            conn.commit()
            print(f"총 {len(df)}개의 상품 정보가 데이터베이스에 성공적으로 저장되었습니다.")
            
    except Error as e:
        print(f"MySQL 오류 발생: {e}")
        # 에러 세부 정보 출력
        if e.errno:
            print(f"에러 코드: {e.errno}")
        if hasattr(e, 'sqlstate'):
            print(f"SQL 상태: {e.sqlstate}")
        if hasattr(e, 'msg'):
            print(f"에러 메시지: {e.msg}")
    except Exception as e:
        print(f"일반 오류 발생: {e}")
        
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("MySQL 연결이 종료되었습니다.")

# 사용 예
csv_to_mysql(
    csv_file=r"",# 올릴 파일 경로 놓기 
    user="root", 
    password="",  # 실제 비밀번호로 변경
    database="gs25_db"
)