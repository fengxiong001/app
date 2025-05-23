from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
import json
import datetime

app = Flask(__name__)
# IMPORTANT: Use a strong, secret key, ideally from environment variables in production
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24)) # Use env var or random

# 配置上传文件的目录
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/picture')
DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DATA_FOLDER'] = DATA_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB

# 确保上传目录和数据目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

# --- In-Memory Data Store (DEMO ONLY!) ---
# WARNING: DO NOT USE THIS IN PRODUCTION. Use a proper database.
# Structure: users = {'username': {'email': 'email@example.com', 'password_hash': 'hashed_password'}}
users = {
        }

# 基础菜单数据
# 这里使用字典类型的内存存储，存储在数据库
categories = [
    {"id": "1", "name": "热菜", "dishes": []},
    {"id": "2", "name": "冷菜", "dishes": []},
    {"id": "3", "name": "汤品", "dishes": []},
    {"id": "4", "name": "主食", "dishes": []},
    {"id": "5", "name": "点心", "dishes": []},
    {"id": "6", "name": "烧烤", "dishes": []},
    {"id": "7", "name": "炖菜", "dishes": []},
    {"id": "8", "name": "炖品", "dishes": []},
    {"id": "9", "name": "炒菜", "dishes": []},
    {"id": "10", "name": "蒸菜", "dishes": []}
]

# 预设一些示例菜品，存储在数据库
dishes = []

# 添加订单相关的数据结构
orders = {
    # 'username': [{
    #     'order_id': 'unique_id',
    #     'items': [{
    #         'dish_id': 'id',
    #         'name': 'name',
    #         'quantity': 1,
    #         'price': 10.0,
    #         'total': 10.0
    #     }],
    #     'total_amount': 10.0,
    #     'status': 'pending',  # pending, completed, cancelled
    #     'created_at': 'timestamp'
    # }]
}

# 辅助函数
def allowed_file(filename):
    """检查文件扩展名是否允许上传"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Routes ---

@app.route('/')
def index():
    """Redirects to dashboard if logged in, otherwise to login."""
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if 'username' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('用户名和密码不能为空！', 'error')
            return redirect(url_for('login'))

        user_data = users.get(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            session['username'] = username
            flash(f'欢迎回来, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误！', 'error')
            return redirect(url_for('login'))

    # For GET request
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if 'username' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # --- Basic Validation ---
        error = False
        if not username or not email or not password or not confirm_password:
            flash('所有字段都是必填的！', 'error')
            error = True
        if password != confirm_password:
            flash('两次输入的密码不一致！', 'error')
            error = True
        if len(password) < 6:
             flash('密码长度不能少于6位！', 'error')
             error = True
        if username in users:
            flash('用户名已被注册！', 'error')
            error = True
        # Add email format validation if needed

        if error:
            return redirect(url_for('register'))

        # --- Store User (Hash Password!) ---
        hashed_password = generate_password_hash(password)
        users[username] = {'email': email, 'password_hash': hashed_password, 'is_admin': False}
        
        # 保存更新后的用户数据
        save_data()
        
        flash('注册成功，请登录！', 'success')
        return redirect(url_for('login'))

    # For GET request
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    """显示仪表盘页面"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # 重新加载数据以确保显示最新状态
    load_data()
    
    username = session['username']
    is_admin = users.get(username, {}).get('is_admin', False)
    
    # 打印每个分类的菜品数量，用于调试
    for category in categories:
        print(f"分类 {category['id']} 在仪表盘显示 {len(category['dishes'])} 个菜品")
    
    return render_template('dashboard.html', 
                         username=username, 
                         is_admin=is_admin, 
                         categories=categories)

@app.route('/logout')
def logout():
    """Logs the user out."""
    session.pop('username', None)
    flash('您已成功登出。', 'info')
    return redirect(url_for('login'))

# --- API Routes for Dish Management ---

@app.route('/api/dishes/<dish_id>', methods=['GET'])
def get_dish(dish_id):
    """获取单个菜品的详细信息"""
    if 'username' not in session:
        return jsonify({'error': '未授权'}), 401
    
    # 查找菜品
    for dish in dishes:
        if dish['id'] == dish_id:
            return jsonify(dish)
    
    return jsonify({'error': '菜品不存在'}), 404

