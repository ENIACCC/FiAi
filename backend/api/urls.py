from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    StockDataView, WatchlistView, AIAnalyzeView, RegisterView, 
    MarketIndexView, TopGainersView, AIAnalysisLogViewSet,
    UserInfoView, ChangePasswordView, TopIndustriesView, WatchlistGroupViewSet,
    WatchlistCountView
)

router = DefaultRouter()
router.register(r'ai-history', AIAnalysisLogViewSet)
router.register(r'watchlist-groups', WatchlistGroupViewSet, basename='watchlist-groups')

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('stock/', StockDataView.as_view(), name='stock_data'),
    path('watchlist/', WatchlistView.as_view(), name='watchlist'),
    path('watchlist/count/', WatchlistCountView.as_view(), name='watchlist_count'),
    path('ai/analyze/', AIAnalyzeView.as_view(), name='ai_analyze'),
    path('market/index/', MarketIndexView.as_view(), name='market_index'),
    path('market/top-gainers/', TopGainersView.as_view(), name='top_gainers'),
    path('market/top-industries/', TopIndustriesView.as_view(), name='top_industries'),
    path('user/info/', UserInfoView.as_view(), name='user_info'),
    path('user/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('', include(router.urls)),
]
