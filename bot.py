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


def check_fonts_presence():
    """Логируем наличие известных шрифтов в ./fonts"""
    logger.info(f"Проверка наличия шрифтов в {FONT_DIR}...")
    for fname in AVAILABLE_FONT_FILES:
        path = os.path.join(FONT_DIR, fname)
        if os.path.exists(path):
            logger.info(f"Шрифт найден: {fname} ({path})")
        else:
            logger.warning(f"Шрифт НЕ найден: {fname} (ищется по {path})")


def get_donation_keyboard():
    """Клавиатура с кнопкой доната"""
    keyboard = [
        [InlineKeyboardButton("Донат ❤️", url=DONATION_URL)]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    chat_type = update.message.chat.type if update.message else 'private'
    
    keyboard = [
        [InlineKeyboardButton("Поддержать бота 💰", url=DONATION_URL)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if chat_type in ['group', 'supergroup']:
        await update.message.reply_text(
            "Привет! Я бот для создания мемов и демотиваторов.\n\n"
            "Чтобы создать мем в группе:\n"
            "1. Отправь фото с подписью: @memfy_bot\n"
            "2. Выбери тип: классический мем или демотиватор\n"
            "3. Для классического мема - отправь текст в формате 'Верхний|Нижний'\n\n"
            "Или отправь фото с подписью: @memfy_bot Верхний текст|Нижний текст",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "Привет! Я бот для создания мемов и демотиваторов.\n\n"
            "Как пользоваться:\n"
            "1. Отправь мне фото\n"
            "2. Выбери тип: классический мем или демотиватор\n"
            "3. Для классического мема:\n"
            "   - Выбери шрифт\n"
            "   - Выбери тип (верх+низ или только внизу)\n"
            "   - Отправь текст\n"
            "4. Для демотиватора:\n"
            "   - Выбери шрифт\n"
            "   - Выбери тип демотиватора\n"
            "   - Выбери размер, цвет, толщину рамки\n"
            "   - Отправь текст\n\n"
            "Также можно 'зашакалить' фото (сильно ухудшить качество) — кнопка появится после отправки фото.\n\n"
            "Или просто отправь фото с подписью в формате: 'Верхний текст|Нижний текст'\n\n"
            "Бот работает в личных сообщениях и в группах!",
            reply_markup=reply_markup
        )


async def size_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Маленький 📝", callback_data="size_small"),
            InlineKeyboardButton("Средний 📄", callback_data="size_medium"),
        ],
        [
            InlineKeyboardButton("Большой 📰", callback_data="size_large"),
            InlineKeyboardButton("Очень большой 📋", callback_data="size_xlarge"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data="action_back"),
            InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Выбери размер шрифта для демотиватора:",
        reply_markup=reply_markup
    )


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
        await query.edit_message_text("❌ Генерация отменена. Можешь отправить новое фото чтобы начать заново.")
        return

    if query.data == "action_back":
        ud = user_data.get(user_id, {})
        if 'font_file' in ud and ud.get('meme_type') == 'meme_demotivator':
            ud.pop('font_file', None)
            reply_markup = show_font_selection(user_id)
            await query.edit_message_text("⬅️ Возврат: выбери шрифт:", reply_markup=reply_markup)
            return
        if 'font_size' in ud and ud.get('demotivator_type'):
            ud.pop('font_size', None)
            keyboard = [
                [
                    InlineKeyboardButton("Маленький 📝", callback_data="size_small"),
                    InlineKeyboardButton("Средний 📄", callback_data="size_medium"),
                ],
                [
                    InlineKeyboardButton("Большой 📰", callback_data="size_large"),
                    InlineKeyboardButton("Очень большой 📋", callback_data="size_xlarge"),
                ],
                [
                    InlineKeyboardButton("⬅️ Назад", callback_data="action_back"),
                    InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
                ],
            ]
            await query.edit_message_text("⬅️ Возврат: выбери размер шрифта:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        if 'demotivator_type' in ud:
            ud.pop('demotivator_type', None)
            reply_markup = show_font_selection(user_id)
            await query.edit_message_text("⬅️ Возврат: выбери шрифт для демотиватора:", reply_markup=reply_markup)
            return
        if 'meme_type' in ud:
            ud.pop('meme_type', None)
            keyboard = [
                [
                    InlineKeyboardButton("Классический мем 🎨", callback_data="meme_classic"),
                ],
                [
                    InlineKeyboardButton("Демотиватор 📋", callback_data="meme_demotivator"),
                ],
                [
                    InlineKeyboardButton("Зашакалить 🛠️", callback_data="shakalize_menu"),
                ],
                [
                    InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
                ]
            ]
            await query.edit_message_text("⬅️ Возврат: выбери тип мема:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        await query.edit_message_text("Нечего возвращать — отправь новое фото или выбери действие.", reply_markup=None)
        return

    size_map = {
        "size_small": {"top": 30, "bottom": 20},
        "size_medium": {"top": 40, "bottom": 28},
        "size_large": {"top": 50, "bottom": 35},
        "size_xlarge": {"top": 60, "bottom": 40},
    }
    
    if query.data in size_map:
        user_data[user_id]['font_size'] = size_map[query.data]
        
        size_names = {
            "size_small": "Маленький",
            "size_medium": "Средний",
            "size_large": "Большой",
            "size_xlarge": "Очень большой",
        }
        
        keyboard = [
            [
                InlineKeyboardButton("🔴 Красный", callback_data="color_red"),
                InlineKeyboardButton("⚪ Белый", callback_data="color_white"),
            ],
            [
                InlineKeyboardButton("🔵 Синий", callback_data="color_blue"),
                InlineKeyboardButton("🟢 Зелёный", callback_data="color_green"),
            ],
            [
                InlineKeyboardButton("🟣 Фиолетовый", callback_data="color_purple"),
            ],
            [
                InlineKeyboardButton("⬅️ Назад", callback_data="action_back"),
                InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Размер шрифта установлен: **{size_names[query.data]}**\n\n"
            "Выбери цвет шрифта:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    color_map = {
        "color_red": "red",
        "color_white": "white",
        "color_blue": "blue",
        "color_green": "green",
        "color_purple": "purple",
    }
    
    color_names = {
        "color_red": "Красный",
        "color_white": "Белый",
        "color_blue": "Синий",
        "color_green": "Зелёный",
        "color_purple": "Фиолетовый",
    }
    
    if query.data in color_map:
        user_data[user_id]['font_color'] = color_map[query.data]
        
        if user_data.get(user_id, {}).get('meme_type') == 'meme_demotivator':
            keyboard = [
                [
                    InlineKeyboardButton("Тонкая (4px)", callback_data="thickness_thin"),
                    InlineKeyboardButton("Обычная (10px)", callback_data="thickness_normal"),
                ],
                [
                    InlineKeyboardButton("Толстая (20px)", callback_data="thickness_thick"),
                    InlineKeyboardButton("Очень толстая (30px)", callback_data="thickness_xthick"),
                ],
                [
                    InlineKeyboardButton("⬅️ Назад", callback_data="action_back"),
                    InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
                ],
            ]
            await query.edit_message_text(
                f"✅ Цвет шрифта установлен: **{color_names[query.data]}**\n\n"
                "Выбери толщину обводки (рамки) для фотографии в демотиваторе:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        if 'photo' in user_data.get(user_id, {}) and 'font_file' in user_data.get(user_id, {}):
            await query.edit_message_text(
                f"✅ Цвет шрифта установлен: **{color_names[query.data]}**\n\n"
                "Теперь отправь текст в формате:\n"
                "- 'Верхний текст|Нижний текст' (для обычного)\n"
                "- 'Текст' (для типа 'внизу')",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"✅ Цвет шрифта установлен: **{color_names[query.data]}**\n\n"
                "Теперь отправь фото с текстом или просто фото.",
                parse_mode='Markdown'
            )
        return

    thickness_map = {
        "thickness_thin": 4,
        "thickness_normal": 10,
        "thickness_thick": 20,
        "thickness_xthick": 30,
    }
    thickness_names = {
        "thickness_thin": "Тонкая (4px)",
        "thickness_normal": "Обычная (10px)",
        "thickness_thick": "Толстая (20px)",
        "thickness_xthick": "Очень толстая (30px)",
    }
    if query.data in thickness_map:
        user_data[user_id]['border_thickness'] = thickness_map[query.data]
        await query.edit_message_text(
            f"✅ Толщина рамки установлена: **{thickness_names[query.data]}**\n\n"
            "Теперь отправь текст в формате:\n"
            "- 'Верхний текст|Нижний текст' (для обычного)\n"
            "- 'Текст' (для типа 'внизу')",
            parse_mode='Markdown'
        )
        return

    # Обновлённая карта шрифтов с точными именами файлов
    font_map = {
        "font_molodost": "Molodost.ttf",
        "font_roboto": "Roboto_Bold.ttf",
        "font_times": "Times New Roman Bold Italic.ttf",
        "font_nougat": "Nougat Regular.ttf",
        "font_maratype": "Maratype Regular.ttf",
        "font_farabee": "Farabee Bold.ttf",
        "font_impact": "Impact.ttf",
        "font_anton": "Anton-Regular.ttf",           # использует загружённый Anton-Regular.ttf
        "font_comicsans": "Comic Sans MS.ttf",       # использует загружённый "Comic Sans MS.ttf"
        "font_arial_black": "Arial_black.ttf",       # использует загружённый Arial_black.ttf
    }
    
    font_names = {
        "font_molodost": "Molodost Regular",
        "font_roboto": "Roboto Bold",
        "font_times": "Times New Roman Bold Italic",
        "font_nougat": "Nougat Regular",
        "font_maratype": "Maratype Regular",
        "font_farabee": "Farabee Bold",
        "font_impact": "Impact",
        "font_anton": "Anton",
        "font_comicsans": "Comic Sans MS",
        "font_arial_black": "Arial Black",
    }
    
    if query.data in font_map:
        user_data[user_id]['font_file'] = font_map[query.data]
        
        if 'photo' in user_data[user_id]:
            keyboard = [
                [
                    InlineKeyboardButton("Обычный (верх+низ)", callback_data="type_normal"),
                ],
                [
                    InlineKeyboardButton("С текстом внизу", callback_data="type_bottom_only"),
                ],
                [
                    InlineKeyboardButton("⬅️ Назад", callback_data="action_back"),
                    InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Шрифт установлен: **{font_names.get(query.data, query.data)}**\n\n"
                "Выбери тип демотиватора:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                f"✅ Шрифт установлен: **{font_names.get(query.data, query.data)}**\n\n"
                "Теперь отправь фото.",
                parse_mode='Markdown'
            )
        return

    if query.data in ["meme_classic", "meme_demotivator"]:
        user_data[user_id]['meme_type'] = query.data
        
        if user_id not in user_messages:
            user_messages[user_id] = []
        if query.message.message_id not in user_messages[user_id]:
            user_messages[user_id].append(query.message.message_id)
        
        if query.data == "meme_classic":
            keyboard = [
                [
                    InlineKeyboardButton("Impact", callback_data="classic_font_impact"),
                ],
                [
                    InlineKeyboardButton("Lobster Regular", callback_data="classic_font_lobster"),
                ],
                [
                    InlineKeyboardButton("⬅️ Назад", callback_data="action_back"),
                    InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ Выбран тип: **Классический мем**\n\n"
                "Выбери шрифт:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            reply_markup = show_font_selection(user_id)
            await query.edit_message_text(
                "✅ Выбран тип: **Демотиватор**\n\n"
                "Выбери шрифт:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        return

    if query.data in ["classic_font_impact", "classic_font_lobster"]:
        font_map_local = {
            "classic_font_impact": "Impact.ttf",
            "classic_font_lobster": "Lobster.ttf",
        }
        font_names_local = {
            "classic_font_impact": "Impact",
            "classic_font_lobster": "Lobster Regular",
        }
        user_data[user_id]['classic_font'] = font_map_local[query.data]
        
        keyboard = [
            [
                InlineKeyboardButton("Верхний и нижний текст", callback_data="classic_type_normal"),
            ],
            [
                InlineKeyboardButton("Только нижний текст", callback_data="classic_type_bottom_only"),
            ],
            [
                InlineKeyboardButton("⬅️ Назад", callback_data="action_back"),
                InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Шрифт установлен: **{font_names_local[query.data]}**\n\n"
            "Выбери тип классического мема:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return

    if query.data in ["classic_type_normal", "classic_type_bottom_only"]:
        user_data[user_id]['classic_type'] = query.data
        
        type_names = {
            "classic_type_normal": "Верхний и нижний текст",
            "classic_type_bottom_only": "Только нижний текст",
        }
        
        if 'caption_top' in user_data.get(user_id, {}):
            classic_type = user_data[user_id].get('classic_type', 'classic_type_normal')
            if classic_type == 'classic_type_bottom_only':
                top_text = ""
                bottom_text = user_data[user_id].get('caption_top', '') + ((' ' + user_data[user_id].get('caption_bottom', '')) if user_data[user_id].get('caption_bottom', '') else '')
            else:
                top_text = user_data[user_id]['caption_top']
                bottom_text = user_data[user_id].get('caption_bottom', '')
            
            try:
                if user_id in user_messages:
                    for msg_id in user_messages[user_id]:
                        try:
                            await context.bot.delete_message(chat_id=query.message.chat.id, message_id=msg_id)
                        except:
                            pass
                    user_messages[user_id] = []
                
                photo_bytes = user_data[user_id]['photo']
                photo_bytes.seek(0)
                classic_font = user_data[user_id].get('classic_font', 'Impact.ttf')
                is_gif = user_data[user_id].get('is_gif', False)
                
                if is_gif:
                    meme = create_classic_meme_gif(photo_bytes, top_text, bottom_text, classic_font)
                    result_msg = await query.message.reply_animation(animation=meme, caption="Ваш мем готов!\n\n @memfy_bot", reply_markup=get_donation_keyboard())
                else:
                    meme = create_classic_meme(photo_bytes, top_text, bottom_text, classic_font)
                    result_msg = await query.message.reply_photo(photo=meme, caption="Ваш мем готов!\n\n @memfy_bot", reply_markup=get_donation_keyboard())
                
                try:
                    await context.bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
                except:
                    pass
                
                for key in ['photo', 'caption_top', 'caption_bottom', 'meme_type', 'classic_font', 'classic_type', 'is_gif']:
                    user_data[user_id].pop(key, None)
            except Exception as e:
                logger.error(f"Ошибка при создании классического мема: {e}")
                await query.edit_message_text("Произошла ошибка при создании мема. Попробуй еще раз.")
        else:
            classic_type = user_data[user_id].get('classic_type', 'classic_type_normal')
            if classic_type == 'classic_type_bottom_only':
                text_instruction = "Отправь текст (будет размещен только внизу)"
            else:
                text_instruction = "Отправь текст в формате:\n'Верхний текст|Нижний текст'"
            
            await query.edit_message_text(
                f"✅ Тип установлен: **{type_names[classic_type]}**\n\n"
                f"{text_instruction}\n\n"
                "Будет использован белый цвет, большой размер.",
                parse_mode='Markdown'
            )
        return

    if query.data in ["type_normal", "type_bottom_only"]:
        user_data[user_id]['demotivator_type'] = query.data
        
        type_names = {
            "type_normal": "Обычный (верх+низ)",
            "type_bottom_only": "С текстом внизу",
        }
        
        keyboard = [
            [
                InlineKeyboardButton("Маленький 📝", callback_data="size_small"),
                InlineKeyboardButton("Средний 📄", callback_data="size_medium"),
            ],
            [
                InlineKeyboardButton("Большой 📰", callback_data="size_large"),
                InlineKeyboardButton("Очень большой 📋", callback_data="size_xlarge"),
            ],
            [
                InlineKeyboardButton("⬅️ Назад", callback_data="action_back"),
                InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Тип демотиватора: **{type_names[query.data]}**\n\n"
            "Выбери размер шрифта:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return

    if query.data == "shakalize_menu":
        keyboard = [
            [
                InlineKeyboardButton("Лёгкая засвалка", callback_data="shakalize_light"),
                InlineKeyboardButton("Средняя засвалка", callback_data="shakalize_medium"),
            ],
            [
                InlineKeyboardButton("Жёсткая засвалка", callback_data="shakalize_hard"),
            ],
            [
                InlineKeyboardButton("⬅️ Назад", callback_data="action_back"),
                InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
            ]
        ]
        await query.edit_message_text("Выбери уровень ухудшения (шакализации):", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if query.data in ["shakalize_light", "shakalize_medium", "shakalize_hard"]:
        level = query.data.split('_')[-1]
        try:
            if 'photo' not in user_data.get(user_id, {}):
                await query.edit_message_text("Сначала отправь фото.")
                return
            photo_bytes = user_data[user_id]['photo']
            photo_bytes.seek(0)
            result = shakalize_image(photo_bytes, intensity=level)
            await query.message.reply_photo(photo=result, caption="Вот, зашакалил. 🤝\n\n @memfy_bot", reply_markup=get_donation_keyboard())
            if user_id in user_messages:
                for msg_id in user_messages[user_id]:
                    try:
                        await context.bot.delete_message(chat_id=query.message.chat.id, message_id=msg_id)
                    except:
                        pass
                user_messages[user_id] = []
            user_data[user_id].pop('photo', None)
        except Exception as e:
            logger.error(f"Ошибка при шакализации: {e}")
            await query.edit_message_text("Не удалось зашакалить фото.")
        return


def show_font_selection(user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("Molodost Regular", callback_data="font_molodost"),
        ],
        [
            InlineKeyboardButton("Roboto Bold", callback_data="font_roboto"),
        ],
        [
            InlineKeyboardButton("Times New Roman Bold Italic", callback_data="font_times"),
        ],
        [
            InlineKeyboardButton("Nougat Regular", callback_data="font_nougat"),
        ],
        [
            InlineKeyboardButton("Maratype Regular", callback_data="font_maratype"),
        ],
        [
            InlineKeyboardButton("Farabee Bold", callback_data="font_farabee"),
        ],
        [
            InlineKeyboardButton("Impact", callback_data="font_impact"),
            InlineKeyboardButton("Anton", callback_data="font_anton"),
        ],
        [
            InlineKeyboardButton("Comic Sans", callback_data="font_comicsans"),
            InlineKeyboardButton("Arial Black", callback_data="font_arial_black"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data="action_back"),
            InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_type = update.message.chat.type
    
    is_gif = False
    if update.message.animation:
        file = await context.bot.get_file(update.message.animation.file_id)
        photo_bytes = io.BytesIO()
        await file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)
        is_gif = True
    else:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = io.BytesIO()
        await file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)
    
    caption = update.message.caption or ""
    
    if chat_type in ['group', 'supergroup']:
        bot_username = context.bot.username.lower()
        mentioned = False
        if caption:
            if f"@memfy_bot" in caption.lower():
                mentioned = True
            if update.message.entities or update.message.caption_entities:
                entities = update.message.caption_entities or update.message.entities or []
                for entity in entities:
                    if entity.type == "mention":
                        mention_text = caption[entity.offset:entity.offset + entity.length].lower()
                        if f"@memfy_bot" == mention_text:
                            mentioned = True
                            break
        
        if not mentioned:
            return
        
        if caption:
            caption = caption.replace(f"@{bot_username}", "").replace(f"@memfy_bot", "").strip()
            caption = " ".join(caption.split())
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['photo'] = photo_bytes
    user_data[user_id]['is_gif'] = is_gif
    
    if caption and '|' in caption:
        texts = caption.split('|', 1)
        user_data[user_id]['caption_top'] = texts[0].strip()
        user_data[user_id]['caption_bottom'] = texts[1].strip() if len(texts) > 1 else ""
    
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(update.message.message_id)
    
    keyboard = [
        [
            InlineKeyboardButton("Классический мем 🎨", callback_data="meme_classic"),
        ],
        [
            InlineKeyboardButton("Демотиватор 📋", callback_data="meme_demotivator"),
        ],
        [
            InlineKeyboardButton("Зашакалить 🛠️", callback_data="shakalize_menu"),
        ],
        [
            InlineKeyboardButton("Поддержать бота 💰", url=DONATION_URL),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    sent_msg = await update.message.reply_text(
        "Отлично! Фото получено.\n\n"
        "Выбери тип мема или действие:",
        reply_markup=reply_markup
    )
    
    user_messages[user_id].append(sent_msg.message_id)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_type = update.message.chat.type
    
    if chat_type in ['group', 'supergroup']:
        if user_id not in user_data or 'photo' not in user_data[user_id]:
            return
    
    if user_id not in user_data or 'photo' not in user_data[user_id]:
        if chat_type == 'private':
            await update.message.reply_text(
                "Сначала отправь мне фото, затем выбери тип мема и отправь текст."
            )
        return
    
    meme_type = user_data.get(user_id, {}).get('meme_type')
    if not meme_type:
        await update.message.reply_text(
            "Сначала выбери тип мема (классический или демотиватор), нажав на кнопки после отправки фото."
        )
        return
    
    text = update.message.text
    photo_bytes = user_data[user_id]['photo']
    photo_bytes.seek(0)
    
    try:
        if meme_type == 'meme_classic':
            if 'classic_font' not in user_data.get(user_id, {}):
                await update.message.reply_text(
                    "Сначала выбери шрифт (Impact или Lobster), нажав на кнопки после выбора типа мема."
                )
                return
            
            classic_type = user_data.get(user_id, {}).get('classic_type', 'classic_type_normal')
            
            if classic_type == 'classic_type_bottom_only':
                top_text = ""
                bottom_text = text.strip()
            else:
                if '|' not in text:
                    await update.message.reply_text(
                        "Для типа 'верхний и нижний' используй формат: 'Верхний текст|Нижний текст'"
                    )
                    return
                texts = text.split('|', 1)
                top_text = texts[0].strip()
                bottom_text = texts[1].strip() if len(texts) > 1 else ""
            
            if user_id in user_messages:
                for msg_id in user_messages[user_id]:
                    try:
                        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=msg_id)
                    except:
                        pass
                user_messages[user_id] = []
            
            classic_font = user_data[user_id].get('classic_font', 'Impact.ttf')
            is_gif = user_data[user_id].get('is_gif', False)
            
            if is_gif:
                meme = create_classic_meme_gif(photo_bytes, top_text, bottom_text, classic_font)
                result_msg = await update.message.reply_animation(animation=meme, caption="Ваш мем готов!\n\n @memfy_bot", reply_markup=get_donation_keyboard())
            else:
                meme = create_classic_meme(photo_bytes, top_text, bottom_text, classic_font)
                result_msg = await update.message.reply_photo(photo=meme, caption="Ваш мем готов!\n\n @memfy_bot", reply_markup=get_donation_keyboard())
            
            try:
                await context.bot.delete_message(chat_id=update.message.chat.id, message_id=update.message.message_id)
            except:
                pass
            
        else:
            if 'font_file' not in user_data.get(user_id, {}):
                await update.message.reply_text(
                    "Сначала выбери шрифт, нажав на кнопки после отправки фото."
                )
                return
            
            demotivator_type = user_data.get(user_id, {}).get('demotivator_type', 'type_normal')
            
            if demotivator_type == 'type_bottom_only':
                top_text = ""
                bottom_text = text.strip()
            else:
                if '|' not in text:
                    await update.message.reply_text(
                        "Для обычного типа используй формат: 'Верхний текст|Нижний текст'"
                    )
                    return
                texts = text.split('|', 1)
                top_text = texts[0].strip()
                bottom_text = texts[1].strip() if len(texts) > 1 else ""
            
            if user_id in user_messages:
                for msg_id in user_messages[user_id]:
                    try:
                        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=msg_id)
                    except:
                        pass
                user_messages[user_id] = []
            
            font_size = user_data.get(user_id, {}).get('font_size')
            font_file = user_data[user_id]['font_file']
            font_color = user_data.get(user_id, {}).get('font_color', 'white')
            border_thickness = user_data.get(user_id, {}).get('border_thickness', 10)
            demotivator = create_demotivator(photo_bytes, top_text, bottom_text, font_size, font_file, demotivator_type, font_color, border_thickness)
            result_msg = await update.message.reply_photo(photo=demotivator, caption="Ваш демотиватор готов!\n\n @memfy_bot", reply_markup=get_donation_keyboard())
            
            try:
                await context.bot.delete_message(chat_id=update.message.chat.id, message_id=update.message.message_id)
            except:
                pass
        
        for key in ['photo', 'meme_type', 'classic_font', 'classic_type', 'is_gif']:
            user_data[user_id].pop(key, None)
        
    except Exception as e:
        logger.error(f"Ошибка при создании мема: {e}")
        await update.message.reply_text("Произошла ошибка при создании мема. Попробуй еще раз.")


# Список шрифтов, которые бот умеет использовать (имена файлов)
AVAILABLE_FONT_FILES = [
    "Molodost.ttf",
    "Roboto_Bold.ttf",
    "Times New Roman Bold Italic.ttf",
    "Nougat Regular.ttf",
    "Maratype Regular.ttf",
    "Farabee Bold.ttf",
    "Impact.ttf",
    "Anton-Regular.ttf",            # загружённый пользователем
    "Comic Sans MS.ttf",            # загружённый пользователем
    "Arial_black.ttf",              # загружённый пользователем
    "Lobster.ttf",
]


def create_classic_meme(photo_bytes: io.BytesIO, top_text: str, bottom_text: str, font_file: str = "Impact.ttf") -> io.BytesIO:
    photo_bytes.seek(0)
    image = Image.open(photo_bytes)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    img_width, img_height = image.size
    font_size = max(40, int(img_width / 20))
    text_color = (255, 255, 255)
    font_paths = [
        os.path.join(FONT_DIR, font_file),
        font_file,
    ]
    font = None
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, font_size)
            logger.info(f"Шрифт {font_file} загружен: {path}")
            break
        except Exception as e:
            logger.warning(f"Не удалось загрузить {path}: {e}")
            continue
    if font is None:
        logger.error(f"Шрифт {font_file} не найден, используется стандартный шрифт")
        font = ImageFont.load_default()
    meme = image.copy()
    draw = ImageDraw.Draw(meme)

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

    def draw_text_with_outline(draw, position, text, font, fill_color, outline_color=(0, 0, 0), outline_width=2):
        x, y = position
        for adj in range(-outline_width, outline_width + 1):
            for adj2 in range(-outline_width, outline_width + 1):
                if adj != 0 or adj2 != 0:
                    draw.text((x + adj, y + adj2), text, font=font, fill=outline_color)
        draw.text(position, text, font=font, fill=fill_color)

    if top_text:
        max_text_width = img_width - 40
        top_lines = wrap_text(top_text, font, max_text_width)
        y_offset = 20
        for line in top_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (img_width - text_width) // 2
            draw_text_with_outline(draw, (x, y_offset), line, font, text_color)
            y_offset += int(font_size * 1.3)

    if bottom_text:
        max_text_width = img_width - 40
        bottom_lines = wrap_text(bottom_text, font, max_text_width)
        total_bottom_height = len(bottom_lines) * int(font_size * 1.3)
        y_offset = img_height - total_bottom_height - 20
        for line in bottom_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (img_width - text_width) // 2
            draw_text_with_outline(draw, (x, y_offset), line, font, text_color)
            y_offset += int(font_size * 1.3)

    watermark_text = "@memfy_bot"
    watermark_size = 16
    watermark_font_paths = [
        os.path.join(FONT_DIR, "Roboto_Bold.ttf"),
        "Roboto_Bold.ttf",
    ]
    watermark_font = None
    for path in watermark_font_paths:
        try:
            watermark_font = ImageFont.truetype(path, watermark_size)
            break
        except:
            continue
    if watermark_font is None:
        watermark_font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
    watermark_width = bbox[2] - bbox[0]
    watermark_height = bbox[3] - bbox[1]
    watermark_img = Image.new('RGBA', (watermark_width + 10, watermark_height + 5), (0, 0, 0, 0))
    watermark_draw = ImageDraw.Draw(watermark_img)
    watermark_draw.text((5, 0), watermark_text, fill=(255, 255, 255, 128), font=watermark_font)
    offset = 15
    corners = [
        (offset, offset),
        (img_width - watermark_width - offset, offset),
        (offset, img_height - watermark_height - offset),
        (img_width - watermark_width - offset, img_height - watermark_height - offset),
    ]
    watermark_x, watermark_y = random.choice(corners)
    meme_rgba = meme.convert('RGBA')
    meme_rgba.paste(watermark_img, (watermark_x, watermark_y), watermark_img)
    meme = meme_rgba.convert('RGB')
    output = io.BytesIO()
    meme.save(output, format='JPEG', quality=95)
    output.seek(0)
    return output

def create_classic_meme_gif(photo_bytes: io.BytesIO, top_text: str, bottom_text: str, font_file: str = "Impact.ttf") -> io.BytesIO:
    photo_bytes.seek(0)
    gif = Image.open(photo_bytes)
    if not getattr(gif, 'is_animated', False):
        return create_classic_meme(photo_bytes, top_text, bottom_text, font_file)
    gif.seek(0)
    first_frame = gif.copy()
    if first_frame.mode != 'RGB':
        first_frame = first_frame.convert('RGB')
    img_width, img_height = first_frame.size
    font_size = max(40, int(img_width / 20))
    text_color = (255, 255, 255)
    font_paths = [
        os.path.join(FONT_DIR, font_file),
        font_file,
    ]
    font = None
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, font_size)
            logger.info(f"Шрифт {font_file} загружен: {path}")
            break
        except Exception as e:
            logger.warning(f"Не удалось загрузить {path}: {e}")
            continue
    if font is None:
        logger.error(f"Шрифт {font_file} не найден, используется стандартный шрифт")
        font = ImageFont.load_default()
    watermark_text = "@memfy_bot"
    watermark_size = 16
    watermark_font_paths = [
        os.path.join(FONT_DIR, "Roboto_Bold.ttf"),
        "Roboto_Bold.ttf",
    ]
    watermark_font = None
    for path in watermark_font_paths:
        try:
            watermark_font = ImageFont.truetype(path, watermark_size)
            break
        except:
            continue
    if watermark_font is None:
        watermark_font = ImageFont.load_default()

    def wrap_text(text, font, max_width, draw):
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

    def draw_text_with_outline(draw, position, text, font, fill_color, outline_color=(0, 0, 0), outline_width=2):
        x, y = position
        for adj in range(-outline_width, outline_width + 1):
            for adj2 in range(-outline_width, outline_width + 1):
                if adj != 0 or adj2 != 0:
                    draw.text((x + adj, y + adj2), text, font=font, fill=outline_color)
        draw.text(position, text, font=font, fill=fill_color)

    frames = []
    durations = []
    try:
        frame_count = 0
        while True:
            gif.seek(frame_count)
            frame = gif.copy()
            if frame.mode != 'RGB':
                frame = frame.convert('RGB')
            meme_frame = frame.copy()
            draw = ImageDraw.Draw(meme_frame)
            if top_text:
                max_text_width = img_width - 40
                top_lines = wrap_text(top_text, font, max_text_width, draw)
                y_offset = 20
                for line in top_lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    x = (img_width - text_width) // 2
                    draw_text_with_outline(draw, (x, y_offset), line, font, text_color)
                    y_offset += int(font_size * 1.3)
            if bottom_text:
                max_text_width = img_width - 40
                bottom_lines = wrap_text(bottom_text, font, max_text_width, draw)
                total_bottom_height = len(bottom_lines) * int(font_size * 1.3)
                y_offset = img_height - total_bottom_height - 20
                for line in bottom_lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    x = (img_width - text_width) // 2
                    draw_text_with_outline(draw, (x, y_offset), line, font, text_color)
                    y_offset += int(font_size * 1.3)
            bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
            watermark_width = bbox[2] - bbox[0]
            watermark_height = bbox[3] - bbox[1]
            watermark_img = Image.new('RGBA', (watermark_width + 10, watermark_height + 5), (0, 0, 0, 0))
            watermark_draw = ImageDraw.Draw(watermark_img)
            watermark_draw.text((5, 0), watermark_text, fill=(255, 255, 255, 128), font=watermark_font)
            offset = 15
            corners = [
                (offset, offset),
                (img_width - watermark_width - offset, offset),
                (offset, img_height - watermark_height - offset),
                (img_width - watermark_width - offset, img_height - watermark_height - offset),
            ]
            watermark_x, watermark_y = random.choice(corners)
            meme_rgba = meme_frame.convert('RGBA')
            meme_rgba.paste(watermark_img, (watermark_x, watermark_y), watermark_img)
            meme_frame = meme_rgba.convert('RGB')
            frames.append(meme_frame)
            try:
                duration = frame.info.get('duration', gif.info.get('duration', 100))
                durations.append(duration)
            except:
                durations.append(100)
            frame_count += 1
            try:
                gif.seek(frame_count)
            except EOFError:
                break
    except Exception as e:
        logger.error(f"Ошибка при обработке GIF: {e}")
        if frames:
            output = io.BytesIO()
            frames[0].save(output, format='JPEG', quality=95)
            output.seek(0)
            return output
        else:
            return create_classic_meme(photo_bytes, top_text, bottom_text, font_file)

    output = io.BytesIO()
    if frames:
        frames[0].save(
            output,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            optimize=False
        )
    output.seek(0)
    return output

def create_demotivator(photo_bytes: io.BytesIO, top_text: str, bottom_text: str, 
                      font_size: dict = None, font_file: str = "Roboto_Bold.ttf", 
                      demotivator_type: str = "type_normal", font_color: str = "white",
                      border_thickness: int = 10) -> io.BytesIO:
    if font_size is None:
        font_size = {"top": 40, "bottom": 28}
    top_font_size = font_size.get("top", 40)
    bottom_font_size = font_size.get("bottom", 28)
    color_map = {
        "red": (255, 0, 0),
        "white": (255, 255, 255),
        "blue": (0, 0, 255),
        "green": (0, 255, 0),
        "purple": (128, 0, 128),
    }
    text_color = color_map.get(font_color, (255, 255, 255))
    photo_bytes.seek(0)
    image = Image.open(photo_bytes)
    if getattr(image, 'is_animated', False):
        try:
            image.seek(0)
            image = image.convert('RGB')
        except:
            image = image.convert('RGB')
    if image.mode != 'RGB':
        image = image.convert('RGB')
    STANDARD_SIZE = 512
    if image.size != (STANDARD_SIZE, STANDARD_SIZE):
        image = image.resize((STANDARD_SIZE, STANDARD_SIZE), Image.Resampling.LANCZOS)
        img_width = STANDARD_SIZE
        img_height = STANDARD_SIZE
    else:
        img_width, img_height = image.size
    padding = 30
    border_thickness = int(border_thickness or 10)
    total_padding = padding + border_thickness
    top_space = 80 if demotivator_type == "type_normal" else 20
    demotivator_width = img_width + (total_padding * 2)
    demotivator_height = img_height + (total_padding * 2) + (200 if demotivator_type == "type_normal" else 120)
    demotivator = Image.new('RGB', (demotivator_width, demotivator_height), color='black')
    photo_x = total_padding
    photo_y = total_padding + top_space
    demotivator.paste(image, (photo_x, photo_y))
    draw = ImageDraw.Draw(demotivator)
    frame_x1 = photo_x - border_thickness
    frame_y1 = photo_y - border_thickness
    frame_x2 = photo_x + img_width + border_thickness - 1
    frame_y2 = photo_y + img_height + border_thickness - 1
    for i in range(border_thickness):
        draw.rectangle(
            [frame_x1 - i, frame_y1 - i, frame_x2 + i, frame_y2 + i],
            outline='white',
            width=1
        )
    font_paths = [
        os.path.join(FONT_DIR, font_file),
        font_file,
    ]
    font_large = None
    font_small = None
    for path in font_paths:
        try:
            font_large = ImageFont.truetype(path, top_font_size)
            font_small = ImageFont.truetype(path, bottom_font_size)
            logger.info(f"Шрифт загружен: {path}")
            break
        except Exception as e:
            logger.warning(f"Не удалось загрузить {path}: {e}")
            continue
    if font_large is None:
        logger.error(f"Шрифт {font_file} не найден, используется стандартный шрифт")
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
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
    watermark_text = "@memfy_bot"
    watermark_size = 16
    watermark_font_paths = [
        os.path.join(FONT_DIR, "Roboto_Bold.ttf"),
        "Roboto_Bold.ttf",
    ]
    watermark_font = None
    for path in watermark_font_paths:
        try:
            watermark_font = ImageFont.truetype(path, watermark_size)
            break
        except:
            continue
    if watermark_font is None:
        watermark_font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
    watermark_width = bbox[2] - bbox[0]
    watermark_height = bbox[3] - bbox[1]
    watermark_img = Image.new('RGBA', (watermark_width + 10, watermark_height + 5), (0, 0, 0, 0))
    watermark_draw = ImageDraw.Draw(watermark_img)
    watermark_draw.text((5, 0), watermark_text, fill=(255, 255, 255, 128), font=watermark_font)
    offset = 15
    corners = [
        (offset, offset),
        (demotivator_width - watermark_width - offset, offset),
        (offset, demotivator_height - watermark_height - offset),
        (demotivator_width - watermark_width - offset, demotivator_height - watermark_height - offset),
    ]
    watermark_x, watermark_y = random.choice(corners)
    demotivator_rgba = demotivator.convert('RGBA')
    demotivator_rgba.paste(watermark_img, (watermark_x, watermark_y), watermark_img)
    demotivator = demotivator_rgba.convert('RGB')
    output = io.BytesIO()
    demotivator.save(output, format='JPEG', quality=95)
    output.seek(0)
    return output

def shakalize_image(photo_bytes: io.BytesIO, intensity: str = 'hard') -> io.BytesIO:
    photo_bytes.seek(0)
    im = Image.open(photo_bytes)
    if im.mode != 'RGB':
        im = im.convert('RGB')
    if intensity == 'light':
        downscale = 0.6
        poster_bits = 5
        jpeg_quality = 35
    elif intensity == 'medium':
        downscale = 0.35
        poster_bits = 4
        jpeg_quality = 20
    else:
        downscale = 0.14
        poster_bits = 3
        jpeg_quality = 8
    w, h = im.size
    new_w = max(2, int(w * downscale))
    new_h = max(2, int(h * downscale))
    im_small = im.resize((new_w, new_h), resample=Image.Resampling.NEAREST)
    im_pixel = im_small.resize((w, h), resample=Image.Resampling.NEAREST)
    im_poster = ImageOps.posterize(im_pixel, poster_bits)
    im_blur = im_poster.filter(ImageFilter.GaussianBlur(radius=1))
    im_enh = ImageOps.autocontrast(im_blur, cutoff=0)
    out = io.BytesIO()
    im_enh.save(out, format='JPEG', quality=jpeg_quality, optimize=False)
    out.seek(0)
    final = Image.open(out)
    final = final.convert('P', palette=Image.ADAPTIVE, colors=64).convert('RGB')
    final_out = io.BytesIO()
    final.save(final_out, format='JPEG', quality=max(2, jpeg_quality), optimize=False)
    final_out.seek(0)
    return final_out

def main():
    """Запуск бота"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Ошибка: Установите переменную окружения TELEGRAM_BOT_TOKEN")
        return

    # Проверим доступность шрифтов перед стартом
    check_fonts_presence()

    application = Application.builder().token(token).job_queue(None).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("size", size_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.PHOTO | filters.ANIMATION, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()