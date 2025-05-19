from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_login import UserMixin, login_user, login_required, logout_user, LoginManager, current_user
import os
import pandas as pd
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import openpyxl
from io import BytesIO

def generate_unique_code():
    while True:
        code = 'DN-' + ''.join(random.choices(string.digits, k=9))
        if not Customer.query.filter_by(cccd=code).first():
            return code

CV_CODES = [
    "CV01 - KHÁNH", "CV02 - X.Thủy", "CV03 - Ngọc Anh", "CV04 - Nhật Linh",
    "CV05 - Hoàng Biên", "CV06 - Hải", "CV07 - Hoàng Trang", "CV08 - Ly",
    "CV09 - Tiến Cường", "CV010 - Hoàng Thân", "CV011 - Trang(Teamlinh)", 
    "CV12 - Quảng Ninh1", "CV013 - Quảng Ninh2"
]

admin_emails = {
    'khanhlb@meddental.vn',
}

def is_admin():
    return current_user.is_authenticated and current_user.email in admin_emails

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://neondb_owner:npg_KcInu5GkdZ1S@ep-delicate-queen-a1ffwyhq-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xls', 'xlsx'}
app.config['SECRET_KEY'] = 'mysecretkey'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<User {self.email}>'

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    cccd = db.Column(db.String(20), nullable=False)
    dob = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(100), nullable=False)
    program = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.String(200), nullable=True)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    treatment_plans = db.Column(db.String(500), nullable=True)
    appointment_schedules = db.Column(db.String(500), nullable=True)
    revenues = db.Column(db.String(500), nullable=True)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/download_customers', methods=['GET'])
