import sqlite3
from datetime import datetime

class OutreachManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_batch_leads(self, count=1000):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DPIN, Skip_Trace_Phone, Skip_Trace_Email, Owner_First_Name, Property_Address FROM leads WHERE Skip_Trace_Phone != '' ORDER BY Score DESC LIMIT ?", (count,))
        leads = cursor.fetchall()
        conn.close()
        return leads

    def log_outreach(self, dpin, method, template_used):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("UPDATE leads SET Notes = Notes || ? WHERE DPIN = ?", 
                       (f"\n[{now}] {method} sent using: {template_used}", dpin))
        conn.commit()
        conn.close()
