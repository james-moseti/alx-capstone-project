from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, AdminOrderViewSet

router = DefaultRouter()
router.register(r"", OrderViewSet, basename="orders")
router.register(r"admin", AdminOrderViewSet, basename="admin-orders")

urlpatterns = router.urls
