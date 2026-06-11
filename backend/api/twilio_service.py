import logging
import re
from decimal import Decimal

logger = logging.getLogger(__name__)

MIN_SMS_AMOUNT = Decimal('3000')

DEFAULT_TEMPLATE = (
    'Thank you {name} for your donation! '
    'Al-Najaat Foundation has received your amount: PKR {amount}. JazakAllah Khair!'
)

_ADDRESS_MARKERS = (
    'street', 'st.', 'st ', 'road', 'rd.', 'chowk', 'naka', 'block', 'sector',
    'phase', 'lane', 'avenue', 'house', ' plaza', 'market', 'town', 'colony',
)


def _looks_like_address(text: str, address: str = '') -> bool:
    if not text:
        return True
    lower = text.lower().strip()
    if address and lower == address.lower().strip():
        return True
    return any(marker in lower for marker in _ADDRESS_MARKERS)


def get_donor_name_for_sms(box) -> str:
    """Pick the donor's personal name, not the street/location text."""
    donor_field = (box.donor_name or '').strip()
    box_label = (box.name or '').strip()
    address = (box.address or '').strip()

    if donor_field and not _looks_like_address(donor_field, address):
        return donor_field

    if box_label and not _looks_like_address(box_label, address) and 'box' not in box_label.lower():
        return box_label

    if donor_field:
        first_part = donor_field.split(',')[0].split(' - ')[0].strip()
        if first_part and not _looks_like_address(first_part, address):
            return first_part

    return 'Valued Donor'


def normalize_phone(phone: str) -> str | None:
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone.strip())
    if not digits:
        return None
    if digits.startswith('92'):
        digits = digits[2:]
    elif digits.startswith('0'):
        digits = digits[1:]
    if not digits.startswith('3'):
        return None
    if len(digits) >= 10:
        digits = digits[:10]
    if len(digits) == 10:
        return f'+92{digits}'
    return None


def format_amount(amount) -> str:
    val = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    if val == val.to_integral_value():
        return f'{int(val):,}'
    return f'{float(val):,.2f}'


def render_message(template: str, **kwargs) -> str:
    return template.format(**kwargs)


def send_collection_thank_you_sms(*, box, amount) -> dict:
    from .models import TwilioSettings

    amount_value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    if amount_value < MIN_SMS_AMOUNT:
        return {'sent': False, 'reason': 'below_minimum'}

    settings = TwilioSettings.load()
    if not settings.is_configured():
        return {'sent': False, 'reason': 'not_configured'}

    # Admin can pause SMS without removing credentials
    if not settings.enabled:
        return {'sent': False, 'reason': 'disabled'}

    to_number = normalize_phone(box.donor_phone)
    if not to_number:
        logger.warning('Invalid donor phone for box %s: %s', box.id, box.donor_phone)
        return {'sent': False, 'reason': 'invalid_phone'}

    template = settings.message_template or DEFAULT_TEMPLATE
    donor_name = get_donor_name_for_sms(box)
    body = render_message(
        template,
        donorName=donor_name,
        name=donor_name,
        amount=format_amount(amount),
        boxName=box.name,
        boxNumber=box.box_number,
    )

    try:
        from twilio.rest import Client

        client = Client(settings.account_sid, settings.auth_token)
        message = client.messages.create(
            body=body,
            from_=settings.from_number,
            to=to_number,
        )
        return {'sent': True, 'sid': message.sid}
    except Exception as exc:
        logger.exception('Failed to send donor thank-you SMS: %s', exc)
        return {'sent': False, 'reason': str(exc)}


def send_test_sms(*, to_phone: str, body: str | None = None) -> dict:
    from .models import TwilioSettings

    settings = TwilioSettings.load()
    if not settings.account_sid or not settings.auth_token or not settings.from_number:
        return {'sent': False, 'reason': 'incomplete_config'}

    to_number = normalize_phone(to_phone)
    if not to_number:
        return {'sent': False, 'reason': 'invalid_phone'}

    message_body = body or (
        'Al-Najaat Foundation: Twilio SMS is configured correctly. '
        'Donors will receive thank-you messages for collections of PKR 3,000 or more.'
    )

    try:
        from twilio.rest import Client

        client = Client(settings.account_sid, settings.auth_token)
        message = client.messages.create(
            body=message_body,
            from_=settings.from_number,
            to=to_number,
        )
        return {'sent': True, 'sid': message.sid}
    except Exception as exc:
        logger.exception('Failed to send Twilio test SMS: %s', exc)
        return {'sent': False, 'reason': str(exc)}
