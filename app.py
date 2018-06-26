from flask import Flask, render_template, jsonify
from sqlalchemy import create_engine
from datetime import datetime
from pandas.io.sql import read_sql
import pandas as pd
import pymysql, json, get_most_starred


app = Flask(__name__)

# Connecting to MySQL
with open('creds.json', 'rb') as f:
    creds = json.load(f)
engine = create_engine('mysql+pymysql://{}:{}@localhost:3306/victr?charset=utf8mb4'.format(creds['user'], creds['pass']), echo=False)

def format_parent_child(df):
    '''Helper fcn for formatting table HTML w/ expandable rows'''
    desired_cols = ['repository_ID', 'name', 'description', 'URL', 'number_of_stars', 'created_date', 'last_push_date']
    parent_cols = ['name', 'description', 'number_of_stars']
    parent_cols_display = ['Name', 'Description', '# of Stars']
    child_cols = ['repository_ID', 'URL', 'created_date', 'last_push_date']
    child_cols_display = ['Repository ID', 'URL', 'Created Date', 'Last Push Date']

    html_string = df[desired_cols].to_html(classes='table table-striped display responsive" style="white-space:wrap; overflow:visible;" id="a_nice_table', index=False, border=0)
    for i, colname in enumerate(parent_cols):
        html_string = html_string.replace('<th>{}</th>'.format(colname), '<th class="all">{}</th>'.format(parent_cols_display[i]))
    for i, colname in enumerate(child_cols):
        html_string = html_string.replace('<th>{}</th>'.format(colname), '<th class="none">{}: </th>'.format(child_cols_display[i]))
    return html_string

# App pages
@app.route('/')
def index():
    conn = engine.connect()
    df = read_sql('SELECT * FROM starred;', conn)
    conn.close()
    return render_template('index.html', last_refresh_date=df['table_entry_dt'].max(), my_table=format_parent_child(df))

@app.route('/_refresh_table')
def refresh_table():
    get_most_starred.main()
    conn = engine.connect()
    df = read_sql('SELECT * FROM starred;', conn)
    conn.close()
    return jsonify(timestamp=df['table_entry_dt'].max(), my_table=format_parent_child(df))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
