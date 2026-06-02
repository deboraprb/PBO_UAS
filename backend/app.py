"""
AURA SALON - Backend System
Menggunakan konsep OOP (Object-Oriented Programming)
"""

from flask import Flask, request, jsonify, session, g
from flask_cors import CORS
from datetime import datetime, date, time, timedelta
from abc import ABC, abstractmethod
import sqlite3
import hashlib
import json
import os
import re
import secrets

# ─────────────────────────────────────────
# BASE CLASSES (Abstract)
# ─────────────────────────────────────────

class DatabaseManager:
    """Singleton pattern untuk manajemen database"""
    _instance = None
    DB_PATH = "salon.db"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.conn = sqlite3.connect(self.DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'customer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                duration_minutes INTEGER NOT NULL,
                price REAL NOT NULL,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS stylists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialty TEXT,
                bio TEXT,
                photo_url TEXT,
                is_available INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                stylist_id INTEGER,
                service_id INTEGER,
                reservation_date TEXT NOT NULL,
                reservation_time TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                notes TEXT,
                total_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (stylist_id) REFERENCES stylists(id),
                FOREIGN KEY (service_id) REFERENCES services(id)
            );

            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        self.conn.commit()
        self._seed_data()

    def _seed_data(self):
        cursor = self.conn.cursor()
        # Seed admin
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (name, email, phone, password_hash, role) VALUES (?,?,?,?,?)",
                ("Admin Aura", "admin@aurasalon.com", "081234567890", admin_hash, "admin")
            )
        # Seed services
        cursor.execute("SELECT COUNT(*) FROM services")
        if cursor.fetchone()[0] == 0:
            services = [
                ("Precision Haircut", "hair", "Potongan rambut presisi sesuai bentuk wajah", 60, 150000),
                ("Hair Coloring", "hair", "Pewarnaan rambut dengan cat organik premium", 120, 350000),
                ("Balayage", "hair", "Teknik balayage natural dan elegan", 150, 500000),
                ("Aura Facial", "skin", "Facial premium untuk kulit bercahaya", 90, 250000),
                ("Deep Cleansing Facial", "skin", "Pembersihan pori mendalam dengan teknologi terkini", 75, 200000),
                ("Signature Manicure", "nail", "Manikur premium dengan kuteks pilihan", 45, 100000),
                ("Deluxe Pedicure", "nail", "Pedikur mewah dengan scrub eksfoliasi", 60, 130000),
                ("Hot Stone Massage", "spa", "Pijat batu panas untuk relaksasi total", 90, 300000),
                ("Aura Spa Package", "spa", "Paket lengkap spa untuk peremajaan tubuh", 180, 750000),
            ]
            cursor.executemany(
                "INSERT INTO services (name, category, description, duration_minutes, price) VALUES (?,?,?,?,?)",
                services
            )
        # Seed stylists
        cursor.execute("SELECT COUNT(*) FROM stylists")
        if cursor.fetchone()[0] == 0:
            stylists = [
                ("Isabella Hartono", "Hair Specialist", "10 tahun pengalaman dalam styling rambut editorial", None),
                ("Marcus Wijaya", "Color Expert", "Spesialis balayage dan teknik pewarnaan modern", None),
                ("Sophia Rahma", "Skin Therapist", "Terapis kulit bersertifikat internasional", None),
                ("David Santoso", "Nail Artist", "Nail artist kreatif dengan sentuhan fashion", None),
            ]
            cursor.executemany(
                "INSERT INTO stylists (name, specialty, bio, photo_url) VALUES (?,?,?,?)",
                stylists
            )
        self.conn.commit()

    def execute(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor

    def fetchall(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def fetchone(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None


class BaseRepository(ABC):
    """Base class untuk semua repository"""
    def __init__(self):
        self.db = DatabaseManager()

    @abstractmethod
    def get_all(self):
        pass

    @abstractmethod
    def get_by_id(self, id):
        pass


# ─────────────────────────────────────────
# MODEL CLASSES
# ─────────────────────────────────────────

class Pengguna(ABC):
    """<<Interface>> Pengguna"""
    def __init__(self, id, username, emailPengguna, password=None):
        self._id = id
        self._username = username
        self._emailPengguna = emailPengguna
        self._password = password

    @abstractmethod
    def login(self, db_manager):
        pass

    @abstractmethod
    def logout(self, db_manager, token):
        pass

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    @abstractmethod
    def to_dict(self):
        pass


class Admin(Pengguna):
    def __init__(self, id, username, emailPengguna, kodePegawai, password=None, created_at=None, **kwargs):
        super().__init__(id, username, emailPengguna, password)
        self.kodePegawai = kodePegawai
        self.created_at = created_at
        self.role = "admin"

    def kelolaLayanan(self, repo, action, **kwargs):
        if action == "create":
            return repo.create(kwargs['name'], kwargs['category'], kwargs.get('description', ''), kwargs['duration_minutes'], kwargs['price'])
        elif action == "update":
            service_id = kwargs.pop('id')
            return repo.update(service_id, **kwargs)
        elif action == "delete":
            repo.delete(kwargs['id'])
            return True
        return False

    def konfirmasiPesanan(self, repo, id_pesanan, status="confirmed"):
        repo.update_status(id_pesanan, status)
        return True

    def login(self, db_manager):
        token = secrets.token_hex(32)
        db_manager.execute("INSERT INTO auth_tokens (token, user_id) VALUES (?, ?)", (token, self._id))
        return token

    def logout(self, db_manager, token):
        db_manager.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        return True

    def to_dict(self):
        return {
            "id": self._id,
            "name": self._username,
            "email": self._emailPengguna,
            "phone": self.kodePegawai,
            "role": self.role,
            "created_at": self.created_at
        }


class Pelanggan(Pengguna):
    def __init__(self, id, namaLengkap, emailPengguna, noTelp, password=None, created_at=None, **kwargs):
        super().__init__(id, namaLengkap, emailPengguna, password)
        self.noTelp = noTelp
        self.created_at = created_at
        self.role = "customer"

    def buatPesanan(self, service_res, stylist_id, service_id, reservation_date, reservation_time, notes=""):
        return service_res.create_reservation(
            self._id, stylist_id, service_id, reservation_date, reservation_time, notes
        )

    def lihatRiwayat(self, repo_res):
        return repo_res.get_by_user(self._id)

    def login(self, db_manager):
        token = secrets.token_hex(32)
        db_manager.execute("INSERT INTO auth_tokens (token, user_id) VALUES (?, ?)", (token, self._id))
        return token

    def logout(self, db_manager, token):
        db_manager.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        return True

    def to_dict(self):
        return {
            "id": self._id,
            "name": self._username,
            "email": self._emailPengguna,
            "phone": self.noTelp,
            "role": self.role,
            "created_at": self.created_at
        }


class Layanan:
    """Model untuk layanan salon (Katalog)"""
    def __init__(self, idLayanan, namaLayanan, category, description, estimasiWaktuPengerjaan, harga, is_active=True):
        self.idLayanan = idLayanan
        self.namaLayanan = namaLayanan
        self.category = category
        self.description = description
        self.estimasiWaktuPengerjaan = estimasiWaktuPengerjaan
        self.harga = harga
        self.is_active = is_active

    def getInfoLayanan(self):
        return f"{self.namaLayanan} - Rp {self.harga}"

    def to_dict(self):
        return {
            "id": self.idLayanan,
            "name": self.namaLayanan,
            "category": self.category,
            "description": self.description,
            "duration_minutes": self.estimasiWaktuPengerjaan,
            "price": self.harga,
            "price_formatted": f"Rp {self.harga:,.0f}",
            "is_active": bool(self.is_active)
        }


class Stylist:
    """Model untuk stylist"""
    def __init__(self, id, name, specialty, bio, photo_url=None, is_available=True):
        self.id = id
        self.name = name
        self.specialty = specialty
        self.bio = bio
        self.photo_url = photo_url
        self.is_available = is_available

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "specialty": self.specialty,
            "bio": self.bio,
            "photo_url": self.photo_url,
            "is_available": bool(self.is_available)
        }


class Pemesanan:
    """Model untuk Pemesanan (Transaksi)"""
    VALID_STATUSES = ["pending", "confirmed", "completed", "cancelled"]

    def __init__(self, idPesanan, user_id, stylist_id, service_id, tanggalJadwal,
                 reservation_time, statusPesanan, notes, total_price, created_at=None):
        self.idPesanan = idPesanan
        self.user_id = user_id
        self.stylist_id = stylist_id
        self.service_id = service_id
        self.tanggalJadwal = tanggalJadwal
        self.reservation_time = reservation_time
        self._statusPesanan = statusPesanan
        self.notes = notes
        self.total_price = total_price
        self.created_at = created_at

    @property
    def statusPesanan(self):
        return self._statusPesanan

    @statusPesanan.setter
    def statusPesanan(self, value):
        if value not in self.VALID_STATUSES:
            raise ValueError(f"Status tidak valid. Pilih: {self.VALID_STATUSES}")
        self._statusPesanan = value

    def hitungTotalHarga(self):
        return self.total_price

    def ubahStatus(self, status):
        self.statusPesanan = status

    def to_dict(self):
        return {
            "id": self.idPesanan,
            "user_id": self.user_id,
            "stylist_id": self.stylist_id,
            "service_id": self.service_id,
            "reservation_date": self.tanggalJadwal,
            "reservation_time": self.reservation_time,
            "status": self._statusPesanan,
            "notes": self.notes,
            "total_price": self.total_price,
            "total_price_formatted": f"Rp {self.total_price:,.0f}" if self.total_price else "-",
            "created_at": self.created_at
        }


class Pembayaran:
    """Model untuk Pembayaran (Transaksi)"""
    def __init__(self, idBayar, metodeBayar, statusLunas):
        self.idBayar = idBayar
        self.metodeBayar = metodeBayar
        self.statusLunas = statusLunas

    def verifikasiPembayaran(self):
        return self.statusLunas


# ─────────────────────────────────────────
# REPOSITORY CLASSES
# ─────────────────────────────────────────

class UserRepository(BaseRepository):
    """Repository untuk operasi data user"""

    def _map_to_user(self, row):
        if not row:
            return None
        if row["role"] == "admin":
            return Admin(
                id=row["id"],
                username=row["name"],
                emailPengguna=row["email"],
                kodePegawai=row["phone"],
                created_at=row["created_at"]
            )
        else:
            return Pelanggan(
                id=row["id"],
                namaLengkap=row["name"],
                emailPengguna=row["email"],
                noTelp=row["phone"],
                created_at=row["created_at"]
            )

    def get_all(self):
        rows = self.db.fetchall("SELECT * FROM users ORDER BY created_at DESC")
        return [self._map_to_user(r) for r in rows]

    def get_by_id(self, id):
        row = self.db.fetchone("SELECT * FROM users WHERE id = ?", (id,))
        return self._map_to_user(row)

    def get_by_email(self, email):
        row = self.db.fetchone("SELECT * FROM users WHERE email = ?", (email,))
        return row

    def create(self, name, email, phone, password, role="customer"):
        password_hash = Pengguna.hash_password(password)
        try:
            cursor = self.db.execute(
                "INSERT INTO users (name, email, phone, password_hash, role) VALUES (?,?,?,?,?)",
                (name, email, phone, password_hash, role)
            )
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def verify_password(self, email, password):
        row = self.get_by_email(email)
        if not row:
            return None
        if row["password_hash"] == Pengguna.hash_password(password):
            return row
        return None


class ServiceRepository(BaseRepository):
    """Repository untuk operasi data layanan"""

    def get_all(self):
        rows = self.db.fetchall("SELECT * FROM services WHERE is_active = 1 ORDER BY category, name")
        return [Layanan(r["id"], r["name"], r["category"], r["description"], r["duration_minutes"], r["price"], r["is_active"]) for r in rows]

    def get_by_id(self, id):
        row = self.db.fetchone("SELECT * FROM services WHERE id = ?", (id,))
        return Layanan(row["id"], row["name"], row["category"], row["description"], row["duration_minutes"], row["price"], row["is_active"]) if row else None

    def get_by_category(self, category):
        rows = self.db.fetchall(
            "SELECT * FROM services WHERE category = ? AND is_active = 1", (category,)
        )
        return [Layanan(r["id"], r["name"], r["category"], r["description"], r["duration_minutes"], r["price"], r["is_active"]) for r in rows]

    def create(self, name, category, description, duration_minutes, price):
        cursor = self.db.execute(
            "INSERT INTO services (name, category, description, duration_minutes, price) VALUES (?,?,?,?,?)",
            (name, category, description, duration_minutes, price)
        )
        return cursor.lastrowid

    def update(self, id, **kwargs):
        allowed = ["name", "category", "description", "duration_minutes", "price", "is_active"]
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        self.db.execute(
            f"UPDATE services SET {set_clause} WHERE id = ?",
            (*fields.values(), id)
        )
        return True

    def delete(self, id):
        self.db.execute("UPDATE services SET is_active = 0 WHERE id = ?", (id,))


class StylistRepository(BaseRepository):
    """Repository untuk data stylist"""

    def get_all(self):
        rows = self.db.fetchall("SELECT * FROM stylists WHERE is_available = 1")
        return [Stylist(**{k: v for k, v in r.items()}) for r in rows]

    def get_by_id(self, id):
        row = self.db.fetchone("SELECT * FROM stylists WHERE id = ?", (id,))
        return Stylist(**{k: v for k, v in row.items()}) if row else None


class ReservationRepository(BaseRepository):
    """Repository untuk operasi reservasi"""

    def get_all(self):
        rows = self.db.fetchall("""
            SELECT r.*, u.name as user_name, u.email as user_email, u.phone as user_phone,
                   s.name as service_name, s.category as service_category,
                   st.name as stylist_name
            FROM reservations r
            LEFT JOIN users u ON r.user_id = u.id
            LEFT JOIN services s ON r.service_id = s.id
            LEFT JOIN stylists st ON r.stylist_id = st.id
            ORDER BY r.reservation_date DESC, r.reservation_time DESC
        """)
        return rows

    def get_by_id(self, id):
        row = self.db.fetchone("""
            SELECT r.*, u.name as user_name, s.name as service_name, st.name as stylist_name
            FROM reservations r
            LEFT JOIN users u ON r.user_id = u.id
            LEFT JOIN services s ON r.service_id = s.id
            LEFT JOIN stylists st ON r.stylist_id = st.id
            WHERE r.id = ?
        """, (id,))
        return row

    def get_by_user(self, user_id):
        rows = self.db.fetchall("""
            SELECT r.*, s.name as service_name, s.category as service_category,
                   st.name as stylist_name
            FROM reservations r
            LEFT JOIN services s ON r.service_id = s.id
            LEFT JOIN stylists st ON r.stylist_id = st.id
            WHERE r.user_id = ?
            ORDER BY r.reservation_date DESC
        """, (user_id,))
        return rows

    def create(self, user_id, stylist_id, service_id, reservation_date,
               reservation_time, notes, total_price):
        cursor = self.db.execute(
            """INSERT INTO reservations
               (user_id, stylist_id, service_id, reservation_date, reservation_time, notes, total_price)
               VALUES (?,?,?,?,?,?,?)""",
            (user_id, stylist_id, service_id, reservation_date, reservation_time, notes, total_price)
        )
        return cursor.lastrowid

    def update_status(self, id, status):
        self.db.execute("UPDATE reservations SET status = ? WHERE id = ?", (status, id))

    def check_conflict(self, stylist_id, reservation_date, reservation_time):
        row = self.db.fetchone("""
            SELECT id FROM reservations
            WHERE stylist_id = ? AND reservation_date = ? AND reservation_time = ?
            AND status NOT IN ('cancelled')
        """, (stylist_id, reservation_date, reservation_time))
        return row is not None

    def get_stats(self):
        total = self.db.fetchone("SELECT COUNT(*) as cnt FROM reservations")["cnt"]
        pending = self.db.fetchone("SELECT COUNT(*) as cnt FROM reservations WHERE status='pending'")["cnt"]
        confirmed = self.db.fetchone("SELECT COUNT(*) as cnt FROM reservations WHERE status='confirmed'")["cnt"]
        revenue = self.db.fetchone(
            "SELECT COALESCE(SUM(total_price),0) as rev FROM reservations WHERE status IN ('confirmed','completed')"
        )["rev"]
        return {
            "total": total,
            "pending": pending,
            "confirmed": confirmed,
            "revenue": revenue,
            "revenue_formatted": f"Rp {revenue:,.0f}"
        }


# ─────────────────────────────────────────
# SERVICE CLASSES (Business Logic)
# ─────────────────────────────────────────

class AuthService:
    """Layanan autentikasi"""
    def __init__(self):
        self.user_repo = UserRepository()

    def register(self, name, email, phone, password):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return {"success": False, "message": "Format email tidak valid"}
        if len(password) < 6:
            return {"success": False, "message": "Password minimal 6 karakter"}
        existing = self.user_repo.get_by_email(email)
        if existing:
            return {"success": False, "message": "Email sudah terdaftar"}
        user_id = self.user_repo.create(name, email, phone, password)
        if user_id:
            return {"success": True, "message": "Registrasi berhasil", "user_id": user_id}
        return {"success": False, "message": "Gagal mendaftarkan akun"}

    def login(self, email, password):
        user = self.user_repo.verify_password(email, password)
        if user:
            return {
                "success": True,
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "role": user["role"]
                }
            }
        return {"success": False, "message": "Email atau password salah"}


class ReservationService:
    """Layanan reservasi dengan business logic"""
    AVAILABLE_TIMES = [
        "09:00", "10:00", "11:00", "12:00", "13:00",
        "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"
    ]

    def __init__(self):
        self.reservation_repo = ReservationRepository()
        self.service_repo = ServiceRepository()
        self.stylist_repo = StylistRepository()

    def get_available_slots(self, stylist_id, date_str):
        booked = DatabaseManager().fetchall(
            """SELECT reservation_time FROM reservations
               WHERE stylist_id = ? AND reservation_date = ? AND status != 'cancelled'""",
            (stylist_id, date_str)
        )
        booked_times = {r["reservation_time"] for r in booked}
        return [t for t in self.AVAILABLE_TIMES if t not in booked_times]

    def create_reservation(self, user_id, stylist_id, service_id,
                           reservation_date, reservation_time, notes=""):
        # Validasi tanggal
        try:
            res_date = datetime.strptime(reservation_date, "%Y-%m-%d").date()
        except ValueError:
            return {"success": False, "message": "Format tanggal tidak valid"}

        if res_date < date.today():
            return {"success": False, "message": "Tidak bisa memesan untuk tanggal yang sudah lewat"}

        # Cek konflik
        if self.reservation_repo.check_conflict(stylist_id, reservation_date, reservation_time):
            return {"success": False, "message": "Jadwal stylist sudah penuh pada waktu tersebut"}

        # Ambil harga layanan
        service = self.service_repo.get_by_id(service_id)
        if not service:
            return {"success": False, "message": "Layanan tidak ditemukan"}

        res_id = self.reservation_repo.create(
            user_id, stylist_id, service_id,
            reservation_date, reservation_time, notes, service.harga
        )
        return {
            "success": True,
            "message": "Reservasi berhasil dibuat",
            "reservation_id": res_id,
            "total_price": service.harga,
            "total_price_formatted": f"Rp {service.harga:,.0f}"
        }

    def cancel_reservation(self, reservation_id, user_id, is_admin=False):
        row = self.reservation_repo.get_by_id(reservation_id)
        if not row:
            return {"success": False, "message": "Reservasi tidak ditemukan"}
        if not is_admin and row["user_id"] != user_id:
            return {"success": False, "message": "Tidak diizinkan membatalkan reservasi ini"}
        if row["status"] == "completed":
            return {"success": False, "message": "Reservasi yang sudah selesai tidak bisa dibatalkan"}
        self.reservation_repo.update_status(reservation_id, "cancelled")
        return {"success": True, "message": "Reservasi berhasil dibatalkan"}


# ─────────────────────────────────────────
# FLASK APP & ROUTES
# ─────────────────────────────────────────

app = Flask(__name__)
app.secret_key = "aura_salon_secret_2024"
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}}, expose_headers=["Authorization"])

