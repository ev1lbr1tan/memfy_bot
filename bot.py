import logging
import random
import os
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === ПАПКА СО ВСЕМИ ФАЙЛАМИ ===
FONT_DIR = os.path.dirname(__file__)  # ← шрифты и гифка рядом с bot.py

# === ХРАНИЛИЩЕ ===
user_data = {}
user_messages = {}

# === ДОНАТ ===
DONATION_URL = "https://dalink.to/ev1lbr1tan"

# === СПИСОК ШРИФТОВ ===
AVAILABLE_FONT_FILES = [
    "Molodost.ttf", "Roboto_Bold.ttf", "Times New Roman Bold Italic.ttf",
    "Nougat Regular.ttf", "Maratype Regular.ttf", "Farabee Bold.ttf",
    "Impact.ttf", "Anton-Regular.ttf", "Comic Sans MS.ttf",
    "Arial_black.ttf", "Lobster.ttf"
]

# === ПРОВЕРКА ШРИФТОВ ===
def check_fonts_presence():
    logger.info(f"Проверка шрифтов в: {FONT_DIR}")
    for fname in AVAILABLE_FONT_FILES:
        path = os.path.join(FONT_DIR, fname)
        if os.path.exists(path):
            logger.info(f"Шрифт найден: {fname}")
        else:
            logger.warning(f"Шрифт НЕ найден: {fname}")

# === ДОНАТ КНОПКА ===
def get_donation_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Донат", url=DONATION_URL)]])

# === БЕЗОПАСНАЯ ОТПРАВКА ===
async def safe_reply(message, text: str, **kwargs):
    try:
        return await message.reply_text(text, **kwargs)
    except Exception as e:
        clean = text.replace('**', '').replace('*', '').replace('_', '')
        logger.warning(f"Markdown failed: {e}")
        return await message.reply_text(clean, **kwargs)

# === /start (молчит) ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

# === /size ===
async def size_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Маленький", callback_data="size_small"),
         InlineKeyboardButton("Средний", callback_data="size_medium")],
        [InlineKeyboardButton("Большой", callback_data="size_large"),
         InlineKeyboardButton("Очень большой", callback_data="size_xlarge")],
        [InlineKeyboardButton("Назад", callback_data="action_back"),
         InlineKeyboardButton("Отмена", callback_data="action_cancel")],
    ]
    await safe_reply(update.message, "Выбери размер шрифта:", reply_markup=InlineKeyboardMarkup(keyboard))

