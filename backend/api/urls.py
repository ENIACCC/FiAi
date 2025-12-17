from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import StockDataView, WatchlistView, AIAnalyzeView, RegisterView, MarketIndexView, TopGainersView

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('stock/', StockDataView.as_view(), name='stock_data'),
    path('watchlist/', WatchlistView.as_view(), name='watchlist'),
    path('ai/analyze/', AIAnalyzeView.as_view(), name='ai_analyze'),
    path('market/index/', MarketIndexView.as_view(), name='market_index'),
    path('market/top-gainers/', TopGainersView.as_view(), name='top_gainers'),
]
