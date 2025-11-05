import logging
import random
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import io
import tempfile

# moviepy используется для обработки GIF/видео
try:
    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
    MOVIEPY_AVAILABLE = True
except Exception:
    MOVIEPY_AVAILABLE = False

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === ШРИФТЫ В ТОЙ ЖЕ ПАПКЕ, ЧТО И bot.py ===
FONT_DIR = os.path.dirname(__file__)  # ← шрифты рядом с bot.py

# === ХРАНИЛИЩЕ ===
user_data = {}
user_messages = {}

# === СПИСОК ШРИФТОВ (должны быть в той же папке) ===
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
    """Проверка наличия шрифтов в папке с bot.py"""
    logger.info(f"Проверка шрифтов в: {FONT_DIR}")
    for fname in AVAILABLE_FONT_FILES:
        path = os.path.join(FONT_DIR, fname)
        if os.path.exists(path):
            logger.info(f"Шрифт найден: {fname}")
        else:
            logger.warning(f"Шрифт НЕ найден: {fname} (ищется: {path})")


# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.message.chat.type if update.message else 'private'

    if chat_type in ['group', 'supergroup']:
        await update.message.reply_text(
            "Прикрепи фото/гиф/видео и попробуй создать мем!:)\n\n"
            "В группе:\n"
            "1. Отправь медиа с подписью: @memfy_bot\n"
            "2. Выбери тип\n"
            "3. Отправь текст: 'Верхний|Нижний'"
        )
    else:
        await update.message.reply_text(
            "Прикрепи фото/гиф/видео и посмотри что получится!:)\n\n"
            "Как пользоваться:\n"
            "1. Отправь фото/гиф/видео\n"
            "2. Выбери тип: мем или демотиватор\n"
            "3. Настрой шрифт, размер, цвет, фон, рамку\n"
            "4. Отправь текст: 'Верхний|Нижний'\n\n"
            "Работает в личке и группах!"
        )


