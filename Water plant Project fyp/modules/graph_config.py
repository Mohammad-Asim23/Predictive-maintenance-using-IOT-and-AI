import json

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

def update_chart_config(chart_id, new_data):
    config = load_config()
    for chart in config['gauges']:
        if chart['id'] == chart_id:
            chart.update(new_data)
            save_config(config)
            break
