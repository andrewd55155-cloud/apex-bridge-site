import os
import re
from twilio.rest import Client

class TwilioClient:
    """
    Production-ready Twilio client supporting SMS and Voicemail Drops.
    Compliant with A2P 10DLC requirements and E.164 number formatting.
    """
    def __init__(self, account_sid=None, auth_token=None, from_number=None):
        self.account_sid = account_sid or os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = auth_token or os.environ.get('TWILIO_AUTH_TOKEN')
        self.from_number = from_number or os.environ.get('TWILIO_FROM_NUMBER', '+18166669735')
        self._client = None
        if self.account_sid and self.auth_token:
            try:
                self._client = Client(self.account_sid, self.auth_token)
            except Exception as e:
                print(f"[Twilio Client] Init Warning: {e}")

    def format_e164(self, phone):
        """Converts raw phone number into standard E.164 string (+1XXXXXXXXXX)."""
        digits = re.sub(r'\D', '', str(phone or ''))
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"+{digits}"
        elif digits:
            return f"+{digits}"
        return None

    def send_sms(self, to_number, message):
        """Sends an SMS message. Appends opt-out text if not already included."""
        clean_to = self.format_e164(to_number)
        if not clean_to:
            return False, "Invalid phone number"

        # Ensure 10DLC compliance text
        if "STOP" not in message.upper():
            message += " Reply STOP to opt out."

        if self._client:
            try:
                msg = self._client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=clean_to
                )
                return True, msg.sid
            except Exception as e:
                return False, str(e)
        else:
            # Staged dry run mode when running locally without active API keys
            print(f"[SMS DRY RUN] To: {clean_to} | Body: {message}")
            return True, f"STAGED-SMS-TO-{clean_to}"

    def drop_voicemail(self, to_number, twiml_url="https://apexbridgeproperties.com/voice/voicemail-drop"):
        """Dispatches an authentic human voicemail drop using AMD (Answering Machine Detection)."""
        clean_to = self.format_e164(to_number)
        if not clean_to:
            return False, "Invalid phone number"

        if self._client:
            try:
                call = self._client.calls.create(
                    to=clean_to,
                    from_=self.from_number,
                    url=twiml_url,
                    machine_detection='DetectMessageEnd'
                )
                return True, call.sid
            except Exception as e:
                return False, str(e)
        else:
            print(f"[VOICEMAIL DROP DRY RUN] To: {clean_to} | TwiML: {twiml_url}")
            return True, f"STAGED-VM-TO-{clean_to}"

