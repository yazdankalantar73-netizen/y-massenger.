
from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

VERSION = "1.26.1.7"
DB = "ymessenger.db"
UPLOADS = "uploads"

os.makedirs(UPLOADS, exist_ok=True)


# =========================
# DATABASE
# =========================

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            bio TEXT DEFAULT '',
            photo TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            show_phone INTEGER DEFAULT 0,
            message_permission TEXT DEFAULT 'everyone',
            theme TEXT DEFAULT 'blue',
            background TEXT DEFAULT '',
            font_size INTEGER DEFAULT 16,
            blur INTEGER DEFAULT 0,
            profile_music TEXT DEFAULT '',
            last_seen TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS blocked_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            UNIQUE(user_id, blocked_id)
        )
    """)

    con.commit()
    con.close()


init_db()


# =========================
# HELPERS
# =========================

def user_data(row):
    if not row:
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "name": row["name"],
        "bio": row["bio"] or "",
        "photo": row["photo"] or "",
        "phone": row["phone"] if row["show_phone"] else "",
        "theme": row["theme"] or "blue",
        "background": row["background"] or "",
        "font_size": row["font_size"] or 16,
        "blur": bool(row["blur"]),
        "profile_music": row["profile_music"] or "",
        "last_seen": row["last_seen"]
    }


def touch_user(user_id):
    con = db()
    con.execute(
        "UPDATE users SET last_seen=CURRENT_TIMESTAMP WHERE id=?",
        (user_id,)
    )
    con.commit()
    con.close()


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return jsonify({
        "app": "Y MESSENGER",
        "version": VERSION,
        "status": "online"
    })


@app.route("/app")
def app_page():
    return send_from_directory(".", "client.html")


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()
    name = data.get("name", "").strip()

    if not username or not password or not name:
        return jsonify({
            "ok": False,
            "error": "همه فیلدها را کامل کن."
        }), 400

    if len(username) < 3:
        return jsonify({
            "ok": False,
            "error": "نام کاربری حداقل ۳ حرف باشد."
        }), 400

    con = db()

    try:
        cur = con.execute("""
            INSERT INTO users(username,password,name)
            VALUES(?,?,?)
        """, (username, password, name))

        user_id = cur.lastrowid
        con.commit()

        row = con.execute(
            "SELECT * FROM users WHERE id=?",
            (user_id,)
        ).fetchone()

        return jsonify({
            "ok": True,
            "user": user_data(row)
        })

    except sqlite3.IntegrityError:
        return jsonify({
            "ok": False,
            "error": "این نام کاربری قبلاً استفاده شده."
        }), 409

    finally:
        con.close()


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()

    con = db()

    row = con.execute("""
        SELECT * FROM users
        WHERE username=? AND password=?
    """, (username, password)).fetchone()

    if not row:
        con.close()
        return jsonify({
            "ok": False,
            "error": "نام کاربری یا رمز عبور اشتباه است."
        }), 401

    con.execute(
        "UPDATE users SET last_seen=CURRENT_TIMESTAMP WHERE id=?",
        (row["id"],)
    )
    con.commit()
    con.close()

    return jsonify({
        "ok": True,
        "user": user_data(row)
    })


# =========================
# USERS
# =========================

@app.route("/users")
def users():
    current_id = request.args.get("user_id", type=int)

    con = db()

    rows = con.execute("""
        SELECT *
        FROM users
        WHERE id != ?
        ORDER BY name COLLATE NOCASE
    """, (current_id or 0,)).fetchall()

    result = []

    for row in rows:
        result.append({
            "id": row["id"],
            "username": row["username"],
            "name": row["name"],
            "photo": row["photo"] or "",
            "bio": row["bio"] or "",
            "last_seen": row["last_seen"]
        })

    con.close()

    return jsonify({
        "ok": True,
        "users": result
    })


# =========================
# SEND MESSAGE
# =========================

@app.route("/send", methods=["POST"])
def send_message():
    data = request.get_json() or {}

    sender = data.get("sender_id")
    receiver = data.get("receiver_id")
    text = data.get("text", "").strip()

    if not sender or not receiver or not text:
        return jsonify({
            "ok": False,
            "error": "اطلاعات پیام ناقص است."
        }), 400

    con = db()

    blocked = con.execute("""
        SELECT id FROM blocked_users
        WHERE user_id=? AND blocked_id=?
    """, (receiver, sender)).fetchone()

    if blocked:
        con.close()
        return jsonify({
            "ok": False,
            "error": "این کاربر شما را مسدود کرده است."
        }), 403

    receiver_row = con.execute(
        "SELECT message_permission FROM users WHERE id=?",
        (receiver,)
    ).fetchone()

    if not receiver_row:
        con.close()
        return jsonify({
            "ok": False,
            "error": "کاربر پیدا نشد."
        }), 404

    if receiver_row["message_permission"] == "nobody":
        con.close()
        return jsonify({
            "ok": False,
            "error": "این کاربر دریافت پیام را محدود کرده است."
        }), 403

    cur = con.execute("""
        INSERT INTO messages(sender_id,receiver_id,text)
        VALUES(?,?,?)
    """, (sender, receiver, text))

    con.commit()

    message_id = cur.lastrowid

    row = con.execute("""
        SELECT *
        FROM messages
        WHERE id=?
    """, (message_id,)).fetchone()

    con.close()

    return jsonify({
        "ok": True,
        "message": dict(row)
    })


# =========================
# GET MESSAGES
# =========================

@app.route("/messages")
def messages():
    user_id = request.args.get("user_id", type=int)
    other_id = request.args.get("other_id", type=int)

    if not user_id or not other_id:
        return jsonify({
            "ok": False,
            "error": "کاربر مشخص نشده."
        }), 400

    touch_user(user_id)

    con = db()

    rows = con.execute("""
        SELECT *
        FROM messages
        WHERE
            (sender_id=? AND receiver_id=?)
            OR
            (sender_id=? AND receiver_id=?)
        ORDER BY id ASC
    """, (
        user_id,
        other_id,
        other_id,
        user_id
    )).fetchall()

    con.close()

    return jsonify({
        "ok": True,
        "messages": [dict(row) for row in rows]
    })


# =========================
# PROFILE GET
# =========================

@app.route("/profile/<int:user_id>", methods=["GET"])
def get_profile(user_id):
    con = db()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    con.close()

    if not row:
        return jsonify({
            "ok": False,
            "error": "کاربر پیدا نشد."
        }), 404

    return jsonify({
        "ok": True,
        "user": user_data(row)
    })


# =========================
# PROFILE UPDATE
# =========================

@app.route("/profile/<int:user_id>", methods=["PUT"])
def update_profile(user_id):
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    bio = data.get("bio", "").strip()
    phone = data.get("phone", "").strip()

    theme = data.get("theme", "blue")
    background = data.get("background", "")
    font_size = int(data.get("font_size", 16))
    blur = 1 if data.get("blur") else 0
    profile_music = data.get("profile_music", "")

    message_permission = data.get(
        "message_permission",
        "everyone"
    )

    if not name:
        return jsonify({
            "ok": False,
            "error": "نام نمی‌تواند خالی باشد."
        }), 400

    if message_permission not in ["everyone", "nobody"]:
        message_permission = "everyone"

    font_size = max(12, min(font_size, 24))

    con = db()

    con.execute("""
        UPDATE users
        SET
            name=?,
            bio=?,
            phone=?,
            theme=?,
            background=?,
            font_size=?,
            blur=?,
            profile_music=?,
            message_permission=?,
            last_seen=CURRENT_TIMESTAMP
        WHERE id=?
    """, (
        name,
        bio,
        phone,
        theme,
        background,
        font_size,
        blur,
        profile_music,
        message_permission,
        user_id
    ))

    con.commit()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    con.close()

    return jsonify({
        "ok": True,
        "user": user_data(row)
    })


# =========================
# PROFILE PHOTO
# =========================

@app.route("/profile/<int:user_id>/photo", methods=["POST"])
def upload_photo(user_id):
    if "photo" not in request.files:
        return jsonify({
            "ok": False,
            "error": "فایلی انتخاب نشده."
        }), 400

    file = request.files["photo"]

    if not file.filename:
        return jsonify({
            "ok": False,
            "error": "فایل معتبر نیست."
        }), 400

    allowed = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }

    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in allowed:
        return jsonify({
            "ok": False,
            "error": "فرمت عکس مجاز نیست."
        }), 400

    filename = secure_filename(
        f"user_{user_id}_{file.filename}"
    )

    path = os.path.join(UPLOADS, filename)

    file.save(path)

    photo_url = f"/uploads/{filename}"

    con = db()

    con.execute("""
        UPDATE users
        SET photo=?
        WHERE id=?
    """, (photo_url, user_id))

    con.commit()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    con.close()

    return jsonify({
        "ok": True,
        "user": user_data(row)
    })


# =========================
# BLOCK USER
# =========================

@app.route("/block", methods=["POST"])
def block_user():
    data = request.get_json() or {}

    user_id = data.get("user_id")
    blocked_id = data.get("blocked_id")

    if not user_id or not blocked_id:
        return jsonify({
            "ok": False,
            "error": "اطلاعات ناقص است."
        }), 400

    con = db()

    con.execute("""
        INSERT OR IGNORE INTO blocked_users(user_id,blocked_id)
        VALUES(?,?)
    """, (user_id, blocked_id))

    con.commit()
    con.close()

    return jsonify({
        "ok": True
    })


# =========================
# UNBLOCK USER
# =========================

@app.route("/unblock", methods=["POST"])
def unblock_user():
    data = request.get_json() or {}

    user_id = data.get("user_id")
    blocked_id = data.get("blocked_id")

    con = db()

    con.execute("""
        DELETE FROM blocked_users
        WHERE user_id=? AND blocked_id=?
    """, (user_id, blocked_id))

    con.commit()
    con.close()

    return jsonify({
        "ok": True
    })


# =========================
# UPLOADS
# =========================

@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOADS, filename)


# =========================
# VERSION
# =========================

@app.route("/version")
def version():
    return jsonify({
        "name": "Y MESSENGER",
        "version": VERSION
    })


# =========================
# RUN
# =========================

if __name__ == "__main__":
    print()
    print("==============================")
    print("       Y MESSENGER")
    print("       VERSION 1.26.1.7")
    print("==============================")
    print("Server: http://127.0.0.1:5000")
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
    # =========================
# APP UPDATE SYSTEM
# =========================

APP_VERSION = "1.26.1.7"

APP_UPDATE = {
    "version": APP_VERSION,
    "version_code": 126017,
    "title": "Y MESSENGER 1.26.1.7",
    "description": "نسخه فعلی Y MESSENGER",
    "download_url": "",
    "force_update": False
}


@app.route("/update")
def update():

    return jsonify({
        "ok": True,
        "app": "Y MESSENGER",
        "version": APP_UPDATE["version"],
        "version_code": APP_UPDATE["version_code"],
        "title": APP_UPDATE["title"],
        "description": APP_UPDATE["description"],
        "download_url": APP_UPDATE["download_url"],
        "force_update": APP_UPDATE["force_update"]
    })