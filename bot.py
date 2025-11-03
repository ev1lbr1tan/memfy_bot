import logging
import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import io

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Фиксированная папка для шрифтов
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")

# Хранилище для временных данных пользователей
user_data = {}

# Хранилище для ID сообщений, которые нужно удалить
user_messages = {}

# Ссылка на DonationAlerts
DONATION_URL = "https://dalink.to/ev1lbr1tan"

# Список шрифтов
AVAILABLE_FONT_FILES = [
    "Molodost.ttf",
    "Roboto_Bold.ttf",
    "Times New Roman Bold Italic.ttf",
    "Nougat Regular.ttf",
    "Maratype Regular.ttf",
    "Farabee Bold.ttf",
    "Impact.ttf",
    "Anton-Regular.ttf",
    "Comic Sans MS.ttf",
    "Arial_black.ttf",
    "Lobster.ttf",
]


def check_fonts_presence():
    logger.info(f"Проверка наличия шрифтов в {FONT_DIR}...")
    for fname in AVAILABLE_FONT_FILES:
        path = os.path.join(FONT_DIR, fname)
        if os.path.exists(path):
            logger.info(f"Шрифт найден: {fname}")
        else:
            logger.warning(f"Шрифт НЕ найден: {fname}")


def get_donation_keyboard():
    """Клавиатура с кнопкой 'Донат'"""
    keyboard = [[InlineKeyboardButton("Донат", url=DONATION_URL)]]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    chat_type = update.message.chat.type if update.message else 'private'
    reply_markup = get_donation_keyboard()

    if chat_type in ['group', 'supergroup']:
        await update.message.reply_text(
            "Прикрепи фото, и посмотри что получиться!:)\n\n"
            "Чтобы создать мем в группе:\n"
            "1. Отправь фото с подписью: @memfy_bot\n"
            "2. Выбери тип: мем или демотиватор\n"
            "3. Отправь текст в формате 'Верхний|Нижний'",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "Прикрепи фото, и посмотри что получиться!:)\n\n"
            "Как пользоваться:\n"
            "1. Отправь мне фото\n"
            "2. Выбери тип: мем или демотиватор\n"
            "3. Для мема: выбери шрифт, тип, отправь текст\n"
            "4. Для демотиватора: выбери шрифт, размер, цвет, фон, рамку, текст\n\n"
            "Или просто отправь фото с подписью: 'Верхний текст|Нижний текст'\n\n"
            "Бот работает в личке и группах!",
            reply_markup=reply_markup
        )


