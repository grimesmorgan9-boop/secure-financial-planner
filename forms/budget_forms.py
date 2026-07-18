"""
forms/budget_forms.py
----------------------
The Plan/Actual entry pages render one amount input per Category,
and the category list is data-driven (loaded from the database), so
those grids are built dynamically in the template/route rather than
as static WTForms fields. `MonthSelectForm` still gives us CSRF
protection and basic validation for the fixed-shape "create/select
month" action, and `validate_amount` is a shared helper used by the
API layer to validate the dynamic amount fields consistently.
"""

from decimal import Decimal, InvalidOperation

from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange

CURRENT_YEAR_SPAN = 5  # allow selecting a few years back/forward


class MonthSelectForm(FlaskForm):
    month = SelectField(
        "Month",
        choices=[(i, name) for i, name in enumerate(
            ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"],
            start=1,
        )],
        coerce=int,
        validators=[DataRequired()],
    )
    year = IntegerField("Year", validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    submit = SubmitField("Go")


class CSRFOnlyForm(FlaskForm):
    """A bare form used purely to render/validate a CSRF token on pages
    with dynamically generated fields (plan/actual entry grids, close
    month button, etc.)."""

    submit = SubmitField("Save")


def validate_amount(raw_value) -> Decimal:
    """Validate and coerce a submitted amount string into a non-negative Decimal.

    Raises ValueError with a user-friendly message on invalid input.
    Used by both the HTML form routes and the JSON API so validation
    logic isn't duplicated.
    """
    if raw_value is None or str(raw_value).strip() == "":
        return Decimal("0")
    try:
        amount = Decimal(str(raw_value))
    except (InvalidOperation, ValueError):
        raise ValueError("Amount must be a valid number.")
    if amount < 0:
        raise ValueError("Amount cannot be negative.")
    if amount > Decimal("9999999.99"):
        raise ValueError("Amount is unreasonably large.")
    return amount.quantize(Decimal("0.01"))
