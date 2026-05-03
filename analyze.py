# analyze.py - обновлённая версия с учётом доступности статистики
import json
import os
from datetime import datetime
from collections import defaultdict

# ============ КОНФИГУРАЦИЯ ЛИГ ============
LEAGUES = {
    'premier_league': {
        'name': 'Английская Премьер-лига',
        'folder': 'premier_league',
        'short_name': 'АПЛ',
        'has_extended_stats': True
    },
    'bundesliga': {
        'name': 'Немецкая Бундеслига',
        'folder': 'bundesliga',
        'short_name': 'Бундеслига',
        'has_extended_stats': True
    },
    'laliga': {
        'name': 'Испанская Ла Лига',
        'folder': 'laliga',
        'short_name': 'Ла Лига',
        'has_extended_stats': True
    },
    'serie_a': {
        'name': 'Итальянская Серия А',
        'folder': 'serie_a',
        'short_name': 'Серия А',
        'has_extended_stats': True
    },
    'ligue_1': {
        'name': 'Французская Лига 1',
        'folder': 'ligue_1',
        'short_name': 'Лига 1',
        'has_extended_stats': True
    },
    'rpl': {
        'name': 'Российская Премьер-лига',
        'folder': 'rpl',
        'short_name': 'РПЛ',
        'has_extended_stats': True
    }
}