# === КНОПКИ ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}

    # === ОТМЕНА ===
    if query.data == "action_cancel":
        await clear_user_messages(context, query, user_id)
        user_data[user_id] = {}
        await query.edit_message_text("Генерация отменена.")
        return

    # === НАЗАД ===
    if query.data == "action_back":
        ud = user_data[user_id]
        if 'font_file' in ud and ud.get('meme_type') == 'meme_demotivator':
            ud.pop('font_file', None)
            await query.edit_message_text("Выбери шрифт:", reply_markup=show_font_selection())
        elif 'font_size' in ud:
            ud.pop('font_size', None)
            await size_command_from_callback(query)
        elif 'demotivator_type' in ud:
            ud.pop('demotivator_type', None)
            await query.edit_message_text("Выбери шрифт:", reply_markup=show_font_selection())
        elif 'meme_type' in ud:
            ud.pop('meme_type', None)
            await query.edit_message_text("Выбери тип:", reply_markup=main_menu_keyboard())
        else:
            await query.edit_message_text("Нечего возвращать.")
        return

    # === РАЗМЕР ===
    size_map = {
        "size_small": {"top": 30, "bottom": 20},
        "size_medium": {"top": 40, "bottom": 28},
        "size_large": {"top": 50, "bottom": 35},
        "size_xlarge": {"top": 60, "bottom": 40},
    }
    if query.data in size_map:
        user_data[user_id]['font_size'] = size_map[query.data]
        await query.edit_message_text(
            f"Размер: **{query.data.split('_')[1].capitalize()}**\n\nВыбери цвет:",
            parse_mode='Markdown', reply_markup=color_keyboard()
        )
        return

    # === ЦВЕТ ===
    color_map = {"color_red": "red", "color_white": "white", "color_blue": "blue", "color_green": "green", "color_purple": "purple"}
    if query.data in color_map:
        user_data[user_id]['font_color'] = color_map[query.data]
        if user_data[user_id].get('meme_type') == 'meme_demotivator':
            await query.edit_message_text(
                f"Цвет: **{query.data.split('_')[1].capitalize()}**\n\nВыбери рамку:",
                parse_mode='Markdown', reply_markup=thickness_keyboard()
            )
        else:
            await query.edit_message_text("Отправь текст: 'Верхний|Нижний'")
        return

    # === РАМКА ===
    thickness_map = {"thickness_thin": 4, "thickness_normal": 10, "thickness_thick": 20, "thickness_xthick": 30}
    if query.data in thickness_map:
        user_data[user_id]['border_thickness'] = thickness_map[query.data]
        await query.edit_message_text("Отправь текст: 'Верхний|Нижний'")
        return

    # === ШРИФТЫ ===
    font_map = {
        "font_molodost": "Molodost.ttf", "font_roboto": "Roboto_Bold.ttf", "font_times": "Times New Roman Bold Italic.ttf",
        "font_nougat": "Nougat Regular.ttf", "font_maratype": "Maratype Regular.ttf", "font_farabee": "Farabee Bold.ttf",
        "font_impact": "Impact.ttf", "font_anton": "Anton-Regular.ttf", "font_comicsans": "Comic Sans MS.ttf",
        "font_arial_black": "Arial_black.ttf"
    }
    if query.data in font_map:
        user_data[user_id]['font_file'] = font_map[query.data]
        await query.edit_message_text(
            f"Шрифт: **{query.data.split('_')[1].capitalize()}**\n\nТип:",
            parse_mode='Markdown', reply_markup=type_keyboard()
        )
        return

    # === ТИП МЕМА ===
    if query.data in ["meme_classic", "meme_demotivator"]:
        user_data[user_id]['meme_type'] = query.data
        track_message(user_id, query.message.message_id)
        if query.data == "meme_classic":
            await query.edit_message_text("Шрифт:", reply_markup=classic_font_keyboard())
        else:
            await query.edit_message_text("Шрифт:", reply_markup=show_font_selection())
        return

    # === КЛАССИЧЕСКИЙ ШРИФТ ===
    if query.data in ["classic_font_impact", "classic_font_lobster"]:
        user_data[user_id]['classic_font'] = "Impact.ttf" if "impact" in query.data else "Lobster.ttf"
        await query.edit_message_text("Тип:", reply_markup=classic_type_keyboard())
        return

    # === ТИП КЛАССИЧЕСКОГО ===
    if query.data in ["classic_type_normal", "classic_type_bottom_only"]:
        user_data[user_id]['classic_type'] = query.data
        await query.edit_message_text("Отправь текст: 'Верхний|Нижний'")
        return

    # === ТИП ДЕМОТИВАТОРА ===
    if query.data in ["type_normal", "type_bottom_only"]:
        user_data[user_id]['demotivator_type'] = query.data
        await size_command_from_callback(query)
        return

    # === ШАКАЛИЗАЦИЯ ===
    if query.data.startswith("shakalize_"):
        level = query.data.split('_')[-1]
        if level not in ["light", "medium", "hard"]:
            return
        try:
            photo = user_data[user_id]['photo']
            photo.seek(0)
            result = shakalize_image(photo, intensity=level)
            await query.message.reply_photo(
                photo=result,
                caption="Зашакалил!\n\n@memfy_bot",
                reply_markup=get_donation_keyboard()
            )
            await clear_user_messages(context, query, user_id)
            user_data[user_id].clear()
        except Exception as e:
            logger.error(f"Шакализация: {e}")
            await query.edit_message_text("Ошибка при шакализации.")
        return

