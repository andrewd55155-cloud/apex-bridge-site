from flask import Flask, render_template, request, session, redirect, url_for, jsonify, Response, send_file
import pandas as pd
import sqlite3
import os
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'apex_bridge_secret_key_2026')
app.jinja_env.globals.update(enumerate=enumerate)

TWILIO_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_FROM = os.environ.get('TWILIO_FROM_NUMBER', '+18166669735')
FORWARD_PHONE = os.environ.get('FORWARD_PHONE', '+18649139408')

DB_PATH = 'crm_leads.db'
CSV_PATH = 'combined_leads.csv'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, last_name TEXT, address TEXT, city TEXT, state TEXT, zip TEXT, primary_phone TEXT, primary_phone_type TEXT, mail_address TEXT, mail_city TEXT, mail_state TEXT, mailing_zip TEXT, email_1 TEXT, email_2 TEXT, mobile_1 TEXT, mobile_2 TEXT, landline_1 TEXT, landline_2 TEXT, status TEXT DEFAULT 'UNCALLED', notes TEXT DEFAULT '', call_outcome TEXT DEFAULT '', called_by TEXT DEFAULT '', last_called_at TIMESTAMP)""")
    
    # Dynamic Schema Migration for missing columns in leads
    cursor.execute("PRAGMA table_info(leads)")
    existing_cols = {col[1] for col in cursor.fetchall()}
    migrations = [
        ("called_by", "TEXT DEFAULT ''"),
        ("last_called_at", "TIMESTAMP"),
        ("call_outcome", "TEXT DEFAULT ''")
    ]
    for col_name, col_def in migrations:
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_def}")
            except Exception as e:
                print(f"Migration error for {col_name}: {e}")

    cursor.execute("""CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        event_type TEXT NOT NULL,
        area TEXT,
        deal_phase TEXT,
        event_date DATE NOT NULL,
        notes TEXT,
        color TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    cursor.execute('SELECT COUNT(*) FROM leads')
    if cursor.fetchone()[0] == 0 and os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH).fillna('')
        for _, r in df.iterrows():
            cursor.execute("""INSERT INTO leads (first_name, last_name, address, city, state, zip, primary_phone, primary_phone_type, mail_address, mail_city, mail_state, mailing_zip, email_1, email_2, mobile_1, mobile_2, landline_1, landline_2, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNCALLED')""", (str(r.get('first_name','')), str(r.get('last_name','')), str(r.get('address','')), str(r.get('city','')), str(r.get('state','')), str(r.get('zip','')), str(r.get('primary_phone','')), str(r.get('primary_phone_type','')), str(r.get('mail_address','')), str(r.get('mail_city','')), str(r.get('mail_state','')), str(r.get('mailing_zip','')), str(r.get('Email-1','')), str(r.get('Email-2','')), str(r.get('Mobile-1','')), str(r.get('Mobile-2','')), str(r.get('Landline-1','')), str(r.get('Landline-2',''))))
        conn.commit()
    conn.close()

init_db()

AUTH_USERS = {
    'CLI-001': {'name': 'Caller Lize (750 Dial List)', 'role': 'caller_750'},
    'CLI-002': {'name': 'Caller 02 (Uncontacted / Unphoned)', 'role': 'caller_secondary'},
    'ADMIN-APEX': {'name': 'Administrator (Full Access)', 'role': 'admin'}
}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/portal/login', methods=['GET', 'POST'])
def login():
    err = None
    if request.method == 'POST':
        u = request.form.get('user_id', '').strip().upper()
        if u in AUTH_USERS:
            session['user_id'] = u
            session['user_name'] = AUTH_USERS[u]['name']
            session['role'] = AUTH_USERS[u]['role']
            return redirect(url_for('portal'))
        err = 'Unauthorized Access. Please enter a valid User ID.'
    return render_template('login.html', error=err)