@app.route('/api/dishes/<dish_id>', methods=['POST'])
def update_dish(dish_id):
    """更新菜品信息"""
    if 'username' not in session:
        return jsonify({'error': '未授权'}), 401
    
    username = session['username']
    is_admin = users.get(username, {}).get('is_admin', False)
    if not is_admin:
        return jsonify({'error': '权限不足'}), 403
    
    # 查找菜品
    dish_to_update = None
    for dish in dishes:
        if dish['id'] == dish_id:
            dish_to_update = dish
            break
    
    if not dish_to_update:
        return jsonify({'error': '菜品不存在'}), 404
    
    # 更新菜品信息
    dish_to_update['name'] = request.form.get('name', dish_to_update['name'])
    dish_to_update['price'] = float(request.form.get('price', dish_to_update['price']))
    
    # 如果分类改变，需要把菜品移动到新分类
    new_category_id = request.form.get('category')
    if new_category_id and new_category_id != dish_to_update['category_id']:
        # 从旧分类移除
        old_category = next((c for c in categories if c['id'] == dish_to_update['category_id']), None)
        if old_category:
            old_category['dishes'] = [d for d in old_category['dishes'] if d['id'] != dish_id]
        
        # 添加到新分类
        new_category = next((c for c in categories if c['id'] == new_category_id), None)
        if new_category:
            dish_to_update['category_id'] = new_category_id
            new_category['dishes'].append(dish_to_update)
    
    # 处理图片上传
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{dish_id}.png")  # 统一使用PNG格式
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            dish_to_update['image_url'] = f"static/picture/{filename}"
    
    # 保存更新后的数据
    save_data()
    
    return jsonify({'success': True, 'message': '菜品更新成功'})

@app.route('/api/dishes/<dish_id>', methods=['DELETE'])
def delete_dish(dish_id):
    """删除菜品"""
    if 'username' not in session:
        return jsonify({'error': '未授权'}), 401
    
    username = session['username']
    is_admin = users.get(username, {}).get('is_admin', False)
    if not is_admin:
        return jsonify({'error': '权限不足'}), 403
    
    # 找到菜品并从全局列表和分类中移除
    dish_to_delete = None
    for dish in dishes:
        if dish['id'] == dish_id:
            dish_to_delete = dish
            break
    
    if not dish_to_delete:
        return jsonify({'error': '菜品不存在'}), 404
    
    # 获取菜品的图片路径
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], dish_to_delete['image_url'].replace('static/picture/', ''))
    
    # 从菜品列表移除
    dishes.remove(dish_to_delete)
    
    # 从分类中移除
    for category in categories:
        if category['id'] == dish_to_delete['category_id']:
            category['dishes'] = [d for d in category['dishes'] if d['id'] != dish_id]
            break
        
    # 删除图片文件
    if os.path.exists(image_path):
        os.remove(image_path)
    
    # 保存更新后的数据
    save_data()

    return jsonify({'success': True, 'message': '菜品删除成功'})

@app.route('/api/dishes/add', methods=['POST'])
def add_dish():
    """添加新菜品"""
    if 'username' not in session:
        return jsonify({'error': '未授权'}), 401
    
    username = session['username']
    is_admin = users.get(username, {}).get('is_admin', False)
    if not is_admin:
        return jsonify({'error': '权限不足'}), 403
    
    try:
        # 获取表单数据
        name = request.form.get('name')
        category_id = request.form.get('category')
        price = request.form.get('price')
        
        if not name or not category_id or not price:
            return jsonify({'error': '缺少必要的菜品信息'}), 400
        
        # 生成菜品ID，使用分类ID作为前缀
        dish_id = f"{category_id}{str(uuid.uuid4().int)[:3]}"
        
        # 处理图片上传
        image_url = f'static/picture/placeholder.png'  # 默认使用占位图片
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                # 生成文件名，使用菜品ID作为文件名
                filename = secure_filename(f"{dish_id}.png")  # 统一使用PNG格式
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_url = f"static/picture/{filename}"
        
        # 创建新菜品
        new_dish = {
            'id': dish_id,
            'name': name,
            'price': float(price),
            'category_id': category_id,
            'image_url': image_url
        }
        
        # 添加到全局菜品列表
        dishes.append(new_dish)
        
        # 添加到对应分类
        category_found = False
        for category in categories:
            if category['id'] == category_id:
                category['dishes'].append(new_dish)
                category_found = True
                break
        
        if not category_found:
            return jsonify({'error': '分类不存在'}), 404
        
        # 保存到文件
        save_data()
        
        # 重新加载数据以确保一致性
        load_data()
        
        return jsonify({
            'success': True, 
            'message': '菜品添加成功', 
            'dish': new_dish,
            'category': {
                'id': category_id,
                'name': next((c['name'] for c in categories if c['id'] == category_id), '')
            }
        })
    
    except Exception as e:
        return jsonify({'error': f'添加菜品失败: {str(e)}'}), 500

