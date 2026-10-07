from src.db import init_db
from src.log import configurar_logging
from src.scheduler import rodar_loop

if __name__ == "__main__":
    configurar_logging()
    init_db()
    rodar_loop()
