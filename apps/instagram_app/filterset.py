from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q

from apps.instagram_app.models import CoinTransaction


class CoinTransactionFilterBackend(DjangoFilterBackend):
    """
    Filter that only allows users to see their own objects.
    """

    def filter_queryset(self, request, queryset, view):
        qs = super(CoinTransactionFilterBackend, self).filter_queryset(request, queryset, view)
        transaction_type = {
            'daily_reward': qs.filter(transaction_type=CoinTransaction.TYPE_DAILY_REWARD),
            'package': qs.filter(package__isnull=False),
            'transfer': qs.filter(Q(to_page__isnull=False) | Q(from_page__isnull=False))
        }.get(request.query_params.get('type'))

        if transaction_type is not None:
            qs = transaction_type
        return qs
