from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.services.analytics_service import AnalyticsService


class DashboardStatsAPI(APIView):
    """
    API for admin dashboard statistics.
    """

    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Get dashboard statistics (MRR, Users, etc).",
        responses={200: "Dashboard Stats JSON"},
    )
    def get(self, request):
        stats = AnalyticsService.get_dashboard_stats()
        return Response(
            {"message": "Dashboard stats retrieved successfully", "data": stats}
        )
