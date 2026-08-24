import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from common.dates import add_months
from loans.models import Loan, LoanPayment
from loans.services import (
    amortization_schedule,
    log_payment,
    monthly_payment,
    payoff_date,
    projected_payoff_date,
    remaining_balance,
)
from loans.tests.factories import LoanFactory
from users.tests.factories import UserFactory

TODAY = datetime.date.today()


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestLoanCRUD:
    def test_create_loan(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.post(
            "/api/loans/",
            {
                "lender": "BDO",
                "principal": "10000.00",
                "interest_rate": "12.000",
                "term_months": 12,
                "start_date": TODAY.isoformat(),
            },
        )
        assert response.status_code == 201
        loan = Loan.objects.get(id=response.data["id"])
        assert loan.user_id == user.id
        assert Decimal(response.data["monthly_payment"]) == Decimal("888.49")
        assert Decimal(response.data["remaining_balance"]) == Decimal("10000.00")

    def test_principal_must_be_positive(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.post(
            "/api/loans/",
            {
                "principal": "0.00",
                "interest_rate": "5.000",
                "term_months": 12,
                "start_date": TODAY.isoformat(),
            },
        )
        assert response.status_code == 400

    def test_term_months_must_be_positive(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.post(
            "/api/loans/",
            {
                "principal": "1000.00",
                "interest_rate": "5.000",
                "term_months": 0,
                "start_date": TODAY.isoformat(),
            },
        )
        assert response.status_code == 400

    def test_cannot_retrieve_another_users_loan(self):
        loan = LoanFactory()
        client = authed_client(UserFactory())
        response = client.get(f"/api/loans/{loan.id}/")
        assert response.status_code == 404

    def test_unauthenticated_request_is_rejected(self):
        loan = LoanFactory()
        client = APIClient()
        response = client.get(f"/api/loans/{loan.id}/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestMonthlyPayment:
    def test_standard_formula(self):
        loan = LoanFactory(principal=Decimal("10000.00"), interest_rate=Decimal("12.000"), term_months=12)
        assert monthly_payment(loan) == Decimal("888.49")

    def test_zero_interest_is_a_flat_split(self):
        loan = LoanFactory(principal=Decimal("1200.00"), interest_rate=Decimal("0.000"), term_months=12)
        assert monthly_payment(loan) == Decimal("100.00")


@pytest.mark.django_db
class TestAmortizationSchedule:
    def test_full_schedule_matches_hand_computed_values(self):
        loan = LoanFactory(
            principal=Decimal("10000.00"),
            interest_rate=Decimal("12.000"),
            term_months=12,
            start_date=datetime.date(2026, 1, 1),
        )
        rows = amortization_schedule(loan)

        assert len(rows) == 12
        assert rows[0]["interest_portion"] == Decimal("100.00")
        assert rows[0]["principal_portion"] == Decimal("788.49")
        assert rows[0]["remaining_balance"] == Decimal("9211.51")
        assert rows[0]["date"] == datetime.date(2026, 1, 1)
        assert rows[1]["date"] == datetime.date(2026, 2, 1)

        last = rows[-1]
        assert last["remaining_balance"] == Decimal("0")
        assert last["interest_portion"] == Decimal("8.80")
        assert last["principal_portion"] == Decimal("879.67")

    def test_schedule_fully_amortizes_principal(self):
        loan = LoanFactory(principal=Decimal("10000.00"), interest_rate=Decimal("12.000"), term_months=12)
        rows = amortization_schedule(loan)
        total_principal = sum((row["principal_portion"] for row in rows), Decimal("0"))
        assert total_principal == loan.principal

    def test_interest_decreases_and_principal_increases_over_time(self):
        loan = LoanFactory(principal=Decimal("10000.00"), interest_rate=Decimal("12.000"), term_months=12)
        rows = amortization_schedule(loan)
        assert rows[0]["interest_portion"] > rows[-1]["interest_portion"]
        assert rows[0]["principal_portion"] < rows[-1]["principal_portion"]

    def test_zero_interest_schedule_has_no_interest_portion(self):
        loan = LoanFactory(principal=Decimal("1200.00"), interest_rate=Decimal("0.000"), term_months=12)
        rows = amortization_schedule(loan)
        assert all(row["interest_portion"] == Decimal("0.00") for row in rows)
        assert rows[-1]["remaining_balance"] == Decimal("0")

    def test_single_month_term(self):
        loan = LoanFactory(principal=Decimal("500.00"), interest_rate=Decimal("6.000"), term_months=1)
        rows = amortization_schedule(loan)
        assert len(rows) == 1
        assert rows[0]["remaining_balance"] == Decimal("0")
        assert rows[0]["principal_portion"] == Decimal("500.00")

    def test_endpoint_returns_schedule(self):
        user = UserFactory()
        loan = LoanFactory(user=user, principal=Decimal("10000.00"), interest_rate=Decimal("12.000"), term_months=12)
        client = authed_client(user)
        response = client.get(f"/api/loans/{loan.id}/amortization-schedule/")
        assert response.status_code == 200
        assert len(response.data) == 12

    def test_cannot_view_another_users_schedule(self):
        loan = LoanFactory()
        client = authed_client(UserFactory())
        response = client.get(f"/api/loans/{loan.id}/amortization-schedule/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestPayoffDate:
    def test_theoretical_payoff_date_is_start_plus_term(self):
        loan = LoanFactory(start_date=datetime.date(2026, 1, 15), term_months=12)
        assert payoff_date(loan) == datetime.date(2027, 1, 15)

    def test_projected_payoff_date_with_no_payments_matches_full_term(self):
        loan = LoanFactory(
            principal=Decimal("10000.00"), interest_rate=Decimal("12.000"), term_months=12
        )
        projected = projected_payoff_date(loan, as_of=TODAY)
        assert projected == add_months(TODAY, 12)

    def test_extra_payment_moves_projected_payoff_date_earlier(self):
        loan = LoanFactory(
            principal=Decimal("10000.00"), interest_rate=Decimal("12.000"), term_months=12
        )
        before = projected_payoff_date(loan, as_of=TODAY)

        log_payment(loan, date_=TODAY, amount=Decimal("3000.00"), is_extra=True)

        after = projected_payoff_date(loan, as_of=TODAY)
        assert after < before

    def test_projected_payoff_date_is_today_once_paid_off(self):
        loan = LoanFactory(principal=Decimal("1000.00"), interest_rate=Decimal("0.000"), term_months=1)
        log_payment(loan, date_=TODAY, amount=Decimal("1000.00"), is_extra=False)
        assert projected_payoff_date(loan, as_of=TODAY) == TODAY

    def test_none_when_payment_does_not_cover_interest(self):
        # An absurdly high rate relative to term means the standard
        # monthly payment (computed from principal/rate/term) may still
        # cover interest in the normal case, so force a degenerate one:
        # a payment lower than interest owed by simulating a rate that
        # outpaces principal reduction is easiest via a synthetic loan.
        loan = LoanFactory(
            principal=Decimal("100000.00"), interest_rate=Decimal("999.000"), term_months=360
        )
        assert projected_payoff_date(loan, as_of=TODAY) is None


@pytest.mark.django_db
class TestLogPayment:
    def test_regular_payment_splits_between_interest_and_principal(self):
        loan = LoanFactory(principal=Decimal("10000.00"), interest_rate=Decimal("12.000"), term_months=12)
        payment = log_payment(loan, date_=TODAY, amount=Decimal("888.49"), is_extra=False)

        assert payment.interest_portion == Decimal("100.00")
        assert payment.principal_portion == Decimal("788.49")
        assert remaining_balance(loan) == Decimal("9211.51")

    def test_extra_payment_is_all_principal(self):
        loan = LoanFactory(principal=Decimal("10000.00"), interest_rate=Decimal("12.000"), term_months=12)
        payment = log_payment(loan, date_=TODAY, amount=Decimal("500.00"), is_extra=True)

        assert payment.interest_portion == Decimal("0.00")
        assert payment.principal_portion == Decimal("500.00")
        assert remaining_balance(loan) == Decimal("9500.00")

    def test_cannot_pay_more_than_remaining_balance(self):
        loan = LoanFactory(principal=Decimal("1000.00"), interest_rate=Decimal("0.000"), term_months=12)
        with pytest.raises(Exception):
            log_payment(loan, date_=TODAY, amount=Decimal("5000.00"), is_extra=True)

    def test_cannot_pay_off_an_already_paid_off_loan(self):
        loan = LoanFactory(principal=Decimal("1000.00"), interest_rate=Decimal("0.000"), term_months=1)
        log_payment(loan, date_=TODAY, amount=Decimal("1000.00"), is_extra=False)
        with pytest.raises(Exception):
            log_payment(loan, date_=TODAY, amount=Decimal("1.00"), is_extra=True)

    def test_payment_before_start_date_is_rejected(self):
        loan = LoanFactory(start_date=TODAY)
        with pytest.raises(Exception):
            log_payment(
                loan, date_=TODAY - datetime.timedelta(days=1), amount=Decimal("100.00"), is_extra=True
            )

    def test_regular_payment_must_cover_interest(self):
        loan = LoanFactory(principal=Decimal("10000.00"), interest_rate=Decimal("12.000"), term_months=12)
        with pytest.raises(Exception):
            log_payment(loan, date_=TODAY, amount=Decimal("50.00"), is_extra=False)


@pytest.mark.django_db
class TestPaymentsEndpoint:
    def test_log_payment_via_api(self):
        user = UserFactory()
        loan = LoanFactory(user=user, principal=Decimal("10000.00"), interest_rate=Decimal("12.000"), term_months=12)
        client = authed_client(user)

        response = client.post(
            f"/api/loans/{loan.id}/payments/",
            {"date": TODAY.isoformat(), "amount": "888.49", "is_extra": False},
        )
        assert response.status_code == 201
        assert Decimal(response.data["principal_portion"]) == Decimal("788.49")
        assert LoanPayment.objects.filter(loan=loan).count() == 1

    def test_list_payments_via_api(self):
        user = UserFactory()
        loan = LoanFactory(user=user, principal=Decimal("1000.00"), interest_rate=Decimal("0.000"), term_months=12)
        log_payment(loan, date_=TODAY, amount=Decimal("100.00"), is_extra=False)
        log_payment(loan, date_=TODAY, amount=Decimal("50.00"), is_extra=True)

        client = authed_client(user)
        response = client.get(f"/api/loans/{loan.id}/payments/")
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_invalid_amount_via_api_returns_400(self):
        user = UserFactory()
        loan = LoanFactory(user=user, principal=Decimal("1000.00"), interest_rate=Decimal("0.000"), term_months=12)
        client = authed_client(user)

        response = client.post(
            f"/api/loans/{loan.id}/payments/",
            {"date": TODAY.isoformat(), "amount": "0.00", "is_extra": True},
        )
        assert response.status_code == 400

    def test_cannot_log_payment_on_another_users_loan(self):
        loan = LoanFactory()
        client = authed_client(UserFactory())
        response = client.post(
            f"/api/loans/{loan.id}/payments/",
            {"date": TODAY.isoformat(), "amount": "100.00", "is_extra": True},
        )
        assert response.status_code == 404
