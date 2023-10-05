import pandas as pd
import requests
from flask import Flask, render_template

app = Flask(__name__, template_folder='templates', static_folder='static')

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

# Create an empty DataFrame with defined data types
player_data = pd.DataFrame(columns=data_types.keys()).astype(data_types)

# Define the URLs for the API endpoints
api_urls = [
    'https://nba-stats-db.herokuapp.com/api/playerdata/topscorers/total/season/2023/',
    'https://nba-stats-db.herokuapp.com/api/playerdata/season/2023',
    'https://nba-stats-db.herokuapp.com/api/top_rebounds/totals/2023/',
    'https://nba-stats-db.herokuapp.com/api/top_assists/totals/2023/'
]

# Set to keep track of added player names
added_players = set()

# Lists to store TS% and Usage Rate for correlation calculation
ts_list = []
usage_rate_list = []

# Calculate Usage Rate (USG%)
def calculate_usage_rate(points, fga, fta, gp):
    if fga is not None and fta is not None and gp is not None:
        usage_rate = ((points + fga - fta) / (gp * 100)) * 100
        return usage_rate
    else:
        return None


# Iterate through the list of API endpoints
for api_url in api_urls:
    # Make a GET request to the API
    response = requests.get(api_url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Extract relevant information from the 'results' field
        results = data.get('results', [])

        # Iterate through the list of top scorers (results)
        for player in results:
            player_name = player.get('player_name', '')

            # Check if the player name is not in the set of added players (avoid duplicates)
            if player_name not in added_players:
                season = player.get('season')
                points = player.get('PTS', 0)
                fga = player.get('field_attempts')
                fta = player.get('fta')
                gp = player.get('games')

                # Check if the denominators are greater than zero
                if fga > 0 and fta > 0:
                    ppg = points / gp

                    # Calculate True Shooting Percentage (TS%)
                    ts = (points / (2 * (fga + (0.44 * fta)))) * 100

                    # Calculate Usage Rate
                    usage_rate = calculate_usage_rate(points, fga, fta, gp)

                    if usage_rate is not None:
                        # Add player data to the DataFrame
                        player_data = pd.concat([player_data, pd.DataFrame({
                            'Player': [player_name],
                            'Season': [season],
                            'PPG': [round(ppg, 1)],
                            'TS%': [round(ts, 1)],
                            'Usage Rate': [round(usage_rate, 1)],
                        })], ignore_index=True)

                        # Add the player name to the set of added players
                        added_players.add(player_name)

                        # Add TS% and Usage Rate to the lists for correlation calculation
                        ts_list.append(ts)
                        usage_rate_list.append(usage_rate)

# Calculate the correlation coefficient
correlation_coefficient = pd.Series(ts_list).corr(pd.Series(usage_rate_list))

# Calculate meanTS and meanUSG
mean_ts = pd.Series(ts_list).mean()
mean_usg = pd.Series(usage_rate_list).mean()

# Calculate 'β_0' using the formula β_0 = meanTS - b * meanUSG
β_0 = mean_ts - correlation_coefficient * mean_usg

# Calculate aTS% using dynamic values
player_data['aTS%'] = round(((β_0 + correlation_coefficient * player_data['Usage Rate']) - 58.1) + player_data['TS%'], 1)

# Sort the player_data DataFrame by 'PPG' column in descending order
player_data = player_data.sort_values(by='PPG', ascending=False)

# Pass the DataFrame to the HTML template and render it
@app.route('/')
def index():
    return render_template('index.html', df=player_data)

if __name__ == '__main__':
    app.run(debug=True)