def save_data():
    """保存数据到文件"""
    try:
        data = {
            'dishes': dishes,
            'categories': categories,
            'users': users
        }
        data_file = os.path.join(app.config['DATA_FOLDER'], 'menu_data.json')
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        for dish in dishes:
            print(f"菜品ID: {dish['id']}, 名称: {dish['name']}")
    except Exception as e:
        print(f"保存数据失败: {str(e)}")

def load_data():
    """从文件加载数据"""
    try:
        data_file = os.path.join(app.config['DATA_FOLDER'], 'menu_data.json')
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8-sig') as f:  # 修改这里
                data = json.load(f)
                loaded_dishes = data.get('dishes', [])
                loaded_categories = data.get('categories', [])
                loaded_users = data.get('users', {})
                
                # 更新全局变量
                global dishes, categories, users
                dishes = loaded_dishes
                categories = loaded_categories
                users = loaded_users
                
                # 确保每个分类的dishes列表是最新的
                for category in categories:
                    category_dishes = [dish for dish in dishes if dish['category_id'] == category['id']]
                    category['dishes'] = category_dishes
                return dishes, categories, users
    except Exception as e:
        print(f"加载数据失败: {str(e)}")
    return [], [], {}

def init_data():
    """初始化数据"""
    # 预设菜品数据
    initial_dishes = [
        # 热菜
        {"id": "101", "name": "红烧肉", "price": 38.0, "category_id": "1", "image_url": "static/picture/101.png"},
        {"id": "102", "name": "糖醋排骨", "price": 42.0, "category_id": "1", "image_url": "static/picture/102.png"},
        {"id": "103", "name": "宫保鸡丁", "price": 35.0, "category_id": "1", "image_url": "static/picture/103.png"},
        {"id": "104", "name": "鱼香肉丝", "price": 32.0, "category_id": "1", "image_url": "static/picture/104.png"},
        {"id": "105", "name": "麻婆豆腐", "price": 28.0, "category_id": "1", "image_url": "static/picture/105.png"},
        
        # 冷菜
        {"id": "201", "name": "凉拌黄瓜", "price": 18.0, "category_id": "2", "image_url": "static/picture/201.png"},
        {"id": "202", "name": "皮蛋豆腐", "price": 22.0, "category_id": "2", "image_url": "static/picture/202.png"},
        {"id": "203", "name": "口水鸡", "price": 36.0, "category_id": "2", "image_url": "static/picture/203.png"},
        {"id": "204", "name": "夫妻肺片", "price": 38.0, "category_id": "2", "image_url": "static/picture/204.png"},
        {"id": "205", "name": "凉拌木耳", "price": 20.0, "category_id": "2", "image_url": "static/picture/205.png"},
        
        # 汤品
        {"id": "301", "name": "紫菜蛋花汤", "price": 15.0, "category_id": "3", "image_url": "static/picture/301.png"},
        {"id": "302", "name": "番茄蛋汤", "price": 16.0, "category_id": "3", "image_url": "static/picture/302.png"},
        {"id": "303", "name": "冬瓜排骨汤", "price": 28.0, "category_id": "3", "image_url": "static/picture/303.png"},
        {"id": "304", "name": "酸辣汤", "price": 18.0, "category_id": "3", "image_url": "static/picture/304.png"},
        {"id": "305", "name": "菌菇汤", "price": 25.0, "category_id": "3", "image_url": "static/picture/305.png"},
        
        # 主食
        {"id": "401", "name": "米饭", "price": 3.0, "category_id": "4", "image_url": "static/picture/401.png"},
        {"id": "402", "name": "炒饭", "price": 15.0, "category_id": "4", "image_url": "static/picture/402.png"},
        {"id": "403", "name": "面条", "price": 12.0, "category_id": "4", "image_url": "static/picture/403.png"},
        {"id": "404", "name": "饺子", "price": 20.0, "category_id": "4", "image_url": "static/picture/404.png"},
        {"id": "405", "name": "馒头", "price": 2.0, "category_id": "4", "image_url": "static/picture/405.png"},
        
        # 点心
        {"id": "501", "name": "小笼包", "price": 25.0, "category_id": "5", "image_url": "static/picture/501.png"},
        {"id": "502", "name": "烧卖", "price": 22.0, "category_id": "5", "image_url": "static/picture/502.png"},
        {"id": "503", "name": "春卷", "price": 18.0, "category_id": "5", "image_url": "static/picture/503.png"},
        {"id": "504", "name": "蛋挞", "price": 15.0, "category_id": "5", "image_url": "static/picture/504.png"},
        {"id": "505", "name": "叉烧包", "price": 20.0, "category_id": "5", "image_url": "static/picture/505.png"},
        
        # 烧烤
        {"id": "601", "name": "羊肉串", "price": 8.0, "category_id": "6", "image_url": "static/picture/601.png"},
        {"id": "602", "name": "烤鸡翅", "price": 12.0, "category_id": "6", "image_url": "static/picture/602.png"},
        {"id": "603", "name": "烤茄子", "price": 15.0, "category_id": "6", "image_url": "static/picture/603.png"},
        {"id": "604", "name": "烤鱼", "price": 45.0, "category_id": "6", "image_url": "static/picture/604.png"},
        {"id": "605", "name": "烤玉米", "price": 10.0, "category_id": "6", "image_url": "static/picture/605.png"},
        
        # 炖菜
        {"id": "701", "name": "红烧牛肉", "price": 48.0, "category_id": "7", "image_url": "static/picture/701.png"},
        {"id": "702", "name": "土豆炖鸡", "price": 38.0, "category_id": "7", "image_url": "static/picture/702.png"},
        {"id": "703", "name": "红烧排骨", "price": 42.0, "category_id": "7", "image_url": "static/picture/703.png"},
        {"id": "704", "name": "红烧鱼", "price": 45.0, "category_id": "7", "image_url": "static/picture/704.png"},
        {"id": "705", "name": "红烧茄子", "price": 25.0, "category_id": "7", "image_url": "static/picture/705.png"},
        
        # 炖品
        {"id": "801", "name": "银耳莲子羹", "price": 18.0, "category_id": "8", "image_url": "static/picture/801.png"},
        {"id": "802", "name": "冰糖雪梨", "price": 15.0, "category_id": "8", "image_url": "static/picture/802.png"},
        {"id": "803", "name": "红枣枸杞汤", "price": 20.0, "category_id": "8", "image_url": "static/picture/803.png"},
        {"id": "804", "name": "桂圆莲子汤", "price": 22.0, "category_id": "8", "image_url": "static/picture/804.png"},
        {"id": "805", "name": "百合绿豆汤", "price": 16.0, "category_id": "8", "image_url": "static/picture/805.png"},
        
        # 炒菜
        {"id": "901", "name": "青椒炒肉", "price": 28.0, "category_id": "9", "image_url": "static/picture/901.png"},
        {"id": "902", "name": "蒜蓉空心菜", "price": 18.0, "category_id": "9", "image_url": "static/picture/902.png"},
        {"id": "903", "name": "西红柿炒蛋", "price": 22.0, "category_id": "9", "image_url": "static/picture/903.png"},
        {"id": "904", "name": "干煸四季豆", "price": 20.0, "category_id": "9", "image_url": "static/picture/904.png"},
        {"id": "905", "name": "炒青菜", "price": 15.0, "category_id": "9", "image_url": "static/picture/905.png"},
        
        # 蒸菜
        {"id": "1001", "name": "清蒸鲈鱼", "price": 58.0, "category_id": "10", "image_url": "static/picture/1001.png"},
        {"id": "1002", "name": "蒸蛋", "price": 12.0, "category_id": "10", "image_url": "static/picture/1002.png"},
        {"id": "1003", "name": "蒸排骨", "price": 38.0, "category_id": "10", "image_url": "static/picture/1003.png"},
        {"id": "1004", "name": "蒸鸡", "price": 45.0, "category_id": "10", "image_url": "static/picture/1004.png"},
        {"id": "1005", "name": "蒸南瓜", "price": 15.0, "category_id": "10", "image_url": "static/picture/1005.png"}
    ]

    # 将菜品添加到对应分类
    for dish in initial_dishes:
        for category in categories:
            if dish['category_id'] == category['id']:
                category['dishes'].append(dish)
                break

    # 保存初始数据
    data = {
        'dishes': initial_dishes,
        'categories': categories,
        'users': users
    }
    data_file = os.path.join(app.config['DATA_FOLDER'], 'menu_data.json')
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return initial_dishes, categories, users

