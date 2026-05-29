from backend.routers.documents import router as documents_router
from backend.routers.layers import router as layers_router
from backend.routers.knowledge import router as knowledge_router
from backend.routers.scrape import router as scrape_router

routers = [documents_router, layers_router, knowledge_router, scrape_router]
