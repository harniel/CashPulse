from django.contrib import admin

from .models import Loan, LoanPayment


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["lender", "principal", "interest_rate", "term_months", "start_date", "user"]
    search_fields = ["lender", "user__email"]


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ["loan", "date", "amount", "principal_portion", "interest_portion", "is_extra"]
    list_filter = ["is_extra"]
    search_fields = ["loan__lender"]
