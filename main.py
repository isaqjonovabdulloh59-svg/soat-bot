import asyncio
from datetime import datetime, timedelta, timezone, date
import json
import os
import random
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from telethon import TelegramClient, functions
from telethon.errors import (
    AuthKeyDuplicatedError,
    UserDeactivatedError,
    SessionPasswordNeededError,
)

# ================= ASOSIY SOZLAMALAR =================
# Token va API ma'lumotlari environment (muhit) o'zgaruvchilaridan olinadi
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8817958511:AAF6VJWPiwjSlsy9nefL2SbqVXGvpq5PG1I")

API_ID = int(os.environ.get("API_ID", 27309538))
API_HASH = os.environ.get("API_HASH", "a728b10f5fe73b9d2eec290147f7c74c")

CARD_NUMBER = "9860606758705960"
CARD_OWNER = "Muxiddinova V"

ADMIN_ID = 8488328091

# Toshkent vaqt zonasi (+5 soat)
TASHKENT_TZ = timezone(timedelta(hours=5))

DAYS_OF_WEEK_UZ = {
    0: "dushanba",
    1: "seshanba",
    2: "chorshanba",
    3: "payshanba",
    4: "juma",
    5: "shanba",
    6: "yakshanba"
}
# =======================================================

os.makedirs("sessions", exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "users_db.json"
PROMO_FILE = "promos_db.json"

db_lock = threading.Lock()

# Render port xatosi va HEAD so'rovlar uchun mini server
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()


def load_db():
    with db_lock:
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}


def save_db(data):
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


def load_promos():
    if os.path.exists(PROMO_FILE):
        try:
            with open(PROMO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {"DEFAULTPROMO": {"amount": 2000, "uses": 10}}


def save_promos(data):
    with open(PROMO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


db = load_db()
promos_db = load_promos()

user_sessions = {}
active_clocks = {}


def get_user_data(user_id):
    str_id = str(user_id)
    if str_id not in db:
        db[str_id] = {
            "balance": 0,
            "plan": "Free",
            "joined_date": datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "clock_active": False,
            "nick_clock": True,
            "bio_clock": False,
            "bio_type": "oddiy",
            "online_mode": False,
            "referrals_count": 0,
            "clock_installed_referrals": 0,
            "used_promos": [],
            "birthday_date": "12-25",
            "plan_expire": "Mavjud emas",
            "font_style": "Default",
            "saved_pubg_id": None,
        }
        save_db(db)
    return db[str_id]


def apply_font(text, font_style):
    if font_style == "Monospace":
        trans = str.maketrans("0123456789", "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿")
        return text.translate(trans)
    elif font_style == "Bold":
        trans = str.maketrans("0123456789", "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗")
        return text.translate(trans)
    elif font_style == "Double Struck":
        trans = str.maketrans("0123456789", "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡")
        return text.translate(trans)
    elif font_style == "Circle":
        trans = str.maketrans("0123456789", "⓪①②③④⑤⑥⑦⑧⑨")
        return text.translate(trans)
    elif font_style == "SuperScript":
        trans = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
        return text.translate(trans)
    elif font_style == "SubScript":
        trans = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
        return text.translate(trans)
    elif font_style == "Strike-Through":
        return "".join([c + "\u0336" if c.isdigit() else c for c in text])
    elif font_style == "Bold Serif":
        trans = str.maketrans("0123456789", "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗")
        return text.translate(trans)
    elif font_style == "Double Circle":
        trans = str.maketrans("0123456789", "⓪①②③④⑤⑥⑦⑧⑨")
        return text.translate(trans)
    elif font_style == "Dark Circle":
        trans = str.maketrans("0123456789", "⓪①②③④⑤⑥⑦⑧⑨")
        return text.translate(trans)
    elif font_style == "Crazify":
        styles = ["Default", "Monospace", "Bold", "Double Struck", "Circle"]
        chosen = random.choice(styles)
        if chosen != "Crazify":
            return apply_font(text, chosen)
    return text


def get_hijri_qurbon_hayiti(year):
    qurbon_dates = {
        2025: (datetime(2025, 6, 6, tzinfo=TASHKENT_TZ), "05:30"),
        2026: (datetime(2026, 5, 27, tzinfo=TASHKENT_TZ), "05:30"),
        2027: (datetime(2027, 5, 17, tzinfo=TASHKENT_TZ), "05:30"),
        2028: (datetime(2028, 5, 6, tzinfo=TASHKENT_TZ), "05:30"),
    }
    target_dt = qurbon_dates.get(year, (datetime(year, 6, 1, tzinfo=TASHKENT_TZ), "05:30"))
    return target_dt


class ClockSetup(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_password = State()
    waiting_for_birthday = State()


class PaymentState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_receipt = State()


class PromoState(StatesGroup):
    waiting_for_promo = State()


class NickGenState(StatesGroup):
    waiting_for_name = State()
    waiting_for_choice = State()


class PubgState(StatesGroup):
    waiting_for_pubg_id = State()
    waiting_for_new_pubg_id = State()


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Soat Sozlamalari ⚙️"),
            KeyboardButton(text="Mening Hisobim 👤"),
        ],
        [
            KeyboardButton(text="PUBG UC 🎮"),
        ],
        [
            KeyboardButton(text="Hisobni To'ldirish 💰"),
            KeyboardButton(text="Tariflar 🛍"),
        ],
        [
            KeyboardButton(text="Referral 💸"),
            KeyboardButton(text="Promokod 🎟"),
        ],
        [
            KeyboardButton(text="Savollar (FAQ) ❓"),
            KeyboardButton(text="Nik yaratish 🤩"),
        ],
    ],
    resize_keyboard=True,
)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅️ Bekor qilish")]], resize_keyboard=True
)

phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📞 Telefon raqamni jo'natish", request_contact=True)],
        [KeyboardButton(text="⬅️ Bekor qilish")],
    ],
    resize_keyboard=True,
)


async def start_user_clock(user_id, client):
    while user_id in active_clocks:
        try:
            u_data = get_user_data(user_id)
            
            # --- PREMIUMLAR VA FREE UCHUN TEKSHiruv (Siz so'ragan o'zgarish) ---
            if u_data.get("plan") == "Free":
                active_clocks.pop(user_id, None)
                u_data["clock_active"] = False
                save_db(db)
                try:
                    await bot.send_message(user_id, "⚠️ Profil soat faqat pullik (Standard, Plus, Premium) tariflardagi foydalanuvchilar uchun ishlaydi. Iltimos, tarif sotib oling!")
                except Exception:
                    pass
                break
            
            if u_data.get("plan") != "Free" and u_data.get("plan_expire") != "Mavjud emas":
                try:
                    exp_dt = datetime.strptime(u_data.get("plan_expire"), "%Y-%m-%d %H:%M:%S")
                    exp_dt = exp_dt.replace(tzinfo=TASHKENT_TZ)
                    if datetime.now(TASHKENT_TZ) > exp_dt:
                        u_data["plan"] = "Free"
                        u_data["plan_expire"] = "Mavjud emas"
                        save_db(db)
                        active_clocks.pop(user_id, None)
                        u_data["clock_active"] = False
                        save_db(db)
                        try:
                            await bot.send_message(user_id, "⏰ Tarifingiz muddati tugadi va soat to'xtatildi.")
                        except Exception:
                            pass
                        break
                except Exception:
                    pass

            now_dt = datetime.now(TASHKENT_TZ)
            now_raw = now_dt.strftime("%H:%M")
            font_style = u_data.get("font_style", "Default")
            now = apply_font(now_raw, font_style)
            
            me = await client.get_me()
            full_user = await client(functions.users.GetFullUserRequest(id=me))
            
            about_text = ""
            if hasattr(full_user, "about"):
                about_text = full_user.about or ""
            elif hasattr(full_user, "full_user") and hasattr(full_user.full_user, "about"):
                about_text = full_user.full_user.about or ""

            if u_data.get("plan") in ["Plus", "Premium"] and u_data.get("online_mode", False):
                try:
                    await client(functions.account.UpdateStatusRequest(offline=False))
                except Exception:
                    pass

            first_name = me.first_name or "User"
            
            if u_data.get("nick_clock", True):
                new_last_name = now
            else:
                new_last_name = ""

            if "|" in about_text:
                clean_bio = about_text.split("|")[0].strip()
            else:
                clean_bio = about_text
            
            clean_bio = re.sub(r"(🕒|⏳|🎂|🎄|✨|🕌|Good|Tug'ilgan|Yangi|Vatan|Qurbon|8-mart).*$", "", clean_bio).strip()
            
            extra_bio = []
            if u_data.get("bio_clock", False):
                b_type = u_data.get("bio_type", "oddiy")
                if b_type == "oddiy":
                    extra_bio.append(f"🕒 {now}")
                elif b_type == "salomlashish":
                    hour = now_dt.hour
                    if 5 <= hour < 12:
                        salom = "Good morning ☀️"
                    elif 12 <= hour < 17:
                        salom = "Good afternoon 🌤"
                    elif 17 <= hour < 22:
                        salom = "Good evening 🌙"
                    else:
                        salom = "Good night 🌠"
                    extra_bio.append(salom)
                elif b_type == "tugilgan_kun":
                    b_date_str = u_data.get("birthday_date", "12-25")
                    try:
                        b_month, b_day = map(int, b_date_str.split("-"))
                        b_target = datetime(now_dt.year, b_month, b_day, 0, 0, tzinfo=TASHKENT_TZ)
                        if b_target < now_dt:
                            b_target = datetime(now_dt.year + 1, b_month, b_day, 0, 0, tzinfo=TASHKENT_TZ)
                        diff = b_target - now_dt
                        days = diff.days
                        hours = diff.total_seconds() // 3600
                        weekday_name = DAYS_OF_WEEK_UZ[b_target.weekday()]
                        extra_bio.append(f"🎂 Tug'ilgan kungacha: {days} kun {int(hours)%24} soat ({weekday_name})")
                    except Exception:
                        extra_bio.append("🎂 Tug'ilgan kun")
                elif b_type == "yangi_yil":
                    ny_target = datetime(now_dt.year + 1, 1, 1, 0, 0, tzinfo=TASHKENT_TZ)
                    diff = ny_target - now_dt
                    days = diff.days
                    hours = int(diff.total_seconds()) // 3600
                    extra_bio.append(f"🎄 Yangi yilgacha: {days} kun {hours%24} soat")
                elif b_type == "vatan_himoyachilari":
                    target = datetime(now_dt.year, 1, 14, 0, 0, tzinfo=TASHKENT_TZ)
                    if target < now_dt:
                        target = datetime(now_dt.year + 1, 1, 14, 0, 0, tzinfo=TASHKENT_TZ)
                    diff = target - now_dt
                    days = diff.days
                    hours = int(diff.total_seconds()) // 3600
                    wday = DAYS_OF_WEEK_UZ[target.weekday()]
                    extra_bio.append(f"🎖 14-yanvargacha: {days}k {hours%24}s ({wday})")
                elif b_type == "sakkiz_mart":
                    target = datetime(now_dt.year, 3, 8, 0, 0, tzinfo=TASHKENT_TZ)
                    if target < now_dt:
                        target = datetime(now_dt.year + 1, 3, 8, 0, 0, tzinfo=TASHKENT_TZ)
                    diff = target - now_dt
                    days = diff.days
                    hours = int(diff.total_seconds()) // 3600
                    wday = DAYS_OF_WEEK_UZ[target.weekday()]
                    extra_bio.append(f"🌷 8-martgacha: {days}k {hours%24}s ({wday})")
                elif b_type == "qurbon_hayiti":
                    qh_dt, namoz_time = get_hijri_qurbon_hayiti(now_dt.year)
                    if qh_dt < now_dt:
                        qh_dt, namoz_time = get_hijri_qurbon_hayiti(now_dt.year + 1)
                    diff = qh_dt - now_dt
                    days = diff.days
                    hours = int(diff.total_seconds()) // 3600
                    wday = DAYS_OF_WEEK_UZ[qh_dt.weekday()]
                    extra_bio.append(f"🕌 Qurbon hayiti ({wday}): {days}k {hours%24}s | Namoz: {namoz_time}")

            final_bio = f"{clean_bio} " + " | ".join(extra_bio) if extra_bio else clean_bio

            await client(
                functions.account.UpdateProfileRequest(
                    first_name=first_name, last_name=new_last_name, about=final_bio[:70]
                )
            )

        except (AuthKeyDuplicatedError, UserDeactivatedError, Exception) as err:
            if "authorization" in str(err).lower() or "session" in str(err).lower() or isinstance(err, (AuthKeyDuplicatedError, UserDeactivatedError)):
                active_clocks.pop(user_id, None)
                u_data = get_user_data(user_id)
                u_data["clock_active"] = False
                save_db(db)
                try:
                    await bot.send_message(user_id, "Siz botni profilingizdan chiqarib yubordingiz, iltimos qaytadan urinib ko'ring")
                except Exception:
                    pass
                break
            else:
                print(f"Soat yangilash xatosi ({user_id}):", err)

        now_sec = datetime.now(TASHKENT_TZ).second
        sleep_time = 60 - now_sec
        if sleep_time <= 0:
            sleep_time = 60
        await asyncio.sleep(sleep_time)


