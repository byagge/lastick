from django.urls import path, include
from .views import FinishedGoodsPageView, FinishedGoodSaleViewSet
from rest_framework.routers import DefaultRouter
from .views import FinishedGoodViewSet

router = DefaultRouter()
router.register(r'finished_goods', FinishedGoodViewSet, basename='finishedgood')
router.register(r'sales', FinishedGoodSaleViewSet, basename='finishedgoodsale')

urlpatterns = [
    path('api/', include(router.urls)),
    path('', FinishedGoodsPageView.as_view(), name='finished_goods_page'),
] 
