# ind_analyze.py - автоматический анализ всех команд
import json
import os
from datetime import datetime
from collections import defaultdict

# ============ КОНФИГУРАЦИЯ ЛИГ ============
LEAGUES = {
    'premier_league': {
        'name': 'Английская Премьер-лига',
        'folder': 'premier_league',
        'short_name': 'АПЛ'
    },
    'bundesliga': {
        'name': 'Немецкая Бундеслига',
        'folder': 'bundesliga',
        'short_name': 'Бундеслига'
    },
    'laliga': {
        'name': 'Испанская Ла Лига',
        'folder': 'laliga',
        'short_name': 'Ла Лига'
    },
    'serie_a': {
        'name': 'Итальянская Серия А',
        'folder': 'serie_a',
        'short_name': 'Серия А'
    },
    'ligue_1': {
        'name': 'Французская Лига 1',
        'folder': 'ligue_1',
        'short_name': 'Лига 1'
    },
    'rpl': {
        'name': 'Российская Премьер-лига',
        'folder': 'rpl',
        'short_name': 'РПЛ'
    }
}

# ============ ОСНОВНЫЕ ФУНКЦИИ ============

def analyze_team(json_file):
    """Анализирует данные одной команды из JSON-файла"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    team = data['team']
    league = data.get('league', 'Неизвестная лига')
    last_5 = data['form']['last_5']
    
    wins = data['form']['wins']
    draws = data['form']['draws']
    losses = data['form']['losses']
    points = data['form']['points']
    
    goals_for = 0
    goals_against = 0
    total_xG = 0
    total_xG_against = 0
    total_shots = 0
    total_shots_on_target = 0
    total_corners = 0
    yellow_cards = 0
    red_cards = 0
    matches = len(last_5)
    
    goals_trend = []
    goals_conceded_trend = []
    result_trend = []
    
    stats_matches = {
        'xG': 0,
        'shots': 0,
        'corners': 0,
        'yellow': 0,
        'red': 0
    }
    
    match_details = []
    
    for match in last_5:
        is_home = (match['home'] == team)
        
        if is_home:
            gf = int(match['home_score']) if match['home_score'].isdigit() else 0
            ga = int(match['away_score']) if match['away_score'].isdigit() else 0
            opponent = match['away']
            venue = 'Д'
        else:
            gf = int(match['away_score']) if match['away_score'].isdigit() else 0
            ga = int(match['home_score']) if match['home_score'].isdigit() else 0
            opponent = match['home']
            venue = 'Г'
        
        goals_for += gf
        goals_against += ga
        goals_trend.append(gf)
        goals_conceded_trend.append(ga)
        
        if match['result'] == 'В':
            result_trend.append(3)
            result_text = 'Победа'
        elif match['result'] == 'Н':
            result_trend.append(1)
            result_text = 'Ничья'
        else:
            result_trend.append(0)
            result_text = 'Поражение'
        
        stats = match.get('stats', {})
        
        match_data = {
            'opponent': opponent,
            'venue': venue,
            'score': f"{gf}-{ga}",
            'result': result_text,
            'xG_for': None,
            'xG_against': None,
            'shots': None,
            'shots_on_target': None,
            'corners': None,
            'yellow': None,
            'possession': None
        }
        
        if 'Ожидаемые голы (xG)' in stats and stats['Ожидаемые голы (xG)']:
            stats_matches['xG'] += 1
            if is_home:
                xg_for = float(stats['Ожидаемые голы (xG)']['home'])
                xg_against = float(stats['Ожидаемые голы (xG)']['away'])
            else:
                xg_for = float(stats['Ожидаемые голы (xG)']['away'])
                xg_against = float(stats['Ожидаемые голы (xG)']['home'])
            total_xG += xg_for
            total_xG_against += xg_against
            match_data['xG_for'] = round(xg_for, 2)
            match_data['xG_against'] = round(xg_against, 2)
        
        if 'Всего ударов' in stats and stats['Всего ударов']:
            stats_matches['shots'] += 1
            if is_home:
                shots = int(stats['Всего ударов']['home'])
                shots_ot = int(stats['Удары в створ']['home'])
            else:
                shots = int(stats['Всего ударов']['away'])
                shots_ot = int(stats['Удары в створ']['away'])
            total_shots += shots
            total_shots_on_target += shots_ot
            match_data['shots'] = shots
            match_data['shots_on_target'] = shots_ot
        
        if 'Угловые' in stats and stats['Угловые']:
            stats_matches['corners'] += 1
            if is_home:
                corners = int(stats['Угловые']['home'])
            else:
                corners = int(stats['Угловые']['away'])
            total_corners += corners
            match_data['corners'] = corners
        
        if 'Желтые карточки' in stats and stats['Желтые карточки']:
            stats_matches['yellow'] += 1
            if is_home:
                yellow = int(stats['Желтые карточки']['home'])
            else:
                yellow = int(stats['Желтые карточки']['away'])
            yellow_cards += yellow
            match_data['yellow'] = yellow
        
        if 'Владение мячом' in stats and stats['Владение мячом']:
            if is_home:
                possession = stats['Владение мячом']['home']
            else:
                possession = stats['Владение мячом']['away']
            match_data['possession'] = possession
        
        if 'Красные карточки' in stats and stats['Красные карточки']:
            if is_home:
                red = int(stats['Красные карточки']['home'])
            else:
                red = int(stats['Красные карточки']['away'])
            red_cards += red
        
        match_details.append(match_data)
    
    efficiency = round(goals_for / total_xG, 2) if total_xG else 0
    defensive_efficiency = round(goals_against / total_xG_against, 2) if total_xG_against else 0
    realization = round(goals_for / total_xG * 100, 1) if total_xG else 0
    
    def calc_trend(values):
        if len(values) < 2:
            return 0
        n = len(values)
        x = list(range(1, n + 1))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0
        return round(slope, 2)
    
    goals_trend_value = calc_trend(goals_trend)
    conceded_trend = calc_trend(goals_conceded_trend)
    form_trend_value = calc_trend(result_trend)
    
    result = {
        'league': league,
        'team': team,
        'form': f"{wins}-{draws}-{losses}",
        'points': points,
        'points_avg': round(points / matches, 2),
        'goals_for': goals_for,
        'goals_against': goals_against,
        'goals_avg': round(goals_for / matches, 2),
        'goals_against_avg': round(goals_against / matches, 2),
        'goal_difference': goals_for - goals_against,
        
        'xG_avg': round(total_xG / stats_matches['xG'], 2) if stats_matches['xG'] else None,
        'xG_against_avg': round(total_xG_against / stats_matches['xG'], 2) if stats_matches['xG'] else None,
        'xG_matches': stats_matches['xG'],
        'efficiency': efficiency,
        'defensive_efficiency': defensive_efficiency,
        'realization': realization,
        
        'shots_avg': round(total_shots / stats_matches['shots'], 1) if stats_matches['shots'] else None,
        'shots_matches': stats_matches['shots'],
        'shots_on_target_avg': round(total_shots_on_target / stats_matches['shots'], 1) if stats_matches['shots'] else None,
        'accuracy': round(total_shots_on_target / total_shots * 100, 1) if total_shots else None,
        
        'corners_avg': round(total_corners / stats_matches['corners'], 1) if stats_matches['corners'] else None,
        'corners_matches': stats_matches['corners'],
        'yellow_avg': round(yellow_cards / stats_matches['yellow'], 1) if stats_matches['yellow'] else None,
        'yellow_matches': stats_matches['yellow'],
        'red_cards': red_cards,
        
        'match_details': match_details,
        
        'trend': {
            'goals': goals_trend_value,
            'goals_conceded': conceded_trend,
            'form': form_trend_value,
            'direction': '📈' if form_trend_value > 0 else '📉' if form_trend_value < 0 else '➡️'
        },
        
        'win_probability': round(wins / matches * 100),
        'wins': wins,
        'draws': draws,
        'losses': losses
    }
    
    return result

def get_all_teams(base_dir='leagues'):
    """Собирает список всех команд из всех лиг"""
    all_teams = []
    
    for league_key, league_config in LEAGUES.items():
        teams_dir = os.path.join(base_dir, league_config['folder'], 'teams')
        if not os.path.exists(teams_dir):
            continue
        
        for file in os.listdir(teams_dir):
            if file.endswith('.json'):
                filepath = os.path.join(teams_dir, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_teams.append({
                        'name': data['team'],
                        'league': league_config['name'],
                        'league_key': league_key,
                        'file': filepath
                    })
    
    return sorted(all_teams, key=lambda x: x['league'])

# ============ ФУНКЦИИ ДЛЯ ГЕНЕРАЦИИ ОТЧЁТОВ ============

def generate_match_table(team_data):
    """Генерирует детальную таблицу матчей"""
    matches = team_data.get('match_details', [])
    if not matches:
        return "Нет данных о матчах"
    
    table = "| № | Соперник | Д/Г | Счёт | Результат | xG (за/против) | Удары | В створ | Угловые | ЖК | Владение |\n"
    table += "|---|----------|-----|------|-----------|-----------------|-------|---------|---------|-----|----------|\n"
    
    for i, match in enumerate(matches, 1):
        xg_str = f"{match.get('xG_for', '-')}/{match.get('xG_against', '-')}" if match.get('xG_for') else "-"
        shots_str = str(match.get('shots', '-'))
        shots_ot_str = str(match.get('shots_on_target', '-'))
        corners_str = str(match.get('corners', '-'))
        yellow_str = str(match.get('yellow', '-'))
        possession_str = match.get('possession', '-')
        
        table += f"| {i} | {match['opponent']} | {match['venue']} | {match['score']} | {match['result']} | {xg_str} | {shots_str} | {shots_ot_str} | {corners_str} | {yellow_str} | {possession_str} |\n"
    
    return table

def generate_averages_table(team_data):
    """Генерирует таблицу усреднённых показателей"""
    stats = []
    
    # Результаты
    points_status = 'Ниже среднего' if team_data['points'] < 7 else ('Средне' if team_data['points'] < 10 else 'Выше среднего')
    stats.append(('🏆 Очки', f"{team_data['points']} из 15", points_status))
    
    form_status = 'Нестабильная' if '1-2-2' in team_data['form'] or '2-1-2' in team_data['form'] else 'Стабильная'
    stats.append(('📊 Форма', team_data['form'], form_status))
    
    goals_status = 'Ниже среднего' if team_data['goals_avg'] < 1.5 else ('Средне' if team_data['goals_avg'] < 2.0 else 'Выше среднего')
    stats.append(('⚽ Забито', f"{team_data['goals_avg']:.1f} за матч", goals_status))
    
    against_status = 'Выше среднего' if team_data['goals_against_avg'] > 1.5 else 'Средне'
    stats.append(('🛡️ Пропущено', f"{team_data['goals_against_avg']:.1f} за матч", against_status))
    
    # Атака
    if team_data.get('xG_avg'):
        xg_status = 'Выше' if team_data['xG_avg'] > 1.5 else 'Ниже'
        stats.append(('📈 xG (за)', f"{team_data['xG_avg']:.2f}", f"{xg_status} среднего"))
        
        xg_against = team_data.get('xG_against_avg', 0)
        xg_against_status = 'Высокий (опасно)' if xg_against > 1.8 else 'Средний'
        stats.append(('📉 xG (против)', f"{xg_against:.2f}", xg_against_status))
        
        realization_status = 'Нормально' if 80 < team_data['realization'] < 110 else ('Отлично' if team_data['realization'] >= 110 else 'Плохо')
        stats.append(('💪 Реализация', f"{team_data['realization']:.0f}% от xG", realization_status))
    
    if team_data.get('shots_avg'):
        shots_status = 'Хорошо' if team_data['shots_avg'] > 12 else ('Средне' if team_data['shots_avg'] > 9 else 'Мало')
        stats.append(('🎯 Ударов за матч', f"{team_data['shots_avg']:.1f}", shots_status))
        
        shots_ot = team_data.get('shots_on_target_avg', 0)
        shots_ot_status = 'Хорошо' if shots_ot > 4 else 'Средне'
        stats.append(('🎯 Ударов в створ', f"{shots_ot:.1f}", shots_ot_status))
        
        if team_data['accuracy']:
            accuracy_status = 'Приемлемо' if team_data['accuracy'] > 30 else 'Низкая'
            stats.append(('🎯 Точность ударов', f"{team_data['accuracy']:.0f}%", accuracy_status))
    
    if team_data.get('corners_avg'):
        corners_status = 'Много' if team_data['corners_avg'] >= 7 else ('Средне' if team_data['corners_avg'] >= 4 else 'Мало')
        stats.append(('🚩 Угловые за матч', f"{team_data['corners_avg']:.1f}", corners_status))
    
    if team_data.get('yellow_avg'):
        yellow_status = 'Хорошо' if team_data['yellow_avg'] < 2 else 'Средне'
        stats.append(('🟨 Жёлтые карточки', f"{team_data['yellow_avg']:.1f}", yellow_status))
    
    # Формируем таблицу
    table = "| Категория | Показатель | Значение | Оценка |\n"
    table += "|-----------|------------|----------|--------|\n"
    
    for row in stats:
        # Убеждаемся, что в строке 4 элемента
        if len(row) >= 3:
            # Если 3 элемента, добавляем пустую оценку
            if len(row) == 3:
                table += f"| {row[0]} | {row[1]} | {row[2]} | — |\n"
            else:
                table += f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |\n"
    
    return table

def generate_insights(team_data):
    """Генерирует аналитические выводы и тенденции"""
    insights = []
    
    # Тенденции
    if team_data['trend']['goals'] > 0.3:
        insights.append(f"✅ **Атака улучшается**: забитые голы растут ({team_data['trend']['goals']:+.2f} за матч)")
    elif team_data['trend']['goals'] < -0.3:
        insights.append(f"⚠️ **Атака ухудшается**: забитые голы падают ({team_data['trend']['goals']:+.2f} за матч)")
    
    if team_data['trend']['goals_conceded'] > 0.3:
        insights.append(f"⚠️ **Оборона ухудшается**: пропущенные голы растут ({team_data['trend']['goals_conceded']:+.2f} за матч)")
    elif team_data['trend']['goals_conceded'] < -0.3:
        insights.append(f"✅ **Оборона улучшается**: пропущенные голы падают ({team_data['trend']['goals_conceded']:+.2f} за матч)")
    
    # xG анализ
    if team_data.get('xG_avg') and team_data.get('xG_against_avg'):
        if team_data['xG_against_avg'] > 1.8:
            insights.append(f"⚠️ **Проблемы в обороне**: команда пропускает много опасных моментов (xG против {team_data['xG_against_avg']:.2f})")
        if team_data['xG_avg'] < 1.2:
            insights.append(f"⚠️ **Проблемы в атаке**: команда создаёт мало моментов (xG {team_data['xG_avg']:.2f})")
    
    # Реализация
    if team_data.get('realization'):
        if team_data['realization'] > 110:
            insights.append(f"✅ **Перебивают xG**: забивают больше ожидаемого (реализация {team_data['realization']:.0f}%)")
        elif team_data['realization'] < 90:
            insights.append(f"⚠️ **Недобирают xG**: забивают меньше ожидаемого (реализация {team_data['realization']:.0f}%)")
    
    return insights

def generate_betting_picks(team_data):
    """Генерирует рекомендации для ставок на основе данных"""
    matches = team_data.get('match_details', [])
    if len(matches) < 5:
        return []
    
    both_scored = 0
    over_25 = 0
    
    for match in matches:
        score = match['score']
        goals = sum(int(x) for x in score.split('-') if x.isdigit())
        
        home_goal = int(score.split('-')[0]) if score.split('-')[0].isdigit() else 0
        away_goal = int(score.split('-')[1]) if score.split('-')[1].isdigit() else 0
        
        if home_goal > 0 and away_goal > 0:
            both_scored += 1
        if goals > 2.5:
            over_25 += 1
    
    total_matches = len(matches)
    picks = []
    
    if both_scored / total_matches >= 0.6:
        picks.append({
            'bet': 'Обе забьют — ДА',
            'probability': f'{both_scored/total_matches*100:.0f}%',
            'reason': f'Заходила в {both_scored}/{total_matches} матчах'
        })
    
    if over_25 / total_matches >= 0.6:
        picks.append({
            'bet': 'Тотал голов БОЛЬШЕ 2.5',
            'probability': f'{over_25/total_matches*100:.0f}%',
            'reason': f'Заходил в {over_25}/{total_matches} матчах'
        })
    
    if team_data.get('corners_avg') and team_data['corners_avg'] >= 5:
        picks.append({
            'bet': 'Угловые команды БОЛЬШЕ 4.5',
            'probability': 'Ожидается',
            'reason': f'В среднем {team_data["corners_avg"]:.1f} угловых за матч'
        })
    
    return picks

def generate_full_team_report(team_data):
    """Генерирует полный отчёт по команде"""
    
    report = []
    report.append("=" * 70)
    report.append(f"📊 РАСШИРЕННЫЙ АНАЛИЗ: {team_data['team']} ({team_data['league']})")
    report.append("=" * 70)
    report.append("")
    
    report.append("### 1. 📋 ДЕТАЛЬНАЯ ТАБЛИЦА МАТЧЕЙ")
    report.append(generate_match_table(team_data))
    report.append("")
    
    report.append("### 2. 📊 УСРЕДНЁННЫЕ ПОКАЗАТЕЛИ")
    report.append(generate_averages_table(team_data))
    report.append("")
    
    report.append("### 3. 📈 ТЕНДЕНЦИИ И ВЫВОДЫ")
    insights = generate_insights(team_data)
    if insights:
        for insight in insights:
            report.append(f"{insight}")
    else:
        report.append("Нет ярко выраженных тенденций")
    report.append("")
    
    report.append("### 4. 💰 СТАВОЧНЫЕ ПРОГНОЗЫ")
    picks = generate_betting_picks(team_data)
    if picks:
        report.append("| Ставка | Вероятность | Обоснование |")
        report.append("|--------|-------------|-------------|")
        for pick in picks:
            report.append(f"| **{pick['bet']}** | {pick['probability']} | {pick['reason']} |")
    else:
        report.append("Недостаточно данных для уверенных прогнозов")
    report.append("")
    
    report.append("### 5. 🎯 ПРОГНОЗ НА СЛЕДУЮЩИЙ МАТЧ")
    report.append("| Показатель | Прогноз |")
    report.append("|------------|---------|")
    report.append(f"| **Ожидаемые голы (xG)** | {team_data.get('xG_avg', 1.4):.2f} |")
    report.append(f"| **Ожидаемые угловые** | ~{team_data.get('corners_avg', 5):.1f} |")
    report.append(f"| **Вероятность победы** | {team_data['win_probability']}% |")
    report.append("")
    
    report.append("### 🏁 ИТОГОВЫЙ ВЕРДИКТ")
    
    if team_data['points'] < 7:
        report.append(f"{team_data['team']} — команда в кризисе. Требуется смена тактики.")
    elif team_data['points'] < 10:
        report.append(f"{team_data['team']} — нестабильная команда с потенциалом.")
    else:
        report.append(f"{team_data['team']} — в хорошей форме, претендует на высокие места.")
    
    report.append("")
    report.append("=" * 70)
    
    return "\n".join(report)

def generate_short_stats_table(all_teams_data):
    """Генерирует краткую статистическую таблицу по всем командам"""
    
    table = "| № | Команда | Лига | Форма | Очки | Голы (за/против) | xG | Удары | Угловые |\n"
    table += "|---|---------|------|-------|------|-------------------|-----|-------|---------|\n"
    
    # Сортируем по очкам
    sorted_teams = sorted(all_teams_data, key=lambda x: x['points'], reverse=True)
    
    for i, team in enumerate(sorted_teams, 1):
        xg_str = f"{team['xG_avg']:.2f}" if team.get('xG_avg') else "-"
        shots_str = f"{team['shots_avg']:.1f}" if team.get('shots_avg') else "-"
        corners_str = f"{team['corners_avg']:.1f}" if team.get('corners_avg') else "-"
        
        table += f"| {i} | {team['team']} | {team['league']} | {team['form']} | {team['points']} | {team['goals_for']}/{team['goals_against']} | {xg_str} | {shots_str} | {corners_str} |\n"
    
    return table

def analyze_all_teams_and_save(base_dir='leagues', output_dir='analysis_reports'):
    """Анализирует все команды и сохраняет отчёты"""
    
    # Создаём основную папку для отчётов
    os.makedirs(output_dir, exist_ok=True)
    
    # Собираем все команды
    all_teams_info = get_all_teams(base_dir)
    print(f"📊 Найдено команд: {len(all_teams_info)}")
    
    all_teams_data = []
    teams_by_league = defaultdict(list)
    
    for team_info in all_teams_info:
        print(f"  📈 Анализируем: {team_info['name']} ({team_info['league']})")
        
        # Анализируем команду
        team_data = analyze_team(team_info['file'])
        all_teams_data.append(team_data)
        teams_by_league[team_info['league']].append(team_data)
        
        # Создаём папку для команды
        safe_name = team_info['name'].lower().replace(' ', '_').replace('-', '_').replace('.', '').replace('ё', 'e')
        team_folder = os.path.join(output_dir, safe_name)
        os.makedirs(team_folder, exist_ok=True)
        
        # Сохраняем подробный отчёт
        report = generate_full_team_report(team_data)
        report_file = os.path.join(team_folder, f"analysis_{safe_name}.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Сохраняем JSON с данными
        json_file = os.path.join(team_folder, f"data_{safe_name}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(team_data, f, ensure_ascii=False, indent=2)
    
    # Сохраняем общую статистическую таблицу
    stats_table = generate_short_stats_table(all_teams_data)
    stats_file = os.path.join(output_dir, "all_teams_stats.txt")
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("📊 СВОДНАЯ СТАТИСТИКА ПО ВСЕМ КОМАНДАМ\n")
        f.write(f"📅 Дата анализа: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write("=" * 100 + "\n\n")
        f.write(stats_table)
    
    # Сохраняем отчёты по лигам
    for league_name, teams in teams_by_league.items():
        league_safe = league_name.lower().replace(' ', '_')
        league_file = os.path.join(output_dir, f"{league_safe}_stats.txt")
        with open(league_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"📊 СТАТИСТИКА ЛИГИ: {league_name}\n")
            f.write(f"📅 Дата анализа: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Таблица по лиге
            f.write("| № | Команда | Форма | Очки | Голы (за/против) | xG | Угловые |\n")
            f.write("|---|---------|-------|------|-------------------|-----|---------|\n")
            
            sorted_teams = sorted(teams, key=lambda x: x['points'], reverse=True)
            for i, team in enumerate(sorted_teams, 1):
                xg_str = f"{team['xG_avg']:.2f}" if team.get('xG_avg') else "-"
                corners_str = f"{team['corners_avg']:.1f}" if team.get('corners_avg') else "-"
                f.write(f"| {i} | {team['team']} | {team['form']} | {team['points']} | {team['goals_for']}/{team['goals_against']} | {xg_str} | {corners_str} |\n")
    
    print(f"\n✅ Анализ завершён!")
    print(f"📁 Отчёты сохранены в папку: {output_dir}")
    print(f"   - {stats_file} (общая статистика)")
    print(f"   - Папки с отчётами для каждой команды")
    
    return all_teams_data

def print_teams_list(teams):
    """Выводит список команд для выбора"""
    print("\n📋 ДОСТУПНЫЕ КОМАНДЫ:\n")
    current_league = None
    for i, team in enumerate(teams, 1):
        if current_league != team['league']:
            current_league = team['league']
            print(f"\n  🏆 {current_league}:")
        print(f"     {i:2}. {team['name']}")

def main():
    print("=" * 70)
    print("📊 АВТОМАТИЧЕСКИЙ АНАЛИЗ ФУТБОЛЬНЫХ КОМАНД")
    print("=" * 70)
    
    # Получаем список всех команд
    teams = get_all_teams()
    
    if not teams:
        print("❌ Нет данных для анализа. Сначала запустите парсер.")
        return
    
    print(f"\n📊 Найдено {len(teams)} команд в {len(LEAGUES)} лигах")
    
    # Спрашиваем пользователя
    print("\nВыберите режим работы:")
    print("1. Автоматический анализ ВСЕХ команд (сохранить отчёты)")
    print("2. Показать список команд")
    print("3. Анализ конкретной команды (с выбором)")
    
    choice = input("\nВаш выбор (1/2/3): ").strip()
    
    if choice == '1':
        print("\n🚀 Запускаем автоматический анализ всех команд...")
        analyze_all_teams_and_save()
    
    elif choice == '2':
        print_teams_list(teams)
    
    elif choice == '3':
        print_teams_list(teams)
        try:
            team_num = int(input("\nВведите номер команды: ")) - 1
            if 0 <= team_num < len(teams):
                team = teams[team_num]
                print(f"\n📊 Анализируем: {team['name']} ({team['league']})")
                team_data = analyze_team(team['file'])
                report = generate_full_team_report(team_data)
                print(report)
                
                # Сохраняем отчёт
                safe_name = team['name'].lower().replace(' ', '_').replace('-', '_')
                os.makedirs('analysis_reports', exist_ok=True)
                filename = f"analysis_reports/{safe_name}_analysis.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n✅ Отчёт сохранён: {filename}")
            else:
                print("❌ Неверный номер команды")
        except ValueError:
            print("❌ Введите число")
    
    else:
        print("❌ Неверный выбор. Запускаем автоматический анализ...")
        analyze_all_teams_and_save()

if __name__ == "__main__":
    main()

LEAGUES = LEAGUES