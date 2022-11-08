import yaml


def load_state():
    with open('state.yaml', 'r') as handle:
        return yaml.safe_load(handle)

def save_state(STATE):
    with open('state.yaml', 'w') as handle:
        yaml.dump(STATE, handle)


