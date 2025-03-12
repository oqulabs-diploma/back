from django.forms import Form

def get_first_error_text(form: Form) -> str:
    """Get the first error text from the form."""

    assert not form.is_valid(), "Form must be invalid"

    for _, errors in form.errors.items():
        return errors[0]
