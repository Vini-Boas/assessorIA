from .chat_route import router as chat_router
from .session_route import router as session_router

# Combine all routers into a single list or dictionary if needed
routers = [chat_router, session_router]