@app.route('/portal/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/portal')
def portal():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    role = session.get('role', 'caller_750')
    f = request.args.get('filter', 'ALL')
    conn = get_db_connection()
    c = conn.cursor()

    # Determine Base Scope by Role
    # CLI-001 gets all leads WITH phone numbers (~750 skip-traced calling leads)
    # CLI-002 gets leads WITHOUT phone numbers (for direct mail / secondary skip tracing)
    # ADMIN gets all leads
    if role == 'caller_750':
        base_where = "(primary_phone != '' OR mobile_1 != '' OR landline_1 != '')"
    elif role == 'caller_secondary':
        base_where = "(primary_phone = '' AND mobile_1 = '' AND landline_1 = '')"
    else:
        base_where = "1=1"

    c.execute(f'SELECT COUNT(*) FROM leads WHERE {base_where}')
    tot = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM leads WHERE {base_where} AND status != 'UNCALLED'")
    cal = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM leads WHERE {base_where} AND status = 'INTERESTED'")
    inte = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM leads WHERE {base_where} AND status = 'NOT_INTERESTED'")
    nint = c.fetchone()[0]
    unc = tot - cal

    if f == 'UNCALLED':
        c.execute(f"SELECT * FROM leads WHERE {base_where} AND status = 'UNCALLED' ORDER BY id ASC")
    elif f == 'CALLED':
        c.execute(f"SELECT * FROM leads WHERE {base_where} AND status != 'UNCALLED' ORDER BY last_called_at DESC")
    elif f == 'INTERESTED':
        c.execute(f"SELECT * FROM leads WHERE {base_where} AND status = 'INTERESTED' ORDER BY last_called_at DESC")
    else:
        c.execute(f"SELECT * FROM leads WHERE {base_where} ORDER BY id ASC")

    leads = c.fetchall()
    
    # Query live campaign calendar events & deal progression milestones
    c.execute("SELECT * FROM calendar_events ORDER BY event_date ASC")
    events = [dict(row) for row in c.fetchall()]
    
    conn.close()
    metrics = {'total': tot, 'called': cal, 'uncalled': unc, 'interested': inte, 'not_interested': nint}
    return render_template('portal.html', leads=leads, metrics=metrics, current_filter=f, user_name=session.get('user_name', 'Caller'), events=events)

@app.route('/portal/update/<int:lead_id>', methods=['POST'])
def update_lead(lead_id):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 403
    st = request.form.get('status', 'CALLED')
    nt = request.form.get('notes', '')
    oc = request.form.get('outcome', '')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE leads SET status=?, notes=?, call_outcome=?, called_by=?, last_called_at=CURRENT_TIMESTAMP WHERE id=?', (st, nt, oc, session.get('user_id'), lead_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'lead_id': lead_id, 'status': st})

@app.route('/portal/dial/<int:lead_id>', methods=['POST'])
def dial_lead(lead_id):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    lead = conn.execute('SELECT primary_phone FROM leads WHERE id = ?', (lead_id,)).fetchone()
    conn.close()
    if lead and TWILIO_SID and TWILIO_TOKEN:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        # client.calls.create(to=lead['primary_phone'], from_=TWILIO_FROM, url='http://demo.twilio.com/docs/voice.xml')
        return jsonify({'success': True, 'message': 'Dialing triggered'})
    return jsonify({'error': 'Config error'}), 500

# ==============================================================================
# VOICE & VOICEMAIL INFRASTRUCTURE ENDPOINTS
# ==============================================================================

@app.route('/voice/audio')
def voice_audio():
    """Serves authentic human voicemail audio payload with proper MIME headers."""
    audio_path = os.path.join(app.root_path, 'static', 'audio', 'voicemail.m4a')
    if os.path.exists(audio_path):
        return send_file(audio_path, mimetype='audio/mp4')
    fallback = os.path.join(app.root_path, 'static', 'audio', 'voicemail.mp3')
    return send_file(fallback, mimetype='audio/mp4')

@app.route('/voice/inbound', methods=['GET', 'POST'])
def voice_inbound():
    """
    Twilio Voice Webhook for Inbound Calls to +1 (816) 666-9735:
    1. Forwards call directly to Andrew (+1 864-913-9408) with 20 second timeout.
    2. If unanswered or busy, plays authentic human voicemail and records caller's message.
    """
    base_url = request.url_root.rstrip('/')
    audio_url = f"{base_url}/voice/audio"
    dial_action = f"{base_url}/voice/dial-status"
    record_action = f"{base_url}/voice/recorded"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial timeout="20" action="{dial_action}" callerId="{TWILIO_FROM}">
        {FORWARD_PHONE}
    </Dial>
    <Play>{audio_url}</Play>
    <Record maxLength="120" action="{record_action}" transcribe="true"/>
    <Hangup/>
</Response>"""
    return Response(twiml, mimetype='text/xml')

@app.route('/voice/dial-status', methods=['GET', 'POST'])
def voice_dial_status():
    """Fallback if dialed phone is busy or unanswered: drop voicemail & record."""
    status = request.values.get('DialCallStatus', '')
    if status == 'completed':
        return Response('<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>', mimetype='text/xml')

    base_url = request.url_root.rstrip('/')
    audio_url = f"{base_url}/voice/audio"
    record_action = f"{base_url}/voice/recorded"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Record maxLength="120" action="{record_action}" transcribe="true"/>
    <Hangup/>
</Response>"""
    return Response(twiml, mimetype='text/xml')

