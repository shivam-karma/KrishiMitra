import os
import requests
import random
import math
import pickle
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from model import get_disease_info, predict_disease_and_generate_gradcam
from werkzeug.utils import secure_filename
from groq import Groq
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///krishimitra.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ── Models ───────────────────────────────────────────────────────────────────
class User(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    phone         = db.Column(db.String(20), unique=True, nullable=False)
    name          = db.Column(db.String(100), nullable=True)
    role          = db.Column(db.String(20), nullable=False, default='Farmer')
    location      = db.Column(db.String(100), nullable=True)
    primary_crops = db.Column(db.String(200), nullable=True)
    otp           = db.Column(db.String(6), nullable=True)
    balance       = db.Column(db.Float, nullable=False, default=0.0)
    is_registered = db.Column(db.Boolean, default=False)  # True after signup completed
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    amount      = db.Column(db.Float, nullable=False)  # positive=income, negative=expense
    category    = db.Column(db.String(50), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class Listing(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    farmer_name  = db.Column(db.String(100), nullable=False)
    crop         = db.Column(db.String(100), nullable=False)
    qty          = db.Column(db.String(50), nullable=False)
    price        = db.Column(db.String(50), nullable=False)
    location     = db.Column(db.String(100), nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class CalendarTask(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    crop        = db.Column(db.String(100), nullable=False)
    task_title  = db.Column(db.String(200), nullable=False)
    task_date   = db.Column(db.String(50), nullable=False)

class Purchase(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    listing_id   = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    buyer_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    farmer_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    crop         = db.Column(db.String(100), nullable=False)
    qty          = db.Column(db.String(50), nullable=False)
    price        = db.Column(db.String(50), nullable=False)
    status       = db.Column(db.String(20), default='pending')  # pending/confirmed/completed
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    purchase_id  = db.Column(db.Integer, db.ForeignKey('purchase.id'), nullable=False)
    sender_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_name  = db.Column(db.String(100), nullable=False)
    text         = db.Column(db.Text, nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class EcommerceOrder(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items         = db.Column(db.Text, nullable=False) # JSON representation
    total         = db.Column(db.Float, nullable=False)
    address       = db.Column(db.String(255), nullable=False)
    status        = db.Column(db.String(50), default='Processing')
    delivery_date = db.Column(db.DateTime, nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()
    # ── Inline migration: add new columns if they don't exist yet ──────────────
    import sqlite3 as _sqlite3
    _db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'instance', 'krishimitra.db')
    _migrations = [
        # ── user table ──────────────────────────────────────────────────────
        "ALTER TABLE user ADD COLUMN name VARCHAR(100)",
        "ALTER TABLE user ADD COLUMN location VARCHAR(100)",
        "ALTER TABLE user ADD COLUMN primary_crops VARCHAR(200)",
        "ALTER TABLE user ADD COLUMN balance REAL NOT NULL DEFAULT 0.0",
        "ALTER TABLE user ADD COLUMN is_registered BOOLEAN DEFAULT 0",
        "ALTER TABLE user ADD COLUMN created_at DATETIME",
        # ── listing table ───────────────────────────────────────────────────
        "ALTER TABLE listing ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE listing ADD COLUMN farmer_name VARCHAR(100)",
        "ALTER TABLE listing ADD COLUMN qty VARCHAR(50)",
        "ALTER TABLE listing ADD COLUMN price VARCHAR(50)",
        "ALTER TABLE listing ADD COLUMN location VARCHAR(100)",
        # ── purchase table ──────────────────────────────────────────────────
        "ALTER TABLE purchase ADD COLUMN status VARCHAR(20) DEFAULT 'pending'",
        # ── message table ───────────────────────────────────────────────────
        "ALTER TABLE message ADD COLUMN sender_name VARCHAR(100)",
    ]
    try:
        _conn = _sqlite3.connect(_db_path)
        for _stmt in _migrations:
            try:
                _conn.execute(_stmt)
                _conn.commit()
                print(f"Migration applied: {_stmt[:50]}")
            except _sqlite3.OperationalError:
                pass  # Column already exists — safe to skip
        _conn.close()
    except Exception as _e:
        print(f"Migration warning: {_e}")


GROQ_API_KEY        = os.getenv('GROQ_API_KEY', '')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')
MANDI_API_KEY       = os.getenv('MANDI_API_KEY', '')

client = Groq(api_key=GROQ_API_KEY)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ── Load Soil Model ─────────────────────────────────────────────────────────────────
_SOIL_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soil_model.pkl')
_soil_model = None
if os.path.exists(_SOIL_MODEL_PATH):
    try:
        with open(_SOIL_MODEL_PATH, 'rb') as _f:
            _soil_model = pickle.load(_f)
        print(f"Soil model loaded: {len(_soil_model['train_data'])} training samples, "
              f"{len(_soil_model['classes'])} crops, accuracy={_soil_model['accuracy']}%")
    except Exception as _e:
        print(f"Soil model load warning: {_e}")
else:
    print("soil_model.pkl not found. Run train_soil_model.py first.")

def _soil_knn_predict(n, p, k, ph, moisture):
    """Pure-Python KNN prediction using the loaded soil model."""
    if _soil_model is None:
        return None, 0.0, []
    means  = _soil_model['means']
    stds   = _soil_model['stds']
    kval   = _soil_model['k']
    data   = _soil_model['train_data']
    n_feat = _soil_model['n_feat']
    xraw   = [n, p, k, ph, moisture]
    xn     = [(xraw[i] - means[i]) / stds[i] for i in range(n_feat)]

    dists = []
    for r in data:
        d = math.sqrt(sum((xn[i] - r['xn'][i]) ** 2 for i in range(n_feat)))
        dists.append((d, r['y']))
    dists.sort(key=lambda x: x[0])
    top_k = dists[:kval]

    votes = {}
    for _, label in top_k:
        votes[label] = votes.get(label, 0) + 1
    best = max(votes, key=votes.get)
    conf = round(votes[best] / kval * 100, 1)
    ranked = sorted(votes.items(), key=lambda x: -x[1])
    alternatives = [c for c, _ in ranked if c != best][:3]
    return best, conf, alternatives


# ── Auth ─────────────────────────────────────────────────────────────────────
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/auth/send-otp', methods=['POST'])
def send_otp():
    data  = request.json
    phone = data.get('phone')
    role  = data.get('role', 'Farmer')
    if not phone:
        return jsonify({'error': 'Phone required'}), 400

    user = User.query.filter_by(phone=phone).first()
    is_new = user is None
    if is_new:
        user = User(phone=phone, role=role, balance=0.0, is_registered=False)
        db.session.add(user)
    else:
        user.role = role

    otp = str(random.randint(100000, 999999))
    user.otp = otp
    db.session.commit()
    print(f'OTP for {phone}: {otp}')

    # Send Actual SMS API Logic (Fast2SMS for Indian numbers)
    # import requests
    # try:
    #     # Note: You MUST provide your own API key below for SMS to deliver correctly in India!
    #     FAST2SMS_API_KEY = 'hGATXMoCHlSm5k9ID41BNtKZn8OeJ2bQFYyjVaqEgdU3sL06zRyoBUsWZwRC48vlpuEkrM2TegcY3SaN'
    #     
    #     # Fast2SMS requires just the 10-digit number
    #     indian_number = phone[-10:] 
    #     
    #     url = "https://www.fast2sms.com/dev/bulkV2"
    #     querystring = {
    #         "authorization": FAST2SMS_API_KEY,
    #         "variables_values": otp,
    #         "route": "otp",
    #         "numbers": indian_number
    #     }
    #     headers = {'cache-control': "no-cache"}
    #     # resp = requests.request("GET", url, headers=headers, params=querystring, timeout=3)
    #     # print("Fast2SMS API Response:", resp.text)
    # except Exception as e:
    #     print("Failed to send Actual SMS:", e)

    return jsonify({'message': 'OTP sent via SMS', 'otp': otp, 'is_new_user': is_new})

@app.route('/auth/verify-otp', methods=['POST'])
def verify_otp():
    data  = request.json
    phone = data.get('phone')
    otp   = data.get('otp')

    user = User.query.filter_by(phone=phone).first()
    if not user or user.otp != otp:
        return jsonify({'error': 'Invalid OTP'}), 401

    user.otp = None
    db.session.commit()
    return jsonify({
        'message':       'Verified',
        'user_id':       user.id,
        'role':          user.role,
        'is_registered': user.is_registered,
        'name':          user.name or '',
        'balance':       user.balance,
    })

@app.route('/auth/firebase-verify', methods=['POST'])
def firebase_verify():
    """
    Called by the Flutter app AFTER Firebase Phone Auth has verified the
    user's phone number on the client. We trust the verification, create
    the user record if new, and return the user session data.
    No OTP validation happens here — Firebase already did it.
    """
    data  = request.json
    phone = data.get('phone')
    role  = data.get('role', 'Farmer')
    if not phone:
        return jsonify({'error': 'Phone required'}), 400

    user   = User.query.filter_by(phone=phone).first()
    is_new = user is None
    if is_new:
        user = User(phone=phone, role=role, balance=0.0, is_registered=False)
        db.session.add(user)
    else:
        # Update role only if user is NOT yet fully registered
        # (lets them correct a wrong role selection before completing signup)
        if not user.is_registered:
            user.role = role
    db.session.commit()

    return jsonify({
        'message':       'Firebase-verified',
        'user_id':       user.id,
        'role':          user.role,
        'is_registered': user.is_registered,
        'name':          user.name or '',
        'balance':       user.balance,
        'is_new':        is_new,
    })

@app.route('/auth/register', methods=['POST'])
def register():
    """Complete profile after first OTP verification."""
    data    = request.json
    user_id = data.get('user_id')
    user    = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.name          = data.get('name', '')
    user.location      = data.get('location', '')
    user.primary_crops = data.get('primary_crops', '')
    user.role          = data.get('role', user.role)
    user.balance       = 0.0
    user.is_registered = True
    db.session.commit()
    return jsonify({'message': 'Registered', 'user_id': user.id, 'role': user.role, 'balance': user.balance})

@app.route('/auth/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id':            user.id,
        'phone':         user.phone,
        'name':          user.name or '',
        'role':          user.role,
        'location':      user.location or '',
        'primary_crops': user.primary_crops or '',
        'balance':       user.balance,
        'created_at':    user.created_at.isoformat() if user.created_at else '',
    })

@app.route('/auth/profile/<int:user_id>', methods=['PUT'])
def update_profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Not found'}), 404
        
    data = request.json
    if 'name' in data:
        user.name = data['name']
    if 'location' in data:
        user.location = data['location']
    if 'primary_crops' in data:
        user.primary_crops = data['primary_crops']
        
    db.session.commit()
    return jsonify({'message': 'Profile updated'})

# ── Finance ──────────────────────────────────────────────────────────────────
@app.route('/finance/<int:user_id>', methods=['GET'])
def get_finance(user_id):
    user    = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Not found'}), 404
    txns    = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).limit(20).all()
    income  = sum(t.amount for t in txns if t.amount > 0)
    expense = abs(sum(t.amount for t in txns if t.amount < 0))
    return jsonify({
        'balance':      user.balance,
        'income':       income,
        'expense':      expense,
        'profit':       income - expense,
        'transactions': [{'id': t.id, 'title': t.title, 'amount': t.amount,
                           'category': t.category,
                           'date': t.created_at.strftime('%b %d, %Y')} for t in txns],
    })

@app.route('/finance/<int:user_id>/transaction', methods=['POST'])
def add_transaction(user_id):
    user  = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Not found'}), 404
    data  = request.json
    amount = float(data.get('amount', 0))
    txn   = Transaction(user_id=user_id, title=data['title'], amount=amount,
                        category=data.get('category', 'Other'))
    user.balance += amount
    db.session.add(txn)
    db.session.commit()
    return jsonify({'message': 'Added', 'balance': user.balance})

# ── eCommerce (Agriculture Products Discovery Engine) ──────────────────────────
@app.route('/ecommerce/search', methods=['GET'])
def ecommerce_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
        
    lower_q = query.lower()
    title_q = query.title()

    products = [
        {'id': 1, 'name': f'{title_q} - Premium Quality Pack', 'price': '₹450', 'source': 'Amazon India', 'url': f'https://www.amazon.in/s?k={lower_q}+agriculture', 'category': 'General'},
        {'id': 2, 'name': f'Bulk {title_q} Wholesale', 'price': '₹850', 'source': 'IndiaMART', 'url': f'https://dir.indiamart.com/search.mp?ss={lower_q}', 'category': 'Wholesale'},
        {'id': 3, 'name': f'Organic {title_q} Variety', 'price': '₹320', 'source': 'Ugaoo Agri', 'url': f'https://www.ugaoo.com/search?q={lower_q}', 'category': 'Organic'},
        {'id': 4, 'name': f'{title_q} (Fast Delivery)', 'price': '₹550', 'source': 'Flipkart', 'url': f'https://www.flipkart.com/search?q={lower_q}', 'category': 'Retail'},
        {'id': 5, 'name': f'Agri-Grade Certified {title_q}', 'price': '₹1200', 'source': 'BigHaat', 'url': f'https://www.bighaat.com/search?q={lower_q}', 'category': 'Professional'},
        {'id': 6, 'name': f'Govt Subsidized {title_q}', 'price': '₹250', 'source': 'IFFCO eBazar', 'url': f'https://www.iffcoebazar.in/en/search?q={lower_q}', 'category': 'Subsidized'},
    ]
    return jsonify(products)

# ── Listings (P2P Marketplace) ────────────────────────────────────────────────
@app.route('/listings', methods=['GET', 'POST'])
def listings_handler():
    if request.method == 'GET':
        all_listings = Listing.query.order_by(Listing.created_at.desc()).all()
        return jsonify([{
            'id':         L.id,
            'user_id':    L.user_id,
            'farmer':     L.farmer_name,
            'crop':       L.crop,
            'qty':        L.qty,
            'price':      L.price,
            'location':   L.location,
            'created_at': L.created_at.strftime('%b %d, %Y') if L.created_at else '',
        } for L in all_listings])

    if request.method == 'POST':
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({'error': 'Invalid JSON body'}), 400
        try:
            L = Listing(
                user_id     = data.get('user_id', 1),
                farmer_name = data.get('farmer_name', 'Unknown'),
                crop        = data.get('crop', ''),
                qty         = data.get('qty', ''),
                price       = data.get('price', ''),
                location    = data.get('location', ''),
            )
            db.session.add(L)
            db.session.commit()
            return jsonify({'message': 'Listing created', 'id': L.id}), 200
        except Exception as e:
            db.session.rollback()
            print(f'Listing creation error: {e}')
            return jsonify({'error': str(e)}), 500

@app.route('/listings/<int:listing_id>', methods=['DELETE'])
def delete_listing(listing_id):
    L = db.session.get(Listing, listing_id)
    if not L:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(L)
    db.session.commit()
    return jsonify({'message': 'Deleted'})

# ── Purchase (Buy Now) ────────────────────────────────────────────────────────
@app.route('/purchase', methods=['POST'])
def create_purchase():
    """Buyer places a purchase request for a listing."""
    data       = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON body'}), 400
    try:
        listing_id = data.get('listing_id')
        buyer_id   = data.get('buyer_id')
        listing    = db.session.get(Listing, listing_id)
        buyer      = db.session.get(User, buyer_id)

        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        if not buyer:
            return jsonify({'error': 'Buyer not found'}), 404

        farmer = db.session.get(User, listing.user_id)

        purchase = Purchase(
            listing_id = listing_id,
            buyer_id   = buyer_id,
            farmer_id  = listing.user_id,
            crop       = listing.crop,
            qty        = listing.qty,
            price      = listing.price,
            status     = 'pending',
        )
        db.session.add(purchase)

        # Auto-send a greeting message from the buyer
        greeting = Message(
            purchase_id = 0,  # will update after flush
            sender_id   = buyer_id,
            sender_name = buyer.name or 'Buyer',
            text        = f"Hi! I'm interested in buying {listing.crop} ({listing.qty}) listed at {listing.price}. Is it still available?",
        )
        db.session.flush()  # get purchase.id without committing
        greeting.purchase_id = purchase.id
        db.session.add(greeting)
        db.session.commit()

        return jsonify({
            'message':     'Purchase request sent',
            'purchase_id': purchase.id,
            'farmer_name': farmer.name if farmer else 'Farmer',
            'farmer_id':   listing.user_id,
            'crop':        listing.crop,
            'qty':         listing.qty,
            'price':       listing.price,
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f'Purchase error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/purchase/buyer/<int:buyer_id>', methods=['GET'])
def get_buyer_purchases(buyer_id):
    """Get all purchases made by a buyer."""
    purchases = Purchase.query.filter_by(buyer_id=buyer_id).order_by(Purchase.created_at.desc()).all()
    result = []
    for p in purchases:
        farmer = db.session.get(User, p.farmer_id)
        result.append({
            'id':          p.id,
            'crop':        p.crop,
            'qty':         p.qty,
            'price':       p.price,
            'status':      p.status,
            'farmer_name': farmer.name if farmer else 'Farmer',
            'farmer_id':   p.farmer_id,
            'created_at':  p.created_at.strftime('%b %d, %Y'),
        })
    return jsonify(result)

@app.route('/purchase/farmer/<int:farmer_id>', methods=['GET'])
def get_farmer_purchases(farmer_id):
    """Get all purchase requests received by a farmer."""
    purchases = Purchase.query.filter_by(farmer_id=farmer_id).order_by(Purchase.created_at.desc()).all()
    result = []
    for p in purchases:
        buyer = db.session.get(User, p.buyer_id)
        result.append({
            'id':         p.id,
            'crop':       p.crop,
            'qty':        p.qty,
            'price':      p.price,
            'status':     p.status,
            'buyer_name': buyer.name if buyer else 'Buyer',
            'buyer_id':   p.buyer_id,
            'created_at': p.created_at.strftime('%b %d, %Y'),
        })
    return jsonify(result)

@app.route('/purchase/<int:purchase_id>/status', methods=['PATCH'])
def update_purchase_status(purchase_id):
    """Farmer confirms or completes a purchase."""
    data   = request.get_json(force=True, silent=True) or {}
    status = data.get('status', 'confirmed')
    p = db.session.get(Purchase, purchase_id)
    if not p:
        return jsonify({'error': 'Not found'}), 404
    p.status = status
    db.session.commit()
    return jsonify({'message': 'Status updated', 'status': p.status})

# ── Messages (Buyer-Farmer Chat) ──────────────────────────────────────────────
@app.route('/messages/<int:purchase_id>', methods=['GET', 'POST'])
def messages(purchase_id):
    if request.method == 'GET':
        msgs = Message.query.filter_by(purchase_id=purchase_id)\
                            .order_by(Message.created_at.asc()).all()
        return jsonify([{
            'id':          m.id,
            'sender_id':   m.sender_id,
            'sender_name': m.sender_name,
            'text':        m.text,
            'created_at':  m.created_at.strftime('%H:%M'),
            'date':        m.created_at.strftime('%b %d'),
        } for m in msgs])

    if request.method == 'POST':
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({'error': 'Invalid body'}), 400
        try:
            sender   = db.session.get(User, data.get('sender_id'))
            msg = Message(
                purchase_id = purchase_id,
                sender_id   = data.get('sender_id'),
                sender_name = sender.name if sender else data.get('sender_name', 'User'),
                text        = data.get('text', ''),
            )
            db.session.add(msg)
            db.session.commit()
            return jsonify({
                'id':          msg.id,
                'sender_id':   msg.sender_id,
                'sender_name': msg.sender_name,
                'text':        msg.text,
                'created_at':  msg.created_at.strftime('%H:%M'),
                'date':        msg.created_at.strftime('%b %d'),
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500


@app.route('/tasks', methods=['GET', 'POST'])
def handle_tasks():
    if request.method == 'POST':
        data           = request.json
        user_id        = data.get('user_id', 1)
        crop           = data.get('crop')
        start_date_str = data.get('start_date')
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except Exception:
            start_date = datetime.now()

        CalendarTask.query.filter_by(user_id=user_id, crop=crop).delete()

        tasks = [
            {'title': f'Prepare soil for {crop}',   'days_offset': 0},
            {'title': f'Sowing {crop} seeds',        'days_offset': 5},
            {'title': f'First Irrigation for {crop}','days_offset': 10},
            {'title':  'Apply Base Fertilizer',      'days_offset': 12},
            {'title':  'Weeding and Inspection',     'days_offset': 25},
            {'title':  'Expected Harvest Window',    'days_offset': 90},
        ]
        for t in tasks:
            task_time = start_date + timedelta(days=t['days_offset'])
            db.session.add(CalendarTask(user_id=user_id, crop=crop,
                                        task_title=t['title'],
                                        task_date=task_time.strftime('%b %d, %Y (%I:%M %p)')))
        db.session.commit()
        return jsonify({'message': 'Tasks generated'})

    if request.method == 'GET':
        user_id    = request.args.get('user_id', 1)
        user_tasks = CalendarTask.query.filter_by(user_id=user_id).all()
        return jsonify([{'id': t.id, 'crop': t.crop, 'title': t.task_title, 'date': t.task_date}
                        for t in user_tasks])

# ── Disease Detection ─────────────────────────────────────────────────────────
@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename  = secure_filename(file.filename)
    filepath  = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    prediction_result, heatmap_path, confidence = predict_disease_and_generate_gradcam(filepath)
    disease_details = get_disease_info(prediction_result)
    heatmap_filename = os.path.basename(heatmap_path) if heatmap_path else ''
    heatmap_url = f"{request.host_url}uploads/{heatmap_filename}" if heatmap_filename else ''

    return jsonify({
        'disease':    prediction_result,
        'why':        disease_details.get('why_it_happens', ''),
        'spread':     disease_details.get('spread_details', ''),
        'treatment':  disease_details.get('treatment', ''),
        'steps':      disease_details.get('steps_to_cure', []),
        'confidence': confidence,
        'image':      heatmap_url,
    })

# ── AI Chat ───────────────────────────────────────────────────────────────────
@app.route('/chat', methods=['POST'])
def chat():
    data         = request.json
    user_message = data.get('message', '')
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    try:
        completion = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {'role': 'system', 'content': 'You are KrishiMitra, an expert agricultural assistant helping Indian farmers with crops, diseases, fertilizers, weather, government schemes, and market prices. Keep answers clear and concise.'},
                {'role': 'user', 'content': user_message},
            ],
            temperature=0.7, max_tokens=1024, top_p=1, stream=False,
        )
        return jsonify({'response': completion.choices[0].message.content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Weather ───────────────────────────────────────────────────────────────────
@app.route('/weather', methods=['GET'])
def get_weather():
    lat  = request.args.get('lat')
    lon  = request.args.get('lon')
    city = request.args.get('city')

    if city:
        url          = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric'
        forecast_url = f'https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_API_KEY}&units=metric'
    elif lat and lon:
        url          = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric'
        forecast_url = f'https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric'
    else:
        return jsonify({'error': 'Latitude/longitude or city required'}), 400

    try:
        current_res  = requests.get(url).json()
        forecast_res = requests.get(forecast_url).json()
        if current_res.get('cod') != 200:
            return jsonify(current_res), 400

        # Build weather alerts
        alerts = []
        temp   = current_res['main']['temp']
        wind   = current_res['wind']['speed']
        desc   = current_res['weather'][0]['main'].lower()
        humidity = current_res['main']['humidity']

        if temp > 40:
            alerts.append({'level': 'HIGH', 'message': 'Extreme heat alert! Avoid field work between 11 AM - 4 PM.'})
        elif temp > 35:
            alerts.append({'level': 'MEDIUM', 'message': 'High temperature. Ensure crops are well irrigated.'})
        if temp < 5:
            alerts.append({'level': 'HIGH', 'message': 'Frost warning! Protect sensitive crops immediately.'})
        if wind > 15:
            alerts.append({'level': 'HIGH', 'message': f'Strong winds ({wind:.1f} m/s). Secure crops and equipment.'})
        if 'storm' in desc or 'thunder' in desc:
            alerts.append({'level': 'HIGH', 'message': 'Thunderstorm expected. Take precautions.'})
        if 'rain' in desc and humidity > 85:
            alerts.append({'level': 'MEDIUM', 'message': 'Heavy rain and high humidity. Risk of fungal diseases.'})

        return jsonify({
            'current':  current_res,
            'forecast': forecast_res,
            'alerts':   alerts,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Market Data ───────────────────────────────────────────────────────────────
@app.route('/market', methods=['GET'])
def get_market_data():
    state    = request.args.get('state', '')
    district = request.args.get('district', '')
    crop     = request.args.get('crop', '')

    base_url = f'https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key={MANDI_API_KEY}&format=json'
    filters  = []
    if state:    filters.append(f'filters[state]={state}')
    if district: filters.append(f'filters[district]={district}')
    if crop:     filters.append(f'filters[commodity]={crop}')
    if filters:  base_url += '&' + '&'.join(filters)

    try:
        res = requests.get(base_url).json()
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Soil Analysis & Crop Recommendation ──────────────────────────────────────
_CROP_TIPS = {
    'rice':        {'water': 'High', 'season': 'Kharif (Jun-Nov)', 'tip': 'Keep fields flooded during growing period.'},
    'maize':       {'water': 'Medium', 'season': 'Kharif/Rabi', 'tip': 'Requires well-drained fertile soil.'},
    'chickpea':    {'water': 'Low', 'season': 'Rabi (Oct-Mar)', 'tip': 'Drought tolerant. Avoid waterlogging.'},
    'kidneybeans': {'water': 'Medium', 'season': 'Kharif', 'tip': 'Needs moderate temperature and rainfall.'},
    'pigeonpeas':  {'water': 'Low', 'season': 'Kharif', 'tip': 'Drought resistant. Good for intercropping.'},
    'mothbeans':   {'water': 'Very Low', 'season': 'Kharif', 'tip': 'Excellent for arid regions.'},
    'mungbean':    {'water': 'Low', 'season': 'Kharif/Summer', 'tip': 'Short duration crop, 60-75 days.'},
    'blackgram':   {'water': 'Low', 'season': 'Kharif', 'tip': 'Good source of protein for crop rotation.'},
    'lentil':      {'water': 'Low', 'season': 'Rabi', 'tip': 'Cold tolerant, suited for winter.'},
    'pomegranate': {'water': 'Low', 'season': 'Year-round', 'tip': 'Drought hardy fruit crop.'},
    'banana':      {'water': 'High', 'season': 'Year-round', 'tip': 'Needs regular watering and potassium.'},
    'mango':       {'water': 'Low-Mid', 'season': 'Summer fruit', 'tip': 'Needs dry spell before flowering.'},
    'grapes':      {'water': 'Medium', 'season': 'Rabi', 'tip': 'Needs trellising and pruning management.'},
    'watermelon':  {'water': 'Medium', 'season': 'Summer', 'tip': 'Needs warm temperature and sandy loam soil.'},
    'muskmelon':   {'water': 'Medium', 'season': 'Summer', 'tip': 'Well-drained soil essential.'},
    'apple':       {'water': 'Medium', 'season': 'Temperate', 'tip': 'Needs cold winters for dormancy.'},
    'orange':      {'water': 'Medium', 'season': 'Winter fruit', 'tip': 'Well-drained, slightly acidic soil.'},
    'papaya':      {'water': 'Medium', 'season': 'Year-round', 'tip': 'Very sensitive to waterlogging.'},
    'coconut':     {'water': 'High', 'season': 'Year-round', 'tip': 'Coastal crop, needs high humidity.'},
    'cotton':      {'water': 'Medium', 'season': 'Kharif', 'tip': 'Deep black soil ideal (regur).'},
    'jute':        {'water': 'High', 'season': 'Kharif', 'tip': 'Alluvial soil, warm humid climate.'},
    'coffee':      {'water': 'Medium', 'season': 'Year-round', 'tip': 'Shade-grown in hill tracts.'},
}

@app.route('/soil-analysis', methods=['POST'])
def soil_analysis():
    """
    Accepts: { nitrogen, phosphorus, potassium, ph, moisture }
    Returns: recommended crop, alternatives, soil health score, fertilizer tips
    """
    data = request.json
    try:
        n        = float(data.get('nitrogen', 0))
        p        = float(data.get('phosphorus', 0))
        k        = float(data.get('potassium', 0))
        ph       = float(data.get('ph', 7.0))
        moisture = float(data.get('moisture', 50))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid numeric values'}), 400

    # Validate ranges
    errors = []
    if not (0 <= n <= 300):   errors.append('Nitrogen should be 0-300 kg/ha')
    if not (0 <= p <= 300):   errors.append('Phosphorus should be 0-300 kg/ha')
    if not (0 <= k <= 300):   errors.append('Potassium should be 0-300 kg/ha')
    if not (3.0 <= ph <= 10): errors.append('pH should be 3.0-10.0')
    if not (0 <= moisture <= 100): errors.append('Moisture should be 0-100%')
    if errors:
        return jsonify({'error': '; '.join(errors)}), 400

    # KNN Prediction
    best_crop, confidence, alternatives = _soil_knn_predict(n, p, k, ph, moisture)
    if best_crop is None:
        return jsonify({'error': 'Soil model not loaded. Run train_soil_model.py.'}), 503

    # Soil Health Score (0-100)
    ph_score       = max(0, 100 - abs(ph - 6.5) * 20)          # ideal pH ~6.5
    moisture_score = max(0, 100 - abs(moisture - 50) * 1.5)     # ideal ~50%
    npk_balance    = 100 - abs(n - p) * 0.3 - abs(p - k) * 0.3
    soil_score     = round((ph_score + moisture_score + max(0, npk_balance)) / 3)
    soil_health    = 'Excellent' if soil_score >= 80 else 'Good' if soil_score >= 60 else 'Fair' if soil_score >= 40 else 'Poor'

    # Fertilizer Recommendations
    fert_tips = []
    if n < 20:   fert_tips.append('Very low Nitrogen — Apply Urea (46-0-0) at 20-30 kg/acre.')
    elif n < 50: fert_tips.append('Low Nitrogen — Apply DAP or Ammonium Sulphate.')
    elif n > 150:fert_tips.append('High Nitrogen — Reduce N fertilizer to avoid burning.')

    if p < 15:   fert_tips.append('Low Phosphorus — Apply Single Superphosphate (SSP).')
    elif p > 130:fert_tips.append('High Phosphorus — Avoid excess P, it locks micronutrients.')

    if k < 15:   fert_tips.append('Low Potassium — Apply Muriate of Potash (MOP).')
    elif k > 180:fert_tips.append('High Potassium — Reduce K inputs.')

    if ph < 5.5: fert_tips.append('Acidic soil (pH<5.5) — Apply agricultural lime to raise pH.')
    elif ph > 8: fert_tips.append('Alkaline soil (pH>8) — Apply Gypsum or Sulphur to lower pH.')

    if moisture < 20: fert_tips.append('Very dry soil — Irrigate before sowing.')
    elif moisture > 85: fert_tips.append('Waterlogged — Improve drainage before planting.')

    if not fert_tips:
        fert_tips.append('Soil nutrients are well-balanced. Maintain with organic compost.')

    crop_info = _CROP_TIPS.get(best_crop, {})

    return jsonify({
        'recommended_crop': best_crop,
        'confidence':       confidence,
        'alternatives':     alternatives,
        'soil_health': {
            'score':    soil_score,
            'label':    soil_health,
            'nitrogen': {'value': n, 'status': 'Low' if n < 30 else 'High' if n > 150 else 'Optimal'},
            'phosphorus': {'value': p, 'status': 'Low' if p < 15 else 'High' if p > 130 else 'Optimal'},
            'potassium': {'value': k, 'status': 'Low' if k < 15 else 'High' if k > 180 else 'Optimal'},
            'ph': {'value': ph, 'status': 'Acidic' if ph < 5.5 else 'Alkaline' if ph > 7.5 else 'Neutral'},
            'moisture': {'value': moisture, 'status': 'Low' if moisture < 20 else 'High' if moisture > 85 else 'Optimal'},
        },
        'fertilizer_tips': fert_tips,
        'crop_info': {
            'water_requirement': crop_info.get('water', 'Medium'),
            'best_season':       crop_info.get('season', 'Kharif'),
            'farming_tip':       crop_info.get('tip', ''),
        },
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
