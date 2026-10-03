import json
import os
import threading
import requests

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput

APP_NAME = "Y MESSENGER"
VERSION = "1.26.1.7"

# روی گوشی باید آدرس IP کامپیوتری که server.py روی آن اجراست را بنویسی.
# مثال: http://192.168.1.20:5000
API = "http://127.0.0.1:5000"

Window.clearcolor = (0.02, 0.035, 0.07, 1)


class Card(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = dp(10)
        self.spacing = dp(8)
        with self.canvas.before:
            Color(0.04, 0.08, 0.14, 1)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size


def label(text="", size=14, color=(1, 1, 1, 1), bold=False, **kwargs):
    return Label(
        text=text,
        font_size=dp(size),
        color=color,
        bold=bold,
        halign="right",
        valign="middle",
        **kwargs,
    )


def button(text, callback, height=dp(48), danger=False):
    b = Button(
        text=text,
        size_hint_y=None,
        height=height,
        background_normal="",
        background_color=(0.09, 0.41, 1, 1) if not danger else (0.65, 0.12, 0.18, 1),
        color=(1, 1, 1, 1),
        font_size=dp(15),
    )
    b.bind(on_release=callback)
    return b


def field(hint, password=False):
    return TextInput(
        hint_text=hint,
        password=password,
        multiline=False,
        size_hint_y=None,
        height=dp(48),
        padding=[dp(12), dp(10)],
        background_normal="",
        background_color=(0.04, 0.08, 0.14, 1),
        foreground_color=(1, 1, 1, 1),
        cursor_color=(0.15, 0.5, 1, 1),
        font_size=dp(15),
    )


class AuthScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "login"
        root = BoxLayout(orientation="vertical", padding=dp(28), spacing=dp(12))
        root.add_widget(Label(size_hint_y=.18))
        title = label("Y MESSENGER", 30, (0.16, .5, 1, 1), True, size_hint_y=None, height=dp(48))
        root.add_widget(title)
        root.add_widget(label(f"Version {VERSION}", 12, (0.45, .52, .62, 1), size_hint_y=None, height=dp(30)))

        self.name = field("نام شما")
        self.username = field("نام کاربری")
        self.password = field("رمز عبور", True)
        root.add_widget(self.name)
        root.add_widget(self.username)
        root.add_widget(self.password)

        self.action = button("ورود", self.submit)
        root.add_widget(self.action)
        self.switch = Button(
            text="حساب نداری؟ ثبت‌نام",
            size_hint_y=None,
            height=dp(42),
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(0.2, .5, 1, 1),
            font_size=dp(14),
        )
        self.switch.bind(on_release=self.toggle)
        root.add_widget(self.switch)

        server_btn = button("آدرس سرور", self.change_server, dp(42))
        root.add_widget(server_btn)
        root.add_widget(Label(size_hint_y=.2))
        self.add_widget(root)

    def toggle(self, *_):
        self.mode = "register" if self.mode == "login" else "login"
        self.name.opacity = 1 if self.mode == "register" else 0
        self.name.disabled = self.mode != "register"
        self.action.text = "ساخت حساب" if self.mode == "register" else "ورود"
        self.switch.text = "حساب داری؟ ورود" if self.mode == "register" else "حساب نداری؟ ثبت‌نام"

    def change_server(self, *_):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        inp = field("http://192.168.1.20:5000")
        inp.text = API
        box.add_widget(inp)
        p = Popup(title="آدرس سرور Flask", content=box, size_hint=(.9, .32))
        box.add_widget(button("ذخیره", lambda *_: self.save_server(p, inp)))
        p.open()

    def save_server(self, popup, inp):
        global API
        API = inp.text.strip().rstrip("/")
        App.get_running_app().save_local()
        popup.dismiss()

    def submit(self, *_):
        if not self.username.text.strip() or not self.password.text:
            App.get_running_app().alert("نام کاربری و رمز عبور را وارد کن.")
            return
        if self.mode == "register" and not self.name.text.strip():
            App.get_running_app().alert("نام خودت را وارد کن.")
            return

        payload = {
            "username": self.username.text.strip(),
            "password": self.password.text,
        }
        endpoint = "/login"
        if self.mode == "register":
            payload["name"] = self.name.text.strip()
            endpoint = "/register"

        def work():
            try:
                r = requests.post(API + endpoint, json=payload, timeout=10)
                data = r.json()
                Clock.schedule_once(lambda dt: self.auth_result(data))
            except Exception as e:
                Clock.schedule_once(lambda dt: App.get_running_app().alert("اتصال به سرور برقرار نشد."))

        threading.Thread(target=work, daemon=True).start()

    def auth_result(self, data):
        if not data.get("ok"):
            App.get_running_app().alert(data.get("error", "خطا"))
            return
        App.get_running_app().set_user(data["user"])


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.users = []
        self.selected = None
        self.poll_event = None

        root = BoxLayout(orientation="vertical")
        head = BoxLayout(size_hint_y=None, height=dp(62), padding=dp(8), spacing=dp(8))
        head.add_widget(label(APP_NAME, 21, (0.16, .5, 1, 1), True))
        head.add_widget(button("پروفایل", self.profile, dp(44)))
        head.add_widget(button("تنظیمات", self.settings, dp(44)))
        root.add_widget(head)

        self.search = TextInput(
            hint_text="جستجوی کاربران...",
            multiline=False,
            size_hint_y=None, height=dp(45),
            background_normal="", background_color=(.04, .08, .14, 1),
            foreground_color=(1, 1, 1, 1), padding=[dp(12), dp(9)]
        )
        self.search.bind(text=lambda *_: self.render_users())
        root.add_widget(self.search)

        scroll = ScrollView()
        self.user_box = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(8), size_hint_y=None)
        self.user_box.bind(minimum_height=self.user_box.setter("height"))
        scroll.add_widget(self.user_box)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self, *_):
        self.load_users()

    def load_users(self):
        uid = App.get_running_app().user["id"]

        def work():
            try:
                data = requests.get(API + "/users", params={"user_id": uid}, timeout=10).json()
                Clock.schedule_once(lambda dt: self.set_users(data))
            except:
                Clock.schedule_once(lambda dt: App.get_running_app().alert("دریافت کاربران انجام نشد."))

        threading.Thread(target=work, daemon=True).start()

    def set_users(self, data):
        if data.get("ok"):
            self.users = data.get("users", [])
            self.render_users()

    def render_users(self):
        self.user_box.clear_widgets()
        q = self.search.text.lower().strip()
        for u in self.users:
            if q and q not in u["name"].lower() and q not in u["username"].lower():
                continue
            row = Card(orientation="horizontal", size_hint_y=None, height=dp(70))
            info = BoxLayout(orientation="vertical")
            info.add_widget(label(u["name"], 16, bold=True))
            info.add_widget(label("@" + u["username"] + ((" • " + u["bio"]) if u.get("bio") else ""), 11, (0.45, .52, .62, 1)))
            row.add_widget(info)
            row.add_widget(button("گفتگو", lambda btn, user=u: self.open_chat(user), dp(42)))
            self.user_box.add_widget(row)

    def open_chat(self, user):
        self.selected = user
        chat = self.manager.get_screen("chat")
        chat.start_chat(user)
        self.manager.current = "chat"

    def profile(self, *_):
        self.manager.current = "profile"

    def settings(self, *_):
        self.manager.current = "settings"


