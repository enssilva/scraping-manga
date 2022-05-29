from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Table, Column, Integer, String, MetaData, Float
import requests
from bs4 import BeautifulSoup as bs
import sys, getopt
import webbrowser
import notify2
import os
import logging
import logzero
from logzero import logger

def addManga(conn, manga):
    url = input("Manga's URL: ")
    if 'https://manganelo.com/manga/' not in url:
        print('URL need to be from https://manganelo.com')
    chapter = input('Last chapter you had read (default 0): ')
    if chapter is None:
        chapter = 0
    site = requests.get(url)
    bs_content = bs(site.content, 'html.parser')
    div = bs_content.find('div', {'class':'story-info-right'})
    name = div.find_next('h1').contents[0]
    ins = manga.insert().values(
        name = name, 
        chapter = chapter,
        url = url)
    conn.execute(ins)

def checkNewChapterForManga(row, conn, manga, iterative, logger):
    id = row[0]
    name = row[1]
    chapter = row[2]
    url = row[3]
    logger.debug(f'Request URL: {url}')
    site = requests.get(url)
    logger.debug('Parsing URL...')
    bs_content = bs(site.content, 'html.parser')
    logger.debug('Get ul element')
    ul_element = bs_content.find('ul', {'class':'row-content-chapter'})
    logger.debug('Get chapter name:')
    chapter_name = ul_element.find_next('li').find_next('a').contents[0]
    logger.debug(chapter_name)
    logger.debug('Get last chapter:')
    last_chapter = float(chapter_name.split(':')[0].split(' ')[-1])
    logger.debug(last_chapter)
    logger.debug('Get last chapter URL:')
    url_chapter = ul_element.find_next('li').find_next('a')['href']
    logger.debug(url_chapter)
    if last_chapter > chapter:
        print(f'New chapter for {name}')
        if iterative:
            ans = input('Do you want to read the new chapter? (y/n) ')
            if ans in ('y', 'Y'):
                upd = manga.update().where(manga.c.id == id).values(chapter = last_chapter)
                conn.execute(upd)
                webbrowser.open(url_chapter)
        else:
            notify2.init('Manga')
            n = notify2.Notification(f'New Chapter for {name}', url_chapter)
            n.show()
    else:
        print(f"There isn't any new chapter in manga {name}")

def checkNewChapter(conn, manga, iterative, logger):
    m = manga.select()
    result = conn.execute(m)
    for row in result:
        logger.debug(row)
        checkNewChapterForManga(row, conn, manga, iterative, logger)

def listMangaChapter(conn, manga):
    m = manga.select()
    result = conn.execute(m)
    for row in result:
        id = row[0]
        name = row[1]
        chapter = row[2]
        print(f'ID ({id:3}) Manga ({name:20}) chapter ({chapter:3})')

def updateChapter(conn, manga):
    listMangaChapter(conn, manga)
    id = input('ID of manga: ')
    chapter = input('Last chapter: ')
    stmt = manga.update().where(manga.c.id == id).values(chapter = chapter)
    conn.execute(stmt)

def removeManga(conn, manga):
    listMangaChapter(conn, manga)
    id = input('ID of manga: ')
    stmt = manga.delete().where(manga.c.id == id)
    conn.execute(stmt)

def printHelp():
    print('scraping-manga.py [option]')
    print('Options:')
    print('\t-h help')
    print('\t-a add new manga')
    print('\t-l list last chapter for all mangas')
    print('\t-u update last chapter for a manga')
    print('\t-i list last chapter for all mangas with iterative')
    print('\t-d run with debug')
    print('\t-r remove a manga')

def main(argv):
    try:
        opts, _ = getopt.getopt(argv, 'haluidr')
    except:
        printHelp()
        sys.exit(2)
    debug = False
    opt = None
    logzero.loglevel(logging.WARNING)
    for op in opts:
        if op[0] == '-d':
            debug = True
            logzero.loglevel(logging.DEBUG)
        else:
            opt = op[0]
    path = os.path.dirname(os.path.abspath(__file__))
    logger.debug(f'path: {path}')
    engine = create_engine(f'sqlite:///{path}/manga.db', echo = debug)
    logger.debug('engine created')
    meta = MetaData()
    manga = Table(
        'manga', meta,
        Column('id', Integer, primary_key = True),
        Column('name', String),
        Column('chapter', Float),
        Column('url', String)
    )
    meta.create_all(engine)
    conn = engine.connect()
    logger.debug(f'opt: {opt}')
    if opts == [] or opt == None:
        logger.debug('checkNewChapter without iterative')
        checkNewChapter(conn, manga, False, logger)
    elif opt == '-h':
        logger.debug('help')
        printHelp()
        conn.close()
        engine.dispose()
        sys.exit()
    elif opt == '-a':
        logger.debug('addManga')
        addManga(conn, manga)
    elif opt == '-l':
        logger.debug('listMangaChapter')
        listMangaChapter(conn, manga)
    elif opt == '-u':
        logger.debug('updateChapter')
        updateChapter(conn, manga)
    elif opt == '-i':
        logger.debug('checkNewChapter with iterative')
        checkNewChapter(conn, manga, True, logger)
    elif opt == '-r':
        logger.debug('removeManga')
        removeManga(conn, manga)
    conn.close()
    engine.dispose()
    logger.debug('end')

if __name__ == "__main__":
    main(sys.argv[1:])