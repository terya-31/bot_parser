# bot.py - Telegram бот для футбольной аналитики
import os
import json
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Импортируем функции из ваших модулей
try:
    from ind_analyze import (
        analyze_team, 
        generate_full_team_report, 
        get_all_teams,
        LEAGUES as ANALYZE_LEAGUES
    )
    from analyze import analyze_league, print_league_table
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что файлы ind_analyze.py и analyze.py находятся в той же папке")
    exit(1)

# ============ КОНФИГУРАЦИЯ ============
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Токен не найден! Установите переменную окружения BOT_TOKEN")
    exit(1)

# Базовая директория с данными
DATA_DIR = 'leagues'

# Кэш для команд
teams_cache = None

def get_cached_teams():
    """Получает список команд с кэшированием"""
    global teams_cache
    if teams_cache is None:
        teams_cache = get_all_teams(DATA_DIR)
    return teams_cache

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

def format_team_stats_short(team_data):
    """Форматирует краткую статистику команды"""
    message = (
        f"⚽ *{team_data['team']}* ({team_data['league']})\n\n"
        f"📊 *Форма:* {team_data['form']} ({team_data['points']} очков)\n"
        f"🥅 *Голы:* {team_data['goals_for']} забито / {team_data['goals_against']} пропущено\n"
        f"📈 *xG:* {team_data.get('xG_avg', '—')}\n"
        f"🚩 *Угловые:* {team_data.get('corners_avg', '—')} за матч\n"
        f"🎯 *Точность ударов:* {team_data.get('accuracy', '—')}%\n"
        f"📉 *Тренд:* {team_data['trend']['direction']}\n"
        f"👑 *Вероятность победы:* {team_data['win_probability']}%\n"
    )
    return message

def split_long_message(text, max_length=4000):
    """Разбивает длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    lines = text.split('\n')
    current_part = ""
    
    for line in lines:
        if len(current_part) + len(line) + 1 > max_length:
            parts.append(current_part)
            current_part = line + "\n"
        else:
            current_part += line + "\n"
    
    if current_part:
        parts.append(current_part)
    
    return parts

def get_league_key_by_name(league_name):
    """Возвращает ключ лиги по её названию"""
    for key, config in ANALYZE_LEAGUES.items():
        if config['name'] == league_name:
            return key
    return None

# ============ КОМАНДЫ БОТА ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение"""
    await update.message.reply_text(
        "⚽ *Футбольный аналитический бот*\n\n"
        "Я анализирую форму команд на основе последних 5 матчей.\n\n"
        "⚠️ *ВАЖНО:* Выводимые данные носят информационный характер и не являются\n"
        "рекомендацией для совершения ставок. Бот помогает в поиске статистической\n"
        "информации, но окончательное решение всегда за вами.\n\n"
        "📋 *Доступные команды:*\n"
        "• `/teams` - показать все команды\n"
        "• `/top` - топ-10 команд по форме\n"
        "• `/stats` - общая статистика\n"
        "• `/analyze <название>` - детальный анализ команды\n"
        "• `/league <название>` - таблица лиги\n"
        "• `/menu` - меню выбора лиги\n\n"
        "📊 *Примеры:*\n"
        "`/analyze Айнтрахт Ф`\n"
        "`/league Английская Премьер-лига`",
        parse_mode='Markdown'
    )

