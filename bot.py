import logging
import random
import os
import shlex
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import io
try:
    import moviepy.editor as mp
    VIDEO_SUPPORT = True
    logging.info("MoviePy загружен успешно.")
except ImportError as e:
    VIDEO_SUPPORT = False
    logging.warning(f"MoviePy не установлен: {e}. Видео-функции отключены.")

# Кэш шрифтов для производительности
font_cache = {}

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
            "Прикрепи фото, и посмотри что получиться!:)\n\n"
            "В группе:\n"
            "1. Отправь фото с подписью: @memfy_bot\n"
            "2. Выбери тип\n"
            "3. Отправь текст: 'Верхний|Нижний'"
        )
    else:
        await update.message.reply_text(
            "Прикрепи фото, и посмотри что получиться!:)\n\n"
            "Как пользоваться:\n"
            "1. Отправь фото\n"
            "2. Выбери тип: мем или демотиватор\n"
            "3. Настрой шрифт, размер, цвет, фон, рамку\n"
            "4. Отправь текст: 'Верхний|Нижний'\n\n"
            "Или просто фото + подпись с текстом.\n"
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
            logger.error(f"Шакализация: {e}")
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


# === ОБРАБОТКА ФОТО ===
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_type = update.message.chat.type

    # GIF или фото
    if update.message.animation:
        file = await context.bot.get_file(update.message.animation.file_id)
        is_gif = True
        media_type = 'gif'
    else:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        is_gif = False
        media_type = 'photo'

    photo_bytes = io.BytesIO()
    await file.download_to_memory(photo_bytes)
    photo_bytes.seek(0)

    # Проверка размера (только для фото, GIF без лимита)
    if not is_gif and len(photo_bytes.getvalue()) > 50 * 1024 * 1024:
        await update.message.reply_text("Файл слишком большой (макс 50MB).")
        return

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
                    mention = caption[e.offset:e.offset+e.length].lower()
                    if mention in [f"@memfy_bot", f"@{bot_username}"]:
                        mentioned = True
                        break
        if not mentioned:
            return
        caption = caption.replace(f"@{bot_username}", "").replace("@memfy_bot", "").strip()

    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['photo'] = photo_bytes
    user_data[user_id]['is_gif'] = is_gif
    user_data[user_id]['media_type'] = media_type

    if caption and '|' in caption:
        texts = caption.split('|', 1)
        user_data[user_id]['caption_top'] = texts[0].strip()
        user_data[user_id]['caption_bottom'] = texts[1].strip() if len(texts) > 1 else ""

    # Обработка GIF с текстом
    if is_gif and 'gif_text' in user_data[user_id]:
        text = user_data[user_id]['gif_text']
        options = user_data[user_id].get('options', {})
        try:
            result = add_text_to_gif(photo_bytes, text, options)
            await update.message.reply_animation(animation=result, caption="GIF с текстом готов!\n\n@memfy_bot")
            user_data[user_id].pop('gif_text', None)
            user_data[user_id].pop('options', None)
            user_data[user_id].pop('photo', None)
            return
        except Exception as e:
            logger.error(f"Ошибка GIF: {e}")
            await update.message.reply_text("Ошибка обработки GIF. Проверьте формат файла.")

    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(update.message.message_id)

    keyboard = [
        [InlineKeyboardButton("Классический мем", callback_data="meme_classic")],
        [InlineKeyboardButton("Демотиватор", callback_data="meme_demotivator")],
        [InlineKeyboardButton("Зашакалить", callback_data="shakalize_menu")],
    ]
    sent = await update.message.reply_text(
        "Фото получено!\n\nВыбери действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    user_messages[user_id].append(sent.message_id)


# === ОБРАБОТКА ВИДЕО ===
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_type = update.message.chat.type

    video = update.message.video
    file = await context.bot.get_file(video.file_id)
    video_bytes = io.BytesIO()
    await file.download_to_memory(video_bytes)
    video_bytes.seek(0)

    # Проверка размера
    if len(video_bytes.getvalue()) > 50 * 1024 * 1024:
        await update.message.reply_text("Файл слишком большой (макс 50MB).")
        return

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
                    mention = caption[e.offset:e.offset+e.length].lower()
                    if mention in [f"@memfy_bot", f"@{bot_username}"]:
                        mentioned = True
                        break
        if not mentioned:
            return
        caption = caption.replace(f"@{bot_username}", "").replace("@memfy_bot", "").strip()

    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['video'] = video_bytes

    if 'video_text' in user_data[user_id]:
        # Обработка с текстом
        text = user_data[user_id]['video_text']
        options = user_data[user_id].get('options', {})
        try:
            result = add_text_to_video(video_bytes, text, options)
            await update.message.reply_video(video=result, caption="Видео с текстом готово!\n\n@memfy_bot")
            user_data[user_id].pop('video_text', None)
            user_data[user_id].pop('options', None)
            user_data[user_id].pop('video', None)
        except Exception as e:
            logger.error(f"Ошибка видео: {e}")
            await update.message.reply_text("Ошибка обработки видео. Попробуйте файл меньшего размера.")
    else:
        await update.message.reply_text("Видео получено. Используй /video_text для добавления текста.")


# === ОБРАБОТКА ТЕКСТА ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or 'photo' not in user_data[user_id]:
        if update.message.chat.type == 'private':
            await update.message.reply_text("Сначала отправь фото.")
        return

    meme_type = user_data[user_id].get('meme_type')
    if not meme_type:
        await update.message.reply_text("Сначала выбери тип мема.")
        return

    text = update.message.text.strip()
    photo_bytes = user_data[user_id]['photo']
    photo_bytes.seek(0)

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
            if is_gif:
                text = f"{top}|{bottom}" if top and bottom else (top or bottom)
                meme = add_text_to_gif(photo_bytes, text, {'font': font, 'position': 'top' if top and not bottom else 'bottom'})
                await update.message.reply_animation(animation=meme, caption="Готово!\n\n@memfy_bot")
            else:
                meme = create_classic_meme(photo_bytes, top, bottom, font)
                await update.message.reply_photo(photo=meme, caption="Готово!\n\n@memfy_bot")

        else:  # демотиватор
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
                photo_bytes, top, bottom,
                font_size=user_data[user_id].get('font_size'),
                font_file=user_data[user_id]['font_file'],
                demotivator_type=dtype,
                font_color=user_data[user_id].get('font_color', 'white'),
                border_thickness=user_data[user_id].get('border_thickness', 10),
                bg_color=user_data[user_id].get('bg_color', (0, 0, 0))
            )
            await update.message.reply_photo(photo=demotivator, caption="Демотиватор готов!\n\n@memfy_bot")

        # Очистка
        for key in ['photo', 'meme_type', 'classic_font', 'classic_type', 'is_gif', 'font_file', 'font_size', 'font_color', 'bg_color', 'border_thickness', 'demotivator_type']:
            user_data[user_id].pop(key, None)

    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")
        await update.message.reply_text("Ошибка обработки файла. Проверьте формат и размер файла.")


# === КЛАССИЧЕСКИЙ МЕМ ===
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

    def draw_outline(text, pos, fill=(255,255,255), outline=(0,0,0), width=2):
        x, y = pos
        for adj in range(-width, width+1):
            for adj2 in range(-width, width+1):
                if adj or adj2:
                    draw.text((x+adj, y+adj2), text, font=font, fill=outline)
        draw.text(pos, text, font=font, fill=fill)

    def wrap(text, max_w):
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

    if top_text:
        lines = wrap(top_text, w - 40)
        y = 10
        for line in lines:
            tw = draw.textbbox((0,0), line, font=font)[2]
            draw_outline(line, ((w - tw) // 2, y))
            y += int(font_size * 1.3)

    if bottom_text:
        lines = wrap(bottom_text, w - 40)
        y = h - len(lines) * int(font_size * 1.3) - 10
        for line in lines:
            tw = draw.textbbox((0,0), line, font=font)[2]
            draw_outline(line, ((w - tw) // 2, y))
            y += int(font_size * 1.3)

    # Водяной знак
    wm_text = "@memfy_bot"
    wm_font = ImageFont.truetype(os.path.join(FONT_DIR, "Roboto_Bold.ttf"), 16) if os.path.exists(os.path.join(FONT_DIR, "Roboto_Bold.ttf")) else ImageFont.load_default()
    tw, th = draw.textbbox((0,0), wm_text, font=wm_font)[2:]
    wm_img = Image.new('RGBA', (tw + 10, th + 5), (0,0,0,0))
    wm_draw = ImageDraw.Draw(wm_img)
    wm_draw.text((5,0), wm_text, fill=(255,255,255,128), font=wm_font)
    corners = [(10,10), (w-tw-20,10), (10,h-th-20), (w-tw-20,h-th-20)]
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
        "red": (255,0,0), "white": (255,255,255), "yellow": (255,255,0), "orange": (255,165,0),
        "blue": (0,0,255), "green": (0,255,0), "purple": (128,0,128), "brown": (165,42,42),
        "black": (0,0,0), "gray": (128,128,128), "pink": (255,192,203),
    }
    text_color = color_map.get(font_color, (255,255,255))

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
        draw.rectangle([x1-i, y1-i, x2+i, y2+i], outline=border_color, width=1)

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
            if draw.textbbox((0,0), test, font=font)[2] <= max_w:
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
            tw = draw.textbbox((0,0), line, font=font_large)[2]
            draw.text(((dw - tw) // 2, y), line, fill=text_color, font=font_large)
            y += int(top_fs * 1.25)

    if bottom_text:
        lines = wrap(bottom_text, font_small, dw - 100)
        y = total_pad + h + top_space + border_thickness + 30
        for line in lines:
            tw = draw.textbbox((0,0), line, font=font_small)[2]
            draw.text(((dw - tw) // 2, y), line, fill=text_color, font=font_small)
            y += int(bottom_fs * 1.25)

    # Водяной знак
    wm_text = "@memfy_bot"
    wm_font = ImageFont.truetype(os.path.join(FONT_DIR, "Roboto_Bold.ttf"), 16) if os.path.exists(os.path.join(FONT_DIR, "Roboto_Bold.ttf")) else ImageFont.load_default()
    tw, th = draw.textbbox((0,0), wm_text, font=wm_font)[2:]
    wm_img = Image.new('RGBA', (tw + 10, th + 5), (0,0,0,0))
    wm_draw = ImageDraw.Draw(wm_img)
    wm_draw.text((5,0), wm_text, fill=watermark_color, font=wm_font)
    corners = [(15,15), (dw-tw-25,15), (15,dh-th-25), (dw-tw-25,dh-th-25)]
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


# === ДОБАВИТЬ ТЕКСТ К GIF ===
def add_text_to_gif(gif_bytes: io.BytesIO, text: str, options: dict = None) -> io.BytesIO:
    if options is None:
        options = {}
    font_name = options.get('font', 'Impact.ttf')
    color = options.get('color', 'white')
    position = options.get('position', 'bottom')
    animate = options.get('animate', 'none')

    # Цвета
    color_map = {
        "red": (255,0,0), "white": (255,255,255), "yellow": (255,255,0), "orange": (255,165,0),
        "blue": (0,0,255), "green": (0,255,0), "purple": (128,0,128), "brown": (165,42,42),
        "black": (0,0,0), "gray": (128,128,128), "pink": (255,192,203),
    }
    text_color = color_map.get(color, (255,255,255))

    # Загрузка GIF
    gif = Image.open(gif_bytes)
    frames = []
    durations = []

    try:
        while True:
            frame = gif.convert('RGBA')
            frames.append(frame)
            durations.append(gif.info.get('duration', 100))
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass

    # Шрифт из кэша
    font_key = font_name
    if font_key not in font_cache:
        font_paths = [os.path.join(FONT_DIR, font_name), font_name]
        font_cache[font_key] = ImageFont.load_default()
        for path in font_paths:
            try:
                font_cache[font_key] = ImageFont.truetype(path, 40)
                break
            except Exception as e:
                logger.warning(f"Не удалось загрузить шрифт {path}: {e}")
    font = font_cache[font_key]

    # Обработка кадров (ограничить до 100 кадров для производительности)
    processed_frames = []
    max_frames = min(len(frames), 100)
    for i in range(max_frames):
        frame = frames[i]
        draw = ImageDraw.Draw(frame)
        w, h = frame.size

        # Позиция
        if position == 'top':
            y = 10
        elif position == 'center':
            y = h // 2 - 20
        else:  # bottom
            y = h - 60

        # Анимация
        if animate == 'fade':
            alpha = max(128, int(255 * (i / max(1, max_frames - 1))))
            text_color_with_alpha = text_color + (alpha,)
        else:
            text_color_with_alpha = text_color

        # Текст
        tw, th = draw.textbbox((0,0), text, font=font)[2:]
        draw.text(((w - tw) // 2, y), text, fill=text_color_with_alpha, font=font)

        # Водяной знак
        wm_text = "@memfy_bot"
        wm_font_key = "Roboto_Bold.ttf"
        if wm_font_key not in font_cache:
            wm_path = os.path.join(FONT_DIR, "Roboto_Bold.ttf")
            font_cache[wm_font_key] = ImageFont.truetype(wm_path, 16) if os.path.exists(wm_path) else ImageFont.load_default()
        wm_font = font_cache[wm_font_key]
        tw_wm, th_wm = draw.textbbox((0,0), wm_text, font=wm_font)[2:]
        wm_img = Image.new('RGBA', (int(tw_wm + 10), int(th_wm + 5)), (0,0,0,0))
        wm_draw = ImageDraw.Draw(wm_img)
        wm_draw.text((5,0), wm_text, fill=(255,255,255,128), font=wm_font)
        frame.paste(wm_img, (10, 10), wm_img)

        processed_frames.append(frame)

    # Сохранение GIF
    out = io.BytesIO()
    processed_frames[0].save(out, format='GIF', save_all=True, append_images=processed_frames[1:], duration=durations, loop=0)
    out.seek(0)
    return out


# === ДОБАВИТЬ ТЕКСТ К ВИДЕО ===
def add_text_to_video(video_bytes: io.BytesIO, text: str, options: dict = None) -> io.BytesIO:
    if options is None:
        options = {}
    font_name = options.get('font', 'Impact.ttf')
    color = options.get('color', 'white')
    position = options.get('position', 'bottom')
    animate = options.get('animate', 'none')

    # Цвета
    color_map = {
        "red": (255,0,0), "white": (255,255,255), "yellow": (255,255,0), "orange": (255,165,0),
        "blue": (0,0,255), "green": (0,255,0), "purple": (128,0,128), "brown": (165,42,42),
        "black": (0,0,0), "gray": (128,128,128), "pink": (255,192,203),
    }
    text_color = color_map.get(color, (255,255,255))

    # Сохранить видео во временный файл с уникальным именем
    temp_video = f'temp_video_{uuid.uuid4()}.mp4'
    with open(temp_video, 'wb') as f:
        f.write(video_bytes.getvalue())

    try:
        # Загрузка видео
        clip = mp.VideoFileClip(temp_video)

        # Функция для добавления текста
        def add_text_frame(frame):
            img = Image.fromarray(frame)
            draw = ImageDraw.Draw(img)
            w, h = img.size

            # Шрифт из кэша
            font_key = font_name
            if font_key not in font_cache:
                font_paths = [os.path.join(FONT_DIR, font_name), font_name]
                font_cache[font_key] = ImageFont.load_default()
                for path in font_paths:
                    try:
                        font_cache[font_key] = ImageFont.truetype(path, 40)
                        break
                    except Exception as e:
                        logger.warning(f"Не удалось загрузить шрифт {path}: {e}")
            font = font_cache[font_key]

            # Позиция
            if position == 'top':
                y = 10
            elif position == 'center':
                y = h // 2 - 20
            else:  # bottom
                y = h - 60

            # Анимация (простая fade)
            if animate == 'fade':
                alpha = 255  # Для простоты, без fade по времени
            else:
                alpha = 255

            text_color_with_alpha = text_color + (alpha,) if alpha < 255 else text_color

            # Текст
            tw, th = draw.textbbox((0,0), text, font=font)[2:]
            draw.text(((w - tw) // 2, y), text, fill=text_color_with_alpha, font=font)

            # Водяной знак
            wm_text = "@memfy_bot"
            wm_font_key = "Roboto_Bold.ttf"
            if wm_font_key not in font_cache:
                wm_path = os.path.join(FONT_DIR, "Roboto_Bold.ttf")
                font_cache[wm_font_key] = ImageFont.truetype(wm_path, 16) if os.path.exists(wm_path) else ImageFont.load_default()
            wm_font = font_cache[wm_font_key]
            tw_wm, th_wm = draw.textbbox((0,0), wm_text, font=wm_font)[2:]
            wm_img = Image.new('RGBA', (tw_wm + 10, th_wm + 5), (0,0,0,0))
            wm_draw = ImageDraw.Draw(wm_img)
            wm_draw.text((5,0), wm_text, fill=(255,255,255,128), font=wm_font)
            img.paste(wm_img, (10, 10), wm_img)

            return np.array(img)

        # Применить функцию к каждому кадру
        video_with_text = clip.fl_image(add_text_frame)

        # Сохранить в BytesIO (ограничить длительность для производительности)
        if clip.duration > 60:
            clip = clip.subclip(0, 60)  # Ограничить до 60 секунд
        out = io.BytesIO()
        temp_output = f'temp_output_{uuid.uuid4()}.mp4'
        video_with_text.write_videofile(temp_output, codec='libx264', audio_codec='aac', fps=24, verbose=False, logger=None)
        with open(temp_output, 'rb') as f:
            out.write(f.read())
        out.seek(0)

    except Exception as e:
        logger.error(f"Ошибка обработки видео: {e}")
        raise
    finally:
        # Очистка
        try:
            os.remove(temp_video)
        except FileNotFoundError:
            pass
        try:
            os.remove(temp_output)
        except (FileNotFoundError, NameError):
            pass

    return out


# === КОМАНДЫ ДЛЯ GIF И ВИДЕО ===
async def gif_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /gif_text \"Текст\" --font Arial --color red --position bottom --animate fade")
        return
    text = args[0].strip()
    if not text:
        await update.message.reply_text("Текст не может быть пустым.")
        return
    options = parse_options(args[1:])
    user_data[user_id] = {'gif_text': text, 'options': options}
    await update.message.reply_text("Отправь GIF для добавления текста.")

async def video_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not VIDEO_SUPPORT:
        await update.message.reply_text("Видео-функции отключены из-за отсутствия зависимостей.")
        return
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /video_text \"Текст\" --font Arial --color red --position bottom --animate fade")
        return
    text = args[0].strip()
    if not text:
        await update.message.reply_text("Текст не может быть пустым.")
        return
    options = parse_options(args[1:])
    user_data[user_id] = {'video_text': text, 'options': options}
    await update.message.reply_text("Отправь видео для добавления текста.")

def parse_options(args):
    options = {}
    try:
        parsed = shlex.split(' '.join(args))
        i = 0
        while i < len(parsed):
            if parsed[i].startswith('--'):
                key = parsed[i][2:]
                if i + 1 < len(parsed) and not parsed[i+1].startswith('--'):
                    options[key] = parsed[i+1]
                    i += 2
                else:
                    options[key] = True
                    i += 1
            else:
                i += 1
    except ValueError:
        # Fallback to simple parsing if shlex fails
        i = 0
        while i < len(args):
            if args[i].startswith('--'):
                key = args[i][2:]
                if i + 1 < len(args) and not args[i+1].startswith('--'):
                    options[key] = args[i+1]
                    i += 2
                else:
                    options[key] = True
                    i += 1
            else:
                i += 1
    return options

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
    app.add_handler(CommandHandler("gif_text", gif_text_command))
    app.add_handler(CommandHandler("video_text", video_text_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.ANIMATION, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()