class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user = None
        self.timer = None

        root = BoxLayout(orientation="vertical")
        head = BoxLayout(size_hint_y=None, height=dp(62), padding=dp(7), spacing=dp(7))
        head.add_widget(button("←", self.back, dp(44)))
        self.title = label("گفتگو", 18, bold=True)
        head.add_widget(self.title)
        head.add_widget(button("پروفایل", self.other_profile, dp(44)))
        root.add_widget(head)

        scroll = ScrollView()
        self.messages = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(10), size_hint_y=None)
        self.messages.bind(minimum_height=self.messages.setter("height"))
        scroll.add_widget(self.messages)
        self.scroll = scroll
        root.add_widget(scroll)

        compose = BoxLayout(size_hint_y=None, height=dp(58), padding=dp(7), spacing=dp(7))
        self.input = TextInput(
            hint_text="پیام بنویس...",
            multiline=False,
            background_normal="", background_color=(.04, .08, .14, 1),
            foreground_color=(1, 1, 1, 1), padding=[dp(10), dp(9)]
        )
        compose.add_widget(self.input)
        compose.add_widget(button("➤", self.send, dp(48)))
        root.add_widget(compose)
        self.add_widget(root)

    def start_chat(self, user):
        self.user = user
        self.title.text = user["name"]
        self.load_messages()
        if self.timer:
            self.timer.cancel()
        self.timer = Clock.schedule_interval(lambda dt: self.load_messages(), 1.5)

    def load_messages(self):
        if not self.user:
            return
        app = App.get_running_app()
        def work():
            try:
                data = requests.get(
                    API + "/messages",
                    params={"user_id": app.user["id"], "other_id": self.user["id"]},
                    timeout=8,
                ).json()
                Clock.schedule_once(lambda dt: self.render(data))
            except:
                pass
        threading.Thread(target=work, daemon=True).start()

    def render(self, data):
        if not data.get("ok"):
            return
        self.messages.clear_widgets()
        me = App.get_running_app().user["id"]
        for m in data.get("messages", []):
            mine = m["sender_id"] == me
            row = BoxLayout(size_hint_y=None, height=dp(50))
            if mine:
                row.padding = [dp(80), 0, 0, 0]
            else:
                row.padding = [0, 0, dp(80), 0]
            bg = Card(orientation="horizontal")
            bg.add_widget(label(m["text"], 14))
            row.add_widget(bg)
            self.messages.add_widget(row)
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.05)

    def send(self, *_):
        text = self.input.text.strip()
        if not text or not self.user:
            return
        app = App.get_running_app()
        payload = {"sender_id": app.user["id"], "receiver_id": self.user["id"], "text": text}
        self.input.text = ""

        def work():
            try:
                data = requests.post(API + "/send", json=payload, timeout=10).json()
                if not data.get("ok"):
                    Clock.schedule_once(lambda dt: app.alert(data.get("error", "ارسال پیام ناموفق بود.")))
                else:
                    Clock.schedule_once(lambda dt: self.load_messages())
            except:
                Clock.schedule_once(lambda dt: app.alert("ارتباط با سرور قطع شده است."))

        threading.Thread(target=work, daemon=True).start()

    def other_profile(self, *_):
        if self.user:
            p = self.manager.get_screen("other")
            p.load_user(self.user)
            self.manager.current = "other"

    def back(self, *_):
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.manager.current = "main"


class ProfileScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        root.add_widget(label("پروفایل من", 24, (0.16, .5, 1, 1), True, size_hint_y=None, height=dp(50)))
        self.name = field("نام")
        self.username = field("نام کاربری")
        self.username.disabled = True
        self.bio = TextInput(hint_text="بیو", multiline=True, size_hint_y=None, height=dp(95),
                             background_normal="", background_color=(.04,.08,.14,1), foreground_color=(1,1,1,1))
        self.phone = field("شماره تلفن")
        self.music = field("لینک موسیقی پروفایل")
        for w in (self.name, self.username, self.bio, self.phone, self.music):
            root.add_widget(w)
        root.add_widget(button("ذخیره تغییرات", self.save))
        root.add_widget(button("تغییر عکس پروفایل", self.pick_photo, dp(44)))
        root.add_widget(button("بازگشت", lambda *_: setattr(self.manager, "current", "main"), dp(44)))
        self.add_widget(root)

    def on_pre_enter(self, *_):
        u = App.get_running_app().user
        self.name.text = u.get("name", "")
        self.username.text = "@" + u.get("username", "")
        self.bio.text = u.get("bio", "")
        self.phone.text = u.get("phone", "")
        self.music.text = u.get("profile_music", "")

    def save(self, *_):
        app = App.get_running_app()
        u = app.user
        payload = {
            "name": self.name.text.strip(),
            "bio": self.bio.text.strip(),
            "phone": self.phone.text.strip(),
            "profile_music": self.music.text.strip(),
            "theme": u.get("theme", "blue"),
            "background": u.get("background", ""),
            "font_size": u.get("font_size", 16),
            "blur": u.get("blur", False),
            "message_permission": u.get("message_permission", "everyone"),
        }
        def work():
            try:
                data = requests.put(API + f"/profile/{u['id']}", json=payload, timeout=10).json()
                if data.get("ok"):
                    app.user = data["user"]
                    app.save_local()
                    Clock.schedule_once(lambda dt: app.alert("پروفایل ذخیره شد."))
                else:
                    Clock.schedule_once(lambda dt: app.alert(data.get("error", "خطا")))
            except:
                Clock.schedule_once(lambda dt: app.alert("خطا در ذخیره پروفایل."))
        threading.Thread(target=work, daemon=True).start()

    def pick_photo(self, *_):
        chooser = FileChooserListView(filters=["*.png", "*.jpg", "*.jpeg", "*.webp"])
        box = BoxLayout(orientation="vertical")
        box.add_widget(chooser)
        box.add_widget(button("انتخاب", lambda *_: self.upload_photo(popup, chooser), dp(45)))
        popup = Popup(title="انتخاب عکس", content=box, size_hint=(.95, .85))
        popup.open()

    def upload_photo(self, popup, chooser):
        if not chooser.selection:
            return
        path = chooser.selection[0]
        app = App.get_running_app()
        try:
            with open(path, "rb") as f:
                data = requests.post(API + f"/profile/{app.user['id']}/photo",
                                      files={"photo": (os.path.basename(path), f)},
                                      timeout=20).json()
            if data.get("ok"):
                app.user = data["user"]
                app.save_local()
                popup.dismiss()
                app.alert("عکس پروفایل تغییر کرد.")
            else:
                app.alert(data.get("error", "آپلود عکس ناموفق بود."))
        except:
            app.alert("آپلود عکس انجام نشد.")


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        root.add_widget(label("تنظیمات", 24, (0.16, .5, 1, 1), True, size_hint_y=None, height=dp(50)))
        root.add_widget(label("ظاهر", 14, (0.6,.65,.75,1), True, size_hint_y=None, height=dp(30)))
        self.theme = TextInput(hint_text="blue یا dark", multiline=False, size_hint_y=None, height=dp(48),
                               background_normal="", background_color=(.04,.08,.14,1), foreground_color=(1,1,1,1))
        self.background = field("لینک تصویر پس‌زمینه")
        self.font_size = field("اندازه فونت: 12 تا 24")
        root.add_widget(self.theme)
        root.add_widget(self.background)
        root.add_widget(self.font_size)
        root.add_widget(label("حریم خصوصی", 14, (0.6,.65,.75,1), True, size_hint_y=None, height=dp(30)))
        self.permission = TextInput(hint_text="everyone یا nobody", multiline=False, size_hint_y=None, height=dp(48),
                                    background_normal="", background_color=(.04,.08,.14,1), foreground_color=(1,1,1,1))
        root.add_widget(self.permission)
        root.add_widget(button("ذخیره تنظیمات", self.save))
        root.add_widget(button("آدرس سرور", self.change_server, dp(44)))
        root.add_widget(button("خروج از حساب", self.logout, dp(44), danger=True))
        root.add_widget(button("بازگشت", lambda *_: setattr(self.manager, "current", "main"), dp(44)))
        self.add_widget(root)

    def on_pre_enter(self, *_):
        u = App.get_running_app().user
        self.theme.text = u.get("theme", "blue")
        self.background.text = u.get("background", "")
        self.font_size.text = str(u.get("font_size", 16))
        self.permission.text = u.get("message_permission", "everyone")

    def save(self, *_):
        app = App.get_running_app()
        u = app.user
        try:
            fs = max(12, min(int(self.font_size.text or 16), 24))
        except:
            fs = 16
        perm = self.permission.text.strip()
        if perm not in ("everyone", "nobody"):
            perm = "everyone"
        payload = {
            "name": u["name"], "bio": u.get("bio",""), "phone": u.get("phone",""),
            "profile_music": u.get("profile_music",""),
            "theme": self.theme.text.strip() or "blue",
            "background": self.background.text.strip(),
            "font_size": fs, "blur": False, "message_permission": perm,
        }
        def work():
            try:
                data = requests.put(API + f"/profile/{u['id']}", json=payload, timeout=10).json()
                if data.get("ok"):
                    app.user = data["user"]; app.save_local()
                    Clock.schedule_once(lambda dt: app.alert("تنظیمات ذخیره شد."))
                else:
                    Clock.schedule_once(lambda dt: app.alert(data.get("error", "خطا")))
            except:
                Clock.schedule_once(lambda dt: app.alert("خطا در ذخیره تنظیمات."))
        threading.Thread(target=work, daemon=True).start()

    def change_server(self, *_):
        self.manager.get_screen("auth").change_server()

    def logout(self, *_):
        app = App.get_running_app()
        app.user = None
        app.save_local()
        self.manager.current = "auth"


class OtherProfileScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user = None
        root = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        self.title = label("پروفایل کاربر", 24, (0.16,.5,1,1), True, size_hint_y=None, height=dp(50))
        root.add_widget(self.title)
        self.info = label("", 15, size_hint_y=None, height=dp(180))
        root.add_widget(self.info)
        root.add_widget(button("مسدود کردن کاربر", self.block, dp(48), danger=True))
        root.add_widget(button("رفع مسدودیت", self.unblock, dp(48)))
        root.add_widget(button("بازگشت", lambda *_: setattr(self.manager, "current", "chat"), dp(48)))
        self.add_widget(root)

    def load_user(self, user):
        self.user = user
        self.title.text = user.get("name", "کاربر")
        self.info.text = (
            f"نام: {user.get('name','')}\n"
            f"نام کاربری: @{user.get('username','')}\n"
            f"بیو: {user.get('bio','')}\n"
            f"آخرین فعالیت: {user.get('last_seen','')}"
        )

    def action(self, endpoint):
        app = App.get_running_app()
        def work():
            try:
                data = requests.post(API + endpoint, json={
                    "user_id": app.user["id"], "blocked_id": self.user["id"]
                }, timeout=10).json()
                Clock.schedule_once(lambda dt: app.alert("انجام شد." if data.get("ok") else data.get("error","خطا")))
            except:
                Clock.schedule_once(lambda dt: app.alert("ارتباط با سرور برقرار نشد."))
        threading.Thread(target=work, daemon=True).start()

    def block(self, *_):
        if self.user: self.action("/block")

    def unblock(self, *_):
        if self.user: self.action("/unblock")


class MessengerApp(App):
    user = None

    def build(self):
        self.load_local()
        sm = ScreenManager()
        sm.add_widget(AuthScreen(name="auth"))
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(ChatScreen(name="chat"))
        sm.add_widget(ProfileScreen(name="profile"))
        sm.add_widget(SettingsScreen(name="settings"))
        sm.add_widget(OtherProfileScreen(name="other"))
        self.sm = sm
        sm.current = "main" if self.user else "auth"
        return sm

    def load_local(self):
        global API
        try:
            with open(self.local_path("config.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
                API = data.get("api", API)
                self.user = data.get("user")
        except:
            pass

    def save_local(self):
        try:
            with open(self.local_path("config.json"), "w", encoding="utf-8") as f:
                json.dump({"api": API, "user": self.user}, f, ensure_ascii=False)
        except:
            pass

    def local_path(self, name):
        return os.path.join(self.user_data_dir, name)

    def set_user(self, user):
        self.user = user
        self.save_local()
        self.sm.current = "main"

    def alert(self, msg):
        Popup(
            title=APP_NAME,
            content=label(msg, 14),
            size_hint=(.85, .28),
        ).open()


if __name__ == "__main__":
    MessengerApp().run()