# === КЛАВИАТУРЫ ===
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Классический мем", callback_data="meme_classic")],
        [InlineKeyboardButton("Демотиватор", callback_data="meme_demotivator")],
        [InlineKeyboardButton("Зашакалить", callback_data="shakalize_menu")],
        [InlineKeyboardButton("Отмена", callback_data="action_cancel")]
    ])

def classic_font_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Impact", callback_data="classic_font_impact")],
        [InlineKeyboardButton("Lobster", callback_data="classic_font_lobster")],
        [InlineKeyboardButton("Назад", callback_data="action_back")]
    ])

def classic_type_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Верх+низ", callback_data="classic_type_normal")],
        [InlineKeyboardButton("Только низ", callback_data="classic_type_bottom_only")],
        [InlineKeyboardButton("Назад", callback_data="action_back")]
    ])

def color_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Красный", callback_data="color_red"), InlineKeyboardButton("Белый", callback_data="color_white")],
        [InlineKeyboardButton("Синий", callback_data="color_blue"), InlineKeyboardButton("Зелёный", callback_data="color_green")],
        [InlineKeyboardButton("Фиолетовый", callback_data="color_purple")],
        [InlineKeyboardButton("Назад", callback_data="action_back")]
    ])

def thickness_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Тонкая", callback_data="thickness_thin"), InlineKeyboardButton("Обычная", callback_data="thickness_normal")],
        [InlineKeyboardButton("Толстая", callback_data="thickness_thick"), InlineKeyboardButton("Очень толстая", callback_data="thickness_xthick")],
        [InlineKeyboardButton("Назад", callback_data="action_back")]
    ])

def type_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Обычный", callback_data="type_normal")],
        [InlineKeyboardButton("Только снизу", callback_data="type_bottom_only")],
        [InlineKeyboardButton("Назад", callback_data="action_back")]
    ])

