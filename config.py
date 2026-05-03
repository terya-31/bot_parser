# config.py - настройки для всех лиг

# ============ БАЗОВЫЕ URL ============
BASE_URL = 'https://www.flashscorekz.com'

# ============ КОНФИГУРАЦИЯ ЛИГ ============
LEAGUES = {
    'premier_league': {
        'name': 'Английская Премьер-лига',
        'url': 'https://www.flashscorekz.com/football/england/premier-league/standings/OEEq9Yvp/standings/overall/',
        'filename': 'premier_league',
        'short_name': 'АПЛ'
    },
    'bundesliga': {
        'name': 'Немецкая Бундеслига',
        'url': 'https://www.flashscorekz.com/football/germany/bundesliga/standings/8UYeqfiD/standings/overall/',
        'filename': 'bundesliga',
        'short_name': 'Бундеслига'
    },
    'laliga': {
        'name': 'Испанская Ла Лига',
        'url': 'https://www.flashscorekz.com/football/spain/laliga/standings/vcm2MhGk/standings/overall/',
        'filename': 'laliga',
        'short_name': 'Ла Лига'
    },
    'serie_a': {
        'name': 'Итальянская Серия А',
        'url': 'https://www.flashscorekz.com/football/italy/serie-a/standings/6PWwAsA7/standings/overall/',
        'filename': 'serie_a',
        'short_name': 'Серия А'
    },
    'ligue_1': {
        'name': 'Французская Лига 1',
        'url': 'https://www.flashscorekz.com/football/france/ligue-1/standings/j9QeTLPP/standings/overall/',
        'filename': 'ligue_1',
        'short_name': 'Лига 1'
    },
    'rpl': {
        'name': 'Российская Премьер-лига',
        'url': 'https://www.flashscorekz.com/football/russia/premier-league/standings/0UC6tdRa/standings/overall/',
        'filename': 'rpl',
        'short_name': 'РПЛ'
    }
}

# ============ СЕЛЕКТОРЫ (общие для всех лиг) ============
SELECTORS = {
    'team_link': 'tableCellParticipant__name',
    'results_tab_text': 'Результаты',
    'stats_tab_text': 'Статистика',
    'match_link': 'eventRowLink',
    'match_block': 'event__match',
    'home_participant': 'event__homeParticipant',
    'away_participant': 'event__awayParticipant',
    'team_name': 'wcl-name_jjfMf',
    'home_score': 'event__score--home',
    'away_score': 'event__score--away',
    'result_text': 'wcl-scores-simple-text-01_-OvnR',
    'stat_row': 'section',
    'stat_name': 'wcl-bold_NZXv6',
}

# ============ НАСТРОЙКИ ПАРСИНГА ============
PARSER_CONFIG = {
    'headless': False,
    'wait_time': 15,
    'page_load_delay': 5,
    'click_delay': 2,
    'team_delay': 1,
    'matches_per_team': 10,
}

# ============ ФИЛЬТРЫ ============
VALID_RESULTS = ['В', 'П', 'Н']