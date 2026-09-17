import customtkinter as ctk
import threading
from tkinter import messagebox
from outreach_module.outbound_engine import OutboundCampaignEngine

class OutreachCenter(ctk.CTkToplevel):
    def __init__(self, master, db_path):
        super().__init__(master)
        self.title("Apex Bridge - Multi-Channel Outreach Center")
        self.geometry("720x720")
        self.db_path = db_path
        self.engine = OutboundCampaignEngine(db_path=db_path)
        
        ctk.CTkLabel(self, text="Multi-Channel Outreach Processor", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(15, 10))
        
        # Limit frame
        top_bar = ctk.CTkFrame(self)
        top_bar.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(top_bar, text="Batch Size (Top Scored Leads):", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=5)
        self.limit_var = ctk.StringVar(value="25")
        self.limit_menu = ctk.CTkOptionMenu(top_bar, values=["10", "25", "50", "100", "250"], variable=self.limit_var)
        self.limit_menu.pack(side="left", padx=10, pady=5)

        # SMS Template
        ctk.CTkLabel(self, text="SMS Message (A2P 10DLC Compliant):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        self.template_entry = ctk.CTkTextbox(self, height=70)
        self.template_entry.insert("0.0", "Hi {name}, this is Apex Bridge Properties. We are the fastest way to sell a home in Missouri! I was looking at your property on {address} and wanted to see if you'd consider a fair cash offer? No repairs, zero fees, and no commissions. Reply STOP to opt out.")
        self.template_entry.pack(fill="x", padx=20, pady=2)
        
        # Email Subject & Body
        ctk.CTkLabel(self, text="Email Subject (SendGrid Domain Authenticated):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        self.subject_entry = ctk.CTkEntry(self)
        self.subject_entry.pack(fill="x", padx=20, pady=2)
        self.subject_entry.insert(0, "Quick question regarding your property")
        
        ctk.CTkLabel(self, text="Email Body:").pack(anchor="w", padx=20, pady=(5, 2))
        self.email_entry = ctk.CTkTextbox(self, height=90)
        self.email_entry.insert("0.0", "Hi {name},\n\nMy name is Andrew and I'm a local property investor with Apex Bridge Properties. We are the fastest way to sell a home in Missouri. I was looking at your property on {address} and wanted to see if you'd consider a fair cash offer? No repairs, zero fees, zero commissions.\n\nCall/text us at (816) 666-9735.")
        self.email_entry.pack(fill="x", padx=20, pady=2)
        
        # Buttons Frame
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        self.btn_sms = ctk.CTkButton(btn_frame, text="🚀 Send SMS Batch", fg_color="#27ae60", hover_color="#219653", command=self.start_sms_batch)
        self.btn_sms.pack(side="left", padx=10, expand=True, fill="x")
        
        self.btn_email = ctk.CTkButton(btn_frame, text="✉️ Send Email Batch", fg_color="#2980b9", hover_color="#1f618d", command=self.start_email_batch)
        self.btn_email.pack(side="left", padx=10, expand=True, fill="x")

        # Live Console Output
        ctk.CTkLabel(self, text="Activity Log:").pack(anchor="w", padx=20, pady=(5, 2))
        self.log_box = ctk.CTkTextbox(self, height=150, font=("Courier New", 11))
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 15))

    def log(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def start_sms_batch(self):
        limit = int(self.limit_var.get())
        if not messagebox.askyesno("Confirm Outreach", f"Dispatch SMS campaign to top {limit} skip-traced leads?"):
            return
        self.btn_sms.configure(state="disabled")
        self.log(f"[*] Starting SMS batch dispatch to {limit} leads (Throttling active)...")
        threading.Thread(target=self._run_sms_thread, args=(limit,)).start()

    def _run_sms_thread(self, limit):
        try:
            def cb(sent, failed, total, dpin):
                self.log(f" -> Processed {sent + failed}/{total} (DPIN: {dpin})")
            results = self.engine.dispatch_sms_batch(limit=limit, delay=1.0, callback=cb)
            self.log(f"[✓] SMS Batch Complete: {results.get('sent', 0)} Sent, {results.get('failed', 0)} Failed of {results.get('total', 0)} Total.")
            messagebox.showinfo("Complete", f"SMS Campaign finished!\nSent: {results.get('sent', 0)}\nFailed: {results.get('failed', 0)}")
        except Exception as e:
            self.log(f"[!] Error in SMS batch: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self.btn_sms.configure(state="normal")

    def start_email_batch(self):
        limit = int(self.limit_var.get())
        if not messagebox.askyesno("Confirm Outreach", f"Dispatch Email campaign to top {limit} email leads?"):
            return
        self.btn_email.configure(state="disabled")
        self.log(f"[*] Starting Email batch dispatch to {limit} leads...")
        threading.Thread(target=self._run_email_thread, args=(limit,)).start()

    def _run_email_thread(self, limit):
        try:
            def cb(sent, failed, total, dpin):
                self.log(f" -> Processed {sent + failed}/{total} (DPIN: {dpin})")
            results = self.engine.dispatch_email_batch(limit=limit, delay=0.5, callback=cb)
            self.log(f"[✓] Email Batch Complete: {results.get('sent', 0)} Sent, {results.get('failed', 0)} Failed of {results.get('total', 0)} Total.")
            messagebox.showinfo("Complete", f"Email Campaign finished!\nSent: {results.get('sent', 0)}\nFailed: {results.get('failed', 0)}")
        except Exception as e:
            self.log(f"[!] Error in Email batch: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self.btn_email.configure(state="normal")