@dp.message(F.text.startswith("/addpromo"))
async def add_promo_admin_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) == 4:
        _, code, amount_str, uses_str = parts
        code_upper = code.upper()
        promos_db[code_upper] = {
            "amount": int(amount_str),
            "uses": int(uses_str)
        }
        save_promos(promos_db)
        
        copy_text = f"copromo {code_upper} {amount_str} {uses_str}"
        resp_msg = (
            f"✅ Promokod yaratildi: <b>{code_upper}</b> ({int(amount_str):,} so'm, {uses_str} ta limit)\n\n"
            f"📋 <b>Copy promo uchun:</b>\n"
            f"<code>{copy_text}</code>"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 Copy promo", callback_data=f"copy_promo_info_{code_upper}")]
            ]
        )
        await message.answer(resp_msg, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer("ℹ️ Foydalanish: <code>/addpromo <KOD> <summa> <limit></code>", parse_mode="HTML")


@dp.message(F.text.startswith("/3"))
async def admin_add_balance_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) == 3:
        _, target_user_id_str, amount_str = parts
        if target_user_id_str.isdigit() and amount_str.isdigit():
            target_user_id = int(target_user_id_str)
            amount = int(amount_str)
            
            u_data = get_user_data(target_user_id)
            u_data["balance"] += amount
            save_db(db)
            
            await message.answer(
                f"✅ Foydalanuvchi (<code>{target_user_id}</code>) balansiga <b>{amount:,} so'm</b> qo'shildi!\n"
                f"Jami balans: <b>{u_data['balance']:,} so'm</b>",
                parse_mode="HTML"
            )
            try:
                await bot.send_message(
                    target_user_id,
                    f"🎁 Admin tomonidan hisobingizga <b>{amount:,} so'm</b> qo'shildi! 💰",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        else:
            await message.answer("❌ ID va summa faqat raqamlardan iborat bo'lishi kerak!")
    else:
        await message.answer("ℹ️ Foydalanish: <code>/3 &lt;user_id&gt; &lt;summa&gt;</code>", parse_mode="HTML")


@dp.message(F.text.startswith("/setzero"))
async def admin_set_zero_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) == 2:
        _, target_user_id_str = parts
        if target_user_id_str.isdigit():
            target_user_id = int(target_user_id_str)
            u_data = get_user_data(target_user_id)
            u_data["balance"] = 0
            save_db(db)
            await message.answer(f"✅ Foydalanuvchi (<code>{target_user_id}</code>) balansi <b>0 so'm</b> qilindi!", parse_mode="HTML")
            try:
                await bot.send_message(
                    target_user_id,
                    "⚠️ Admin tomonidan hisobingiz <b>0 so'm</b> qilib qo'yildi.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        else:
            await message.answer("❌ ID raqam noto'g'ri!")
    else:
        await message.answer("ℹ️ Foydalanish: <code>/setzero &lt;user_id&gt;</code>", parse_mode="HTML")


@dp.callback_query(F.data.startswith("copy_promo_info_"))
async def copy_promo_callback(call: types.CallbackQuery):
    c_code = call.data.replace("copy_promo_info_", "")
    pdata = promos_db.get(c_code, {})
    amt = pdata.get("amount", 0)
    uses = pdata.get("uses", 0)
    copy_payload = f"copromo {c_code} {amt} {uses}"
    await call.message.answer(
        f"📋 <b>Nusxalash uchun matn:</b>\n<code>{copy_payload}</code>",
        parse_mode="HTML"
    )
    await call.answer("Tayyor!")


@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id:
            u_data = get_user_data(user_id)
            if u_data.get("referred_by") is None:
                u_data["referred_by"] = ref_id
                ref_data = get_user_data(ref_id)
                ref_data["referrals_count"] = ref_data.get("referrals_count", 0) + 1
                save_db(db)

    get_user_data(user_id)
    first_name = message.from_user.first_name or "Foydalanuvchi"
    await message.answer(
        f"Xush kelibsiz, {first_name}!\n\nMenyu tugmalaridan birini tanlang:",
        reply_markup=main_menu,
    )


@dp.message(F.text == "⬅️ Bekor qilish")
async def cancel_all_states(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Amal bekor qilindi.", reply_markup=main_menu)


@dp.message(F.text == "PUBG UC 🎮")
async def pubg_uc_menu(message: types.Message, state: FSMContext):
    await state.clear()
    text = (
        "🎮 <b>PUBG Mobile UC do'koni</b>\n\n"
        "Kerakli UC miqdorini tanlang:"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="60 UC - 12,500 so'm", callback_data="buy_uc_60"),
                InlineKeyboardButton(text="325 UC - 58,200 so'm", callback_data="buy_uc_325"),
            ],
            [
                InlineKeyboardButton(text="660 UC - 117,300 so'm", callback_data="buy_uc_660"),
                InlineKeyboardButton(text="1800 UC - 290,000 so'm", callback_data="buy_uc_1800"),
            ],
            [
                InlineKeyboardButton(text="3850 UC - 570,200 so'm", callback_data="buy_uc_3850"),
                InlineKeyboardButton(text="8100 UC - 1,220,000 so'm", callback_data="buy_uc_8100"),
            ],
            [
                InlineKeyboardButton(text="16200 UC - 2,400,000 so'm", callback_data="buy_uc_16200"),
                InlineKeyboardButton(text="24300 UC - 3,520,000 so'm", callback_data="buy_uc_24300"),
            ],
            [
                InlineKeyboardButton(text="32400 UC - 4,620,000 so'm", callback_data="buy_uc_32400"),
                InlineKeyboardButton(text="40500 UC - 6,000,000 so'm", callback_data="buy_uc_40500"),
            ]
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.data.startswith("buy_uc_"))
async def process_uc_selection(call: types.CallbackQuery, state: FSMContext):
    uc_amount = call.data.replace("buy_uc_", "")
    
    prices = {
        "60": 12500,
        "325": 58200,
        "660": 117300,
        "1800": 290000,
        "3850": 570200,
        "8100": 1220000,
        "16200": 2400000,
        "24300": 3520000,
        "32400": 4620000,
        "40500": 6000000,
    }
    
    price = prices.get(uc_amount, 0)
    user_id = call.from_user.id
    u_data = get_user_data(user_id)

    if u_data["balance"] < price:
        await call.answer(f"❌ Hisobingizda mablag' yetarli emas! Kerakli summa: {price:,} so'm", show_alert=True)
        return

    await state.update_data(uc_amount=uc_amount, uc_price=price)
    
    saved_id = u_data.get("saved_pubg_id")
    if saved_id:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"Saqlangan ID: {saved_id} ✅", callback_data=f"use_saved_id_{saved_id}")],
                [InlineKeyboardButton(text="Boshqa ID kiritish ✍️", callback_data="enter_new_pubg_id")]
            ]
        )
        await call.message.edit_text(
            f"🛒 Siz tanladingiz: <b>{uc_amount} UC</b> — <b>{price:,} so'm</b>\n\n"
            f"Sizda oldindan saqlangan PUBG ID mavjud. Qaysi biridan foydalanasiz?",
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        await state.set_state(PubgState.waiting_for_pubg_id)
        await call.message.edit_text(
            f"🛒 Siz tanladingiz: <b>{uc_amount} UC</b> — <b>{price:,} so'm</b>\n\n"
            f"🆔 Iltimos, PUBG ID raqamingizni yuboring (Nik emas!):",
            parse_mode="HTML"
        )


@dp.callback_query(F.data.startswith("use_saved_id_"))
async def use_saved_pubg_id_cb(call: types.CallbackQuery, state: FSMContext):
    pubg_id = call.data.replace("use_saved_id_", "")
    await finalize_pubg_order(call.message, state, pubg_id, call.from_user)
    await call.answer()


@dp.callback_query(F.data == "enter_new_pubg_id")
async def enter_new_pubg_id_cb(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(PubgState.waiting_for_pubg_id)
    await call.message.edit_text(
        "🆔 Iltimos, yangi PUBG ID raqamingizni yuboring (Nik emas!):",
        parse_mode="HTML"
    )


@dp.message(PubgState.waiting_for_pubg_id)
async def process_pubg_id(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Bekor qilish":
        await state.clear()
        await message.answer("❌ Amal bekor qilindi.", reply_markup=main_menu)
        return

    pubg_id = message.text.strip()

    if not pubg_id.isdigit():
        await message.answer(
            "❌ <b>Xato!</b> Faqat ID raqamingizni tashlang (faqat raqamlardan iborat bo'lsin):",
            parse_mode="HTML"
        )
        return

    await state.update_data(pubg_id=pubg_id)
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ha ✅", callback_data="save_pubg_yes"),
                InlineKeyboardButton(text="Yo'q ❌", callback_data="save_pubg_no")
            ]
        ]
    )
    await message.answer(
        "Shu ID ni eslab qolaylikmi?",
        reply_markup=kb
    )


