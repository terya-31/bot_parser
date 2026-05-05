# bot.py - добавлена история поиска и улучшенный /top
import os
import json
from datetime import datetime
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Импорт функций из ind_analyze
from ind_analyze import analyze_team, get_all_teams, LEAGUES

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Токен не найден")
    exit(1)

# ============ ФАЙЛ ДЛЯ ХРАНЕНИЯ ДАННЫХ ============
USERS_DATA_FILE = "users_data.json"


def get_message(update: Update):
    """Возвращает правильный объект message (из команды или из callback)"""
    if update.callback_query:
        return update.callback_query.message
    return update.message

def load_users_data():
    """Загружает данные пользователей (история, подписки и т.д.)"""
    if os.path.exists(USERS_DATA_FILE):
        with open(USERS_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users_data(data):
    """Сохраняет данные пользователей"""
    with open(USERS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_history(user_id):
    """Возвращает историю поиска пользователя"""
    users_data = load_users_data()
    user_id_str = str(user_id)
    if user_id_str not in users_data:
        return []
    return users_data[user_id_str].get('history', [])

def add_to_history(user_id, query):
    """Добавляет запрос в историю поиска"""
    users_data = load_users_data()
    user_id_str = str(user_id)
    if user_id_str not in users_data:
        users_data[user_id_str] = {'history': []}
    
    history = users_data[user_id_str].get('history', [])
    # Добавляем в начало, удаляем дубликаты
    if query in history:
        history.remove(query)
    history.insert(0, query)
    # Оставляем только последние 10
    users_data[user_id_str]['history'] = history[:10]
    save_users_data(users_data)

# ============ КЭШ КОМАНД ============
teams_cache = None
DATA_DIR = 'leagues'

def get_cached_teams():
    global teams_cache
    if teams_cache is None:
        teams_cache = get_all_teams(DATA_DIR)
    return teams_cache

def split_long_message(text, max_length=4000):
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

# ============ КОМАНДЫ БОТА ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ *Футбольный аналитический бот*\n\n"
        "Я анализирую форму команд на основе последних 5 матчей.\n\n"
        "⚠️ *ВАЖНО:* Выводимые данные носят информационный характер.\n\n"
        "📋 *Доступные команды:*\n"
        "• `/teams` - показать все команды\n"
        "• `/top` - топ-10 команд по форме (с выбором лиги)\n"
        "• `/history` - история поиска\n"
        "• `/analyze <название>` - анализ команды\n"
        "• `/league <название>` - таблица лиги\n"
        "• `/menu` - меню выбора лиги",
        parse_mode='Markdown'
    )

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает историю поиска пользователя"""
    user_id = update.effective_user.id
    history = get_user_history(user_id)
    
    if not history:
        await update.message.reply_text("📭 История поиска пуста.\nИспользуйте /analyze <команда>")
        return
    
    message = "📜 *История поиска:*\n\n"
    for i, query in enumerate(history, 1):
        message += f"{i}. {query}\n"
    
    message += "\n_Чтобы повторить поиск, нажмите на команду:_\n"
    message += f"`/analyze {history[0]}`" if history else ""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает топ-10 команд с возможностью выбора лиги"""
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
    sorted_teams = sorted(all_teams_data, key=lambda x: x['points'], reverse=True)
    
    # Группируем по лигам
    teams_by_league = defaultdict(list)
    for team in sorted_teams:
        teams_by_league[team['league']].append(team)
    
    # Создаём клавиатуру для выбора лиги
    keyboard = []
    for league in teams_by_league.keys():
        keyboard.append([InlineKeyboardButton(f"🏆 {league}", callback_data=f"top_league_{league}")])
    
    keyboard.append([InlineKeyboardButton("🌍 Все лиги", callback_data="top_league_all")])
    
    await update.message.reply_text(
        "🏆 *ТОП КОМАНД ПО ФОРМЕ*\n\n"
        "Выберите лигу для просмотра топа:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def show_top_for_league(update: Update, context: ContextTypes.DEFAULT_TYPE, league_name=None):
    """Показывает топ команд для конкретной лиги"""
    teams = get_cached_teams()
    if not teams:
        await get_message(update).reply_text("❌ Нет данных.")
        return
    
    all_teams_data = []
    for team in teams:
        try:
            team_data = analyze_team(team['file'])
            all_teams_data.append(team_data)
        except Exception as e:
            continue
    
    # Фильтруем по лиге
    if league_name and league_name != "Все лиги":
        filtered_teams = [t for t in all_teams_data if t['league'] == league_name]
    else:
        filtered_teams = all_teams_data
    
    # Сортируем
    sorted_teams = sorted(filtered_teams, key=lambda x: x['points'], reverse=True)[:10]
    
    if not sorted_teams:
        await get_message(update).reply_text(f"❌ Нет данных для лиги {league_name}")
        return
    
    message = f"🏆 *ТОП-10 КОМАНД*"
    if league_name and league_name != "Все лиги":
        message += f" *{league_name}*\n\n"
    else:
        message += "\n\n"
    
    for i, team in enumerate(sorted_teams, 1):
        message += f"{i}. *{team['team']}*\n"
        message += f"   📊 {team['form']} | ⭐ {team['points']} очков\n"
        message += f"   ⚽ {team['goals_for']}/{team['goals_against']}\n"
        if team.get('xG_avg'):
            message += f"   📈 xG: {team['xG_avg']:.2f}\n"
        if team.get('corners_avg'):
            message += f"   🚩 Угловые: {team['corners_avg']:.1f}\n"
        message += "\n"
    
    # Используем правильный способ отправки сообщения
    await get_message(update).reply_text(message, parse_mode='Markdown')

async def _show_top_for_league(update: Update, context: ContextTypes.DEFAULT_TYPE, league_name=None):
    """Показывает топ команд для конкретной лиги"""
    teams = get_cached_teams()
    if not teams:
        await update.message.reply_text("❌ Нет данных.")
        return
    
    all_teams_data = []
    for team in teams:
        try:
            team_data = analyze_team(team['file'])
            all_teams_data.append(team_data)
        except Exception as e:
            continue
    
    # Фильтруем по лиге
    if league_name and league_name != "Все лиги":
        filtered_teams = [t for t in all_teams_data if t['league'] == league_name]
    else:
        filtered_teams = all_teams_data
    
    # Сортируем
    sorted_teams = sorted(filtered_teams, key=lambda x: x['points'], reverse=True)[:10]
    
    if not sorted_teams:
        await update.message.reply_text(f"❌ Нет данных для лиги {league_name}")
        return
    
    message = f"🏆 *ТОП-10 КОМАНД*"
    if league_name and league_name != "Все лиги":
        message += f" *{league_name}*\n\n"
    else:
        message += "\n\n"
    
    for i, team in enumerate(sorted_teams, 1):
        message += f"{i}. *{team['team']}*\n"
        message += f"   📊 {team['form']} | ⭐ {team['points']} очков\n"
        message += f"   ⚽ {team['goals_for']}/{team['goals_against']}\n"
        if team.get('xG_avg'):
            message += f"   📈 xG: {team['xG_avg']:.2f}\n"
        if team.get('corners_avg'):
            message += f"   🚩 Угловые: {team['corners_avg']:.1f}\n"
        message += "\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Анализирует команду и сохраняет в историю"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название команды.\n"
            "Пример: `/analyze Айнтрахт Ф`\n"
            "Используйте /teams для просмотра всех команд",
            parse_mode='Markdown'
        )
        return
    
    team_name = ' '.join(context.args)
    
    # Сохраняем в историю
    user_id = update.effective_user.id
    add_to_history(user_id, team_name)
    
    teams = get_cached_teams()
    found_team = None
    
    for team in teams:
        if team['name'].lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team:
        matches = [t for t in teams if team_name.lower() in t['name'].lower()]
        if matches:
            if len(matches) == 1:
                found_team = matches[0]
            else:
                message = "🔍 *Найдено несколько команд:*\n\n"
                for m in matches[:5]:
                    message += f"• {m['name']} ({m['league']})\n"
                message += "\nУточните запрос"
                await update.message.reply_text(message, parse_mode='Markdown')
                return
        else:
            await update.message.reply_text(f"❌ Команда '{team_name}' не найдена.")
            return
    
    msg = await update.message.reply_text(f"📊 Анализирую {found_team['name']}...")
    
    try:
        from ind_analyze import generate_full_team_report
        team_data = analyze_team(found_team['file'])
        report = generate_full_team_report(team_data)
        
        for part in split_long_message(report):
            await update.message.reply_text(f"```\n{part}\n```", parse_mode='Markdown')
        
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка при анализе: {e}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик инлайн-кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("top_league_"):
        league_name = data[11:]
        if league_name == "all":
            league_name = "Все лиги"
        await show_top_for_league(update, context, league_name)
        await query.delete()

async def league_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает таблицу лиги"""
    if not context.args:
        league_names = "\n".join([f"• {cfg['name']}" for cfg in LEAGUES.values()])
        await update.message.reply_text(
            f"❌ Укажите название лиги.\n\n*Доступные лиги:*\n{league_names}\n\nПример: `/league Английская Премьер-лига`",
            parse_mode='Markdown'
        )
        return
    
    league_name = ' '.join(context.args)
    league_key = None
    
    for key, cfg in LEAGUES.items():
        if cfg['name'].lower() == league_name.lower():
            league_key = key
            break
    
    if not league_key:
        await update.message.reply_text(f"❌ Лига '{league_name}' не найдена.")
        return
    
    try:
        from analyze import analyze_league
        results = analyze_league(league_key, DATA_DIR)
        if not results:
            await update.message.reply_text("❌ Нет данных для этой лиги.")
            return
        
        message = f"🏆 *{LEAGUES[league_key]['name']}*\n\n```\n"
        message += f"{'#':<3} {'Команда':<32} {'Форма':<8} {'Очки':<5}\n"
        message += "-" * 50 + "\n"
        
        for i, team in enumerate(results, 1):
            message += f"{i:<3} {team['team']:<32} {team['form']:<8} {team['points']:<5}\n"
        
        message += "```"
        
        for part in split_long_message(message):
            await update.message.reply_text(part, parse_mode='Markdown')
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def teams_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список команд"""
    teams = get_cached_teams()
    if not teams:
        await update.message.reply_text("❌ Нет данных.")
        return
    
    message = "📋 *Список команд по лигам:*\n\n"
    current_league = None
    for team in teams:
        if current_league != team['league']:
            current_league = team['league']
            message += f"\n🏆 *{current_league}*\n"
        message += f"• {team['name']}\n"
    
    for part in split_long_message(message):
        await update.message.reply_text(part, parse_mode='Markdown')

async def league_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню выбора лиги"""
    keyboard = [[InlineKeyboardButton(f"🏆 {cfg['name']}", callback_data=f"top_league_{cfg['name']}")] 
                for cfg in LEAGUES.values()]
    keyboard.append([InlineKeyboardButton("🌍 Все лиги", callback_data="top_league_all")])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="menu")])
    
    await update.message.reply_text(
        "🏆 *Выберите лигу для просмотра топа:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("teams", teams_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("league", league_command))
    app.add_handler(CommandHandler("menu", league_menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()