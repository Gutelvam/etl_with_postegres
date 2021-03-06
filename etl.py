import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *
from datetime import datetime


def process_song_file(cur, filepath):
    ''' Function that join songs JSON files and insert into database 
    at songs, artists tables'''
    # open song file
    df=pd.read_json(filepath,lines=True)

    # insert song record
    song_cols = ['song_id', 'title', 'artist_id', 'year', 'duration']
    song_data = tuple(df[song_cols].values[0])
    cur.execute(song_table_insert, song_data)
    
    # insert artist record
    artists_cols = ['artist_id', 'artist_name', 'artist_location', 'artist_latitude', 'artist_longitude']
    artist_data = tuple(df[artists_cols].values[0])
    cur.execute(artist_table_insert, artist_data)
    
def get_time_columns(dataframe):
    """
     Function that transform timestamp column from miliseconds into  
     hour, day, week, year, month and weekday
     
     input: 
        dataframe - pandas dataframe containing timestamp column in miliseconds called 'ts'
     output:
        time - New dataframe containg only  timestamp ,hour, day, week, year, month and weekday columns
    """
    time = pd.DataFrame()
    time['start_time'] = dataframe['ts_tstamp'].copy()
    time['hour'] = dataframe['ts'].dt.hour
    time['day'] = dataframe['ts'].dt.day
    time['week'] = dataframe['ts'].dt.week
    time['year'] = dataframe['ts'].dt.year
    time['month'] = dataframe['ts'].dt.month
    time['weekday'] = dataframe['ts'].dt.weekday
    return time


def process_log_file(cur, filepath):
    ''' Function that joins logs JSON files and insert into database 
    at users, time and songplays tables'''
    # open log file
    df = pd.read_json(filepath,lines=True)
    
    # filter by NextSong action
    df = df[df.page == 'NextSong'].copy()

    # convert timestamp column to datetime
    df['ts_tstamp'] = df['ts'].copy()
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    time_df = get_time_columns(df).copy()

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_cols = ["userId", "firstName", "lastName", "gender", "level"]
    user_df = df[user_cols].copy()

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in df.iterrows():
        
        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist ,row.length))
        results = cur.fetchone()
        
        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None
            
        # insert songplay record
        if row.userId == '':
            user_id = 0
        else:
            user_id = row.userId
            
        songplay_data = (str(row.ts), row.userId, row.level, songid, artistid, row.sessionId, row.location, row.userAgent)
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    ''' Function that get all JSON paths and execute process function inserting on DB '''
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()
