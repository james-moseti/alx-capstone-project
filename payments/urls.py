from rest_framework.routers import DefaultRouter
from .views import CustomerPaymentViewSet, AdminPaymentViewSet

router = DefaultRouter()
router.register(r"", CustomerPaymentViewSet, basename="payments")
router.register(r"admin", AdminPaymentViewSet, basename="admin-payments")

urlpatterns = router.urls
