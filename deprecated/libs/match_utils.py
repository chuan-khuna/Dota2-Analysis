import requests
import pandas as pd
import json
from bs4 import BeautifulSoup
import numpy as np
import random
import yaml

HEADERS = {
    'User-Agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
}


def rotate_agent() -> str:
    agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
    ]
    return random.choice(agents)


def rotate_proxies(proxies_list) -> dict:
    return random.choice(proxies_list)


def request_wrapper(url, proxies_lisr):
    num_try = 0
    while num_try < 16:
        try:
            proxies = rotate_proxies(proxies_lisr)
            headers = {'User-Agent': rotate_agent()}
            res = requests.get(url, headers=headers, proxies=proxies, timeout=5)

            if res.status_code != 200:
                print(res.status_code)

            soup = BeautifulSoup(res.content)

            get_match_title(soup)

            # get games section
            soup = get_matches_section(soup)
            table_body_soup = soup.find('tbody')

            return res
        except Exception as e:
            num_try += 1
    return ''


# a match consists many games
# for example, a match of Secret vs Tundra, BO3 games (max 3 games)


def get_matches_section(soup):
    return soup.find('section',
                     attrs={'class': 'series-matches recent-esports-matches series-show'})


def get_match_title(soup):
    header = soup.find('div', attrs={'class': 'header-content-secondary'})
    try:
        return header.find('a', attrs={'class': 'esports-link'}).text
    except:
        return ''


def get_teams(soup):
    # table soup

    teams_soup = soup.find_all('span', attrs={'class': 'team-text team-text-full'})
    teams = []
    for team_soup in teams_soup:
        teams.append(team_soup.text)
    return teams


def get_winner(soup):
    # tr soup

    return soup.find('td', attrs={'class': 'winner'}).text


def get_match_id(soup):
    # tr soup

    return soup.find('div', attrs={'class': 'match-link'}).text


def get_side_and_first_draft(soup):
    # tr soup

    sides = []
    first_picks = []

    draft_cols = soup.find_all('td', attrs={'class': 'r-none-tablet cell-xxlarge'})

    for col in draft_cols:

        side = ''
        first_pick = ''

        if col.find('span', attrs={'class': 'the-radiant'}):
            side = col.find('span', attrs={'class': 'the-radiant'}).text

        if col.find('span', attrs={'class': 'the-dire'}):
            side = col.find('span', attrs={'class': 'the-dire'}).text

        if col.find('acronym'):
            first_pick = col.find('acronym').text

        sides.append(side)
        first_picks.append(first_pick)

    return sides, first_picks


def get_phrase_heroes(soup, phrase):
    # tr soup

    heroes = soup.find_all('div', attrs={'class': phrase})

    heroes_data = []
    for hero in heroes:
        seq = hero.find('div', attrs={'class': 'seq'}).text
        hero_div = hero.find(
            'div', attrs={'class': 'image-container image-container-hero image-container-medicon'})
        hero_name = hero_div.find('img')['alt']

        heroes_data.append((int(seq), hero_name))

    return heroes_data


def get_heroes(soup):
    # tr soup

    heroes = []
    for phrase in ['pick', 'ban']:
        phrase_heroes = get_phrase_heroes(soup, phrase)
        heroes += phrase_heroes

    return heroes


def get_game_data(soup):

    winner = get_winner(soup)
    match_id = get_match_id(soup)
    sides, first_pick = get_side_and_first_draft(soup)
    heroes = get_heroes(soup)

    dict_ = {
        'winner': winner,
        'match_id': match_id,
        'team1_side': sides[0],
        'team2_side': sides[1],
        'team1_pick': first_pick[0],
        'team2_pick': first_pick[1],
        'heroes': heroes
    }

    # return winner, match_id, sides, first_pick, heroes
    return dict_


def get_hero_df(hero_pairs):
    hero_dict = {}
    for k, v in hero_pairs:
        hero_dict[k] = [v]
    hero = pd.DataFrame(hero_dict)
    hero = hero[np.sort(hero.columns)]
    return hero


def get_match_dataframe(url, proxies_list=None):

    if proxies_list is not None:
        res = request_wrapper(url, proxies_list)
    else:
        headers = {'User-Agent': rotate_agent()}
        res = requests.get(url, headers=headers, timeout=3)

    if res.status_code != 200:
        print(res.status_code)
    soup = BeautifulSoup(res.content)

    match_title = get_match_title(soup)

    # get games section
    soup = get_matches_section(soup)
    table_body_soup = soup.find('tbody')
    rows = table_body_soup.find_all('tr')
    teams = get_teams(soup)

    rows_data = []
    draft_dfs = []

    for row in rows:
        if not row.find('td', attrs={'class': 'not-played'}):
            row_d = get_game_data(row)
            rows_data.append(row_d)
            draft_dfs.append(get_hero_df(row_d['heroes']))

    df = pd.DataFrame(rows_data)
    df['match_title'] = match_title
    df['team1_name'] = teams[0]
    df['team2_name'] = teams[1]
    df = df.drop(columns=['heroes'])

    new_df = df[[
        'match_title', 'match_id', 'team1_name', 'team2_name', 'team1_side', 'team2_side',
        'team1_pick', 'team2_pick', 'winner'
    ]]

    assert len(new_df.columns) == len(df.columns)
    df = new_df

    df = df.join(pd.concat(draft_dfs).reset_index(drop=True))

    return df