# 在应用启动时加载数据
dishes, categories, users = load_data()
if not dishes or not categories or not users:
    print("初始化数据...")  # 添加日志
    dishes, categories, users = init_data()

# --- API Routes for Order Management ---

@app.route('/api/orders', methods=['POST'])
def create_order():
    """创建新订单"""
    if 'username' not in session:
        return jsonify({'error': '未授权'}), 401
    
    username = session['username']
    order_items = request.json.get('items', [])
    
    if not order_items:
        return jsonify({'error': '订单不能为空'}), 400
    
    # 生成订单ID
    order_id = str(uuid.uuid4())
    
    # 初始化订单项目列表和总金额
    items = []
    total_amount = 0
    
    # 处理每个订单项
    for item in order_items:
        dish_id = item.get('dish_id')
        quantity = int(item.get('quantity', 1))
        
        # 查找菜品
        dish = next((d for d in dishes if d['id'] == dish_id), None)
        if not dish:
            return jsonify({'error': f'菜品 {dish_id} 不存在'}), 404
        
        # 计算项目总价
        item_total = dish['price'] * quantity
        total_amount += item_total
        
        # 添加到订单项目列表
        items.append({
            'dish_id': dish_id,
            'name': dish['name'],
            'quantity': quantity,
            'price': dish['price'],
            'total': item_total
        })
    
    # 创建新订单
    new_order = {
        'order_id': order_id,
        'items': items,
        'total_amount': total_amount,
        'status': 'pending',
        'created_at': datetime.datetime.now().isoformat()
    }
    
    # 将订单添加到用户的订单列表中
    if username not in orders:
        orders[username] = []
    orders[username].append(new_order)
    
    return jsonify({
        'success': True,
        'message': '订单创建成功',
        'order': new_order
    })

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """获取用户的所有订单"""
    if 'username' not in session:
        return jsonify({'error': '未授权'}), 401
    
    username = session['username']
    user_orders = orders.get(username, [])
    
    return jsonify({
        'success': True,
        'orders': user_orders
    })

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """获取特定订单的详细信息"""
    if 'username' not in session:
        return jsonify({'error': '未授权'}), 401
    
    username = session['username']
    user_orders = orders.get(username, [])
    
    # 查找特定订单
    order = next((o for o in user_orders if o['order_id'] == order_id), None)
    if not order:
        return jsonify({'error': '订单不存在'}), 404
    
    return jsonify({
        'success': True,
        'order': order
    })

