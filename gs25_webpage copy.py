# app.py
from flask import Flask, render_template, request, redirect
import mysql.connector
import os

app = Flask(__name__)

# 데이터베이스 연결 정보
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2741',
    'database': 'gs25_db'
}

def get_products():
    """데이터베이스에서 GS25 상품 정보를 가져오는 함수"""
    conn = None
    cursor = None
    products = []
    
    try:
        # 데이터베이스 연결
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 한글 컬럼명 사용
        cursor.execute("""
            SELECT id, 이미지URL as image_url, 상품명 as product_name, 
                  가격 as price, 행사유형 as promotion_type, 행사분류 as event_category
            FROM gs25_products
            ORDER BY id DESC
        """)
        
        products = cursor.fetchall()
        
        # 결과 확인
        if products:
            print("첫 번째 상품 데이터:", products[0])
        
    except Exception as e:
        print(f"데이터베이스 조회 중 오류 발생: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    
    return products

@app.route('/')
def index():
    """메인 페이지 라우트"""
    products = get_products()
    return render_template('index.html', products=products)

@app.route('/products/<promotion_type>')
def products_by_promotion(promotion_type):
    """행사유형별 상품 조회 페이지"""
    conn = None
    cursor = None
    products = []
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, 이미지URL as image_url, 상품명 as product_name, 
                  가격 as price, 행사유형 as promotion_type, 행사분류 as event_category
            FROM gs25_products
            WHERE 행사유형 = %s
            ORDER BY id DESC
        """, (promotion_type,))
        
        products = cursor.fetchall()
        
    except Exception as e:
        print(f"데이터베이스 조회 중 오류 발생: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    
    return render_template('index.html', products=products, current_promotion=promotion_type)

@app.route('/category/<event_category>')
def products_by_category(event_category):
    """카테고리별 상품 조회 페이지"""
    conn = None
    cursor = None
    products = []
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, 이미지URL as image_url, 상품명 as product_name, 
                  가격 as price, 행사유형 as promotion_type, 행사분류 as event_category
            FROM gs25_products
            WHERE 행사분류 = %s
            ORDER BY id DESC
        """, (event_category,))
        
        products = cursor.fetchall()
        
    except Exception as e:
        print(f"데이터베이스 조회 중 오류 발생: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    
    return render_template('index.html', products=products, current_category=event_category)

# 검색 기능을 위한 라우트 추가
@app.route('/search')
def search():
    keyword = request.args.get('keyword', '')
    
    if not keyword:
        return redirect('/')
        
    conn = None
    cursor = None
    products = []
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, 이미지URL as image_url, 상품명 as product_name, 
                  가격 as price, 행사유형 as promotion_type, 행사분류 as event_category
            FROM gs25_products
            WHERE 상품명 LIKE %s
            ORDER BY id DESC
        """, (f'%{keyword}%',))
        
        products = cursor.fetchall()
        
    except Exception as e:
        print(f"데이터베이스 조회 중 오류 발생: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    
    return render_template('index.html', products=products, search_keyword=keyword)

# 필터링 기능을 위한 라우트 추가
@app.route('/filter')
def filter_products():
    promotion_type = request.args.get('promotion_type', '')
    category = request.args.get('category', '')
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'DESC')
    
    conn = None
    cursor = None
    products = []
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 기본 쿼리 구성
        query = """
            SELECT id, 이미지URL as image_url, 상품명 as product_name, 
                  가격 as price, 행사유형 as promotion_type, 행사분류 as event_category
            FROM gs25_products
            WHERE 1=1
        """
        params = []
        
        # 필터 조건 추가
        if promotion_type:
            query += " AND 행사유형 = %s"
            params.append(promotion_type)
            
        if category:
            query += " AND 행사분류 = %s"
            params.append(category)
        
        # 정렬 조건 추가
        valid_sort_fields = ['id', '상품명', '가격']
        valid_sort_orders = ['ASC', 'DESC']
        
        if sort_by not in valid_sort_fields:
            sort_by = 'id'
        
        if sort_order not in valid_sort_orders:
            sort_order = 'DESC'
            
        query += f" ORDER BY {sort_by} {sort_order}"
        
        cursor.execute(query, tuple(params))
        products = cursor.fetchall()
        
    except Exception as e:
        print(f"데이터베이스 조회 중 오류 발생: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    
    return render_template('index.html', products=products, 
                          current_promotion=promotion_type, 
                          current_category=category,
                          current_sort=sort_by,
                          current_order=sort_order)

if __name__ == '__main__':
    # templates 폴더가 없으면 생성
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # 템플릿 파일 생성
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GS25 상품 목록</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .product-card {
            height: 100%;
            transition: transform 0.3s;
        }
        .product-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }
        .product-img-container {
            height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .product-img {
            max-height: 100%;
            max-width: 100%;
            object-fit: contain;
        }
        .promotion-badge {
            position: absolute;
            top: 10px;
            right: 10px;
        }
        .navbar-dark {
            background-color: #00d900 !important;
        }
        .card {
            border-radius: 10px;
            border: none;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .card-title {
            font-weight: bold;
            height: 48px;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        .price {
            color: #ff6b6b;
            font-weight: bold;
            font-size: 1.2rem;
        }
        .pagination-container {
            display: flex;
            justify-content: center;
            margin-top: 2rem;
            margin-bottom: 2rem;
        }
        .filter-card {
            margin-bottom: 1.5rem;
        }
        .search-count {
            margin-bottom: 1rem;
            color: #666;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="/">
                <img src="https://www.gs25.com/gscvs/ko/images/common/logo.png" height="30" alt="GS25 Logo">
                상품 목록
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">전체상품</a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="promotionDropdown" role="button" data-bs-toggle="dropdown">
                            행사유형
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="/products/1+1">1+1</a></li>
                            <li><a class="dropdown-item" href="/products/2+1">2+1</a></li>
                            <li><a class="dropdown-item" href="/products/할인">할인</a></li>
                            <li><a class="dropdown-item" href="/products/덤증정">덤증정</a></li>
                        </ul>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="categoryDropdown" role="button" data-bs-toggle="dropdown">
                            카테고리
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="/category/음료">음료</a></li>
                            <li><a class="dropdown-item" href="/category/과자">과자</a></li>
                            <li><a class="dropdown-item" href="/category/식품">식품</a></li>
                            <li><a class="dropdown-item" href="/category/생활용품">생활용품</a></li>
                        </ul>
                    </li>
                </ul>
                <!-- 검색 폼 추가 -->
                <form class="d-flex" action="/search" method="get">
                    <input class="form-control me-2" type="search" name="keyword" placeholder="상품명 검색" 
                           value="{{ search_keyword or '' }}" aria-label="Search">
                    <button class="btn btn-outline-light" type="submit">검색</button>
                </form>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- 필터링 카드 추가 -->
        <div class="card filter-card">
            <div class="card-body">
                <h5 class="card-title mb-3">상세 필터</h5>
                <form action="/filter" method="get" class="row g-3">
                    <div class="col-md-3">
                        <label class="form-label">행사유형</label>
                        <select class="form-select" name="promotion_type">
                            <option value="">전체</option>
                            <option value="1+1" {% if current_promotion == '1+1' %}selected{% endif %}>1+1</option>
                            <option value="2+1" {% if current_promotion == '2+1' %}selected{% endif %}>2+1</option>
                            <option value="할인" {% if current_promotion == '할인' %}selected{% endif %}>할인</option>
                            <option value="덤증정" {% if current_promotion == '덤증정' %}selected{% endif %}>덤증정</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">카테고리</label>
                        <select class="form-select" name="category">
                            <option value="">전체</option>
                            <option value="음료" {% if current_category == '음료' %}selected{% endif %}>음료</option>
                            <option value="과자" {% if current_category == '과자' %}selected{% endif %}>과자</option>
                            <option value="식품" {% if current_category == '식품' %}selected{% endif %}>식품</option>
                            <option value="생활용품" {% if current_category == '생활용품' %}selected{% endif %}>생활용품</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">정렬기준</label>
                        <select class="form-select" name="sort_by">
                            <option value="id" {% if current_sort == 'id' %}selected{% endif %}>최신순</option>
                            <option value="상품명" {% if current_sort == '상품명' %}selected{% endif %}>상품명</option>
                            <option value="가격" {% if current_sort == '가격' %}selected{% endif %}>가격</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">정렬방향</label>
                        <select class="form-select" name="sort_order">
                            <option value="DESC" {% if current_order == 'DESC' %}selected{% endif %}>내림차순</option>
                            <option value="ASC" {% if current_order == 'ASC' %}selected{% endif %}>오름차순</option>
                        </select>
                    </div>
                    <div class="col-md-1 d-flex align-items-end">
                        <button type="submit" class="btn btn-primary">적용</button>
                    </div>
                </form>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col">
                <h1>GS25 상품 목록</h1>
                {% if current_promotion %}
                <h4>'{{ current_promotion }}' 행사 상품</h4>
                {% elif current_category %}
                <h4>'{{ current_category }}' 카테고리 상품</h4>
                {% elif search_keyword %}
                <h4>'{{ search_keyword }}' 검색 결과</h4>
                {% endif %}
                
                <!-- 검색 결과 수 표시 -->
                {% if products %}
                <p class="search-count">총 {{ products|length }}개의 상품</p>
                {% endif %}
            </div>
        </div>

        {% if products %}
        <div class="row row-cols-1 row-cols-md-2 row-cols-lg-4 g-4">
            {% for product in products %}
            <div class="col mb-4">
                <div class="card product-card h-100">
                    <div class="product-img-container">
                        {% if product.image_url %}
                        <img src="{{ product.image_url }}" class="product-img" alt="{{ product.product_name }}">
                        {% else %}
                        <div class="text-center p-4">이미지 없음</div>
                        {% endif %}
                    </div>
                    <div class="card-body">
                        <h5 class="card-title">{{ product.product_name }}</h5>
                        <p class="price">{{ product.price }}</p>
                        <p class="card-text">
                            <small class="text-muted">{{ product.event_category }}</small>
                        </p>
                    </div>
                    <div class="promotion-badge">
                        <span class="badge bg-primary">{{ product.promotion_type }}</span>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="alert alert-info">
            현재 표시할 상품이 없습니다.
        </div>
        {% endif %}
        
        <!-- 추후 페이지네이션 구현을 위한 공간 -->
        <div class="pagination-container">
            <nav aria-label="Page navigation">
                <ul class="pagination">
                    <li class="page-item disabled">
                        <a class="page-link" href="#" tabindex="-1" aria-disabled="true">이전</a>
                    </li>
                    <li class="page-item active"><a class="page-link" href="#">1</a></li>
                    <li class="page-item"><a class="page-link" href="#">2</a></li>
                    <li class="page-item"><a class="page-link" href="#">3</a></li>
                    <li class="page-item">
                        <a class="page-link" href="#">다음</a>
                    </li>
                </ul>
            </nav>
        </div>
    </div>

    <footer class="bg-dark text-white mt-5 py-3">
        <div class="container text-center">
            <p>&copy; 2025 GS25 상품 정보</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>""")
    
    # 웹 서버 실행
    app.run(debug=True)