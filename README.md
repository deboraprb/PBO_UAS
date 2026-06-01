# 🌸 AURA SALON - Sistem Reservasi Layanan Kecantikan

AURA SALON adalah sistem reservasi layanan kecantikan berbasis web yang dirancang untuk memudahkan pelanggan dalam melakukan pemesanan layanan secara online. Web ini dikembangkan menggunakan Python dengan framework Flask sebagai backend, SQLite sebagai database, serta HTML, CSS, dan JavaScript sebagai frontend. Selain itu, sistem ini menerapkan konsep Object-Oriented Programming (OOP) untuk menciptakan kode yang terstruktur, mudah dikelola dan mudah dikembangkan.

## Anggota Kelompok
1. Diana Yakusuma Lestari     (25051204050)
2. Debora Angelika Purba      (25051204051)
3. Firda Ananda               (25051204129)
4. Dimas Giovanni Trisetyanto (25051204168)

## Fitur
- Registrasi & Login pengguna
- Lihat layanan salon (hair, skin, nail, spa)
- Pilih layanan, stylist & slot waktu yang tersedia
- Buat dan batalkan reservasi
- Dashboard admin untuk manajemen reservasi

## Cara Menjalankan

1. Masuk ke direktori backend dan install dependencies:
```bash
   cd backend
   pip install -r requirements.txt
```

2. Jalankan server:
```bash
   python app.py
```

3. Buka browser ke `http://localhost:5000`

## Akun Admin Default
- Email: `admin@aurasalon.com`
- Password: `admin123`

## Implementasi Object-Oriented Programming
1. Encapsulation: diterapkan pada DatabaseManager yang membungkus akses database, serta atribut status pada Reservation yang dilindungi menggunakan property dan setter.
2. Inheritance: diterapkan pada Admin dan Customer yang mewarisi class User, serta semua repository (UserRepository, ServiceRepository, StylistRepository, ReservationRepository) yang mewarisi BaseRepository.
3. Abstraction: diterapkan pada BaseRepository yang menggunakan ABC dan @abstractmethod untuk method get_all() dan get_by_id() yang wajib diimplementasikan oleh class turunan.
4. Polymorphism: diterapkan pada method get_all() di setiap repository yang memiliki implementasi berbeda sesuai tabel masing-masing (users, services, stylists, reservations).