@app.route('/api/orders/<order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    """取消订单"""
    if 'username' not in session:
        return jsonify({'error': '未授权'}), 401
    
    username = session['username']
    user_orders = orders.get(username, [])
    
    # 查找并更新订单状态
    order = next((o for o in user_orders if o['order_id'] == order_id), None)
    if not order:
        return jsonify({'error': '订单不存在'}), 404
    
    if order['status'] != 'pending':
        return jsonify({'error': '只能取消待处理的订单'}), 400
    
    order['status'] = 'cancelled'
    
    return jsonify({
        'success': True,
        'message': '订单已取消',
        'order': order
    })

@app.route('/order')
def order_page():
    """显示点单页面"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    # 加载所有菜品分类和菜品信息
    return render_template('order.html', 
                         username=username,
                         categories=categories)

@app.route('/order-complete')
def order_complete():
    """显示点单完成页面"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    user_orders = orders.get(username, [])
    
    # 确保 user_orders 是一个列表
    if not isinstance(user_orders, list):
        user_orders = []
    
    # 调试输出
    print(f"用户 {username} 的订单: {user_orders}")
    for order in user_orders:
        print(f"订单: {order}")
    
    return render_template('order_complete.html', 
                         username=username,
                         orders=user_orders)

# --- Run App ---
if __name__ == '__main__':
    # Set debug=False for production
    # host='0.0.0.0' makes it accessible on your network
    app.run(debug=True, host='127.0.0.1', port=5000)
    #app.run(debug=False, host='0.0.0.0', port=5001)  # 修改这里

def run_terminal_cmd(command="mkdir -p zself_file/myDemo1/templates zself_file/myDemo1/static/picture", is_background=False, require_user_approval=True):
    """创建必要的目录结构"""