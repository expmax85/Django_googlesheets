from decimal import Decimal

from dynamic_preferences.preferences import Section
from dynamic_preferences.types import DecimalPreference, StringPreference
from dynamic_preferences.registries import global_preferences_registry

general = Section('general')


@global_preferences_registry.register
class CurrencyValue(DecimalPreference):
    section = general
    name = 'cur_value'
    help_text = 'Set the value currency'
    default = Decimal('0.0')
    required = True
    verbose_name = 'Value of Currency'


@global_preferences_registry.register
class Currency(StringPreference):
    section = general
    name = 'currency'
    help_text = 'Set the currency'
    default = 'USD'
    required = True
    verbose_name = 'Currency'


@global_preferences_registry.register
class SheetID(StringPreference):
    section = general
    name = 'sheet_id'
    help_text = 'Set the sheet id'
    default = '1ZZSVYG6IQLl7ZiYdweGIOUllFmpZMgYs_1tqScY2n54'
    required = True
    verbose_name = 'sheet id'


@global_preferences_registry.register
class SheetListRange(StringPreference):
    section = general
    name = 'sheet_list'
    help_text = 'Set the name of sheet list. Also you can define the range on sheet, example: List1!A1:D10'
    default = 'Лист1'
    required = True
    verbose_name = 'sheet id'