# Service instances
auth_service = AuthService()
reservation_service = ReservationService()
service_repo = ServiceRepository()
stylist_repo = StylistRepository()
reservation_repo = ReservationRepository()
user_repo = UserRepository()


def _get_user_from_token():
    """Helper: extract user from Authorization Bearer token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, None
    token = auth_header[7:]
    db = DatabaseManager()
    row = db.fetchone(
        "SELECT u.id, u.role FROM auth_tokens t JOIN users u ON t.user_id = u.id WHERE t.token = ?",
        (token,)
    )
    if row:
        return row["id"], row["role"]
    return None, None


def require_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id, user_role = _get_user_from_token()
        if not user_id:
            return jsonify({"success": False, "message": "Silakan login terlebih dahulu"}), 401
        request.user_id = user_id
        request.user_role = user_role
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id, user_role = _get_user_from_token()
        if not user_id or user_role != "admin":
            return jsonify({"success": False, "message": "Akses ditolak"}), 403
        request.user_id = user_id
        request.user_role = user_role
        return f(*args, **kwargs)
    return decorated


# ── Auth Routes ──
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    result = auth_service.register(
        data.get("name"), data.get("email"),
        data.get("phone"), data.get("password")
    )
    return jsonify(result), 200 if result["success"] else 400


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    
    user_row = user_repo.verify_password(email, password)
    if user_row:
        user_obj = user_repo.get_by_id(user_row["id"])
        db = DatabaseManager()
        token = user_obj.login(db)
        return jsonify({
            "success": True,
            "token": token,
            "user": user_obj.to_dict()
        }), 200
    return jsonify({"success": False, "message": "Email atau password salah"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user_id, _ = _get_user_from_token()
        db = DatabaseManager()
        if user_id:
            user_obj = user_repo.get_by_id(user_id)
            if user_obj:
                user_obj.logout(db, token)
            else:
                db.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        else:
            db.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
    return jsonify({"success": True, "message": "Berhasil logout"})


@app.route("/api/auth/me", methods=["GET"])
def me():
    user_id, _ = _get_user_from_token()
    if user_id:
        user = user_repo.get_by_id(user_id)
        if user:
            return jsonify({"success": True, "user": user.to_dict()})
    return jsonify({"success": False}), 401


# ── Services Routes ──
@app.route("/api/services", methods=["GET"])
def get_services():
    category = request.args.get("category")
    if category:
        services = service_repo.get_by_category(category)
    else:
        services = service_repo.get_all()
    return jsonify({"success": True, "data": [s.to_dict() for s in services]})


@app.route("/api/services/<int:id>", methods=["GET"])
def get_service(id):
    service = service_repo.get_by_id(id)
    if service:
        return jsonify({"success": True, "data": service.to_dict()})
    return jsonify({"success": False, "message": "Tidak ditemukan"}), 404


@app.route("/api/services", methods=["POST"])
@require_admin
def create_service():
    data = request.json
    admin = user_repo.get_by_id(request.user_id)
    id = admin.kelolaLayanan(service_repo, "create", **data)
    return jsonify({"success": True, "id": id}), 201


@app.route("/api/services/<int:id>", methods=["PUT"])
@require_admin
def update_service(id):
    data = request.json
    data["id"] = id
    admin = user_repo.get_by_id(request.user_id)
    admin.kelolaLayanan(service_repo, "update", **data)
    return jsonify({"success": True})


@app.route("/api/services/<int:id>", methods=["DELETE"])
@require_admin
def delete_service(id):
    admin = user_repo.get_by_id(request.user_id)
    admin.kelolaLayanan(service_repo, "delete", id=id)
    return jsonify({"success": True})


# ── Stylists Routes ──
@app.route("/api/stylists", methods=["GET"])
def get_stylists():
    stylists = stylist_repo.get_all()
    return jsonify({"success": True, "data": [s.to_dict() for s in stylists]})


@app.route("/api/stylists/<int:id>/slots", methods=["GET"])
def get_slots(id):
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"success": False, "message": "Parameter tanggal diperlukan"}), 400
    slots = reservation_service.get_available_slots(id, date_str)
    return jsonify({"success": True, "data": slots})


# ── Reservation Routes ──
@app.route("/api/reservations", methods=["GET"])
@require_auth
def get_reservations():
    if request.user_role == "admin":
        rows = reservation_repo.get_all()
    else:
        pelanggan = user_repo.get_by_id(request.user_id)
        if isinstance(pelanggan, Pelanggan):
            rows = pelanggan.lihatRiwayat(reservation_repo)
        else:
            rows = reservation_repo.get_by_user(request.user_id)
    return jsonify({"success": True, "data": rows})


@app.route("/api/reservations", methods=["POST"])
@require_auth
def create_reservation():
    data = request.json
    pelanggan = user_repo.get_by_id(request.user_id)
    if isinstance(pelanggan, Pelanggan):
        result = pelanggan.buatPesanan(
            reservation_service,
            data.get("stylist_id"),
            data.get("service_id"),
            data.get("reservation_date"),
            data.get("reservation_time"),
            data.get("notes", "")
        )
    else:
        result = reservation_service.create_reservation(
            request.user_id,
            data.get("stylist_id"),
            data.get("service_id"),
            data.get("reservation_date"),
            data.get("reservation_time"),
            data.get("notes", "")
        )
    return jsonify(result), 201 if result["success"] else 400


@app.route("/api/reservations/<int:id>/status", methods=["PUT"])
@require_admin
def update_status(id):
    data = request.json
    status = data.get("status")
    if status not in Pemesanan.VALID_STATUSES:
        return jsonify({"success": False, "message": "Status tidak valid"}), 400
    
    admin = user_repo.get_by_id(request.user_id)
    admin.konfirmasiPesanan(reservation_repo, id, status)
    return jsonify({"success": True})


@app.route("/api/reservations/<int:id>/cancel", methods=["PUT"])
@require_auth
def cancel_reservation(id):
    is_admin = request.user_role == "admin"
    result = reservation_service.cancel_reservation(id, request.user_id, is_admin)
    return jsonify(result), 200 if result["success"] else 400


# ── Dashboard/Stats Routes ──
@app.route("/api/dashboard/stats", methods=["GET"])
@require_admin
def dashboard_stats():
    stats = reservation_repo.get_stats()
    total_users = len(user_repo.get_all())
    stats["total_users"] = total_users
    return jsonify({"success": True, "data": stats})


@app.route("/api/users", methods=["GET"])
@require_admin
def get_users():
    users = user_repo.get_all()
    return jsonify({"success": True, "data": [u.to_dict() for u in users]})


if __name__ == "__main__":
    print("[*] AURA SALON Backend running on http://localhost:5000")
    print("[*] Admin: admin@aurasalon.com / admin123")
    app.run(debug=True, port=5000)