def analyze_team(json_file):
    """Анализирует данные одной команды из JSON-файла"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    team = data['team']
    league = data.get('league', 'Неизвестная лига')
    last_5 = data['form']['last_5']
    
    # Базовые показатели
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
    matches = len(last_5)
    
    # Счётчики для статистики (только матчи, где есть данные)
    stats_matches = {
        'xG': 0,
        'shots': 0,
        'corners': 0,
        'yellow': 0
    }
    
    for match in last_5:
        # Определяем, где наша команда
        if match['home'] == team:
            goals_for += int(match['home_score']) if match['home_score'].isdigit() else 0
            goals_against += int(match['away_score']) if match['away_score'].isdigit() else 0
        else:
            goals_for += int(match['away_score']) if match['away_score'].isdigit() else 0
            goals_against += int(match['home_score']) if match['home_score'].isdigit() else 0
        
        stats = match.get('stats', {})
        
        # xG (только если есть)
        if 'Ожидаемые голы (xG)' in stats and stats['Ожидаемые голы (xG)']:
            stats_matches['xG'] += 1
            if match['home'] == team:
                total_xG += float(stats['Ожидаемые голы (xG)']['home'])
                total_xG_against += float(stats['Ожидаемые голы (xG)']['away'])
            else:
                total_xG += float(stats['Ожидаемые голы (xG)']['away'])
                total_xG_against += float(stats['Ожидаемые голы (xG)']['home'])
        
        # Удары (только если есть)
        if 'Всего ударов' in stats and stats['Всего ударов']:
            stats_matches['shots'] += 1
            if match['home'] == team:
                total_shots += int(stats['Всего ударов']['home'])
                total_shots_on_target += int(stats['Удары в створ']['home'])
            else:
                total_shots += int(stats['Всего ударов']['away'])
                total_shots_on_target += int(stats['Удары в створ']['away'])
        
        # Угловые (только если есть)
        if 'Угловые' in stats and stats['Угловые']:
            stats_matches['corners'] += 1
            if match['home'] == team:
                total_corners += int(stats['Угловые']['home'])
            else:
                total_corners += int(stats['Угловые']['away'])
        
        # Жёлтые карточки (только если есть)
        if 'Желтые карточки' in stats and stats['Желтые карточки']:
            stats_matches['yellow'] += 1
            if match['home'] == team:
                yellow_cards += int(stats['Желтые карточки']['home'])
            else:
                yellow_cards += int(stats['Желтые карточки']['away'])
    
    # Формируем результат с учётом доступности данных
    result = {
        'league': league,
        'team': team,
        'form': f"{wins}-{draws}-{losses}",
        'points': points,
        'goals_for': goals_for,
        'goals_against': goals_against,
        'goals_avg': round(goals_for / matches, 2),
        # Статистика с пометкой, сколько матчей использовано
        'xG_avg': round(total_xG / stats_matches['xG'], 2) if stats_matches['xG'] else None,
        'xG_matches': stats_matches['xG'],
        'shots_avg': round(total_shots / stats_matches['shots'], 1) if stats_matches['shots'] else None,
        'shots_matches': stats_matches['shots'],
        'accuracy': round(total_shots_on_target / total_shots * 100, 1) if total_shots else None,
        'corners_avg': round(total_corners / stats_matches['corners'], 1) if stats_matches['corners'] else None,
        'corners_matches': stats_matches['corners'],
        'yellow_avg': round(yellow_cards / stats_matches['yellow'], 1) if stats_matches['yellow'] else None,
        'yellow_matches': stats_matches['yellow'],
        'win_probability': round(wins / matches * 100)
    }
    
    return result

def analyze_league(league_key, base_dir='leagues'):
    """Анализирует все команды в указанной лиге"""
    league_config = LEAGUES.get(league_key)
    if not league_config:
        print(f"❌ Лига {league_key} не найдена")
        return []
    
    teams_dir = os.path.join(base_dir, league_config['folder'], 'teams')
    
    if not os.path.exists(teams_dir):
        print(f"❌ Папка {teams_dir} не найдена. Сначала запустите парсер.")
        return []
    
    results = []
    for file in os.listdir(teams_dir):
        if file.endswith('.json'):
            filepath = os.path.join(teams_dir, file)
            try:
                result = analyze_team(filepath)
                results.append(result)
            except Exception as e:
                print(f"❌ Ошибка при анализе {file}: {e}")
    
    # Сортируем по очкам
    results.sort(key=lambda x: x['points'], reverse=True)
    return results

def print_league_table(league_key, base_dir='leagues'):
    """Выводит турнирную таблицу лиги в консоль"""
    results = analyze_league(league_key, base_dir)
    
    if not results:
        print(f"❌ Нет данных для {LEAGUES[league_key]['name']}")
        return
    
    league_config = LEAGUES[league_key]
    print(f"\n🏆 {league_config['name']} ({league_config['short_name']})")
    print("-" * 70)
    print(f"{'#':<3} {'Команда':<30} {'Форма':<8} {'Очки':<5} {'Голы':<10} {'xG':<6}")
    print("-" * 70)
    
    for i, team in enumerate(results, 1):
        xg_str = f"{team['xG_avg']:.2f}" if team['xG_avg'] else "—"
        print(f"{i:<3} {team['team']:<30} {team['form']:<8} {team['points']:<5} "
              f"{team['goals_for']}/{team['goals_against']:<9} {xg_str:<6}")

def print_extended_stats_table(league_key, base_dir='leagues'):
    """Выводит таблицу с расширенной статистикой"""
    results = analyze_league(league_key, base_dir)
    
    if not results:
        return
    
    league_config = LEAGUES[league_key]
    print(f"\n📊 РАСШИРЕННАЯ СТАТИСТИКА - {league_config['name']}")
    print("-" * 90)
    print(f"{'Команда':<30} {'Удары':<12} {'Угловые':<12} {'ЖК':<8} {'xG':<8}")
    print("-" * 90)
    
    for team in results[:10]:
        shots = f"{team['shots_avg']}" if team['shots_avg'] else "—"
        corners = f"{team['corners_avg']}" if team['corners_avg'] else "—"
        yellow = f"{team['yellow_avg']}" if team['yellow_avg'] else "—"
        xg = f"{team['xG_avg']:.2f}" if team['xG_avg'] else "—"
        
        print(f"{team['team']:<30} {shots:<12} {corners:<12} {yellow:<8} {xg:<8}")

def generate_report(all_results, filename=None):
    """Генерирует текстовый отчёт по всем лигам"""
    if not filename:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"reports/full_report_{timestamp}.txt"
    
    os.makedirs('reports', exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("📊 ФУТБОЛЬНАЯ АНАЛИТИКА - ОБЩИЙ ОТЧЁТ\n")
        f.write(f"📅 Дата анализа: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
        f.write("=" * 100 + "\n\n")
        
        for league_key, results in all_results.items():
            league_config = LEAGUES[league_key]
            
            f.write(f"\n{'=' * 100}\n")
            f.write(f"🏆 {league_config['name']} ({league_config['short_name']})\n")
            f.write(f"{'=' * 100}\n\n")
            
            # Турнирная таблица
            f.write("📋 ТУРНИРНАЯ ТАБЛИЦА (по форме за 5 матчей)\n")
            f.write("-" * 100 + "\n")
            f.write(f"{'#':<3} {'Команда':<32} {'Форма':<10} {'Очки':<6} {'Голы':<12}\n")
            f.write("-" * 100 + "\n")
            
            for i, team in enumerate(results, 1):
                f.write(f"{i:<3} {team['team']:<32} {team['form']:<10} {team['points']:<6} ")
                f.write(f"{team['goals_for']}/{team['goals_against']:<11}\n")
            
            # Расширенная статистика (только если есть данные)
            f.write(f"\n📈 РАСШИРЕННАЯ СТАТИСТИКА\n")
            f.write("-" * 100 + "\n")
            f.write(f"{'Команда':<32} {'Удары':<12} {'Угловые':<12} {'ЖК':<8} {'xG':<10} {'Примечание':<20}\n")
            f.write("-" * 100 + "\n")
            
            for team in results:
                shots = f"{team['shots_avg']}" if team['shots_avg'] else "—"
                corners = f"{team['corners_avg']}" if team['corners_avg'] else "—"
                yellow = f"{team['yellow_avg']}" if team['yellow_avg'] else "—"
                xg = f"{team['xG_avg']:.2f}" if team['xG_avg'] else "—"
                
                note = ""
                if not team['xG_avg'] and not team['shots_avg']:
                    note = "(нет расшир. статистики)"
                
                f.write(f"{team['team']:<32} {shots:<12} {corners:<12} {yellow:<8} {xg:<10} {note:<20}\n")
            
            f.write("\n")
    
    print(f"\n✅ Отчёт сохранён: {filename}")
    return filename

def analyze_all_leagues(base_dir='leagues'):
    """Анализирует все лиги"""
    all_results = {}
    
    for league_key in LEAGUES:
        print(f"\n📊 Анализируем {LEAGUES[league_key]['name']}...")
        results = analyze_league(league_key, base_dir)
        if results:
            all_results[league_key] = results
            print(f"   ✅ Проанализировано {len(results)} команд")
        else:
            print(f"   ⚠️ Нет данных для анализа")
    
    return all_results

def print_data_quality_report(all_results):
    """Выводит отчёт о качестве данных (сколько матчей с расширенной статистикой)"""
    print("\n" + "=" * 70)
    print("📊 ОТЧЁТ О КАЧЕСТВЕ ДАННЫХ")
    print("=" * 70)
    
    for league_key, results in all_results.items():
        league_config = LEAGUES[league_key]
        
        total_xG_matches = sum(team['xG_matches'] for team in results)
        total_shots_matches = sum(team['shots_matches'] for team in results)
        total_corners_matches = sum(team['corners_matches'] for team in results)
        
        total_possible = len(results) * 5  # 5 матчей на команду
        
        print(f"\n🏆 {league_config['name']}:")
        print(f"   📈 xG: {total_xG_matches}/{total_possible} матчей ({total_xG_matches/total_possible*100:.0f}%)")
        print(f"   🎯 Удары: {total_shots_matches}/{total_possible} матчей ({total_shots_matches/total_possible*100:.0f}%)")
        print(f"   🚩 Угловые: {total_corners_matches}/{total_possible} матчей ({total_corners_matches/total_possible*100:.0f}%)")

def main():
    print("=" * 60)
    print("📊 АНАЛИЗ ДАННЫХ ФУТБОЛЬНЫХ ЛИГ")
    print("=" * 60)
    
    # Анализируем все лиги
    all_results = analyze_all_leagues()
    
    if not all_results:
        print("❌ Нет данных для анализа. Сначала запустите парсер.")
        return
    
    # Отчёт о качестве данных
    print_data_quality_report(all_results)
    
    # Генерируем общий отчёт
    report_file = generate_report(all_results)
    
    # Выводим таблицы для каждой лиги
    for league_key in all_results:
        print_league_table(league_key)
        print_extended_stats_table(league_key)
    
    print(f"\n✅ Полный отчёт сохранён: {report_file}")

if __name__ == "__main__":
    main()