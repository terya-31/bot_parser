# parser.py - универсальный парсер для всех лиг
import time
import json
import os
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from collections import defaultdict

try:
    from config import BASE_URL, LEAGUES, SELECTORS, PARSER_CONFIG, VALID_RESULTS
except ImportError:
    print("❌ Ошибка: не найден файл config.py")
    exit(1)

def get_chromedriver_path():
    """Автоматически находит путь к ChromeDriver"""
    try:
        result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    common_paths = [
        '/usr/local/bin/chromedriver',
        '/usr/bin/chromedriver',
        '/app/chromedriver'
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None

class LeagueParser:
    def __init__(self, league_key, headless=None):
        """Инициализация парсера для конкретной лиги"""
        if league_key not in LEAGUES:
            raise ValueError(f"Лига {league_key} не найдена в конфигурации")
        
        self.league_key = league_key
        self.league_config = LEAGUES[league_key]
        
        if headless is None:
            headless = PARSER_CONFIG.get('headless', False)
        
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--user-agent=Mozilla/5.0')
        
        # Получаем путь к ChromeDriver
        chromedriver_path = get_chromedriver_path()
        
        from selenium.webdriver.chrome.service import Service
        
        if chromedriver_path:
            print(f"✅ Используем ChromeDriver: {chromedriver_path}")
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        else:
            print("⚠️ ChromeDriver не найден, пробуем webdriver-manager...")
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except Exception as e:
                print(f"❌ Ошибка установки ChromeDriver: {e}")
                raise
        
        self.wait = WebDriverWait(self.driver, PARSER_CONFIG.get('wait_time', 15))
        
        # Создаём директории
        self.data_dir = f'leagues/{self.league_config["filename"]}'
        self.teams_dir = f'{self.data_dir}/teams'
        os.makedirs(self.teams_dir, exist_ok=True)
        
        print(f"\n🚀 Запуск парсера для {self.league_config['name']}")
        print(f"📁 Данные будут сохранены в: {self.data_dir}")
    
    # ... остальные методы (get_team_links, get_match_stats и т.д.) остаются без изменений
    
    def get_team_links(self):
        """Получает список команд из таблицы лиги"""
        print(f"🌐 Загружаем таблицу {self.league_config['name']}...")
        print(f"URL: {self.league_config['url']}")
        
        self.driver.get(self.league_config['url'])
        time.sleep(PARSER_CONFIG.get('page_load_delay', 5))
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        team_links = []
        
        links = soup.find_all('a', class_=SELECTORS['team_link'])
        
        for link in links:
            team_name = link.text.strip()
            team_url = link.get('href')
            
            if team_name and team_url:
                if not team_url.startswith('http'):
                    team_url = BASE_URL + team_url
                
                team_links.append({
                    'name': team_name,
                    'url': team_url
                })
        
        print(f"📊 Найдено команд: {len(team_links)}")
        return team_links
    
    def get_match_stats(self, match_url):
        """Собирает расширенную статистику матча"""
        self.driver.get(match_url)
        time.sleep(PARSER_CONFIG.get('click_delay', 2))
        
        # Открываем вкладку "Статистика"
        try:
            stats_tab = self.driver.find_element(By.XPATH, f"//button[contains(text(), '{SELECTORS['stats_tab_text']}')]")
            stats_tab.click()
            time.sleep(PARSER_CONFIG.get('click_delay', 2))
        except:
            return {}
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        stats = {}
        
        container = soup.find('div', class_=SELECTORS['stat_row'])
        if not container:
            return {}
        
        stat_elements = container.find_all('span', class_=SELECTORS['stat_name'])
        
        for i in range(0, len(stat_elements) - 2, 3):
            try:
                home_value = stat_elements[i].text.strip()
                stat_name = stat_elements[i + 1].text.strip()
                away_value = stat_elements[i + 2].text.strip()
                
                stats[stat_name] = {
                    'home': home_value,
                    'away': away_value
                }
            except:
                continue
        
        return stats
    
    def get_team_results(self, team_name, team_url):
        """Собирает результаты для одной команды"""
        self.driver.get(team_url)
        time.sleep(PARSER_CONFIG.get('click_delay', 2))
        
        # Открываем вкладку "Результаты"
        try:
            results_tab = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{SELECTORS['results_tab_text']}')]")
            results_tab.click()
            time.sleep(PARSER_CONFIG.get('click_delay', 2))
        except Exception as e:
            print(f"    ⚠️ Не найдена вкладка 'Результаты': {e}")
            return []
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        matches = []
        
        match_links = soup.find_all('a', class_=SELECTORS['match_link'])
        limit = PARSER_CONFIG.get('matches_per_team', 10)
        
        for match_link in match_links[:limit]:
            try:
                match_block = match_link.find_parent('div', class_=SELECTORS['match_block'])
                if not match_block:
                    continue
                
                # Домашняя команда
                home_div = match_block.find('div', class_=SELECTORS['home_participant'])
                home_team = '?'
                if home_div:
                    home_name_span = home_div.find('span', class_=SELECTORS['team_name'])
                    home_team = home_name_span.text.strip() if home_name_span else '?'
                
                # Гостевая команда
                away_div = match_block.find('div', class_=SELECTORS['away_participant'])
                away_team = '?'
                if away_div:
                    away_name_span = away_div.find('span', class_=SELECTORS['team_name'])
                    away_team = away_name_span.text.strip() if away_name_span else '?'
                
                # Счёт
                home_score_elem = match_block.find('span', class_=SELECTORS['home_score'])
                home_score = home_score_elem.text.strip() if home_score_elem else '?'
                
                away_score_elem = match_block.find('span', class_=SELECTORS['away_score'])
                away_score = away_score_elem.text.strip() if away_score_elem else '?'
                
                # Исход
                result_elems = match_block.find_all('span', class_=SELECTORS['result_text'])
                result_text = '?'
                for elem in result_elems:
                    text = elem.text.strip()
                    if text in VALID_RESULTS:
                        result_text = text
                        break
                
                # URL матча
                match_url = match_link.get('href')
                if match_url and not match_url.startswith('http'):
                    match_url = BASE_URL + match_url
                
                # Собираем статистику
                stats = self.get_match_stats(match_url) if match_url else {}
                
                matches.append({
                    'home': home_team,
                    'away': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'result': result_text,
                    'stats': stats
                })
                
            except Exception as e:
                continue
        
        return matches
    
    def save_team_data(self, team_name, matches):
        """Сохраняет данные одной команды"""
        safe_name = team_name.lower().replace(' ', '_').replace('-', '_').replace('.', '')
        filename = os.path.join(self.teams_dir, f"{safe_name}.json")
        
        last_5 = matches[:5]
        wins = sum(1 for m in last_5 if m['result'] == 'В')
        draws = sum(1 for m in last_5 if m['result'] == 'Н')
        losses = sum(1 for m in last_5 if m['result'] == 'П')
        
        team_data = {
            'league': self.league_config['name'],
            'team': team_name,
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
            'form': {
                'last_5': last_5,
                'wins': wins,
                'draws': draws,
                'losses': losses,
                'points': wins * 3 + draws,
                'form_string': f"{wins}-{draws}-{losses}"
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(team_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def save_metadata(self, teams):
        """Сохраняет метаданные лиги"""
        metadata = {
            'league': self.league_config['name'],
            'short_name': self.league_config['short_name'],
            'total_teams': len(teams),
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
            'teams': [
                {
                    'name': team['name'],
                    'file': f"teams/{team['name'].lower().replace(' ', '_').replace('-', '_').replace('.', '')}.json"
                }
                for team in teams
            ]
        }
        
        filename = os.path.join(self.data_dir, 'metadata.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def parse_all_teams(self):
        """Парсит все команды в лиге"""
        teams = self.get_team_links()
        
        if not teams:
            print(f"❌ Не найдено ни одной команды в {self.league_config['name']}")
            return []
        
        results = []
        for i, team in enumerate(teams, 1):
            print(f"\n  [{i}/{len(teams)}] {team['name']}")
            try:
                matches = self.get_team_results(team['name'], team['url'])
                if matches:
                    filename = self.save_team_data(team['name'], matches)
                    print(f"    ✅ Сохранено: {filename}")
                    results.append({'name': team['name'], 'status': 'success'})
                else:
                    print(f"    ⚠️ Нет матчей для {team['name']}")
                    results.append({'name': team['name'], 'status': 'no_matches'})
            except Exception as e:
                print(f"    ❌ Ошибка: {e}")
                results.append({'name': team['name'], 'status': 'error'})
            
            time.sleep(PARSER_CONFIG.get('team_delay', 1))
        
        # Сохраняем метаданные
        self.save_metadata(teams)
        
        self.driver.quit()
        return results

def parse_all_leagues(leagues=None):
    """Парсит все указанные лиги или все из конфига"""
    if leagues is None:
        leagues = list(LEAGUES.keys())
    
    all_results = {}
    for league_key in leagues:
        print("\n" + "=" * 60)
        print(f"📋 НАЧАЛО ПАРСИНГА: {LEAGUES[league_key]['name']}")
        print("=" * 60)
        
        parser = LeagueParser(league_key)
        results = parser.parse_all_teams()
        
        success = sum(1 for r in results if r['status'] == 'success')
        all_results[league_key] = {
            'name': LEAGUES[league_key]['name'],
            'total': len(results),
            'success': success
        }
        
        print(f"\n📊 Итог по {LEAGUES[league_key]['name']}: {success}/{len(results)} команд")
    
    return all_results

def main():
    print("=" * 60)
    print("🚀 УНИВЕРСАЛЬНЫЙ ПАРСЕР ФУТБОЛЬНЫХ ЛИГ")
    print("=" * 60)
    
    # Список лиг для парсинга
    leagues_to_parse = ['premier_league', 'bundesliga', 'laliga', 'serie_a', 'ligue_1', 'rpl']
    
    results = parse_all_leagues(leagues_to_parse)
    
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 60)
    for league_key, data in results.items():
        print(f"  {data['name']}: {data['success']}/{data['total']} команд")

if __name__ == "__main__":
    main()