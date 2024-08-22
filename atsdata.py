import pandas as pd
import requests
import json
from flask import Flask, render_template

application = Flask(__name__, template_folder='templates', static_folder='static')

# Set display options
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.expand_frame_repr', False)

# Define the data types for the DataFrame columns
data_types = {
    'Player': str,
    'Season': str,
    'PPG': float,
    'aTS%': float,
    'TS%': float,
    'Usage Rate': float,
}

# Create empty DataFrames with defined data types for 2023 and 2024
player_data_2023 = pd.DataFrame(columns=data_types.keys()).astype(data_types)
player_data_2024 = pd.DataFrame(columns=data_types.keys()).astype(data_types)

# Define the URLs for the API endpoints
api_urls = {
    '2023': [
        'https://nba-stats-db.herokuapp.com/api/playerdata/topscorers/total/season/2023/',
        'https://nba-stats-db.herokuapp.com/api/playerdata/season/2023',
        'https://nba-stats-db.herokuapp.com/api/top_rebounds/totals/2023/',
        'https://nba-stats-db.herokuapp.com/api/top_assists/totals/2023/'
    ],
    '2024': ['http://b8c40s8.143.198.70.30.sslip.io/api/PlayerDataTotals/season/2024']
}

# Initialize data structures for both seasons
added_players = {'2023': set(), '2024': set()}
ts_list = {'2023': [], '2024': []}
usage_rate_list = {'2023': [], '2024': []}
player_data = {'2023': pd.DataFrame(columns=data_types.keys()).astype(data_types),
               '2024': pd.DataFrame(columns=data_types.keys()).astype(data_types)}

# Calculate Usage Rate (USG%)
def calculate_usage_rate(points, fga, fta, gp):
    if fga is not None and fta is not None and gp is not None:
        usage_rate = ((points + fga - fta) / (gp * 100)) * 100
        return usage_rate
    else:
        return None


# Function to process player data
def process_player_data(player, added_players, ts_list, usage_rate_list, player_data):
    player_name = player.get('playerName', '')
    if player_name and player_name not in added_players:
        season = player.get('season')
        points = float(player.get('points', 0))
        fga = float(player.get('fieldAttempts', 0))
        fta = float(player.get('ftAttempts', 0))
        gp = float(player.get('games', 0))

        if fga > 0 and fta >= 0 and gp > 0:
            try:
                ppg = points / gp
                ts = (points / (2 * (fga + (0.44 * fta)))) * 100
                usage_rate = calculate_usage_rate(points, fga, fta, gp)

                if usage_rate is not None:
                    new_player = pd.DataFrame({
                        'Player': [player_name],
                        'Season': [season],
                        'PPG': [round(ppg, 1)],
                        'TS%': [round(ts, 1)],
                        'Usage Rate': [round(usage_rate, 1)],
                    })
                    player_data = pd.concat([player_data, new_player], ignore_index=True)

                    added_players.add(player_name)
                    ts_list.append(ts)
                    usage_rate_list.append(usage_rate)
            except ZeroDivisionError:
                print(f"Warning: Division by zero for player {player_name}")
            except Exception as e:
                print(f"Error processing player {player_name}: {str(e)}")

    return player_data

# Process data for both 2023 and 2024 seasons
for season, season_urls in api_urls.items():
    current_player_data = player_data[season]
    current_added_players = added_players[season]
    current_ts_list = ts_list[season]
    current_usage_rate_list = usage_rate_list[season]

    for api_url in season_urls:
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            results = data if season == '2024' else data.get('results', [])

            for player in results:
                current_player_data = process_player_data(player, current_added_players, current_ts_list, current_usage_rate_list, current_player_data)

    player_data[season] = current_player_data
    ts_list[season] = current_ts_list
    usage_rate_list[season] = current_usage_rate_list

# Calculate statistics for both seasons
season_stats = {}
for season in ['2023', '2024']:
    current_ts_list = ts_list[season]
    current_usage_rate_list = usage_rate_list[season]

    if len(current_ts_list) > 0 and len(current_usage_rate_list) > 0:
        correlation_coefficient = pd.Series(current_ts_list).corr(pd.Series(current_usage_rate_list))
        mean_ts = pd.Series(current_ts_list).mean()
        mean_usg = pd.Series(current_usage_rate_list).mean()
        β_0 = mean_ts - correlation_coefficient * mean_usg

        season_stats[season] = {
            'correlation_coefficient': correlation_coefficient,
            'β_0': β_0
        }
    else:
        print(f"Warning: No data for season {season}")
        season_stats[season] = {
            'correlation_coefficient': 0,
            'β_0': 0
        }

# Calculate aTS% for both seasons
for season in ['2023', '2024']:
    season_data = player_data[season]
    if not season_data.empty:
        player_data[season]['aTS%'] = round(
            ((season_stats[season]['β_0'] + season_stats[season]['correlation_coefficient'] * season_data['Usage Rate']) - 58.1) + season_data['TS%'],
            1
        )
    else:
        print(f"Warning: No player data for season {season}")

# Sort the player_data DataFrame by 'Season' (descending) and 'PPG' (descending) columns
non_empty_seasons = [season for season in ['2024', '2023'] if not player_data[season].empty]
player_data = pd.concat([player_data[season] for season in non_empty_seasons])
if not player_data.empty:
    player_data = player_data.sort_values(by=['Season', 'PPG'], ascending=[False, False])
else:
    print("Warning: No player data available for any season")

# Pass the combined DataFrame to the HTML template and render it
@application.route('/')
def index():
    return render_template('index.html', df=player_data)

if __name__ == '__main__':
    application.run(debug=True)
