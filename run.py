import asyncio
import logging
import os
import sys

import django

from bot.telegram.bot import main

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django.setup()

if __name__ == "__main__":
    asyncio.run(main())
