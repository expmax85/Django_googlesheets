from decimal import Decimal

from django.utils.translation import gettext_lazy as _

from dynamic_preferences.preferences import Section
from dynamic_preferences.types import DecimalPreference, StringPreference
from dynamic_preferences.registries import global_preferences_registry


general = Section('general')


@global_preferences_registry.register
class CurrencyValue(DecimalPreference):
    section = general
    name = 'cur_value'
    help_text = _('Set the value currency')
    default = Decimal('0.0')
    required = True
    verbose_name = _('Value of Currency')


@global_preferences_registry.register
class Currency(StringPreference):
    section = general
    name = 'currency'
    help_text = _('Set the currency')
    default = 'USD'
    required = True
    verbose_name = _('Currency')
