import requests, pymysql, json, re
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine

def make_engine():
    '''Load credentials and create engine to `victr` database in MySQL'''
    with open('creds.json', 'rb') as f:
        creds = json.load(f)
    engine = create_engine('mysql+pymysql://{}:{}@localhost:3306/victr?charset=utf8mb4'.format(creds['user'], creds['pass']), echo=False)
    return engine

def collect_repos():
    '''Use GitHub API to get most starred Python repos'''
    # MySQL does not support 4-byte characters, use regex to filter out these characters
    re_pattern = re.compile(u'[^\u0000-\uD7FF\uE000-\uFFFF]', re.UNICODE)

    # Store most starred repos to dataframe
    df = pd.DataFrame(columns=['repository_ID', 'name', 'URL', 'created_date', 'last_push_date', 'description', 'number_of_stars'])
    results = requests.get('https://api.github.com/search/repositories?q=language:python&sort=stars&order=desc').json()

    for repo in results['items']:
        d_tmp = {'repository_ID': repo['id'],
                'name': repo['name'],
                'URL': repo['html_url'],
                'created_date': datetime.strptime(repo['created_at'], '%Y-%m-%dT%H:%M:%SZ'),
                'last_push_date': datetime.strptime(repo['pushed_at'], '%Y-%m-%dT%H:%M:%SZ'),
                'description': re_pattern.sub(u'\uFFFD', unicode(repo['description'])),
                'number_of_stars': repo['stargazers_count']}
        df = df.append(d_tmp, ignore_index=True)

    df['table_entry_dt'] = pd.Timestamp.now()
    print 'Repos have been collected'
    return df

def update_db(df, engine):
    '''Upload df of collected repos to a temporary table, then update existing `starred` table'''
    df.to_sql(name='tmp', con=engine, if_exists='replace', index=False)

    # SQL queries for updating existing table using a temporary table
    update_existing = """
        UPDATE starred s, tmp t
        SET s.name = t.name, s.URL = t.URL, s.last_push_date = t.last_push_date, s.description = t.description,
            s.number_of_stars = t.number_of_stars, s.table_entry_dt = t.table_entry_dt
        WHERE s.repository_ID = t.repository_ID
    """
    add_new = """
        INSERT INTO starred
        SELECT * FROM tmp
        WHERE NOT EXISTS
        (SELECT 1 FROM starred
        WHERE repository_ID = tmp.repository_ID)
    """

    conn = engine.connect()
    conn.execute(update_existing)
    conn.execute(add_new)
    conn.execute('DROP TABLE tmp;')
    conn.close()

def main():
    engine = make_engine()
    df = collect_repos()
    update_db(df, engine)

if __name__ == '__main__':
    main()

# `starred` table schema
#
# '''
# CREATE TABLE starred(
#     repository_ID BIGINT(20) PRIMARY KEY NOT NULL,
#     name TEXT NOT NULL,
#     URL TEXT NOT NULL,
#     created_date DATETIME NOT NULL,
#     last_push_date DATETIME NOT NULL,
#     description TEXT,
#     number_of_stars BIGINT(20) NOT NULL,
#     table_entry_dt DATETIME NOT NULL
# );
# '''
