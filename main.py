from config.loader import load_config
from logging_setup import setup_logging

if __name__ == "__main__":
    _config = load_config()
    setup_logging(_config.log)
    from cli.main import cli
    cli()
