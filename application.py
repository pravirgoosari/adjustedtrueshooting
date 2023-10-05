import pandas as pd
from flask import Flask, render_template

application = Flask(__name__, template_folder='templates', static_folder='static')

# Set display options
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.expand_frame_repr', False)

# Define the data as a list of dictionaries
data = [
    {
        'Player': 'JOEL EMBIID',
        'Season': '2023',
        'PPG': 33.1,
        'aTS%': 70.5,
        'TS%': 65.5,
        'Usage Rate': 41.5
    },
    {
        'Player': 'LUKA DONČIĆ',
        'Season': '2023',
        'PPG': 32.4,
        'aTS%': 66.5,
        'TS%': 60.9,
        'Usage Rate': 43.8
    },
    # Add more player data here...
]

# Create a DataFrame from the hardcoded data
player_data = pd.DataFrame(data)

# Sort the player_data DataFrame by 'PPG' column in descending order
player_data = player_data.sort_values(by='PPG', ascending=False)

# Pass the DataFrame to the HTML template and render it
@application.route('/')
def index():
    return render_template('index.html', df=player_data)

if __name__ == '__main__':
    application.run(host="0.0.0.0", port=5000)
