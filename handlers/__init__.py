from aiogram import Dispatcher
from .common import router as common_router
from .roller import router as roller_router
from .setup import router as setup_router
from .gm_handlers import router as gm_handlers_router
from .meme import router as meme_router

def register_all_routers(dp: Dispatcher):
    """
    Регистрирует все роутеры в диспетчере.
    Порядок регистрации важен: сначала специализированные и мастера, затем общие.
    """
    dp.include_router(setup_router)
    dp.include_router(gm_handlers_router)
    dp.include_router(meme_router)
    dp.include_router(common_router)
    dp.include_router(roller_router)

