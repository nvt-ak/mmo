import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_PATH = Path(__file__).parent.parent / "logs"
LOG_PATH.mkdir(exist_ok=True)

_log_file = LOG_PATH / f"videoscout_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
