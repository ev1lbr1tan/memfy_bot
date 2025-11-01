import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont
import io
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище для временных данных пользователей
user_data = {}

# Хранилище для ID сообщений, которые нужно удалить
user_messages = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    chat_type = update.message.chat.type if update.message else 'private'
    
    if chat_type in ['group', 'supergroup']:
        await update.message.reply_text(
            "Привет! Я бот для создания мемов и демотиваторов.\n\n"
            "Чтобы создать мем в группе:\n"
            "1. Отправь фото с подписью: @memfy_bot\n"
            "2. Выбери тип: классический мем или \n"
            "3. Для классического мема - отправь текст в формате 'Верхний|Нижний'\n"
            "4. Для а - выбери шрифт, тип, размер, цвет и отправь текст\n\n"
            "Или отправь фото с подписью: @memfy_bot Верхний текст|Нижний текст"
        )
    else:
        await update.message.reply_text(
            "Привет! Я бот для создания мемов и ов.\n\n"
            "Как пользоваться:\n"
            "1. Отправь мне фото\n"
            "2. Выбери тип: классический мем или \n"
            "3. Для классического мема:\n"
            "   - Выбери шрифт (Impact или Lobster)\n"
            "   - Выбери тип (верх+низ или только внизу)\n"
            "   - Отправь текст\n"
            "4. Для а:\n"
            "   - Выбери шрифт\n"
            "   - Выбери тип демотиватора\n"
            "   - Выбери размер и цвет шрифта\n"
            "   - Отправь текст\n\n"
            "Или просто отправь фото с подписью в формате: 'Верхний текст|Нижний текст'\n\n"
            "Бот работает в личных сообщениях и в группах!"
        )