@dp.callback_query(F.data.in_(["save_pubg_yes", "save_pubg_no"]))
async def process_save_pubg_choice(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pubg_id = data.get("pubg_id")
    user_id = call.from_user.id
    u_data = get_user_data(user_id)

    if call.data == "save_pubg_yes":
        u_data["saved_pubg_id"] = pubg_id
        save_db(db)
        await finalize_pubg_order(call.message, state, pubg_id, call.from_user, ask_update=True)
    else:
        u_data["saved_pubg_id"] = None
        save_db(db)
        await finalize_pubg_order(call.message, state, pubg_id, call.from_user, ask_update=False)
    await call.answer()


async def finalize_pubg_order(message_obj, state: FSMContext, pubg_id: str, user_obj, ask_update=False):
    data = await state.get_data()
    uc_amount = data.get("uc_amount")
    uc_price = data.get("uc_price")
    
    user_id = user_obj.id
    u_data = get_user_data(user_id)

    if u_data["balance"] >= uc_price:
        u_data["balance"] -= uc_price
        save_db(db)
        await state.clear()
        
        await message_obj.answer(
            f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
            f"🎮 Miqdor: <b>{uc_amount} UC</b>\n"
            f"🆔 PUBG ID: <code>{pubg_id}</code>\n"
            f"💵 Narxi: <b>{uc_price:,} so'm</b>\n\n"
            f"⏳ Admin UC ni profilingizga tushirgach, xabar beramiz.",
            reply_markup=main_menu,
            parse_mode="HTML"
        )
        
        admin_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Tushdi (Bajarildi)",
                        callback_data=f"uc_done_{user_id}_{uc_amount}"
                    )
                ]
            ]
        )
        
        extra_note = "\n📌 (Saqlangan ID orqali buyurtma berildi)" if ask_update else ""
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🔔 <b>Yangi PUBG UC buyurtmasi!</b>{extra_note}\n\n"
                f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{user_obj.first_name}</a> (ID: <code>{user_id}</code>)\n"
                f"🎮 UC miqdori: <b>{uc_amount} UC</b>\n"
                f"🆔 PUBG ID: <code>{pubg_id}</code>\n"
                f"💵 Narxi: <b>{uc_price:,} so'm</b>",
                reply_markup=admin_kb,
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        await state.clear()
        await message_obj.answer(
            "❌ Hisobingizda yetarli mablag' qolmadi.",
            reply_markup=main_menu
        )