@app.route('/voice/voicemail-drop', methods=['GET', 'POST'])
def voicemail_drop_twiml():
    """TwiML for automated ringless voicemail / voicemail drop payload."""
    audio_url = f"{request.url_root.rstrip('/')}/voice/audio"
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Hangup/>
</Response>"""
    return Response(twiml, mimetype='text/xml')

@app.route('/voice/recorded', methods=['POST'])
def voice_recorded():
    """Webhook to capture incoming voicemails left on +1 (816) 666-9735."""
    caller = request.values.get('From', 'Unknown')
    recording_url = request.values.get('RecordingUrl', '')
    duration = request.values.get('RecordingDuration', '')
    digits = ''.join(filter(str.isdigit, caller))[-10:]

    try:
        conn = get_db_connection()
        c = conn.cursor()
        note = f"\n[INBOUND VOICEMAIL] From {caller} ({duration}s): {recording_url}"
        c.execute("UPDATE leads SET status='INTERESTED', notes=notes || ?, call_outcome='Voicemail Received', last_called_at=CURRENT_TIMESTAMP WHERE primary_phone LIKE ? OR mobile_1 LIKE ?", (note, f"%{digits}%", f"%{digits}%"))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving inbound voicemail: {e}")

    twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Say>Thank you for reaching Apex Bridge Properties. We have received your message and will get back to you shortly.</Say><Hangup/></Response>'
    return Response(twiml, mimetype='text/xml')

@app.route('/portal/drop-voicemail/<int:lead_id>', methods=['POST'])
def drop_voicemail(lead_id):
    """Triggers an instant authentic Voicemail Drop to the lead's phone via Twilio."""
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
    if not lead:
        conn.close()
        return jsonify({'error': 'Lead not found'}), 404

    raw_phone = lead['primary_phone'] or lead['mobile_1'] or lead['landline_1']
    if not raw_phone:
        conn.close()
        return jsonify({'error': 'No phone number on file for this lead'}), 400

    digits = ''.join(filter(str.isdigit, str(raw_phone)))
    if len(digits) == 10:
        to_phone = '+1' + digits
    elif len(digits) == 11 and digits.startswith('1'):
        to_phone = '+' + digits
    else:
        to_phone = raw_phone

    called_by = session.get('user_id', 'Caller')
    vm_twiml_url = f"{request.url_root.rstrip('/')}/voice/voicemail-drop"
    note_entry = f"\n[Voicemail Dropped by {called_by}] Authentic audio dispatched to {to_phone}"

    if TWILIO_SID and TWILIO_TOKEN:
        try:
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            call = client.calls.create(
                to=to_phone,
                from_=TWILIO_FROM,
                url=vm_twiml_url,
                machine_detection='DetectMessageEnd'
            )
            c = conn.cursor()
            c.execute("UPDATE leads SET status='CALLED', notes=notes || ?, call_outcome='Voicemail Dropped', called_by=?, last_called_at=CURRENT_TIMESTAMP WHERE id=?", (note_entry, called_by, lead_id))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'call_sid': call.sid, 'status': 'Voicemail Dropped'})
        except Exception as e:
            conn.close()
            return jsonify({'error': str(e)}), 500
    else:
        c = conn.cursor()
        c.execute("UPDATE leads SET status='CALLED', notes=notes || ?, call_outcome='Voicemail Staged', called_by=?, last_called_at=CURRENT_TIMESTAMP WHERE id=?", (note_entry, called_by, lead_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'dry_run': True, 'message': f'Voicemail staged for {to_phone}'})

# ==============================================================================
# PIPELINE SYNC API FOR COMMAND CENTER
# ==============================================================================

@app.route('/api/sync-leads', methods=['GET'])
def api_sync_leads():
    """Secure API endpoint for desktop Command Center to sync live caller activity."""
    auth_key = request.args.get('key')
    if auth_key != os.environ.get('SECRET_KEY', 'apex_bridge_secret_key_2026'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, address, city, state, zip, primary_phone, status, notes, call_outcome, called_by, last_called_at FROM leads WHERE status != 'UNCALLED' OR notes != ''")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'leads': rows, 'count': len(rows)})

@app.route('/api/sync-calendar', methods=['GET', 'POST'])
def api_sync_calendar():
    """Secure endpoint to get or push calendar events/deal progress milestones from Command Center."""
    auth_key = request.args.get('key')
    if auth_key != os.environ.get('SECRET_KEY', 'apex_bridge_secret_key_2026'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    c = conn.cursor()
    
    if request.method == 'POST':
        events = request.json.get('events', [])
        try:
            c.execute("DELETE FROM calendar_events")
            for ev in events:
                c.execute("""INSERT INTO calendar_events (title, event_type, area, deal_phase, event_date, notes, color)
                             VALUES (?, ?, ?, ?, ?, ?, ?)""",
                          (ev.get('title'), ev.get('event_type'), ev.get('area'), ev.get('deal_phase'), ev.get('event_date'), ev.get('notes'), ev.get('color')))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'count': len(events)})
        except Exception as e:
            conn.close()
            return jsonify({'error': str(e)}), 500
            
    # GET method
    c.execute("SELECT * FROM calendar_events ORDER BY event_date ASC")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'events': rows, 'count': len(rows)})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
