from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

import datetime

app = Flask(__name__)
#CORS(app, supports_credentials=True)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lavanderia.db'
app.config['SECRET_KEY'] = '76661be67f58d95a0d538126e2353032794b561845e57b20'  # Replace with a strong secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# Define User model
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    surname = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    phone_number = db.Column(db.Text)
    address = db.Column(db.Text)
    city = db.Column(db.Text)
    state = db.Column(db.Text)
    postal_code = db.Column(db.Text)
    is_owner = db.Column(db.Boolean, default=False, nullable=False)

    # Flask-Login required methods
    def is_active(self):
        return True

    def get_id(self):
        return str(self.id)

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def to_dict(self, include_orders=False):
        user_dict = {
            'id': self.id,
            'name': self.name,
            'surname': self.surname,
            'email': self.email,
            'phone_number': self.phone_number,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'is_owner': self.is_owner
        }
        if include_orders:
            user_dict['orders'] = [order.to_dict() for order in self.orders]
        return user_dict
    
@app.route('/home')
def landing_page():
    return render_template('landing_page.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/order')
def order():
    return render_template('order.html')

@app.route('/register')
def create_account():
    return render_template('create_account.html')

# Define Order model
class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    pickup_date = db.Column(db.DateTime)
    delivery_date = db.Column(db.DateTime)
    status = db.Column(db.Text, nullable=False, default='Pending') # Allowed: Pending, Processing, Ready, Delivered, Cancelled
    total_price = db.Column(db.Float)
    items_description = db.Column(db.Text)

    user = db.relationship('User', backref=db.backref('orders', lazy=True))

    def to_dict(self, include_user=False):
        order_dict = {
            'id': self.id,
            'user_id': self.user_id,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'pickup_date': self.pickup_date.isoformat() if self.pickup_date else None,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'status': self.status,
            'total_price': self.total_price,
            'items_description': self.items_description
        }
        if include_user and self.user:
            order_dict['user'] = self.user.to_dict() # Be careful with recursion if User.to_dict includes orders
        return order_dict

@login_manager.user_loader
def load_user(user_id):
    # return db.session.get(User, int(user_id))
    print(f"\n--- DEBUG: load_user chiamato con user_id: {user_id} ---")
    user = db.session.get(User, int(user_id))
    if user:
        print(f"--- DEBUG: Utente {user.email} con ID {user.id} trovato. ---")
    else:
        print(f"--- DEBUG: Utente con ID {user_id} NON trovato nel DB. ---")
    return user

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    surname = data.get('surname')
    email = data.get('email')
    password = data.get('password')
    phone_number = data.get('phone_number')
    address = data.get('address')
    city = data.get('city')
    state = data.get('state')
    postal_code = data.get('postal_code')

    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 409

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(
        name=name,
        surname=surname,
        email=email,
        password_hash=hashed_password,
        phone_number=phone_number,
        address=address,
        city=city,
        state=state,
        postal_code=postal_code
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST','GET'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'message': 'Email and password are required'}), 400

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'message': 'Invalid email or password'}), 401

        login_user(user)
        user_data = {
            'id': user.id,
            'name': user.name,
            'surname': user.surname,
            'email': user.email,
            'phone_number': user.phone_number,
            'address': user.address,
            'city': user.city,
            'state': user.state,
            'postal_code': user.postal_code,
            'is_owner': user.is_owner
        }
        return jsonify({'message': 'Login successful', 'user': user_data}), 200
     # GET -> mostra la pagina di login
    return render_template('login.html')

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200

# Helper function to parse datetime strings
def parse_datetime(datetime_str):
    if datetime_str:
        return datetime.datetime.fromisoformat(datetime_str)
    return None

# Order Management API Endpoints
@app.route('/api/orders', methods=['GET','POST'])
@login_required
def handle_orders():
    if request.method == 'GET':
        user_orders = Order.query.filter_by(user_id=current_user.id).all()
        return jsonify([order.to_dict() for order in user_orders])
    if request.method == 'POST':
        data = request.get_json()
        items_description = data.get('items_description')
        pickup_date_str = data.get('pickup_date')
        delivery_date_str = data.get('delivery_date')
        total_price = data.get('total_price')

        if not items_description:
            return jsonify({'message': 'Items description is required'}), 400

        new_order = Order(
            user_id=current_user.id,
            items_description=items_description,
            pickup_date=parse_datetime(pickup_date_str),
            delivery_date=parse_datetime(delivery_date_str),
            total_price=total_price,
            status='Pending' # Default status
        )
    db.session.add(new_order)
    db.session.commit()
    return jsonify(new_order.to_dict()), 201

@app.route('/api/orders', methods=['GET'])
@login_required
def get_user_orders():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return jsonify([order.to_dict() for order in orders]), 200

@app.route('/api/admin/orders', methods=['GET'])
@login_required
def get_all_orders():
    if not current_user.is_owner:
        return jsonify({'message': 'Forbidden: Admins only'}), 403
    
    orders = Order.query.all()
    return jsonify([order.to_dict(include_user=True) for order in orders]), 200

@app.route('/api/admin/orders/<int:order_id>/status', methods=['PUT'])
@login_required
def update_order_status(order_id):
    if not current_user.is_owner:
        return jsonify({'message': 'Forbidden: Admins only'}), 403

    data = request.get_json()
    new_status = data.get('status')

    if not new_status:
        return jsonify({'message': 'Status is required'}), 400

    allowed_statuses = ['Pending', 'Processing', 'Ready', 'Delivered', 'Cancelled']
    if new_status not in allowed_statuses:
        return jsonify({'message': f'Invalid status. Allowed statuses are: {", ".join(allowed_statuses)}'}), 400

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({'message': 'Order not found'}), 404

    order.status = new_status
    db.session.commit()
    return jsonify(order.to_dict(include_user=True)), 200

def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_tables() # Create tables if they don't exist
    app.run(debug=True)