@dp.callback_query(F.data.startswith("uc_done_"))
async def admin_uc_done(call: types.CallbackQuery):
    parts = call.data.split("_")
    if len(parts) >= 4:
        target_user_id = int(parts[2])
        uc_amount = parts[3]
    else:
        await call.answer("Xatolik: ma'lumot formati noto'g'ri!", show_alert=True)
        return

    try:
        await bot.send_message(
            target_user_id,
            f"✅ Xarid qilgan <b>{uc_amount} UC</b> pubg mobile akkauntingizga tushirib berildi! 🎮",
            parse_mode="HTML"
        )
        old_text = call.message.text or ""
        await call.message.edit_text(old_text + "\n\n<b>✅ STATUS: Bajarildi (Tushirildi)</b>", parse_mode="HTML")
        await call.answer("Foydalanuvchiga xabar yuborildi!")
    except Exception as e:
        await call.answer(f"Xatolik yuz berdi: {e}", show_alert=True)


@dp.message(F.text == "Referral 💸")
async def referral_menu(message: types.Message):
    user_id = message.from_user.id
    u_data = get_user_data(user_id)
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    installed_count = u_data.get("clock_installed_referrals", 0)
    
    share_text = f"🤖 Eng zo'r profil soat boti!\n\n🔗 Mening havolam orqali kiring va soat o'rnating: {ref_link}"
    share_url = f"https://t.me/share/url?url={ref_link}&text={share_text}"

    text = (
        f"🔗 <b>Referral bo'limi</b>\n\n"
        f"✅ Do'stingiz havolangiz orqali botga kirib, <b>soat o'rnatganida</b> referral hisobga olinadi.\n"
        f"❌ Faqat /start bosib chiqib ketsa — hisoblanmaydi.\n\n"
        f"🎁 <b>Har bir referral uchun 900 so'm beriladi!</b>\n"
        f"📊 Jami natijangiz: <b>{installed_count} ta do'st soat o'rnatgan.</b>\n\n"
        f"🔗 Sizning havolangiz:\n<code>{ref_link}</code>\n\n"
        f"🔻 👤 <b>Do'stlarga yuborish</b> tugmasini bosing — chat tanlaysiz va tayyor post o'zi yuboriladi."
    )
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Do'stlarga yuborish",
                    url=share_url
                )
            ]
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.message(F.text == "Promokod 🎟")
async def promo_menu(message: types.Message, state: FSMContext):
    await state.set_state(PromoState.waiting_for_promo)
    await message.answer(
        "🎟 Promokodni kiriting:",
        reply_markup=cancel_keyboard,
    )