# === /size (для демотиваторов) ===
async def size_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Маленький", callback_data="size_small"),
         InlineKeyboardButton("Средний", callback_data="size_medium")],
        [InlineKeyboardButton("Большой", callback_data="size_large"),
         InlineKeyboardButton("Очень большой", callback_data="size_xlarge")],
        [InlineKeyboardButton("Назад", callback_data="action_back"),
         InlineKeyboardButton("Отмена", callback_data="action_cancel")],
    ]
    await update.message.reply_text(
        "Выбери размер шрифта:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# === КНОПКИ ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {}

    # === ОТМЕНА ===
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

    # === НАЗАД ===
    if query.data == "action_back":
        ud = user_data.get(user_id, {})
        if 'font_file' in ud and ud.get('meme_type') == 'meme_demotivator':
            ud.pop('font_file', None)
            await query.edit_message_text("Выбери шрифт:", reply_markup=show_font_selection(user_id))
            return
        if 'font_size' in ud:
            ud.pop('font_size', None)
            keyboard = [
                [InlineKeyboardButton("Маленький", callback_data="size_small"),
                 InlineKeyboardButton("Средний", callback_data="size_medium")],
                [InlineKeyboardButton("Большой", callback_data="size_large"),
                 InlineKeyboardButton("Очень большой", callback_data="size_xlarge")],
                [InlineKeyboardButton("Назад", callback_data="action_back"),
                 InlineKeyboardButton("Отмена", callback_data="action_cancel")],
            ]
            await query.edit_message_text("Выбери размер:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        if 'demotivator_type' in ud:
            ud.pop('demotivator_type', None)
            await query.edit_message_text("Выбери шрифт:", reply_markup=show_font_selection(user_id))
            return
        if 'meme_type' in ud:
            ud.pop('meme_type', None)
            keyboard = [
                [InlineKeyboardButton("Классический мем", callback_data="meme_classic")],
                [InlineKeyboardButton("Демотиватор", callback_data="meme_demotivator")],
                [InlineKeyboardButton("Зашакалить", callback_data="shakalize_menu")],
                [InlineKeyboardButton("Отмена", callback_data="action_cancel")],
            ]
            await query.edit_message_text("Выбери тип:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        await query.edit_message_text("Нечего возвращать.")
        return

    # === РАЗМЕР ШРИФТА ===
    size_map = {
        "size_small": {"top": 30, "bottom": 20},
        "size_medium": {"top": 40, "bottom": 28},
        "size_large": {"top": 50, "bottom": 35},
        "size_xlarge": {"top": 60, "bottom": 40},
    }
    if query.data in size_map:
        user_data[user_id]['font_size'] = size_map[query.data]
        size_names = {"size_small": "Маленький", "size_medium": "Средний", "size_large": "Большой", "size_xlarge": "Очень большой"}
        keyboard = [
            [InlineKeyboardButton("Красный", callback_data="color_red"), InlineKeyboardButton("Белый", callback_data="color_white")],
            [InlineKeyboardButton("Жёлтый", callback_data="color_yellow"), InlineKeyboardButton("Оранжевый", callback_data="color_orange")],
            [InlineKeyboardButton("Синий", callback_data="color_blue"), InlineKeyboardButton("Зелёный", callback_data="color_green")],
            [InlineKeyboardButton("Фиолетовый", callback_data="color_purple"), InlineKeyboardButton("Коричневый", callback_data="color_brown")],
            [InlineKeyboardButton("Чёрный", callback_data="color_black"), InlineKeyboardButton("Серый", callback_data="color_gray")],
            [InlineKeyboardButton("Розовый", callback_data="color_pink"), InlineKeyboardButton("Назад", callback_data="action_back")],
        ]
        await query.edit_message_text(
            f"Размер: **{size_names[query.data]}**\n\nВыбери цвет текста:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # === ЦВЕТ ТЕКСТА ===
    color_map = {
        "color_red": "red", "color_white": "white", "color_yellow": "yellow", "color_orange": "orange",
        "color_blue": "blue", "color_green": "green", "color_purple": "purple", "color_brown": "brown",
        "color_black": "black", "color_gray": "gray", "color_pink": "pink",
    }
    color_names = {v: k.split('_')[1].capitalize() for k, v in color_map.items()}
    if query.data in color_map:
        user_data[user_id]['font_color'] = color_map[query.data]
        if user_data[user_id].get('meme_type') == 'meme_demotivator':
            keyboard = [
                [InlineKeyboardButton("Чёрный (классика)", callback_data="bg_black"),
                 InlineKeyboardButton("Белый", callback_data="bg_white")],
                [InlineKeyboardButton("Тёмно-серый", callback_data="bg_dark_gray"),
                 InlineKeyboardButton("Светло-серый", callback_data="bg_light_gray")],
                [InlineKeyboardButton("Синий", callback_data="bg_blue"),
                 InlineKeyboardButton("Зелёный", callback_data="bg_green")],
                [InlineKeyboardButton("Назад", callback_data="action_back")],
            ]
            await query.edit_message_text(
                f"Цвет текста: **{color_names[color_map[query.data]]}**\n\nВыбери фон:",
                parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [
                [InlineKeyboardButton("Тонкая (4px)", callback_data="thickness_thin"),
                 InlineKeyboardButton("Обычная (10px)", callback_data="thickness_normal")],
                [InlineKeyboardButton("Толстая (20px)", callback_data="thickness_thick"),
                 InlineKeyboardButton("Очень толстая (30px)", callback_data="thickness_xthick")],
                [InlineKeyboardButton("Назад", callback_data="action_back"),
                 InlineKeyboardButton("Отмена", callback_data="action_cancel")],
            ]
            await query.edit_message_text(
                f"Цвет текста: **{color_names[color_map[query.data]]}**\n\nВыбери рамку:",
                parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    # === ФОН ===
    bg_map = {
        "bg_black": (0, 0, 0), "bg_white": (255, 255, 255), "bg_dark_gray": (50, 50, 50),
        "bg_light_gray": (200, 200, 200), "bg_blue": (0, 0, 139), "bg_green": (0, 100, 0),
    }
    bg_names = {k: v for k, v in zip(bg_map.keys(), ["Чёрный", "Белый", "Тёмно-серый", "Светло-серый", "Синий", "Зелёный"])}
    if query.data in bg_map:
        user_data[user_id]['bg_color'] = bg_map[query.data]
        keyboard = [
            [InlineKeyboardButton("Тонкая (4px)", callback_data="thickness_thin"),
             InlineKeyboardButton("Обычная (10px)", callback_data="thickness_normal")],
            [InlineKeyboardButton("Толстая (20px)", callback_data="thickness_thick"),
             InlineKeyboardButton("Очень толстая (30px)", callback_data="thickness_xthick")],
            [InlineKeyboardButton("Назад", callback_data="action_back"),
             InlineKeyboardButton("Отмена", callback_data="action_cancel")],
        ]
        await query.edit_message_text(
            f"Фон: **{bg_names[query.data]}**\n\nВыбери рамку:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # === РАМКА ===
    thickness_map = {"thickness_thin": 4, "thickness_normal": 10, "thickness_thick": 20, "thickness_xthick": 30}
    if query.data in thickness_map:
        user_data[user_id]['border_thickness'] = thickness_map[query.data]
        await query.edit_message_text(
            f"Рамка: **{query.data.split('_')[1].capitalize()}**\n\n"
            "Отправь текст:\n"
            "- 'Верхний|Нижний'\n"
            "- 'Текст' (только снизу)",
            parse_mode='Markdown'
        )
        return

    # === ШРИФТЫ ===
    font_map = {
        "font_molodost": "Molodost.ttf", "font_roboto": "Roboto_Bold.ttf",
        "font_times": "Times New Roman Bold Italic.ttf", "font_nougat": "Nougat Regular.ttf",
        "font_maratype": "Maratype Regular.ttf", "font_farabee": "Farabee Bold.ttf",
        "font_impact": "Impact.ttf", "font_anton": "Anton-Regular.ttf",
        "font_comicsans": "Comic Sans MS.ttf", "font_arial_black": "Arial_black.ttf",
    }
    font_names = {k: v.split('.')[0].replace('_', ' ') for k, v in font_map.items()}
    if query.data in font_map:
        user_data[user_id]['font_file'] = font_map[query.data]
        keyboard = [
            [InlineKeyboardButton("Обычный (верх+низ)", callback_data="type_normal")],
            [InlineKeyboardButton("Только снизу", callback_data="type_bottom_only")],
            [InlineKeyboardButton("Назад", callback_data="action_back"),
             InlineKeyboardButton("Отмена", callback_data="action_cancel")],
        ]
        await query.edit_message_text(
            f"Шрифт: **{font_names[query.data]}**\n\nВыбери тип:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # === ТИП МЕМА ===
    if query.data in ["meme_classic", "meme_demotivator"]:
        user_data[user_id]['meme_type'] = query.data
        if user_id not in user_messages:
            user_messages[user_id] = []
        user_messages[user_id].append(query.message.message_id)

        if query.data == "meme_classic":
            keyboard = [
                [InlineKeyboardButton("Impact", callback_data="classic_font_impact")],
                [InlineKeyboardButton("Lobster", callback_data="classic_font_lobster")],
                [InlineKeyboardButton("Назад", callback_data="action_back"),
                 InlineKeyboardButton("Отмена", callback_data="action_cancel")],
            ]
            await query.edit_message_text("Выбран: **Классический мем**\n\nШрифт:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text("Выбран: **Демотиватор**\n\nШрифт:", parse_mode='Markdown', reply_markup=show_font_selection(user_id))
        return

    # === КЛАССИЧЕСКИЙ ШРИФТ ===
    if query.data in ["classic_font_impact", "classic_font_lobster"]:
        fmap = {"classic_font_impact": "Impact.ttf", "classic_font_lobster": "Lobster.ttf"}
        user_data[user_id]['classic_font'] = fmap[query.data]
        keyboard = [
            [InlineKeyboardButton("Верх+низ", callback_data="classic_type_normal")],
            [InlineKeyboardButton("Только низ", callback_data="classic_type_bottom_only")],
            [InlineKeyboardButton("Назад", callback_data="action_back"),
             InlineKeyboardButton("Отмена", callback_data="action_cancel")],
        ]
        await query.edit_message_text(f"Шрифт: **{query.data.split('_')[-1].capitalize()}**\n\nТип:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # === ТИП КЛАССИЧЕСКОГО ===
    if query.data in ["classic_type_normal", "classic_type_bottom_only"]:
        user_data[user_id]['classic_type'] = query.data
        if 'caption_top' in user_data[user_id]:
            # Обработка с подписью
            pass  # (логика в handle_text)
        else:
            instr = "Текст: 'Верхний|Нижний'" if query.data == "classic_type_normal" else "Текст (только снизу)"
            await query.edit_message_text(f"Тип: **{'Верх+низ' if 'normal' in query.data else 'Только низ'}**\n\n{instr}", parse_mode='Markdown')
        return

    # === ТИП ДЕМОТИВАТОРА ===
    if query.data in ["type_normal", "type_bottom_only"]:
        user_data[user_id]['demotivator_type'] = query.data
        keyboard = [
            [InlineKeyboardButton("Маленький", callback_data="size_small"),
             InlineKeyboardButton("Средний", callback_data="size_medium")],
            [InlineKeyboardButton("Большой", callback_data="size_large"),
             InlineKeyboardButton("Очень большой", callback_data="size_xlarge")],
            [InlineKeyboardButton("Назад", callback_data="action_back"),
             InlineKeyboardButton("Отмена", callback_data="action_cancel")],
        ]
        await query.edit_message_text("Тип: **{'Обычный' if 'normal' in query.data else 'Только снизу'}**\n\nРазмер:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # === ШАКАЛИЗАЦИЯ ===
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

    if query.data.startswith("shakalize_") and query.data != "shakalize_menu":
        level = query.data.split('_')[-1]
        if level == "glitch":
            await query.edit_message_text("Глитч удалён.")
            return
        try:
            if 'photo' not in user_data[user_id]:
                await query.edit_message_text("Сначала отправь фото.")
                return
            photo_bytes = user_data[user_id]['photo']
            photo_bytes.seek(0)
            result = shakalize_image(photo_bytes, intensity=level)
            await query.message.reply_photo(photo=result, caption="Зашакалил!")
            if user_id in user_messages:
                for msg_id in user_messages[user_id]:
                    try:
                        await context.bot.delete_message(chat_id=query.message.chat.id, message_id=msg_id)
                    except:
                        pass
                user_messages[user_id] = []
            user_data[user_id].pop('photo', None)
        except Exception as e:
            logger.error(f"Шакализация error: {e}", exc_info=True)
            await query.edit_message_text("Ошибка.")
        return


def show_font_selection(user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Molodost", callback_data="font_molodost")],
        [InlineKeyboardButton("Roboto Bold", callback_data="font_roboto")],
        [InlineKeyboardButton("Times New Roman", callback_data="font_times")],
        [InlineKeyboardButton("Nougat", callback_data="font_nougat")],
        [InlineKeyboardButton("Maratype", callback_data="font_maratype")],
        [InlineKeyboardButton("Farabee Bold", callback_data="font_farabee")],
        [InlineKeyboardButton("Impact", callback_data="font_impact"),
         InlineKeyboardButton("Anton", callback_data="font_anton")],
        [InlineKeyboardButton("Comic Sans", callback_data="font_comicsans"),
         InlineKeyboardButton("Arial Black", callback_data="font_arial_black")],
        [InlineKeyboardButton("Назад", callback_data="action_back"),
         InlineKeyboardButton("Отмена", callback_data="action_cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


# === ОБРАБОТКА МЕДИА (ФОТО / GIF / ВИДЕО) ===
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_type = update.message.chat.type

    is_gif = False
    is_video = False

    # Приоритет: animation (gif), затем video, затем фото
    if update.message.animation:
        file = await context.bot.get_file(update.message.animation.file_id)
        is_gif = True
        duration = update.message.animation.duration
        if duration > 10:
            await update.message.reply_text("GIF слишком длинная (макс 10 сек).")
            return
    elif update.message.video:
        file = await context.bot.get_file(update.message.video.file_id)
        is_video = True
        duration = update.message.video.duration
        if duration > 10:
            await update.message.reply_text("Видео слишком длинное (макс 10 сек).")
            return
    else:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

    # Проверка размера файла (макс 50 MB)
    if file.file_size > 50 * 1024 * 1024:
        await update.message.reply_text("Файл слишком большой (макс 50 MB).")
        return

    media_bytes = io.BytesIO()
    await file.download_to_memory(media_bytes)
    media_bytes.seek(0)

    caption = (update.message.caption or "").strip()
    bot_username = context.bot.username.lower()

    # Группа: проверка упоминания
    if chat_type in ['group', 'supergroup']:
        mentioned = False
        if caption and f"@memfy_bot" in caption.lower():
            mentioned = True
        elif update.message.caption_entities:
            for e in update.message.caption_entities:
                if e.type == "mention":
                    mention = caption[e.offset:e.offset + e.length].lower()
                    if mention in [f"@memfy_bot", f"@{bot_username}"]:
                        mentioned = True
                        break
        if not mentioned:
            return
        caption = caption.replace(f"@{bot_username}", "").replace("@memfy_bot", "").strip()

    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['photo'] = media_bytes
    user_data[user_id]['is_gif'] = is_gif
    user_data[user_id]['is_video'] = is_video

    if caption and '|' in caption:
        texts = caption.split('|', 1)
        user_data[user_id]['caption_top'] = texts[0].strip()
        user_data[user_id]['caption_bottom'] = texts[1].strip() if len(texts) > 1 else ""

    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(update.message.message_id)

    keyboard = [
        [InlineKeyboardButton("Классический мем", callback_data="meme_classic")],
        [InlineKeyboardButton("Демотиватор", callback_data="meme_demotivator")],
        [InlineKeyboardButton("Зашакалить", callback_data="shakalize_menu")],
    ]
    sent = await update.message.reply_text(
        "Медиа получено!\n\nВыбери действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    user_messages[user_id].append(sent.message_id)


# === ОБРАБОТКА ТЕКСТА ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or 'photo' not in user_data[user_id]:
        if update.message.chat.type == 'private':
            await update.message.reply_text("Сначала отправь фото/гиф/видео.")
        return

    meme_type = user_data[user_id].get('meme_type')
    if not meme_type:
        await update.message.reply_text("Сначала выбери тип мема.")
        return

    text = update.message.text.strip()
    media_bytes = user_data[user_id]['photo']
    media_bytes.seek(0)

    try:
        if meme_type == 'meme_classic':
            if 'classic_font' not in user_data[user_id]:
                await update.message.reply_text("Выбери шрифт.")
                return
            ctype = user_data[user_id].get('classic_type', 'classic_type_normal')
            if ctype == 'classic_type_bottom_only':
                top, bottom = "", text
            else:
                if '|' not in text:
                    await update.message.reply_text("Формат: 'Верхний|Нижний'")
                    return
                top, bottom = [t.strip() for t in text.split('|', 1)]

            if user_id in user_messages:
                for msg_id in user_messages[user_id]:
                    try:
                        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=msg_id)
                    except:
                        pass
                user_messages[user_id] = []

            font = user_data[user_id]['classic_font']
            is_gif = user_data[user_id].get('is_gif', False)
            is_video = user_data[user_id].get('is_video', False)

            if is_gif or is_video:
                # Обработка GIF/видео: вложение текста по кадрам
                if not MOVIEPY_AVAILABLE:
                    await update.message.reply_text("Обработка GIF/видео недоступна: отсутствует moviepy.")
                    return
                out_bytes, out_is_gif = await create_classic_meme_video_or_gif(media_bytes, top, bottom, font, prefer_gif=is_gif)
                if out_is_gif:
                    await update.message.reply_animation(animation=out_bytes, caption="Готово!")
                else:
                    await update.message.reply_video(video=out_bytes, caption="Готово!")
            else:
                meme = create_classic_meme(media_bytes, top, bottom, font)
                await update.message.reply_photo(photo=meme, caption="Готово!")

        else:  # демотиватор (только для фото)
            if 'font_file' not in user_data[user_id]:
                await update.message.reply_text("Выбери шрифт.")
                return
            dtype = user_data[user_id].get('demotivator_type', 'type_normal')
            if dtype == 'type_bottom_only':
                top, bottom = "", text
            else:
                if '|' not in text:
                    await update.message.reply_text("Формат: 'Верхний|Нижний'")
                    return
                top, bottom = [t.strip() for t in text.split('|', 1)]

            if user_id in user_messages:
                for msg_id in user_messages[user_id]:
                    try:
                        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=msg_id)
                    except:
                        pass
                user_messages[user_id] = []

            demotivator = create_demotivator(
                media_bytes, top, bottom,
                font_size=user_data[user_id].get('font_size'),
                font_file=user_data[user_id]['font_file'],
                demotivator_type=dtype,
                font_color=user_data[user_id].get('font_color', 'white'),
                border_thickness=user_data[user_id].get('border_thickness', 10),
                bg_color=user_data[user_id].get('bg_color', (0, 0, 0))
            )
            await update.message.reply_photo(photo=demotivator, caption="Демотиватор готов!")

        # Очистка
        for key in ['photo', 'meme_type', 'classic_font', 'classic_type', 'is_gif', 'is_video',
                    'font_file', 'font_size', 'font_color', 'bg_color', 'border_thickness', 'demotivator_type']:
            user_data[user_id].pop(key, None)

    except Exception as e:
        logger.error(f"Ошибка в handle_text: {e}", exc_info=True)
        await update.message.reply_text("Ошибка. Попробуй снова.")


# === КЛАССИЧЕСКИЙ МЕМ (для фото) ===
def create_classic_meme(photo_bytes: io.BytesIO, top_text: str, bottom_text: str, font_file: str = "Impact.ttf") -> io.BytesIO:
    image = Image.open(photo_bytes).convert('RGB')
    w, h = image.size
    font_size = max(40, int(w / 20))
    font_paths = [os.path.join(FONT_DIR, font_file), font_file]
    font = ImageFont.load_default()
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except:
            continue

    draw = ImageDraw.Draw(image)

    def draw_outline(text, pos, fill=(255, 255, 255), outline=(0, 0, 0), width=2):
        x, y = pos
        for adj in range(-width, width + 1):
            for adj2 in range(-width, width + 1):
                if adj or adj2:
                    draw.text((x + adj, y + adj2), text, font=font, fill=outline)
        draw.text(pos, text, font=font, fill=fill)

    def wrap(text, max_w):
        words = text.split()
        lines = []
        line = []
        for word in words:
            test = ' '.join(line + [word])
            if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
                line.append(word)
            else:
                lines.append(' '.join(line))
                line = [word]
        if line:
            lines.append(' '.join(line))
        return lines

    if top_text:
        lines = wrap(top_text, w - 40)
        y = 10
        for line in lines:
            tw = draw.textbbox((0, 0), line, font=font)[2]
            draw_outline(line, ((w - tw) // 2, y))
            y += int(font_size * 1.3)

    if bottom_text:
        lines = wrap(bottom_text, w - 40)
        y = h - len(lines) * int(font_size * 1.3) - 10
        for line in lines:
            tw = draw.textbbox((0, 0), line, font=font)[2]
            draw_outline(line, ((w - tw) // 2, y))
            y += int(font_size * 1.3)

    # Водяной знак
    wm_text = "@memfy_bot"
    wm_font_path = os.path.join(FONT_DIR, "Roboto_Bold.ttf")
    try:
        wm_font = ImageFont.truetype(wm_font_path, 16) if os.path.exists(wm_font_path) else ImageFont.load_default()
    except:
        wm_font = ImageFont.load_default()
    tw, th = draw.textbbox((0, 0), wm_text, font=wm_font)[2:]
    wm_img = Image.new('RGBA', (tw + 10, th + 5), (0, 0, 0, 0))
    wm_draw = ImageDraw.Draw(wm_img)
    wm_draw.text((5, 0), wm_text, fill=(255, 255, 255, 128), font=wm_font)
    corners = [(10, 10), (w - tw - 20, 10), (10, h - th - 20), (w - tw - 20, h - th - 20)]
    image.paste(wm_img, random.choice(corners), wm_img)

    out = io.BytesIO()
    image.save(out, format='JPEG', quality=95)
    out.seek(0)
    return out


# === ДЕМОТИВАТОР (с адаптивной обводкой и водяным знаком) ===
def create_demotivator(photo_bytes: io.BytesIO, top_text: str, bottom_text: str,
                      font_size: dict = None, font_file: str = "Roboto_Bold.ttf",
                      demotivator_type: str = "type_normal", font_color: str = "white",
                      border_thickness: int = 10, bg_color: tuple = (0, 0, 0)) -> io.BytesIO:
    if font_size is None:
        font_size = {"top": 40, "bottom": 28}
    top_fs, bottom_fs = font_size["top"], font_size["bottom"]

    color_map = {
        "red": (255, 0, 0), "white": (255, 255, 255), "yellow": (255, 255, 0), "orange": (255, 165, 0),
        "blue": (0, 0, 255), "green": (0, 255, 0), "purple": (128, 0, 128), "brown": (165, 42, 42),
        "black": (0, 0, 0), "gray": (128, 128, 128), "pink": (255, 192, 203),
    }
    text_color = color_map.get(font_color, (255, 255, 255))

    # Адаптивные цвета
    is_black_bg = bg_color == (0, 0, 0)
    border_color = (255, 255, 255) if is_black_bg else (100, 100, 100)
    watermark_color = (255, 255, 255, 180) if is_black_bg else (50, 50, 50, 180)

    image = Image.open(photo_bytes).convert('RGB')
    STANDARD = 512
    if image.size != (STANDARD, STANDARD):
        image = image.resize((STANDARD, STANDARD), Image.Resampling.LANCZOS)
    w, h = STANDARD, STANDARD

    padding = 30
    total_pad = padding + border_thickness
    top_space = 80 if demotivator_type == "type_normal" else 20
    dw = w + total_pad * 2
    dh = h + total_pad * 2 + (200 if demotivator_type == "type_normal" else 120)

    canvas = Image.new('RGB', (dw, dh), bg_color)
    canvas.paste(image, (total_pad, total_pad + top_space))
    draw = ImageDraw.Draw(canvas)

    # Рамка
    x1, y1 = total_pad - border_thickness, total_pad + top_space - border_thickness
    x2, y2 = total_pad + w + border_thickness - 1, total_pad + h + top_space + border_thickness - 1
    for i in range(border_thickness):
        draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=border_color, width=1)

    # Шрифты
    font_paths = [os.path.join(FONT_DIR, font_file), font_file]
    font_large = font_small = ImageFont.load_default()
    for path in font_paths:
        try:
            font_large = ImageFont.truetype(path, top_fs)
            font_small = ImageFont.truetype(path, bottom_fs)
            break
        except:
            continue

    def wrap(text, font, max_w):
        words = text.split()
        lines = []
        line = []
        for word in words:
            test = ' '.join(line + [word])
            if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
                line.append(word)
            else:
                lines.append(' '.join(line))
                line = [word]
        if line:
            lines.append(' '.join(line))
        return lines

    # Текст
    if top_text and demotivator_type == "type_normal":
        lines = wrap(top_text, font_large, dw - 100)
        y = 20
        for line in lines:
            tw = draw.textbbox((0, 0), line, font=font_large)[2]
            draw.text(((dw - tw) // 2, y), line, fill=text_color, font=font_large)
            y += int(top_fs * 1.25)

    if bottom_text:
        lines = wrap(bottom_text, font_small, dw - 100)
        y = total_pad + h + top_space + border_thickness + 30
        for line in lines:
            tw = draw.textbbox((0, 0), line, font=font_small)[2]
            draw.text(((dw - tw) // 2, y), line, fill=text_color, font=font_small)
            y += int(bottom_fs * 1.25)

    # Водяной знак
    wm_text = "@memfy_bot"
    wm_font_path = os.path.join(FONT_DIR, "Roboto_Bold.ttf")
    try:
        wm_font = ImageFont.truetype(wm_font_path, 16) if os.path.exists(wm_font_path) else ImageFont.load_default()
    except:
        wm_font = ImageFont.load_default()
    tw, th = draw.textbbox((0, 0), wm_text, font=wm_font)[2:]
    wm_img = Image.new('RGBA', (tw + 10, th + 5), (0, 0, 0, 0))
    wm_draw = ImageDraw.Draw(wm_img)
    wm_draw.text((5, 0), wm_text, fill=watermark_color, font=wm_font)
    corners = [(15, 15), (dw - tw - 25, 15), (15, dh - th - 25), (dw - tw - 25, dh - th - 25)]
    canvas.paste(wm_img, random.choice(corners), wm_img)

    out = io.BytesIO()
    canvas.save(out, format='JPEG', quality=95)
    out.seek(0)
    return out


# === ШАКАЛИЗАЦИЯ (без глитча) ===
def shakalize_image(photo_bytes: io.BytesIO, intensity: str = 'hard') -> io.BytesIO:
    im = Image.open(photo_bytes).convert('RGB')
    levels = {
        'mild': (0.8, 6, 50), 'light': (0.6, 5, 35), 'medium': (0.35, 4, 20),
        'hard': (0.14, 3, 8), 'extreme': (0.05, 2, 5),
    }
    down, bits, qual = levels.get(intensity, levels['hard'])
    w, h = im.size
    nw, nh = max(2, int(w * down)), max(2, int(h * down))
    small = im.resize((nw, nh), Image.Resampling.NEAREST)
    pixel = small.resize((w, h), Image.Resampling.NEAREST)
    poster = ImageOps.posterize(pixel, bits)
    blur = poster.filter(ImageFilter.GaussianBlur(1))
    final = ImageOps.autocontrast(blur)
    out = io.BytesIO()
    final.save(out, format='JPEG', quality=qual)
    final = Image.open(out).convert('P', palette=Image.ADAPTIVE, colors=64).convert('RGB')
    final_out = io.BytesIO()
    final.save(final_out, format='JPEG', quality=max(2, qual))
    final_out.seek(0)
    return final_out


# === ОБРАБОТКА GIF/ВИДЕО (moviepy) ===
async def create_classic_meme_video_or_gif(media_bytes: io.BytesIO, top_text: str, bottom_text: str, font_file: str = "Impact.ttf", prefer_gif: bool = True) -> tuple[io.BytesIO, bool]:
    """
    Возвращает (bytes_io, is_gif)
    Если moviepy не доступен — вернёт исходный поток как mp4/gif и флаг False.
    prefer_gif=True попытается вернуть GIF для анимации (если вход GIF) — иначе mp4.
    """
    if not MOVIEPY_AVAILABLE:
        media_bytes.seek(0)
        return media_bytes, False

    # Записываем входной байтстрим во временный файл
    media_bytes.seek(0)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as in_tmp:
        in_tmp.write(media_bytes.read())
        in_path = in_tmp.name

    out_is_gif = prefer_gif
    with tempfile.NamedTemporaryFile(suffix=".gif" if out_is_gif else ".mp4", delete=False) as out_tmp:
        out_path = out_tmp.name

    try:
        clip = VideoFileClip(in_path)
        fontsize = max(20, int(clip.w / 12))
        font_path = os.path.join(FONT_DIR, font_file)
        # TextClip может требовать установки ImageMagick для сложных шрифтов/эффектов.
        # Попытка создать простые TextClip'ы.
        txt_clips = []
        if top_text:
            txt_top = TextClip(top_text, fontsize=fontsize, font=font_path if os.path.exists(font_path) else None,
                               color='white', stroke_color='black', stroke_width=2).set_pos(("center", 10)).set_duration(clip.duration)
            txt_clips.append(txt_top)
        if bottom_text:
            bottom_y = clip.h - fontsize * 1.5 - 10
            txt_bottom = TextClip(bottom_text, fontsize=fontsize, font=font_path if os.path.exists(font_path) else None,
                                  color='white', stroke_color='black', stroke_width=2).set_pos(("center", bottom_y)).set_duration(clip.duration)
            txt_clips.append(txt_bottom)
        comp = CompositeVideoClip([clip, *txt_clips])
        # Пишем результат с оптимизацией: низкое качество, сжатие
        if out_is_gif:
            # Для GIF: низкий fps, оптимизация
            comp.write_gif(out_path, program='imageio', fps=min(10, clip.fps), optimize=True, fuzz=5)
        else:
            # Для видео: низкое качество, сжатие
            comp.write_videofile(out_path, codec='libx264', audio=False, threads=0, preset='ultrafast', bitrate='500k', logger=None)
        # Читаем результат в BytesIO
        with open(out_path, "rb") as f:
            data = f.read()
        out = io.BytesIO(data)
        out.seek(0)
        return out, out_is_gif
    except Exception as e:
        logger.error(f"create_classic_meme_video_or_gif error: {e}", exc_info=True)
        # fallback: вернуть исходный
        media_bytes.seek(0)
        return media_bytes, False
    finally:
        try:
            clip.close()
        except:
            pass
        try:
            os.unlink(in_path)
        except:
            pass
        try:
            os.unlink(out_path)
        except:
            pass


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
    app.add_handler(CallbackQueryHandler(button_callback))
    # Обрабатываем фото, анимации и видео
    app.add_handler(MessageHandler(filters.PHOTO | filters.ANIMATION | filters.VIDEO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()