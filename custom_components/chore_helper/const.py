"""Constants for the Chore Helper integration."""

from logging import Logger, getLogger

from homeassistant.helpers import selector

LOGGER: Logger = getLogger(__package__)

DOMAIN = "chore_helper"
CALENDAR_NAME = "Chores"
SENSOR_PLATFORM = "sensor"
CALENDAR_PLATFORM = "calendar"
ATTRIBUTION = "Data is provided by chore_helper"
CONFIG_VERSION = 6

ATTR_NEXT_DATE = "next_due_date"
ATTR_DAYS = "days"
ATTR_LAST_COMPLETED = "last_completed"
ATTR_LAST_UPDATED = "last_updated"
ATTR_OVERDUE = "overdue"
ATTR_OVERDUE_DAYS = "overdue_days"
ATTR_OFFSET_DATES = "offset_dates"
ATTR_ADD_DATES = "add_dates"
ATTR_REMOVE_DATES = "remove_dates"

BINARY_SENSOR_DEVICE_CLASS = "connectivity"
DEVICE_CLASS = "chore_helper__schedule"

CONF_SENSOR = "sensor"
CONF_ENABLED = "enabled"
CONF_FORECAST_DATES = "forecast_dates"
CONF_SHOW_OVERDUE_TODAY = "show_overdue_today"
CONF_FREQUENCY = "frequency"
CONF_MANUAL = "manual_update"
CONF_ICON_NORMAL = "icon_normal"
CONF_ICON_TODAY = "icon_today"
CONF_ICON_TOMORROW = "icon_tomorrow"
CONF_ICON_OVERDUE = "icon_overdue"
CONF_OFFSET = "offset"
CONF_DAY_OF_MONTH = "day_of_month"
CONF_DUE_DATE_OFFSET = "due_date_offset"
CONF_FIRST_MONTH = "first_month"
CONF_LAST_MONTH = "last_month"
CONF_CHORE_DAY = "chore_day"
CONF_WEEKDAY_ORDER_NUMBER = "weekday_order_number"
CONF_FORCE_WEEK_NUMBERS = "force_week_order_numbers"
CONF_DATE = "date"
CONF_TIME = "time"
CONF_PERIOD = "period"
CONF_FIRST_WEEK = "first_week"
CONF_START_DATE = "start_date"
CONF_SENSORS = "sensors"
CONF_DATE_FORMAT = "date_format"

DEFAULT_NAME = DOMAIN
DEFAULT_FIRST_MONTH = "jan"
DEFAULT_LAST_MONTH = "dec"
DEFAULT_FREQUENCY = "every-n-days"
DEFAULT_PERIOD = 1
DEFAULT_FIRST_WEEK = 1
DEFAULT_DATE_FORMAT = "%b-%d-%Y"
DEFAULT_FORECAST_DATES = 10
DEFAULT_SHOW_OVERDUE_TODAY = False

DEFAULT_ICON_NORMAL = "mdi:broom"
DEFAULT_ICON_TODAY = "mdi:bell"
DEFAULT_ICON_TOMORROW = "mdi:bell-outline"
DEFAULT_ICON_OVERDUE = "mdi:bell-alert"
ICON = DEFAULT_ICON_NORMAL

STATE_TODAY = "today"
STATE_TOMORROW = "tomorrow"

FREQUENCY_OPTIONS = [
    selector.SelectOptionDict(value="every-n-days", label="Every [x] days"),
    selector.SelectOptionDict(value="every-n-weeks", label="Every [x] weeks"),
    selector.SelectOptionDict(value="every-n-months", label="Every [x] months"),
    selector.SelectOptionDict(value="every-n-years", label="Every [x] years"),
    selector.SelectOptionDict(value="after-n-days", label="After [x] days"),
    selector.SelectOptionDict(value="after-n-weeks", label="After [x] weeks"),
    selector.SelectOptionDict(value="after-n-months", label="After [x] months"),
    selector.SelectOptionDict(value="after-n-years", label="After [x] years"),
    selector.SelectOptionDict(value="blank", label="Manual"),
]

DAILY_FREQUENCY = ["every-n-days", "after-n-days"]
WEEKLY_FREQUENCY = ["every-n-weeks", "after-n-weeks"]
MONTHLY_FREQUENCY = ["every-n-months", "after-n-months"]
YEARLY_FREQUENCY = ["every-n-years", "after-n-years"]
BLANK_FREQUENCY = ["blank"]

WEEKDAY_OPTIONS = [
    selector.SelectOptionDict(value="0", label="None"),
    selector.SelectOptionDict(value="mon", label="Monday"),
    selector.SelectOptionDict(value="tue", label="Tuesday"),
    selector.SelectOptionDict(value="wed", label="Wednesday"),
    selector.SelectOptionDict(value="thu", label="Thursday"),
    selector.SelectOptionDict(value="fri", label="Friday"),
    selector.SelectOptionDict(value="sat", label="Saturday"),
    selector.SelectOptionDict(value="sun", label="Sunday"),
]

MONTH_OPTIONS = [
    selector.SelectOptionDict(value="jan", label="January"),
    selector.SelectOptionDict(value="feb", label="February"),
    selector.SelectOptionDict(value="mar", label="March"),
    selector.SelectOptionDict(value="apr", label="April"),
    selector.SelectOptionDict(value="may", label="May"),
    selector.SelectOptionDict(value="jun", label="June"),
    selector.SelectOptionDict(value="jul", label="July"),
    selector.SelectOptionDict(value="aug", label="August"),
    selector.SelectOptionDict(value="sep", label="September"),
    selector.SelectOptionDict(value="oct", label="October"),
    selector.SelectOptionDict(value="nov", label="November"),
    selector.SelectOptionDict(value="dec", label="December"),
]

ORDER_OPTIONS = [
    selector.SelectOptionDict(value="0", label="None"),
    selector.SelectOptionDict(value="1", label="1st"),
    selector.SelectOptionDict(value="2", label="2nd"),
    selector.SelectOptionDict(value="3", label="3rd"),
    selector.SelectOptionDict(value="4", label="4th"),
    selector.SelectOptionDict(value="5", label="5th"),
    selector.SelectOptionDict(value="-1", label="last"),
    selector.SelectOptionDict(value="-2", label="2nd from last"),
    selector.SelectOptionDict(value="-3", label="3rd from last"),
    selector.SelectOptionDict(value="-4", label="4th from last"),
]