@dp.message(PromoState.waiting_for_promo)
async def process_promo_code(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Bekor qilish":
        await state.clear()
        await message.answer("❌ Amal bekor qilindi.", reply_markup=main_menu)
        return
    
    code = message.text.strip().upper()
    user_id = message.from_user.id
    u_data = get_user_data(user_id)
    
    if "used_promos" not in u_data:
        u_data["used_promos"] = []
        
    if code in u_data["used_promos"]:
        await message.answer("❌ Siz bu promokoddan allaqachon foylangansiz!", reply_markup=main_menu)
        await state.clear()
        return
        
    if code in promos_db:
        promo_info = promos_db[code]
        if promo_info["uses"] > 0:
            promo_info["uses"] -= 1
            amount = promo_info["amount"]
            u_data["balance"] += amount
            u_data["used_promos"].append(code)
            save_promos(promos_db)
            save_db(db)
            await message.answer(f"🎉 Tabriklaymiz! Promokod muvaffaqiyatli faollashtirildi va balansingizga <b>{amount:,} so'm</b> qo'shildi! 💰", reply_markup=main_menu, parse_mode="HTML")
        else:
            await message.answer("❌ Bu promokodning ishlatish limiti tugagan!", reply_markup=main_menu)
    else:
        await message.answer("❌ Bunday promokod mavjud emas yoki xato kiritildi!", reply_markup=main_menu)
    
    await state.clear()


@dp.message(F.text == "Nik yaratish 🤩")
async def nick_gen_menu(message: types.Message, state: FSMContext):
    await state.set_state(NickGenState.waiting_for_name)
    await message.answer(
        "🤩 Chiroyli niklar uchun ismingizni yoki so'zni kiriting:",
        reply_markup=cancel_keyboard,
    )


@dp.message(NickGenState.waiting_for_name)
async def process_nick_generation(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Bekor qilish":
        await state.clear()
        await message.answer("❌ Amal bekor qilindi.", reply_markup=main_menu)
        return
        
    name = message.text.strip()
    
    def style_text(txt, mode):
        if mode == "bold":
            trans = str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝑗𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝑟𝑠𝐭𝑢𝑣𝑤𝐱𝑦𝐳𝐀𝐁𝐶𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗")
            return txt.translate(trans)
        elif mode == "sans":
            trans = str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", "𝖺𝖻𝖼𝖽𝖾𝖿𝗀𝗁𝗂𝗃𝗄𝗅𝗆𝗇𝗈𝗉𝗊𝗋𝗌𝗍𝗎𝗏𝗐𝗑𝗒𝗓𝖠𝖡𝖢𝖣𝖤𝖥𝖦𝖧𝖨𝖩𝖪𝖫𝖬𝖭𝖮𝖯𝖰𝖱𝖲𝖳𝖴𝖵𝖶𝖷𝖸𝖹𝟎𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡")
            return txt.translate(trans)
        elif mode == "italic":
            trans = str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍")
            return txt.translate(trans)
        elif mode == "circle":
            trans = str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩⒶⒷⒸⒹⒺⒻGⒽⒾⒿⓀⓁⓂⓃ𝓄ⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ")
            return txt.translate(trans)
        return txt

    n1 = style_text(name, 'bold')
    n2 = style_text(name, 'sans')
    n3 = style_text(name, 'italic')
    n4 = style_text(name, 'circle')
    n5 = f"꧁ {name} ꧂"
    n6 = f"♛ {name} ♛"
    n7 = f"⚡️ {name} ⚡️"

    await state.update_data(nicks={
        "1": n1,
        "2": n2,
        "3": n3,
        "4": n4,
        "5": n5,
        "6": n6,
        "7": n7
    })
    await state.set_state(NickGenState.waiting_for_choice)

    res = (
        f"✨ Siz kiritgan so'z uchun chiroyli niklar:\n\n"
        f"1. {n1}\n"
        f"2. {n2}\n"
        f"3. {n3}\n"
        f"4. {n4}\n"
        f"5. {n5}\n"
        f"6. {n6}\n"
        f"7. {n7}\n\n"
        f"<i>💡 Kerakli nik raqamini (1 dan 7 gacha) yuboring, men uni sizga yuboraman!</i>"
    )
    await message.answer(res, reply_markup=cancel_keyboard, parse_mode="HTML")


@dp.message(NickGenState.waiting_for_choice)
async def process_nick_choice(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Bekor qilish":
        await state.clear()
        await message.answer("❌ Amal bekor qilindi.", reply_markup=main_menu)
        return

    choice = message.text.strip()
    data = await state.get_data()
    nicks = data.get("nicks", {})

    if choice in nicks:
        selected_nick = nicks[choice]
        await message.answer(f"Siz tanlagan nik:\n\n<code>{selected_nick}</code>", reply_markup=main_menu, parse_mode="HTML")
        await state.clear()
    else:
        await message.answer("❌ Iltimos, 1 dan 7 gacha bo'lgan raqamlardan birini yuboring yoki Bekor qilishni bosing:", reply_markup=cancel_keyboard)


@dp.message(F.text == "Tariflar 🛍")
async def tariffs_menu(message: types.Message):
    text = (
        "📋 Tariflar haqida ma'lumot:\n\n"
        "📌 Tarif: 🔰 Free\n"
        "💰 Narxi: 0 so'm / oy\n"
        "✨ Imkoniyatlar:\n"
        "> Profil soat: ✅\n\n"
        "📌 Tarif: ⏰ Standard\n"
        "💰 Narxi: 4,000 so'm / oy\n"
        "✨ Imkoniyatlar:\n"
        "> Profil soat: ✅\n"
        "> Reklamasiz: ✅\n\n"
        "📌 Tarif: ✨ Plus\n"
        "💰 Narxi: 7,000 so'm / oy\n"
        "✨ Imkoniyatlar:\n"
        "> Profil soat: ✅\n"
        "> Reklamasiz: ✅\n"
        "> Bioga soat: ✅\n"
        "> Soat fontlari: Bazi fontlar\n\n"
        "📌 Tarif: ⭐️ Premium ✔️\n"
        "💰 Narxi: 13,000 so'm / oy\n"
        "✨ Imkoniyatlar:\n"
        "> Profil soat: ✅\n"
        "> Reklamasiz: ✅\n"
        "> Bioga soat: ✅\n"
        "> Online Mode: ✅\n"
        "> Soat fontlari: Hamma fontlar\n\n"
        "Ko'rsatilgan narxlar 1 oy uchun!\n"
        "Tariflardan birini tanlang:"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔰 Free", callback_data="buy_plan_Free"),
                InlineKeyboardButton(text="⏰ Standard", callback_data="buy_plan_Standard"),
            ],
            [
                InlineKeyboardButton(text="✨ Plus", callback_data="buy_plan_Plus"),
                InlineKeyboardButton(text="⭐️ Premium", callback_data="buy_plan_Premium"),
            ],
            [
                InlineKeyboardButton(text="💰 Hisobni to'ldirish", callback_data="go_topup")
            ]
        ]
    )
    await message.answer(text, reply_markup=kb)


@dp.callback_query(F.data.startswith("buy_plan_"))
async def choose_plan_callback(call: types.CallbackQuery):
    plan_name = call.data.replace("buy_plan_", "")
    user_id = call.from_user.id
    u_data = get_user_data(user_id)
    
    if u_data.get("plan") == plan_name:
        await call.answer(f"Siz allaqachon {plan_name} tarifidasiz!", show_alert=True)
        return

    prices = {
        "Free": 0,
        "Standard": 4000,
        "Plus": 7000,
        "Premium": 13000
    }
    
    cost = prices.get(plan_name, 0)
    if u_data["balance"] >= cost:
        u_data["balance"] -= cost
        u_data["plan"] = plan_name
        if plan_name == "Free":
            u_data["plan_expire"] = "Mavjud emas"
        else:
            expire_dt = datetime.now(TASHKENT_TZ) + timedelta(days=30)
            u_data["plan_expire"] = expire_dt.strftime("%Y-%m-%d %H:%M:%S")
        save_db(db)
        await call.message.edit_text(f"🎉 Tabriklaymiz! Siz muvaffaqiyatli <b>{plan_name}</b> tarifini tanladingiz!", parse_mode="HTML")
    else:
        await call.answer("❌ Hisobingizda mablag' yetarli emas! Avval hisobni to'ldiring.", show_alert=True)


@dp.callback_query(F.data == "go_topup")
async def go_topup_cb(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.set_state(PaymentState.waiting_for_amount)
    await call.message.answer(
        "🌀 To'lov miqdorini so'mda kiriting (masalan: 10000):",
        reply_markup=cancel_keyboard,
    )


@dp.message(F.text == "Soat So