def show_font_selection():
    keyboard = [
        [InlineKeyboardButton("Molodost", callback_data="font_molodost")],
        [InlineKeyboardButton("Roboto", callback_data="font_roboto")],
        [InlineKeyboardButton("Times", callback_data="font_times")],
        [InlineKeyboardButton("Nougat", callback_data="font_nougat")],
        [InlineKeyboardButton("Maratype", callback_data="font_maratype")],
        [InlineKeyboardButton("Farabee", callback_data="font_farabee")],
        [InlineKeyboardButton("Impact", callback_data="font_impact"), InlineKeyboardButton("Anton", callback_data="font_anton")],
        [InlineKeyboardButton("Comic Sans", callback_data="font_comicsans"), InlineKeyboardButton("Arial Black", callback_data="font_arial_black")],
        [InlineKeyboardButton("Назад", callback_data="action_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# === ОТСЛЕЖИВАНИЕ СООБЩЕНИЙ ===
def track_message(user_id: int, msg_id: int):
    if user_id not in user_messages:
        user_messages[user_id] = []
    if msg_id not in user_messages[user_id]:
        user_messages[user_id].append(msg_id)

async def clear_user_messages(context, query, user_id):
    if user_id in user_messages:
        for msg_id in user_messages[user_id]:
            try:
                await context.bot.delete_message(chat_id=query.message.chat.id, message_id=msg_id)
            except:
                pass
        user_messages[user_id] = []

async def size_command_from_callback(query):
    keyboard = [
        [InlineKeyboardButton("Маленький", callback_data="size_small"), InlineKeyboardButton("Средний", callback_data="size_medium")],
        [InlineKeyboardButton("Большой", callback_data="size_large"), InlineKeyboardButton("Очень большой", callback_data="size_xlarge")],
        [InlineKeyboardButton("Назад", callback_data="action_back")]
    ]
    await query.edit_message_text("Размер шрифта:", reply_markup=InlineKeyboardMarkup(keyboard))

# === ОБРАБОТКА ФОТО ===
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_type = update.message.chat.type

    if update.message.animation:
        file = await context.bot.get_file(update.message.animation.file_id)
        is_gif = True
    else:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        is_gif = False

    photo_bytes = io.BytesIO()
    await file.download_to_memory(photo_bytes)
    photo_bytes.seek(0)

    caption = (update.message.caption or "").strip()
    bot_username = context.bot.username.lower()

    if chat_type in ['group', 'supergroup']:
        mentioned = False
        if caption and f"@memfy_bot" in caption.lower():
            mentioned = True
        elif update.message.caption_entities:
            for e in update.message.caption_entities:
                if e.type == "mention":
                    mention = caption[e.offset:e.offset+e.length].lower()
                    if mention in [f"@memfy_bot", f"@{bot_username}"]:
                        mentioned = True
                        break
        if not mentioned:
            return
        caption = caption.replace(f"@{bot_username}", "").replace("@memfy_bot", "").strip()

    user_data[user_id] = {'photo': photo_bytes, 'is_gif': is_gif}
    if caption and '|' in caption:
        parts = caption.split('|', 1)
        user_data[user_id]['caption_top'] = parts[0].strip()
        user_data[user_id]['caption_bottom'] = parts[1].strip() if len(parts) > 1 else ""

    track_message(user_id, update.message.message_id)
    sent = await update.message.reply_text("Фото получено! Выбери:", reply_markup=main_menu_keyboard())
    track_message(user_id, sent.message_id)

# === ОБРАБОТКА ТЕКСТА ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or 'photo' not in user_data[user_id]:
        return

    ud = user_data[user_id]
    photo_bytes = ud['photo']
    photo_bytes.seek(0)

    try:
        if ud.get('meme_type') == 'meme_classic':
            if 'classic_font' not in ud or 'classic_type' not in ud:
                return
            top, bottom = get_top_bottom_text(update.message.text, ud['classic_type'])
            meme_func = create_classic_meme_gif if ud.get('is_gif') else create_classic_meme
            result = meme_func(photo_bytes, top, bottom, ud['classic_font'])
            await send_result(update, result, ud.get('is_gif'), context)
        else:
            if 'font_file' not in ud:
                return
            top, bottom = get_top_bottom_text(update.message.text, ud.get('demotivator_type', 'type_normal'))
            result = create_demotivator(
                photo_bytes, top, bottom,
                font_size=ud.get('font_size'),
                font_file=ud['font_file'],
                demotivator_type=ud.get('demotivator_type'),
                font_color=ud.get('font_color', 'white'),
                border_thickness=ud.get('border_thickness', 10)
            )
            await send_result(update, result, False, context)

        await clear_user_messages(context, type('obj', (), {'message': update.message}), user_id)
        user_data[user_id].clear()

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("Ошибка. Попробуй снова.")

def get_top_bottom_text(text: str, meme_type: str):
    if meme_type == 'type_bottom_only' or 'bottom_only' in meme_type:
        return "", text.strip()
    if '|' not in text:
        return text.strip(), ""
    top, bottom = text.split('|', 1)
    return top.strip(), bottom.strip()

async def send_result(update, result_bytes, is_gif, context):
    if is_gif:
        await update.message.reply_animation(animation=result_bytes, caption="Готово!\n\n@memfy_bot", reply_markup=get_donation_keyboard())
    else:
        await update.message.reply_photo(photo=result_bytes, caption="Готово!\n\n@memfy_bot", reply_markup=get_donation_keyboard())

# === МЕМЫ ===
def create_classic_meme(photo_bytes: io.BytesIO, top_text: str, bottom_text: str, font_file: str = "Impact.ttf") -> io.BytesIO:
    return _create_meme_base(photo_bytes, top_text, bottom_text, font_file, is_gif=False)

def create_classic_meme_gif(photo_bytes: io.BytesIO, top_text: str, bottom_text: str, font_file: str = "Impact.ttf") -> io.BytesIO:
    return _create_meme_base(photo_bytes, top_text, bottom_text, font_file, is_gif=True)

def _create_meme_base(photo_bytes, top_text, bottom_text, font_file, is_gif):
    img = Image.open(photo_bytes)
    if is_gif and getattr(img, 'is_animated', False):
        return _process_gif(img, top_text, bottom_text, font_file)
    img = img.convert('RGB') if img.mode != 'RGB' else img
    w, h = img.size
    font = load_font(font_file, max(40, w // 20))
    draw = ImageDraw.Draw(img)
    _draw_text(draw, top_text, w, h, font, True)
    _draw_text(draw, bottom_text, w, h, font, False)
    img = _add_watermark(img)
    out = io.BytesIO()
    img.save(out, 'JPEG', quality=95)
    out.seek(0)
    return out

def _process_gif(gif, top_text, bottom_text, font_file):
    frames = []
    font = load_font(font_file, 40)
    try:
        i = 0
        while True:
            gif.seek(i)
            frame = gif.convert('RGB')
            draw = ImageDraw.Draw(frame)
            _draw_text(draw, top_text, frame.width, frame.height, font, True)
            _draw_text(draw, bottom_text, frame.width, frame.height, font, False)
            frame = _add_watermark(frame)
            frames.append(frame)
            i += 1
    except EOFError:
        pass
    out = io.BytesIO()
    frames[0].save(out, 'GIF', save_all=True, append_images=frames[1:], duration=gif.info.get('duration', 100), loop=0)
    out.seek(0)
    return out

def _draw_text(draw, text, w, h, font, is_top):
    if not text: return
    lines = _wrap_text(text, font, w - 40, draw)
    line_h = int(font.size * 1.3)
    if is_top:
        y = 10
    else:
        y = h - len(lines) * line_h - 10
    for line in lines:
        tw = draw.textbbox((0,0), line, font=font)[2]
        _draw_outline(draw, ((w - tw) // 2, y), line, font)
        y += line_h

def _wrap_text(text, font, max_w, draw):
    words = text.split()
    lines = []
    line = []
    for word in words:
        test = ' '.join(line + [word])
        if draw.textbbox((0,0), test, font=font)[2] <= max_w:
            line.append(word)
        else:
            lines.append(' '.join(line))
            line = [word]
    if line:
        lines.append(' '.join(line))
    return lines

def _draw_outline(draw, pos, text, font):
    x, y = pos
    for dx in [-2, 0, 2]:
        for dy in [-2, 0, 2]:
            if dx or dy:
                draw.text((x+dx, y+dy), text, font=font, fill=(0,0,0))
    draw.text(pos, text, font=font, fill=(255,255,255))

def _add_watermark(img):
    text = "@memfy_bot"
    font = load_font("Roboto_Bold.ttf", 16)
    draw = ImageDraw.Draw(img)
    tw, th = draw.textbbox((0,0), text, font=font)[2:]
    wm = Image.new('RGBA', (tw+10, th+5), (0,0,0,0))
    wm_draw = ImageDraw.Draw(wm)
    wm_draw.text((5,0), text, fill=(255,255,255,128), font=font)
    x, y = random.choice([(10,10), (img.width-tw-20,10), (10,img.height-th-20), (img.width-tw-20,img.height-th-20)])
    img = img.convert('RGBA')
    img.paste(wm, (x,y), wm)
    return img.convert('RGB')

def load_font(file, size):
    paths = [os.path.join(FONT_DIR, file), file]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except:
            continue
    return ImageFont.load_default()

# === ДЕМОТИВАТОР (ИСПРАВЛЕНО: Cry1.25 → 1.25) ===
def create_demotivator(photo_bytes, top_text, bottom_text, font_size=None, font_file="Roboto_Bold.ttf",
                       demotivator_type="type_normal", font_color="white", border_thickness=10):
    if font_size is None:
        font_size = {"top": 40, "bottom": 28}
    color_map = {"red": (255,0,0), "white": (255,255,255), "blue": (0,0,255), "green": (0,255,0), "purple": (128,0,128)}
    text_color = color_map.get(font_color, (255,255,255))

    img = Image.open(photo_bytes).convert('RGB')
    img = img.resize((512, 512), Image.LANCZOS)
    w, h = 512, 512
    pad = 30 + border_thickness
    top_space = 80 if demotivator_type == "type_normal" else 20
    canvas_w = w + pad * 2
    canvas_h = h + pad * 2 + (200 if demotivator_type == "type_normal" else 120)
    canvas = Image.new('RGB', (canvas_w, canvas_h), (0,0,0))
    canvas.paste(img, (pad, pad + top_space))
    draw = ImageDraw.Draw(canvas)

    for i in range(border_thickness):
        draw.rectangle([pad-i-1, pad+top_space-i-1, pad+w+i, pad+h+top_space+i], outline=(255,255,255))

    font_large = load_font(font_file, font_size["top"])
    font_small = load_font(font_file, font_size["bottom"])

    def draw_text(text, font, y_start):
        if not text: return y_start
        lines = _wrap_text(text, font, canvas_w - 100, draw)
        y = y_start
        for line in lines:
            tw = draw.textbbox((0,0), line, font=font)[2]
            draw.text(((canvas_w - tw) // 2, y), line, fill=text_color, font=font)
            y += int(font.size * 1.25)  # ← ИСПРАВЛЕНО!
        return y

    if demotivator_type == "type_normal" and top_text:
        draw_text(top_text, font_large, 20)
    if bottom_text:
        draw_text(bottom_text, font_small, pad + h + top_space + border_thickness + 30)

    canvas = _add_watermark(canvas)
    out = io.BytesIO()
    canvas.save(out, 'JPEG', quality=95)
    out.seek(0)
    return out

# === ШАКАЛИЗАЦИЯ ===
def shakalize_image(photo_bytes: io.BytesIO, intensity: str = 'hard') -> io.BytesIO:
    photo_bytes.seek(0)
    try:
        im = Image.open(photo_bytes).convert('RGB')
    except Exception as e:
        logger.error(f"Ошибка открытия изображения: {e}")
        raise

    max_size = 800
    if im.width > max_size or im.height > max_size:
        im.thumbnail((max_size, max_size), Image.LANCZOS)

    w, h = im.size
    levels = {
        'light':  (0.6,  6, 40),
        'medium': (0.35, 5, 25),
        'hard':   (0.14, 4, 10),
    }
    scale, bits, quality = levels.get(intensity, levels['hard'])

    new_w = max(4, int(w * scale))
    new_h = max(4, int(h * scale))
    im_small = im.resize((new_w, new_h), Image.NEAREST)
    im_pixel = im_small.resize((w, h), Image.NEAREST)
    im_poster = ImageOps.posterize(im_pixel, bits)
    im_blur = im_poster.filter(ImageFilter.GaussianBlur(radius=0.5))
    im_final = ImageOps.autocontrast(im_blur, cutoff=2)

    out = io.BytesIO()
    im_final.save(out, format='JPEG', quality=quality, optimize=True)
    out.seek(0)
    return out

# === ПАСХАЛКА /dance ===
DANCE_GIF_PATH = os.path.join(os.path.dirname(__file__), "funny-dance.gif")
dance_gif_bytes = None
if os.path.exists(DANCE_GIF_PATH):
    with open(DANCE_GIF_PATH, 'rb') as f:
        dance_gif_bytes = f.read()
    logger.info("Пасхалка /dance загружена: funny-dance.gif")
else:
    logger.warning("Пасхалка: funny-dance.gif не найден!")

async def dance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if dance_gif_bytes:
        await update.message.reply_animation(
            animation=dance_gif_bytes,
            filename="dance.gif",
            caption="Танцуем!"
        )
    else:
        await update.message.reply_text("Танец не найден...")

# === ЗАПУСК ===
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Ошибка: Установите TELEGRAM_BOT_TOKEN")
        return

    check_fonts_presence()

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("size", size_command))
    app.add_handler(CommandHandler("dance", dance_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.ANIMATION, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()