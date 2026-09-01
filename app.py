from flask import Flask, render_template, request, session, redirect, url_for
import pandas as pd
import os

app = Flask(__name__, template_folder='.')
app.secret_key = 'super_secret_key'
app.jinja_env.globals.update(enumerate=enumerate)


# Load leads once when the app starts
LEADS_FILE = 'combined_leads.csv'
df = pd.read_csv(LEADS_FILE)
# Create a 'status' column if it doesn't exist
if 'status' not in df.columns:
    df['status'] = 'UNCALLED'

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/portal/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('user_id') == 'CALLER_LIZE_001':
            session['user_id'] = 'CALLER_LIZE_001'
            return redirect(url_for('portal'))
    return render_template('login.html')

@app.route('/portal')
def portal():
    if 'user_id' not in session: return redirect(url_for('login'))
    # Convert dataframe to list of dicts for the template
    leads = df.to_dict('records')
    return render_template('portal.html', leads=leads)

@app.route('/portal/call/<int:index>', methods=['POST'])
def call_lead(index):
    if 'user_id' not in session: return "Unauthorized", 403
    df.at[index, 'status'] = 'CALLED'
    return "Call Initiated", 200

if __name__ == '__main__':
    app.run()
