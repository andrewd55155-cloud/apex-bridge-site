"""
Multi-Channel Outbound Marketing Engine
Supports SMS (Twilio), Email (SendGrid), and Authentic Voicemail Drops.
from outreach_module.twilio_client import TwilioClient

"""
import os
import time
import sqlite3
from datetime import datetime
from outreach_module.email_client import EmailClient
from outreach_module.twilio_client import TwilioClient

DEFAULT_DB_PATH = "Regional_Wholesaling/Greene_County/Springfield/active_leads.db"

class OutboundCampaignEngine:
    def __init__(self, db_path=DEFAULT_DB_PATH, twilio_sid=None, twilio_token=None, from_phone=None, sendgrid_api_key=None):
        self.db_path = db_path
        self.from_phone = from_phone or os.environ.get('TWILIO_FROM_NUMBER', '+18166669735')
        self.twilio = TwilioClient(account_sid=twilio_sid, auth_token=twilio_token, from_number=self.from_phone)
        self.mailer = EmailClient(api_key=sendgrid_api_key)

    def generate_email(self, first_name, address):
        subject = f"Property Consultation: {address}"
        body = f"""Dear {first_name},

Following our recent conversation regarding your property at {address}, I am pleased to provide further details regarding our acquisition process at Apex Bridge Properties. 

We specialize in professional, transparent solutions for homeowners looking to transition out of their properties efficiently. Unlike traditional sales, we focus entirely on your specific timeline and needs.

Our Consultation & Acquisition Process:
1. Property Assessment: We conduct a thorough, no-obligation valuation of your property based on current market conditions and property specifics.
2. Formal Cash Offer: We present a transparent, firm cash offer. There are no hidden deductions, commissions, or closing fees—the offer amount is the amount you receive at settlement.
3. Structured Closing: To ensure full compliance with state and title requirements, we require a minimum of 14 days to complete necessary due diligence and title searches. This standard timeframe guarantees a secure, professional, and error-free transfer of property for all parties.

We prioritize clear communication and operate primarily through physical, documented mail to ensure all important information is provided in a reliable, permanent format for your records.

Should you have any questions regarding this process or wish to discuss your property further, please feel free to call or text us directly at (816) 666-9735.

Best regards,

Andrew Dimsdale
Apex Bridge Properties
Springfield, MO

---
To stop receiving emails, reply 'UNSUBSCRIBE'."""
        return subject, body

    def dispatch_email_batch(self, limit=50, delay=0.5, callback=None):
        """Dispatches an Email batch to leads sequentially by ID."""
        if not os.path.exists(self.db_path):
            return {"error": f"Database not found at {self.db_path}"}

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""SELECT DPIN, Owner_First_Name, Property_Address, Skip_Trace_Email 
                     FROM leads 
                     WHERE Skip_Trace_Email != '' AND Skip_Trace_Email IS NOT NULL 
                       AND Status NOT IN ('EMAIL_SENT', 'INTERESTED', 'NOT_INTERESTED')
                     ORDER BY DPIN ASC LIMIT ?""", (limit,))
        leads = c.fetchall()

        results = {"total": len(leads), "sent": 0, "failed": 0, "details": []}
        for dpin, fname, addr, email in leads:
            sub, body = self.generate_email(fname, addr)
            success, info = self.mailer.send_email(email, sub, body)
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            if success:
                results["sent"] += 1
                note = f"\n[{now}] [Email Sent via SendGrid] {info}"
                c.execute("UPDATE leads SET Status='EMAIL_SENT', Notes=COALESCE(Notes, '') || ? WHERE DPIN=?", (note, dpin))
            else:
                results["failed"] += 1
                note = f"\n[{now}] [Email Failed] {info}"
                c.execute("UPDATE leads SET Notes=COALESCE(Notes, '') || ? WHERE DPIN=?", (note, dpin))
            conn.commit()

            if callback:
                callback(results["sent"], results["failed"], results["total"], dpin)
            time.sleep(delay)

        conn.close()
        return results
