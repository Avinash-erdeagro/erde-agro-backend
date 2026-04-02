def normalize_indian_phone_number(phone_number: str) -> str:
    phone_number = phone_number.strip().replace(" ", "")

    if phone_number.startswith("+91") and len(phone_number) == 13 and phone_number[1:].isdigit():
        return phone_number

    if len(phone_number) == 10 and phone_number.isdigit():
        return f"+91{phone_number}"

    raise ValueError("Phone number must be a valid Indian mobile number.")
