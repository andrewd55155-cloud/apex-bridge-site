from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import pandas as pd
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'apex_bridge_secret_key_2026')
app.jinja_env.globals.update(enumerate=enumerate)

DB_PATH = 'crm_leads.db'
CSV_PATH = 'combined_leads.csv'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            primary_phone TEXT,
            primary_phone_type TEXT,
            mail_address TEXT,
            mail_city TEXT,
            mail_state TEXT,
            mailing_zip TEXT,
            email_1 TEXT,
            email_2 TEXT,
            mobile_1 TEXT,
            mobile_2 TEXT,
            landline_1 TEXT,
            landline_2 TEXT,
            status TEXT DEFAULT 'UNCALLED',
            notes TEXT DEFAULT '',
            call_outcome TEXT DEFAULT '',
            called_by TEXT DEFAULT '',
            last_called_at TIMESTAMP
        )
    ''')
    conn.commit()
    cursor.execute('SELECT COUNT(*) FROM leads')
    if cursor.fetchone()[0] == 0 and os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH).fillna('')
        for _, r in df.iterrows():
            cursor.execute('''
                INSERT INTO leads (first_name, last_name, address, city, state, zip,
                primary_phone, primary_phone_type, mail_address, mail_city, mail_state,
                mailing_zip, email_1, email_2, mobile_1, mobile_2, landline_1, landline_2, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNCALLED')
            ''', (str(r.get('first_name','')), str(r.get('last_name','')), str(r.get('address','')),
                  str(r.get('city','')), str(r.get('state','')), str(r.get('zip','')),
                  str(r.get('primary_phone','')), str(r.get('primary_phone_type','')),
                  str(r.get('mail_address','')), str(r.get('mail_city','')), str(r.get('mail_state','')),
                  str(r.get('mailing_zip','')), str(r.get('Email-1','')), str(r.get('Email-2','')),
                  str(r.get('Mobile-1','')), str(r.get('Mobile-2','')), str(r.get('Landline-1','')),
                  str(r.get('Landline-2',''))))
        conn.commit()
    conn.close()

init_db()

# SECURE: Only authorized users known to the admin
AUTH_USERS = {
    'CLI-001': 'Caller 01',
    'CLI-002': 'Caller 02',
    'ADMIN-APEX': 'Admin'
}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/portal/login', methods=['GET', 'POST'])
def login():
    err = None
    if request.method == 'POST':
        u = request.form.get('user_id', '').strip()
        if u in AUTH_USERS:
            session['user_id'] = u
            session['user_name'] = AUTH_USERS[u]
            return redirect(url_for('portal'))
        err = 'Invalid User ID'
    return render_template('login.html', error=err)

@app.route('/portal/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/portal')
def portal():
    if 'user_id' not in session: return redirect(url_for('login'))
    f = request.args.get('filter', 'ALL')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM leads')
    tot = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM leads WHERE status != 'UNCALLED'")
    cal = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM leads WHERE status = 'INTERESTED'")
    inte = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM leads WHERE status = 'NOT_INTERESTED'")
    nint = c.fetchone()[0]
    unc = tot - cal

    if f == 'UNCALLED': c.execute("SELECT * FROM leads WHERE status = 'UNCALLED' ORDER BY id ASC")
    elif f == 'CALLED': c.execute("SELECT * FROM leads WHERE status != 'UNCALLED' ORDER BY last_called_at DESC")
    elif f == 'INTERESTED': c.execute("SELECT * FROM leads WHERE status = 'INTERESTED' ORDER BY last_called_at DESC")
    else: c.execute("SELECT * FROM leads ORDER BY id ASC")
    leads = c.fetchall()
    conn.close()
    metrics = {'total': tot, 'called': cal, 'uncalled': unc, 'interested': inte, 'not_interested': nint}
    return render_template('portal.html', leads=leads, metrics=metrics, current_filter=f, user_name=session.get('user_name', 'Caller'))

@app.route('/portal/update/<int:lead_id>', methods=['POST'])
def update_lead(lead_id):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 403
    st = request.form.get('status', 'CALLED')
    nt = request.form.get('notes', '')
    oc = request.form.get('outcome', '')
    conn = get_db_connection()
    c = conn.cursor()
# DIALER INTEGRATION: Placeholder to hook into a softphone provider later
@app.route('/portal/dial/<int:lead_id>', methods=['POST'])
def dial_lead(lead_id):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({'success': True, 'message': 'Dialing sequence initialized.'})

    c.execute('UPDATE leads SET status=?, notes=?, call_outcome=?, called_by=?, last_called_at=CURRENT_TIMESTAMP WHERE id=?',
              (st, nt, oc, session.get('user_id'), lead_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'lead_id': lead_id, 'status': st})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