async def teams_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список всех команд по лигам"""
    teams = get_cached_teams()
    
    if not teams:
        await update.message.reply_text("❌ Нет данных. Сначала запустите парсер.")
        return
    
    message = "📋 *Список команд по лигам:*\n\n"
    current_league = None
    
    for team in teams:
        if current_league != team['league']:
            current_league = team['league']
            message += f"\n🏆 *{current_league}*\n"
        message += f"• {team['name']}\n"
    
    # Разбиваем длинное сообщение
    for part in split_long_message(message):
        await update.message.reply_text(part, parse_mode='Markdown')

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает топ-10 команд по форме"""
    teams = get_cached_teams()
    
    if not teams:
        await update.message.reply_text("❌ Нет данных.")
        return
    
    # Анализируем все команды
    all_teams_data = []
    for team in teams:
        try:
            team_data = analyze_team(team['file'])
            all_teams_data.append(team_data)
        except Exception as e:
            continue
    
    # Сортируем по очкам
    sorted_teams = sorted(all_teams_data, key=lambda x: x['points'], reverse=True)[:10]
    
    message = "🏆 *ТОП-10 КОМАНД ПО ФОРМЕ*\n\n"
    for i, team in enumerate(sorted_teams, 1):
        message += f"{i}. *{team['team']}* ({team['league']})\n"
        message += f"   📊 {team['form']} | ⭐ {team['points']} очков\n"
        message += f"   ⚽ {team['goals_for']}/{team['goals_against']}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает общую статистику"""
    teams = get_cached_teams()
    
    if not teams:
        await update.message.reply_text("❌ Нет данных.")
        return
    
    # Статистика по лигам
    league_stats = {}
    for team in teams:
        league = team['league']
        if league not in league_stats:
            league_stats[league] = {'count': 0}
        league_stats[league]['count'] += 1
    
    message = "📊 *ОБЩАЯ СТАТИСТИКА*\n\n"
    message += f"📁 *Всего команд:* {len(teams)}\n"
    message += f"🏆 *Лиг:* {len(league_stats)}\n\n"
    message += "*По лигам:*\n"
    
    for league, data in league_stats.items():
        message += f"• {league}: {data['count']} команд\n"
    
    # Добавляем дату последнего обновления данных
    message += f"\n📅 *Данные актуальны на:* {datetime.now().strftime('%d.%m.%Y')}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Анализирует конкретную команду"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название команды.\n\n"
            "Пример: `/analyze Айнтрахт Ф`\n"
            "Используйте /teams для просмотра всех команд",
            parse_mode='Markdown'
        )
        return
    
    team_name = ' '.join(context.args)
    
    # Ищем команду
    teams = get_cached_teams()
    found_team = None
    
    for team in teams:
        if team['name'].lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team:
        # Поиск по частичному совпадению
        matches = [t for t in teams if team_name.lower() in t['name'].lower()]
        if matches:
            if len(matches) == 1:
                found_team = matches[0]
            else:
                message = "🔍 *Найдено несколько команд:*\n\n"
                for m in matches[:5]:
                    message += f"• {m['name']} ({m['league']})\n"
                message += "\nУточните запрос или используйте /teams"
                await update.message.reply_text(message, parse_mode='Markdown')
                return
        else:
            await update.message.reply_text(f"❌ Команда '{team_name}' не найдена.\nИспользуйте /teams для просмотра всех команд")
            return
    
    # Отправляем сообщение о начале анализа
    msg = await update.message.reply_text(f"📊 Анализирую {found_team['name']}... Это может занять несколько секунд")
    
    try:
        # Анализируем команду
        team_data = analyze_team(found_team['file'])
        report = generate_full_team_report(team_data)
        
        # Отправляем отчёт
        for part in split_long_message(report):
            await update.message.reply_text(f"```\n{part}\n```", parse_mode='Markdown')
        
        # Удаляем сообщение о загрузке
        await msg.delete()
        
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка при анализе: {e}")

async def league_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает таблицу лиги"""
    if not context.args:
        league_names = "\n".join([f"• {cfg['name']}" for cfg in ANALYZE_LEAGUES.values()])
        await update.message.reply_text(
            f"❌ Укажите название лиги.\n\n"
            f"*Доступные лиги:*\n{league_names}\n\n"
            f"Пример: `/league Английская Премьер-лига`",
            parse_mode='Markdown'
        )
        return
    
    league_name = ' '.join(context.args)
    
    # Ищем лигу
    league_key = None
    for key, cfg in ANALYZE_LEAGUES.items():
        if cfg['name'].lower() == league_name.lower():
            league_key = key
            break
    
    if not league_key:
        await update.message.reply_text(f"❌ Лига '{league_name}' не найдена.")
        return
    
    try:
        results = analyze_league(league_key, DATA_DIR)
        
        if not results:
            await update.message.reply_text(f"❌ Нет данных для лиги {ANALYZE_LEAGUES[league_key]['name']}")
            return
        
        message = f"🏆 *{ANALYZE_LEAGUES[league_key]['name']}*\n\n"
        message += "```\n"
        message += f"{'#':<3} {'Команда':<32} {'Форма':<8} {'Очки':<5} {'Голы':<12}\n"
        message += "-" * 60 + "\n"
        
        for i, team in enumerate(results, 1):
            message += f"{i:<3} {team['team']:<32} {team['form']:<8} {team['points']:<5} {team['goals_for']}/{team['goals_against']:<11}\n"
        
        message += "```"
        
        for part in split_long_message(message):
            await update.message.reply_text(part, parse_mode='Markdown')
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def league_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню выбора лиги"""
    keyboard = []
    for league_key, cfg in ANALYZE_LEAGUES.items():
        keyboard.append([InlineKeyboardButton(f"🏆 {cfg['name']}", callback_data=f"league_{league_key}")])
    
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏆 *Выберите лигу:*", reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик инлайн-кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("league_"):
        league_key = data[7:]
        if league_key in ANALYZE_LEAGUES:
            context.args = [ANALYZE_LEAGUES[league_key]['name']]
            await league_command(update, context)
            await query.delete()
    
    elif data == "menu":
        await start(update, context)
        await query.delete()

# ============ ЗАПУСК БОТА ============

def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("teams", teams_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("league", league_command))
    app.add_handler(CommandHandler("menu", league_menu))
    
    # Обработчик кнопок
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 Бот запущен...")
    print("📋 Доступные команды:")
    print("   /start - Приветствие")
    print("   /teams - Список команд")
    print("   /top - Топ-10 команд")
    print("   /stats - Общая статистика")
    print("   /analyze <название> - Детальный анализ команды")
    print("   /league <название> - Таблица лиги")
    print("   /menu - Меню выбора лиги")
    
    app.run_polling()

if __name__ == "__main__":
    main()