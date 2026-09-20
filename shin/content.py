"""Host-selected SQLite CMS. Public reads never expose drafts."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from .compiler import ShinError


class ContentError(ShinError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status=status


class ContentStore:
    def __init__(self, path, collections):
        self.path=str(Path(path).resolve())
        self.collections=set(collections)
        if not self.collections or any(not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}', c) for c in self.collections):
            raise ShinError('invalid CMS collections')
        with closing(self.connect()) as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS shin_content (
                collection TEXT NOT NULL, slug TEXT NOT NULL, title TEXT NOT NULL,
                body TEXT NOT NULL, published INTEGER NOT NULL, revision INTEGER NOT NULL,
                updated TEXT NOT NULL, PRIMARY KEY(collection,slug))''')

    def connect(self):
        db=sqlite3.connect(self.path, timeout=3)
        db.row_factory=sqlite3.Row
        return db

    def validate_key(self,collection,slug=None):
        if collection not in self.collections:
            raise ContentError('collection not allowed',403)
        if slug is not None and (type(slug) is not str or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',slug)):
            raise ContentError('slug must contain lowercase letters, digits, hyphens or underscores')

    def public_list(self,collection):
        self.validate_key(collection)
        with closing(self.connect()) as db:
            rows=db.execute('SELECT slug,title,substr(body,1,120) AS excerpt FROM shin_content WHERE collection=? AND published=1 ORDER BY slug LIMIT 25',(collection,)).fetchall()
        return {'items':[dict(r) for r in rows]}

    def public_get(self,collection,slug):
        self.validate_key(collection,slug)
        with closing(self.connect()) as db:
            row=db.execute('SELECT slug,title,body,updated FROM shin_content WHERE collection=? AND slug=? AND published=1',(collection,slug)).fetchone()
        return {'found':row is not None, 'item':dict(row) if row else {}}

    def admin_list(self,collection,offset=0):
        self.validate_key(collection)
        if type(offset) is not int or not 0<=offset<=1000:
            raise ContentError('invalid offset')
        with closing(self.connect()) as db:
            rows=db.execute('SELECT slug,title,published,revision,updated FROM shin_content WHERE collection=? ORDER BY slug LIMIT 26 OFFSET ?',(collection,offset)).fetchall()
        return {'items':[dict(r) for r in rows[:25]],'next':offset+25 if len(rows)>25 else None}

    def admin_get(self,collection,slug):
        self.validate_key(collection,slug)
        with closing(self.connect()) as db:
            row=db.execute('SELECT * FROM shin_content WHERE collection=? AND slug=?',(collection,slug)).fetchone()
        if row is None:
            raise ContentError('not found',404)
        result=dict(row)
        result['published']=bool(result['published'])
        return result

    def put(self,data):
        required={'collection','slug','title','body','published','revision'}
        if type(data) is not dict or set(data)!=required:
            raise ContentError('exact content fields required')
        collection,slug=data['collection'],data['slug']
        if type(collection) is not str:
            raise ContentError('invalid collection')
        self.validate_key(collection,slug)
        if type(data['title']) is not str or not 1<=len(data['title'])<=200:
            raise ContentError('title must contain 1..200 characters')
        if type(data['body']) is not str or len(data['body'].encode('utf-8'))>16384:
            raise ContentError('body exceeds 16384 UTF-8 bytes')
        if type(data['published']) is not bool or type(data['revision']) is not int or data['revision']<0:
            raise ContentError('invalid publication state or revision')
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT revision FROM shin_content WHERE collection=? AND slug=?',(collection,slug)).fetchone()
            revision=row['revision'] if row else 0
            if revision!=data['revision']:
                raise ContentError('revision conflict: reload the latest content before saving',409)
            if row is None and db.execute('SELECT count(*) FROM shin_content').fetchone()[0]>=1000:
                raise ContentError('CMS alpha limit: 1000 entries',409)
            updated=datetime.now(timezone.utc).isoformat()
            db.execute('''INSERT INTO shin_content VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(collection,slug) DO UPDATE SET title=excluded.title,
                body=excluded.body,published=excluded.published,
                revision=excluded.revision,updated=excluded.updated''',
                (collection,slug,data['title'],data['body'],int(data['published']),revision+1,updated))
        return self.admin_get(collection,slug)
