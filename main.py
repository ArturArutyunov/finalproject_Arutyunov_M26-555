from valutatrade_hub.cli.interface import CLI
from valutatrade_hub.logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    CLI().run()