async def size_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /size для выбора размера шрифта"""
    keyboard = [
        [
            InlineKeyboardButton("Маленький 📝", callback_data="size_small"),
            InlineKeyboardButton("Средний 📄", callback_data="size_medium"),
        ],
        [
            InlineKeyboardButton("Большой 📰", callback_data="size_large"),
            InlineKeyboardButton("Очень большой 📋", callback_data="size_xlarge"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Выбери размер шрифта для демотиватора:",
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Обработка выбора размера шрифта
    size_map = {
        "size_small": {"top": 30, "bottom": 20},
        "size_medium": {"top": 40, "bottom": 28},
        "size_large": {"top": 50, "bottom": 35},
        "size_xlarge": {"top": 60, "bottom": 40},
    }
    
    if query.data in size_map:
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['font_size'] = size_map[query.data]
        
        size_names = {
            "size_small": "Маленький",
            "size_medium": "Средний",
            "size_large": "Большой",
            "size_xlarge": "Очень большой",
        }
        
        # Показываем выбор цвета шрифта
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
    
    # Обработка выбора цвета шрифта
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
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['font_color'] = color_map[query.data]
        
        # Проверяем, есть ли фото и другие настройки
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
    
    # Обработка выбора шрифта
    font_map = {
        "font_molodost": "Molodost.ttf",
        "font_roboto": "Roboto_Bold.ttf",
        "font_times": "Times New Roman Bold Italic.ttf",
        "font_nougat": "Nougat Regular.ttf",
        "font_maratype": "Maratype Regular.ttf",
        "font_farabee": "Farabee Bold.ttf",
    }
    
    font_names = {
        "font_molodost": "Molodost Regular",
        "font_roboto": "Roboto Bold",
        "font_times": "Times New Roman Bold Italic",
        "font_nougat": "Nougat Regular",
        "font_maratype": "Maratype Regular",
        "font_farabee": "Farabee Bold",
    }
    
    if query.data in font_map:
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['font_file'] = font_map[query.data]
        
        # Проверяем, есть ли фото и нужно ли показать выбор типа демотиватора
        if 'photo' in user_data[user_id]:
            # Показываем выбор типа демотиватора
            keyboard = [
                [
                    InlineKeyboardButton("Обычный (верх+низ)", callback_data="type_normal"),
                ],
                [
                    InlineKeyboardButton("С текстом внизу", callback_data="type_bottom_only"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Шрифт установлен: **{font_names[query.data]}**\n\n"
                "Выбери тип демотиватора:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                f"✅ Шрифт установлен: **{font_names[query.data]}**\n\n"
                "Теперь отправь фото.",
                parse_mode='Markdown'
            )
        return
    
    # Обработка выбора типа мема (классический или демотиватор)
    if query.data in ["meme_classic", "meme_demotivator"]:
        if user_id not in user_data:
            user_data[user_id] = {}
        
        user_data[user_id]['meme_type'] = query.data
        
        # Сохраняем ID сообщения для последующего удаления (но не удаляем сейчас)
        if user_id not in user_messages:
            user_messages[user_id] = []
        if query.message.message_id not in user_messages[user_id]:
            user_messages[user_id].append(query.message.message_id)
        
        if query.data == "meme_classic":
            # Для классического мема показываем выбор шрифта
            keyboard = [
                [
                    InlineKeyboardButton("Impact", callback_data="classic_font_impact"),
                ],
                [
                    InlineKeyboardButton("Lobster Regular", callback_data="classic_font_lobster"),
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
            # Для демотиватора показываем выбор шрифта
            reply_markup = show_font_selection(user_id)
            await query.edit_message_text(
                "✅ Выбран тип: **Демотиватор**\n\n"
                "Выбери шрифт:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        return
    
    # Обработка выбора шрифта для классического мема
    if query.data in ["classic_font_impact", "classic_font_lobster"]:
        if user_id not in user_data:
            user_data[user_id] = {}
        
        font_map = {
            "classic_font_impact": "Impact.ttf",
            "classic_font_lobster": "Lobster.ttf",
        }
        
        font_names = {
            "classic_font_impact": "Impact",
            "classic_font_lobster": "Lobster Regular",
        }
        
        user_data[user_id]['classic_font'] = font_map[query.data]
        
        # Показываем выбор типа классического мема (верх+низ или только внизу)
        keyboard = [
            [
                InlineKeyboardButton("Верхний и нижний текст", callback_data="classic_type_normal"),
            ],
            [
                InlineKeyboardButton("Только нижний текст", callback_data="classic_type_bottom_only"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Шрифт установлен: **{font_names[query.data]}**\n\n"
            "Выбери тип классического мема:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    # Обработка выбора типа классического мема
    if query.data in ["classic_type_normal", "classic_type_bottom_only"]:
        if user_id not in user_data:
            user_data[user_id] = {}
        
        user_data[user_id]['classic_type'] = query.data
        
        type_names = {
            "classic_type_normal": "Верхний и нижний текст",
            "classic_type_bottom_only": "Только нижний текст",
        }
        
        # Проверяем, есть ли сохраненный текст из подписи
        if 'caption_top' in user_data.get(user_id, {}):
            # Если есть текст из подписи, сразу создаем мем
            classic_type = user_data[user_id].get('classic_type', 'classic_type_normal')
            if classic_type == 'classic_type_bottom_only':
                top_text = ""
                bottom_text = user_data[user_id].get('caption_top', '') + ((' ' + user_data[user_id].get('caption_bottom', '')) if user_data[user_id].get('caption_bottom', '') else '')
            else:
                top_text = user_data[user_id]['caption_top']
                bottom_text = user_data[user_id].get('caption_bottom', '')
            
            try:
                # Удаляем старые сообщения во время генерации мема
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
                    result_msg = await query.message.reply_animation(animation=meme, caption="Ваш мем готов!\n\n @memfy_bot\n")
                else:
                    meme = create_classic_meme(photo_bytes, top_text, bottom_text, classic_font)
                    result_msg = await query.message.reply_photo(photo=meme, caption="Ваш мем готов!\n\n @memfy_bot\n")
                
                # Удаляем само сообщение с кнопками после отправки результата
                try:
                    await context.bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
                except:
                    pass
                
                # Очищаем данные
                if 'photo' in user_data[user_id]:
                    del user_data[user_id]['photo']
                if 'caption_top' in user_data[user_id]:
                    del user_data[user_id]['caption_top']
                if 'caption_bottom' in user_data[user_id]:
                    del user_data[user_id]['caption_bottom']
                if 'meme_type' in user_data[user_id]:
                    del user_data[user_id]['meme_type']
                if 'classic_font' in user_data[user_id]:
                    del user_data[user_id]['classic_font']
                if 'classic_type' in user_data[user_id]:
                    del user_data[user_id]['classic_type']
                if 'is_gif' in user_data[user_id]:
                    del user_data[user_id]['is_gif']
            except Exception as e:
                logger.error(f"Ошибка при создании классического мема: {e}")
                await query.edit_message_text("Произошла ошибка при создании мема. Попробуй еще раз.")
        else:
            # Если нет текста из подписи, просим ввести текст в зависимости от типа
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
    
    # Обработка выбора типа демотиватора
    if query.data in ["type_normal", "type_bottom_only"]:
        if user_id not in user_data:
            user_data[user_id] = {}
        
        user_data[user_id]['demotivator_type'] = query.data
        
        type_names = {
            "type_normal": "Обычный (верх+низ)",
            "type_bottom_only": "С текстом внизу",
        }
        
        # Показываем выбор размера шрифта
        keyboard = [
            [
                InlineKeyboardButton("Маленький 📝", callback_data="size_small"),
                InlineKeyboardButton("Средний 📄", callback_data="size_medium"),
            ],
            [
                InlineKeyboardButton("Большой 📰", callback_data="size_large"),
                InlineKeyboardButton("Очень большой 📋", callback_data="size_xlarge"),
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


def show_font_selection(user_id: int) -> InlineKeyboardMarkup:
    """Показывает кнопки выбора шрифта"""
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
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фото"""
    user_id = update.effective_user.id
    chat_type = update.message.chat.type
    
    # Проверяем, это GIF или обычное фото
    is_gif = False
    if update.message.animation:
        # Это анимированный GIF
        file = await context.bot.get_file(update.message.animation.file_id)
        photo_bytes = io.BytesIO()
        await file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)
        is_gif = True
    else:
        # Это обычное фото
        photo = update.message.photo[-1]  # Берем фото наибольшего размера
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = io.BytesIO()
        await file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)
    
    # Получаем подпись, если есть
    caption = update.message.caption or ""
    
    # Проверка для групп: бот должен быть упомянут
    if chat_type in ['group', 'supergroup']:
        bot_username = context.bot.username.lower()
        # Проверяем упоминание бота в подписи или entities
        mentioned = False
        if caption:
            # Проверяем упоминание в тексте
            if f"@memfy_bot" in caption.lower():
                mentioned = True
            # Проверяем через entities (официальные упоминания)
            if update.message.entities or update.message.caption_entities:
                entities = update.message.caption_entities or update.message.entities or []
                for entity in entities:
                    if entity.type == "mention":
                        mention_text = caption[entity.offset:entity.offset + entity.length].lower()
                        if f"@memfy_bot" == mention_text:
                            mentioned = True
                            break
        
        if not mentioned:
            # В группах игнорируем фото без упоминания бота
            return
        
        # Убираем упоминание бота из подписи для дальнейшей обработки
        if caption:
            caption = caption.replace(f"@{bot_username}", "").replace(f"@memfy_bot", "").strip()
            # Убираем множественные пробелы
            caption = " ".join(caption.split())
    
    # Сохраняем фото/GIF для пользователя
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['photo'] = photo_bytes
    user_data[user_id]['is_gif'] = is_gif
    
    # Если есть подпись, сохраняем её для последующего использования
    if caption and '|' in caption:
        texts = caption.split('|', 1)
        user_data[user_id]['caption_top'] = texts[0].strip()
        user_data[user_id]['caption_bottom'] = texts[1].strip() if len(texts) > 1 else ""
    
    # Сохраняем ID сообщения пользователя для последующего удаления
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(update.message.message_id)
    
    # Показываем выбор типа мема
    keyboard = [
        [
            InlineKeyboardButton("Классический мем 🎨", callback_data="meme_classic"),
        ],
        [
            InlineKeyboardButton("Демотиватор 📋", callback_data="meme_demotivator"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    sent_msg = await update.message.reply_text(
        "Отлично! Фото получено.\n\n"
        "Выбери тип мема:",
        reply_markup=reply_markup
    )
    
    # Сохраняем ID сообщения бота для последующего удаления
    user_messages[user_id].append(sent_msg.message_id)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текста"""
    user_id = update.effective_user.id
    chat_type = update.message.chat.type
    
    # В группах проверяем, начал ли пользователь взаимодействие с ботом
    if chat_type in ['group', 'supergroup']:
        # Проверяем, есть ли у пользователя сохраненное фото (значит он начал процесс)
        if user_id not in user_data or 'photo' not in user_data[user_id]:
            # В группах не реагируем на текст без начала процесса
            return
    
    # Проверяем, есть ли у пользователя сохраненное фото
    if user_id not in user_data or 'photo' not in user_data[user_id]:
        if chat_type == 'private':
            await update.message.reply_text(
                "Сначала отправь мне фото, затем выбери тип мема и отправь текст."
            )
        return
    
    # Проверяем, выбран ли тип мема
    meme_type = user_data.get(user_id, {}).get('meme_type')
    if not meme_type:
        await update.message.reply_text(
            "Сначала выбери тип мема (классический или демотиватор), нажав на кнопки после отправки фото."
        )
        return
    
    text = update.message.text
    
    # Получаем сохраненное фото
    photo_bytes = user_data[user_id]['photo']
    photo_bytes.seek(0)
    
    # Обрабатываем в зависимости от типа мема
    try:
        if meme_type == 'meme_classic':
            # Классический мем
            # Проверяем, выбран ли шрифт
            if 'classic_font' not in user_data.get(user_id, {}):
                await update.message.reply_text(
                    "Сначала выбери шрифт (Impact или Lobster), нажав на кнопки после выбора типа мема."
                )
                return
            
            # Проверяем, выбран ли тип классического мема
            classic_type = user_data.get(user_id, {}).get('classic_type', 'classic_type_normal')
            
            # Разделяем текст в зависимости от типа мема
            if classic_type == 'classic_type_bottom_only':
                # Для типа "только внизу" весь текст идет вниз
                top_text = ""
                bottom_text = text.strip()
            else:
                # Для обычного типа проверяем формат
                if '|' not in text:
                    await update.message.reply_text(
                        "Для типа 'верхний и нижний' используй формат: 'Верхний текст|Нижний текст'"
                    )
                    return
                texts = text.split('|', 1)
                top_text = texts[0].strip()
                bottom_text = texts[1].strip() if len(texts) > 1 else ""
            
            # Удаляем старые сообщения во время генерации мема
            if user_id in user_messages:
                for msg_id in user_messages[user_id]:
                    try:
                        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=msg_id)
                    except:
                        pass
                user_messages[user_id] = []
            
            # Получаем выбранный шрифт для классического мема
            classic_font = user_data[user_id].get('classic_font', 'Impact.ttf')
            is_gif = user_data[user_id].get('is_gif', False)
            
            if is_gif:
                meme = create_classic_meme_gif(photo_bytes, top_text, bottom_text, classic_font)
                result_msg = await update.message.reply_animation(animation=meme, caption="Ваш мем готов!\n\n @memfy_bot\n")
            else:
                meme = create_classic_meme(photo_bytes, top_text, bottom_text, classic_font)
                result_msg = await update.message.reply_photo(photo=meme, caption="Ваш мем готов! @memfy_bot")
            
            # Удаляем сообщение пользователя с текстом после отправки результата
            try:
                await context.bot.delete_message(chat_id=update.message.chat.id, message_id=update.message.message_id)
            except:
                pass
            
        else:
            # Демотиватор
            # Проверяем, выбран ли шрифт
            if 'font_file' not in user_data.get(user_id, {}):
                await update.message.reply_text(
                    "Сначала выбери шрифт, нажав на кнопки после отправки фото."
                )
                return
            
            # Проверяем, выбран ли тип демотиватора
            demotivator_type = user_data.get(user_id, {}).get('demotivator_type', 'type_normal')
            
            # Разделяем текст в зависимости от типа демотиватора
            if demotivator_type == 'type_bottom_only':
                # Для типа "только внизу" весь текст идет вниз
                top_text = ""
                bottom_text = text.strip()
            else:
                # Для обычного типа проверяем формат
                if '|' not in text:
                    await update.message.reply_text(
                        "Для обычного типа используй формат: 'Верхний текст|Нижний текст'"
                    )
                    return
                texts = text.split('|', 1)
                top_text = texts[0].strip()
                bottom_text = texts[1].strip() if len(texts) > 1 else ""
            
            # Удаляем старые сообщения во время генерации демотиватора
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
            demotivator = create_demotivator(photo_bytes, top_text, bottom_text, font_size, font_file, demotivator_type, font_color)
            result_msg = await update.message.reply_photo(photo=demotivator, caption="Ваш демотиватор готов!\n\n @memfy_bot\n")
            
            # Удаляем сообщение пользователя с текстом после отправки результата
            try:
                await context.bot.delete_message(chat_id=update.message.chat.id, message_id=update.message.message_id)
            except:
                pass
        
        # Очищаем данные пользователя (кроме настроек)
        if user_id in user_data and 'photo' in user_data[user_id]:
            del user_data[user_id]['photo']
        if user_id in user_data and 'meme_type' in user_data[user_id]:
            del user_data[user_id]['meme_type']
        if user_id in user_data and 'classic_font' in user_data[user_id]:
            del user_data[user_id]['classic_font']
        if user_id in user_data and 'classic_type' in user_data[user_id]:
            del user_data[user_id]['classic_type']
        if user_id in user_data and 'is_gif' in user_data[user_id]:
            del user_data[user_id]['is_gif']
            
    except Exception as e:
        logger.error(f"Ошибка при создании мема: {e}")
        await update.message.reply_text("Произошла ошибка при создании мема. Попробуй еще раз.")


def create_classic_meme(photo_bytes: io.BytesIO, top_text: str, bottom_text: str, font_file: str = "Impact.ttf") -> io.BytesIO:
    """Создает классический мем из фото и текста"""
    # Открываем исходное фото
    photo_bytes.seek(0)
    image = Image.open(photo_bytes)
    
    # Конвертируем в RGB если нужно
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    img_width, img_height = image.size
    
    # Размер шрифта зависит от размера изображения (большой размер)
    font_size = max(40, int(img_width / 20))
    
    # Цвет текста - белый
    text_color = (255, 255, 255)
    
    # Загружаем выбранный шрифт
    font_paths = [
        os.path.join(os.path.dirname(__file__), font_file),
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
    
    # Если не найден, используем дефолтный
    if font is None:
        logger.error(f"Шрифт {font_file} не найден, используется стандартный шрифт")
        font = ImageFont.load_default()
    
    # Создаем копию изображения для рисования
    meme = image.copy()
    draw = ImageDraw.Draw(meme)
    
    # Функция для разбивки текста на строки
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
    
    # Функция для рисования текста с обводкой (outline/stroke)
    def draw_text_with_outline(draw, position, text, font, fill_color, outline_color=(0, 0, 0), outline_width=2):
        """Рисует текст с черной обводкой для лучшей читаемости"""
        x, y = position
        # Рисуем обводку (все направления)
        for adj in range(-outline_width, outline_width + 1):
            for adj2 in range(-outline_width, outline_width + 1):
                if adj != 0 or adj2 != 0:
                    draw.text((x + adj, y + adj2), text, font=font, fill=outline_color)
        # Рисуем основной текст
        draw.text(position, text, font=font, fill=fill_color)
    
    # Рисуем верхний текст
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
    
    # Рисуем нижний текст
    if bottom_text:
        max_text_width = img_width - 40
        bottom_lines = wrap_text(bottom_text, font, max_text_width)
        
        # Вычисляем общую высоту нижнего текста
        total_bottom_height = len(bottom_lines) * int(font_size * 1.3)
        y_offset = img_height - total_bottom_height - 20
        
        for line in bottom_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (img_width - text_width) // 2
            draw_text_with_outline(draw, (x, y_offset), line, font, text_color)
            y_offset += int(font_size * 1.3)
    
    # Добавляем водяной знак в случайном углу
    watermark_text = "@memfy_bot"
    watermark_size = 16
    
    # Загружаем маленький шрифт для водяного знака
    watermark_font_paths = [
        os.path.join(os.path.dirname(__file__), "Roboto_Bold.ttf"),
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
    
    # Получаем размер текста водяного знака
    bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
    watermark_width = bbox[2] - bbox[0]
    watermark_height = bbox[3] - bbox[1]
    
    # Создаем временное изображение с прозрачностью для водяного знака
    watermark_img = Image.new('RGBA', (watermark_width + 10, watermark_height + 5), (0, 0, 0, 0))
    watermark_draw = ImageDraw.Draw(watermark_img)
    
    # Рисуем текст с прозрачностью
    watermark_draw.text((5, 0), watermark_text, fill=(255, 255, 255, 128), font=watermark_font)
    
    # Размещаем водяной знак в случайном углу
    offset = 15
    corners = [
        (offset, offset),
        (img_width - watermark_width - offset, offset),
        (offset, img_height - watermark_height - offset),
        (img_width - watermark_width - offset, img_height - watermark_height - offset),
    ]
    
    watermark_x, watermark_y = random.choice(corners)
    
    # Композитруем водяной знак
    meme_rgba = meme.convert('RGBA')
    meme_rgba.paste(watermark_img, (watermark_x, watermark_y), watermark_img)
    meme = meme_rgba.convert('RGB')
    
    # Сохраняем в байты
    output = io.BytesIO()
    meme.save(output, format='JPEG', quality=95)
    output.seek(0)
    
    return output


def create_classic_meme_gif(photo_bytes: io.BytesIO, top_text: str, bottom_text: str, font_file: str = "Impact.ttf") -> io.BytesIO:
    """Создает классический мем из GIF и текста"""
    # Открываем GIF
    photo_bytes.seek(0)
    gif = Image.open(photo_bytes)
    
    # Проверяем, что это действительно GIF
    if not getattr(gif, 'is_animated', False):
        # Если не анимированный, обрабатываем как обычное изображение
        return create_classic_meme(photo_bytes, top_text, bottom_text, font_file)
    
    # Получаем первый кадр для определения размеров
    gif.seek(0)
    first_frame = gif.copy()
    
    if first_frame.mode != 'RGB':
        first_frame = first_frame.convert('RGB')
    
    img_width, img_height = first_frame.size
    
    # Размер шрифта зависит от размера изображения (большой размер)
    font_size = max(40, int(img_width / 20))
    
    # Цвет текста - белый
    text_color = (255, 255, 255)
    
    # Загружаем выбранный шрифт
    font_paths = [
        os.path.join(os.path.dirname(__file__), font_file),
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
    
    # Если не найден, используем дефолтный
    if font is None:
        logger.error(f"Шрифт {font_file} не найден, используется стандартный шрифт")
        font = ImageFont.load_default()
    
    # Загружаем шрифт для водяного знака
    watermark_text = "@memfy_bot"
    watermark_size = 16
    watermark_font_paths = [
        os.path.join(os.path.dirname(__file__), "Roboto_Bold.ttf"),
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
    
    # Функция для разбивки текста на строки
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
    
    # Функция для рисования текста с обводкой
    def draw_text_with_outline(draw, position, text, font, fill_color, outline_color=(0, 0, 0), outline_width=2):
        """Рисует текст с черной обводкой для лучшей читаемости"""
        x, y = position
        # Рисуем обводку (все направления)
        for adj in range(-outline_width, outline_width + 1):
            for adj2 in range(-outline_width, outline_width + 1):
                if adj != 0 or adj2 != 0:
                    draw.text((x + adj, y + adj2), text, font=font, fill=outline_color)
        # Рисуем основной текст
        draw.text(position, text, font=font, fill=fill_color)
    
    # Обрабатываем каждый кадр GIF
    frames = []
    durations = []
    
    try:
        frame_count = 0
        while True:
            gif.seek(frame_count)
            frame = gif.copy()
            
            # Конвертируем в RGB
            if frame.mode != 'RGB':
                frame = frame.convert('RGB')
            
            # Создаем копию для рисования
            meme_frame = frame.copy()
            draw = ImageDraw.Draw(meme_frame)
            
            # Рисуем верхний текст
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
            
            # Рисуем нижний текст
            if bottom_text:
                max_text_width = img_width - 40
                bottom_lines = wrap_text(bottom_text, font, max_text_width, draw)
                
                # Вычисляем общую высоту нижнего текста
                total_bottom_height = len(bottom_lines) * int(font_size * 1.3)
                y_offset = img_height - total_bottom_height - 20
                
                for line in bottom_lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    x = (img_width - text_width) // 2
                    draw_text_with_outline(draw, (x, y_offset), line, font, text_color)
                    y_offset += int(font_size * 1.3)
            
            # Добавляем водяной знак
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
            
            # Получаем длительность кадра
            try:
                duration = frame.info.get('duration', gif.info.get('duration', 100))
                durations.append(duration)
            except:
                durations.append(100)
            
            frame_count += 1
            
            # Проверяем, есть ли еще кадры
            try:
                gif.seek(frame_count)
            except EOFError:
                break
                
    except Exception as e:
        logger.error(f"Ошибка при обработке GIF: {e}")
        # Если ошибка, возвращаем первый кадр как обычное изображение
        if frames:
            output = io.BytesIO()
            frames[0].save(output, format='JPEG', quality=95)
            output.seek(0)
            return output
        else:
            return create_classic_meme(photo_bytes, top_text, bottom_text, font_file)
    
    # Сохраняем как анимированный GIF
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
                      demotivator_type: str = "type_normal", font_color: str = "white") -> io.BytesIO:
    """Создает демотиватор из фото и текста"""
    # Размеры шрифтов по умолчанию
    if font_size is None:
        font_size = {"top": 40, "bottom": 28}
    
    # Используем выбранные размеры шрифта напрямую, так как все изображения будут 512x512
    top_font_size = font_size.get("top", 40)
    bottom_font_size = font_size.get("bottom", 28)
    
    # Цвета в RGB
    color_map = {
        "red": (255, 0, 0),
        "white": (255, 255, 255),
        "blue": (0, 0, 255),
        "green": (0, 255, 0),
        "purple": (128, 0, 128),
    }
    
    text_color = color_map.get(font_color, (255, 255, 255))  # По умолчанию белый
    
    # Открываем исходное фото (уже открывали выше, но нужно для дальнейшей работы)
    photo_bytes.seek(0)
    image = Image.open(photo_bytes)
    
    # Конвертируем в RGB если нужно
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Изменяем размер изображения до стандартного 512×512
    STANDARD_SIZE = 512
    if image.size != (STANDARD_SIZE, STANDARD_SIZE):
        image = image.resize((STANDARD_SIZE, STANDARD_SIZE), Image.Resampling.LANCZOS)
        img_width = STANDARD_SIZE
        img_height = STANDARD_SIZE
    
    # Размеры
    padding = 30  # Отступ от края черной рамки
    border_thickness = 10  # Толщина черной рамки
    total_padding = padding + border_thickness
    
    # Размеры уже получены выше, используем их
    # img_width, img_height уже определены выше
    
    # Для типа "только внизу" нужно меньше места сверху
    top_space = 80 if demotivator_type == "type_normal" else 20
    demotivator_width = img_width + (total_padding * 2)
    demotivator_height = img_height + (total_padding * 2) + (200 if demotivator_type == "type_normal" else 120)
    
    # Создаем черный фон
    demotivator = Image.new('RGB', (demotivator_width, demotivator_height), color='black')
    
    # Вставляем фото с отступом
    photo_x = total_padding
    photo_y = total_padding + top_space
    demotivator.paste(image, (photo_x, photo_y))
    
    # Рисуем черную рамку вокруг фото
    draw = ImageDraw.Draw(demotivator)
    frame_x1 = photo_x - border_thickness
    frame_y1 = photo_y - border_thickness
    frame_x2 = photo_x + img_width + border_thickness
    frame_y2 = photo_y + img_height + border_thickness
    
    # Рисуем рамку (толщина 10 пикселей)
    for i in range(border_thickness):
        draw.rectangle(
            [frame_x1 - i, frame_y1 - i, frame_x2 + i, frame_y2 + i],
            outline='white',
            width=1
        )
    
    # Загружаем шрифт из папки проекта
    font_paths = [
        os.path.join(os.path.dirname(__file__), font_file),
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
    
    # Если не найден, используем дефолтный
    if font_large is None:
        logger.error(f"Шрифт {font_file} не найден, используется стандартный шрифт")
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Функция для разбивки текста на строки
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
    
    # Рисуем верхний текст (заголовок) - только для обычного типа
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
    
    # Рисуем нижний текст (подпись)
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
    
    # Добавляем водяной знак в случайном углу
    watermark_text = "@memfy_bot"
    watermark_size = 16  # Маленький размер для водяного знака
    
    # Загружаем маленький шрифт для водяного знака (используем Roboto Bold для водяного знака)
    watermark_font_paths = [
        os.path.join(os.path.dirname(__file__), "Roboto_Bold.ttf"),
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
    
    # Получаем размер текста водяного знака
    bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
    watermark_width = bbox[2] - bbox[0]
    watermark_height = bbox[3] - bbox[1]
    
    # Создаем временное изображение с прозрачностью для водяного знака
    watermark_img = Image.new('RGBA', (watermark_width + 10, watermark_height + 5), (0, 0, 0, 0))
    watermark_draw = ImageDraw.Draw(watermark_img)
    
    # Рисуем текст с прозрачностью (128 из 255 = примерно 50% прозрачности)
    watermark_draw.text((5, 0), watermark_text, fill=(255, 255, 255, 128), font=watermark_font)
    
    # Размещаем водяной знак в случайном углу с небольшим отступом
    offset = 15
    corners = [
        (offset, offset),  # Левый верхний
        (demotivator_width - watermark_width - offset, offset),  # Правый верхний
        (offset, demotivator_height - watermark_height - offset),  # Левый нижний
        (demotivator_width - watermark_width - offset, demotivator_height - watermark_height - offset),  # Правый нижний
    ]
    
    # Выбираем случайный угол
    watermark_x, watermark_y = random.choice(corners)
    
    # Композитруем водяной знак на демотиватор
    # Конвертируем демотиватор в RGBA для композитинга
    demotivator_rgba = demotivator.convert('RGBA')
    demotivator_rgba.paste(watermark_img, (watermark_x, watermark_y), watermark_img)
    # Конвертируем обратно в RGB для сохранения в JPEG
    demotivator = demotivator_rgba.convert('RGB')
    
    # Сохраняем в байты
    output = io.BytesIO()
    demotivator.save(output, format='JPEG', quality=95)
    output.seek(0)
    
    return output


def main():
    """Запуск бота"""
    # Получаем токен из переменной окружения
    token = "8591895755:AAGNb8S94EkRhktBXiKEpYJQm_PJFnqkMnY"
    
    if not token:
        print("Ошибка: Установите переменную окружения TELEGRAM_BOT_TOKEN")
        print("Например: set TELEGRAM_BOT_TOKEN=8591895755:AAGNb8S94EkRhktBXiKEpYJQm_PJFnqkMnY")
        return
    
    # Создаем приложение
    application = Application.builder().token(token).job_queue(None).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("size", size_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.PHOTO | filters.ANIMATION, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Запускаем бота
    print("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':

    main()