# ... (все остальные функции до create_demotivator остаются без изменений, кроме кнопок)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {}

    if query.data == "action_cancel":
        if user_id in user_messages:
            for msg_id in list(user_messages[user_id]):
                try:
                    await context.bot.delete_message(chat_id=query.message.chat.id, message_id=msg_id)
                except:
                    pass
            user_messages[user_id] = []
        user_data[user_id] = {}
        await query.edit_message_text("Генерация отменена. Прикрепи новое фото! :)")
        return

    if query.data == "action_back":
        # ... (логика возврата без изменений)
        pass  # оставляем как есть

    # ... (size, color, bg, thickness — без изменений)

    if query.data == "shakalize_menu":
        keyboard = [
            [InlineKeyboardButton("Мягкая", callback_data="shakalize_mild"),
             InlineKeyboardButton("Лёгкая", callback_data="shakalize_light")],
            [InlineKeyboardButton("Средняя", callback_data="shakalize_medium"),
             InlineKeyboardButton("Жёсткая", callback_data="shakalize_hard")],
            [InlineKeyboardButton("Экстремальная", callback_data="shakalize_extreme")],
            [InlineKeyboardButton("Назад", callback_data="action_back"),
             InlineKeyboardButton("Отмена", callback_data="action_cancel")],
        ]
        await query.edit_message_text("Выбери уровень шакализации:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if query.data.startswith("shakalize_"):
        level = query.data.split('_')[-1]
        if level == "glitch":
            await query.edit_message_text("Глитч-эффект удалён.")
            return
        # ... остальная логика шакализации без глитча


# === КЛЮЧЕВАЯ ФУНКЦИЯ: create_demotivator (обновлена) ===
def create_demotivator(photo_bytes: io.BytesIO, top_text: str, bottom_text: str, 
                      font_size: dict = None, font_file: str = "Roboto_Bold.ttf", 
                      demotivator_type: str = "type_normal", font_color: str = "white",
                      border_thickness: int = 10, bg_color: tuple = (0, 0, 0)) -> io.BytesIO:
    if font_size is None:
        font_size = {"top": 40, "bottom": 28}
    top_font_size = font_size.get("top", 40)
    bottom_font_size = font_size.get("bottom", 28)

    color_map = {
        "red": (255, 0, 0), "white": (255, 255, 255), "yellow": (255, 255, 0),
        "orange": (255, 165, 0), "blue": (0, 0, 255), "green": (0, 255, 0),
        "purple": (128, 0, 128), "brown": (165, 42, 42), "black": (0, 0, 0),
        "gray": (128, 128, 128), "pink": (255, 192, 203),
    }
    text_color = color_map.get(font_color, (255, 255, 255))

    # === Определяем цвета обводки и водяного знака ===
    is_black_bg = bg_color == (0, 0, 0)
    border_color = (255, 255, 255) if is_black_bg else (100, 100, 100)  # белая или серая
    watermark_color = (255, 255, 255, 180) if is_black_bg else (50, 50, 50, 180)  # светлый или тёмный

    photo_bytes.seek(0)
    image = Image.open(photo_bytes)
    if getattr(image, 'is_animated', False):
        image = image.convert('RGB')
    if image.mode != 'RGB':
        image = image.convert('RGB')

    STANDARD_SIZE = 512
    if image.size != (STANDARD_SIZE, STANDARD_SIZE):
        image = image.resize((STANDARD_SIZE, STANDARD_SIZE), Image.Resampling.LANCZOS)
    img_width, img_height = STANDARD_SIZE, STANDARD_SIZE

    padding = 30
    border_thickness = int(border_thickness or 10)
    total_padding = padding + border_thickness
    top_space = 80 if demotivator_type == "type_normal" else 20
    demotivator_width = img_width + (total_padding * 2)
    demotivator_height = img_height + (total_padding * 2) + (200 if demotivator_type == "type_normal" else 120)

    demotivator = Image.new('RGB', (demotivator_width, demotivator_height), color=bg_color)
    photo_x = total_padding
    photo_y = total_padding + top_space
    demotivator.paste(image, (photo_x, photo_y))
    draw = ImageDraw.Draw(demotivator)

    # === Рамка (обводка) ===
    frame_x1 = photo_x - border_thickness
    frame_y1 = photo_y - border_thickness
    frame_x2 = photo_x + img_width + border_thickness - 1
    frame_y2 = photo_y + img_height + border_thickness - 1
    for i in range(border_thickness):
        draw.rectangle([frame_x1 - i, frame_y1 - i, frame_x2 + i, frame_y2 + i],
                       outline=border_color, width=1)

    # === Шрифты ===
    font_paths = [os.path.join(FONT_DIR, font_file), font_file]
    font_large = font_small = ImageFont.load_default()
    for path in font_paths:
        try:
            font_large = ImageFont.truetype(path, top_font_size)
            font_small = ImageFont.truetype(path, bottom_font_size)
            break
        except Exception as e:
            logger.warning(f"Шрифт не загружен: {e}")

    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        return lines if lines else [text]

    # === Текст ===
    if demotivator_type == "type_normal" and top_text:
        max_text_width = demotivator_width - 100
        top_lines = wrap_text(top_text, font_large, max_text_width)
        y_offset = 20
        for line in top_lines:
            bbox = draw.textbbox((0, 0), line, font=font_large)
            text_width = bbox[2] - bbox[0]
            x = (demotivator_width - text_width) // 2
            draw.text((x, y_offset), line, fill=text_color, font=font_large)
            y_offset += int(top_font_size * 1.25)

    if bottom_text:
        max_text_width = demotivator_width - 100
        bottom_lines = wrap_text(bottom_text, font_small, max_text_width)
        y_offset = photo_y + img_height + border_thickness + 30
        for line in bottom_lines:
            bbox = draw.textbbox((0, 0), line, font=font_small)
            text_width = bbox[2] - bbox[0]
            x = (demotivator_width - text_width) // 2
            draw.text((x, y_offset), line, fill=text_color, font=font_small)
            y_offset += int(bottom_font_size * 1.25)

    # === Водяной знак ===
    watermark_text = "@memfy_bot"
    watermark_size = 16
    watermark_font = ImageFont.load_default()
    for path in [os.path.join(FONT_DIR, "Roboto_Bold.ttf"), "Roboto_Bold.ttf"]:
        try:
            watermark_font = ImageFont.truetype(path, watermark_size)
            break
        except:
            continue

    bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
    w_w, w_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    wm_img = Image.new('RGBA', (w_w + 10, w_h + 5), (0, 0, 0, 0))
    wm_draw = ImageDraw.Draw(wm_img)
    wm_draw.text((5, 0), watermark_text, fill=watermark_color, font=watermark_font)

    offset = 15
    corners = [
        (offset, offset),
        (demotivator_width - w_w - offset, offset),
        (offset, demotivator_height - w_h - offset),
        (demotivator_width - w_w - offset, demotivator_height - w_h - offset),
    ]
    wm_x, wm_y = random.choice(corners)
    demotivator_rgba = demotivator.convert('RGBA')
    demotivator_rgba.paste(wm_img, (wm_x, wm_y), wm_img)
    demotivator = demotivator_rgba.convert('RGB')

    output = io.BytesIO()
    demotivator.save(output, format='JPEG', quality=95)
    output.seek(0)
    return output


# === УДАЛЕНИЕ ГЛИТЧА ИЗ shakalize_image ===
def shakalize_image(photo_bytes: io.BytesIO, intensity: str = 'hard') -> io.BytesIO:
    photo_bytes.seek(0)
    im = Image.open(photo_bytes).convert('RGB')
    if intensity == 'glitch':
        intensity = 'hard'  # fallback

    levels = {
        'mild': (0.8, 6, 50),
        'light': (0.6, 5, 35),
        'medium': (0.35, 4, 20),
        'hard': (0.14, 3, 8),
        'extreme': (0.05, 2, 5),
    }
    downscale, poster_bits, jpeg_quality = levels.get(intensity, levels['hard'])

    w, h = im.size
    new_w, new_h = max(2, int(w * downscale)), max(2, int(h * downscale))
    im_small = im.resize((new_w, new_h), Image.Resampling.NEAREST)
    im_pixel = im_small.resize((w, h), Image.Resampling.NEAREST)
    im_poster = ImageOps.posterize(im_pixel, poster_bits)
    im_blur = im_poster.filter(ImageFilter.GaussianBlur(1))
    im_enh = ImageOps.autocontrast(im_blur)

    out = io.BytesIO()
    im_enh.save(out, format='JPEG', quality=jpeg_quality)
    final = Image.open(out).convert('P', palette=Image.ADAPTIVE, colors=64).convert('RGB')
    final_out = io.BytesIO()
    final.save(final_out, format='JPEG', quality=max(2, jpeg_quality))
    final_out.seek(0)
    return final_out


# === main() без изменений ===
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Ошибка: Установите TELEGRAM_BOT_TOKEN")
        return
    check_fonts_presence()
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("size", size_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.PHOTO | filters.ANIMATION, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()