@login_required
def download_customers():
    search_query = request.args.get('search', '', type=str)
    if search_query:
        customers = Customer.query.filter(Customer.phone.like(f'%{search_query}%')).all()
    else:
        customers = Customer.query.all()

    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "Danh Sách Khách Hàng"

    columns = ['Họ Tên', 'SĐT', 'Địa Chỉ', 'Gắn Mã CV', 'CT Áp Dụng', 'Ngày Sinh', 'Mã KH', 'Tình Trạng', 'Ghi Chú']
    sheet.append(columns)

    for customer in customers:
        row = [
            customer.name,
            customer.phone,
            customer.address,
            customer.role,
            customer.status,
            customer.dob,
            customer.cccd,
            customer.program,
            customer.notes
        ]
        sheet.append(row)

    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)
    return send_file(file_stream, as_attachment=True, download_name="customers.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials, try again.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not email.endswith('@meddental.vn'):
            flash('Bạn Không Phải Nhân Viên Meddental!!!!', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email đã được đăng ký, vui lòng chọn email khác!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        user = User(email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        flash('Tài khoản đã được tạo thành công!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        employee_id = request.form['employee_id']

        user = User.query.filter_by(email=email).first()
        if user and user.email == email:
            flash('Đặt lại mật khẩu thành công. Kiểm tra email để nhận hướng dẫn!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email hoặc mã nhân viên không đúng!', 'danger')
            return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']

        user = current_user
        if check_password_hash(user.password, current_password):
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            db.session.commit()
            flash('Mật khẩu đã được thay đổi thành công!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Mật khẩu hiện tại không đúng!', 'danger')

    return render_template('change_password.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    search_query = request.args.get('search', '', type=str)
    page = request.args.get('page', 1, type=int)
    if search_query:
        customers = Customer.query.filter(Customer.phone.like(f'%{search_query}%')).paginate(page=page, per_page=20)
    else:
        customers = Customer.query.order_by(Customer.date_added.desc()).paginate(page=page, per_page=20)
    return render_template('index.html', customers=customers, cv_codes=CV_CODES, datetime=datetime, admin_emails=admin_emails)

@app.route('/add_customer', methods=['POST'])
@login_required
def add_customer():
    form_data = {
        'name': request.form['name'],
        'phone': request.form['phone'],
        'address': request.form['address'],
        'dob': request.form['dob'],
        'cccd': generate_unique_code(),
        'role': request.form['cv_code'],
        'status': request.form['status'],
        'program': request.form['program'],
        'notes': request.form['notes']
    }

    new_customer = Customer(
        name=form_data['name'],
        address=form_data['address'],
        phone=form_data['phone'],
        cccd=form_data['cccd'],
        dob=form_data['dob'],
        role=form_data['role'],
        status=form_data['status'],
        program=form_data['program'],
        notes=form_data['notes']
    )
    db.session.add(new_customer)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    # MỞ KHÓA CHO TẤT CẢ USER ĐĂNG NHẬP ĐƯỢC CHỈNH SỬA
    customer = Customer.query.get_or_404(customer_id)
    treatment_plans = customer.treatment_plans.split(',') if customer.treatment_plans else []
    appointment_schedules = customer.appointment_schedules.split(',') if customer.appointment_schedules else []
    revenues = customer.revenues.split(',') if customer.revenues else []

    if request.method == 'POST':
        customer.name = request.form['name']
        customer.address = request.form['address']
        customer.phone = request.form['phone']
        customer.cccd = request.form['cccd']
        customer.dob = request.form['dob']
        customer.role = request.form['role']
        customer.status = request.form['status']
        customer.program = request.form['program']
        customer.notes = request.form['notes']

        customer.treatment_plans = ",".join(request.form.getlist('treatment_plan'))
        customer.appointment_schedules = ",".join(request.form.getlist('appointment_schedule'))
        customer.revenues = ",".join(request.form.getlist('revenue'))

        db.session.commit()
        return redirect(url_for('home'))

    return render_template('edit_customer.html', customer=customer,
                           treatment_plans=treatment_plans,
                           appointment_schedules=appointment_schedules,
                           revenues=revenues)

@app.route('/customer/<int:customer_id>')
@login_required
def view_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    treatment_plans = customer.treatment_plans.split(',') if customer.treatment_plans else []
    appointment_schedules = customer.appointment_schedules.split(',') if customer.appointment_schedules else []
    revenues = customer.revenues.split(',') if customer.revenues else []
    return render_template('customer_detail.html', customer=customer,
                           treatment_plans=treatment_plans,
                           appointment_schedules=appointment_schedules,
                           revenues=revenues)

@app.route('/delete_customer/<int:customer_id>')
@login_required
def delete_customer(customer_id):
    if not is_admin():
        flash('Bạn không có quyền xóa khách hàng!', 'danger')
        return redirect(url_for('home'))

    customer = Customer.query.get_or_404(customer_id)
    now = datetime.utcnow()
    # Nếu là admin (email trong admin_emails) thì không giới hạn thời gian xóa
if not is_admin():
    if (now - customer.date_added) > timedelta(hours=24):
        flash('Không thể xóa khách hàng sau 24 giờ', 'warning')
        return redirect(url_for('home'))

    db.session.delete(customer)
    db.session.commit()
    flash('Khách hàng đã bị xóa', 'success')
    return redirect(url_for('home'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if not is_admin():
        flash('Bạn không có quyền upload file!', 'danger')
        return redirect(url_for('home'))

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Không có file để upload', 'danger')
            return redirect(url_for('upload_file'))

        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            df = pd.read_excel(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            for index, row in df.iterrows():
                customer = Customer(
                    name=row['Họ Tên'],
                    address=row['Địa Chỉ'],
                    phone=row['SĐT'],
                    cccd=generate_unique_code(),
                    dob=row['Ngày Sinh'],
                    role=row['CV Quản Lý'],
                    status=row['Tình Trạng'],
                    program=row['CT Áp Dụng'] if 'CT Áp Dụng' in df.columns else 'Chưa có thông tin',
                    notes=row['Ghi Chú'],
                    treatment_plans=row['Lộ Trình Chữa Bệnh'],
                    appointment_schedules=row['Lịch Hẹn'],
                    revenues=row['Doanh Thu']
                )
                db.session.add(customer)
            db.session.commit()
            customers = Customer.query.all()
            return render_template('upload.html', customers=customers)

    return render_template('upload.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
