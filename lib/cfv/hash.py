import os
import sys

from cfv import osutil
from cfv import strutil

try:
	if os.environ.get('CFV_NOMMAP'): raise ImportError
	# mmap is broken in python 2.4.2 and leaks file descriptors
	if sys.version_info[:3] == (2, 4, 2): raise ImportError
	import mmap
	if hasattr(mmap, 'ACCESS_READ'):
		def dommap(fileno, len):#generic mmap.  python2.2 adds ACCESS_* args that work on both nix and win.
			if len==0: return '' #mmap doesn't like length=0
			return mmap.mmap(fileno, len, access=mmap.ACCESS_READ)
	elif hasattr(mmap, 'PROT_READ'):
		def dommap(fileno, len):#unix mmap.  python default is PROT_READ|PROT_WRITE, but we open readonly.
			if len==0: return '' #mmap doesn't like length=0
			return mmap.mmap(fileno, len, mmap.MAP_SHARED, mmap.PROT_READ)
	else:
		def dommap(fileno, len):#windows mmap.
			if len==0: return ''
			return mmap.mmap(fileno, len)
	_nommap=0
except ImportError:
	_nommap=1

def _getfilechecksum(filename, hasher, callback):
	if filename=='':
		f=sys.stdin
	else:
		f=open(filename,'rb')
	def finish(m,s):
		while 1:
			x=f.read(65536)
			if not x:
				return m.digest(),s
			s += len(x)
			m.update(x)
			if callback: callback(s)

	if f==sys.stdin or _nommap or callback:
		return finish(hasher(),0L)
	else:
		s = os.path.getsize(filename)
		try:
			m = hasher(dommap(f.fileno(), s))
		except OverflowError:
			mmapsize = min(s, 2**31-1) #mmap size is limited by C's int type, which even on 64 bit arches is often 32 bits, so we can't use sys.maxint either.  If we get the error, just assume 32 bits. 
			m = hasher(dommap(f.fileno(), mmapsize))
			f.seek(mmapsize)
			return finish(m,mmapsize) #unfortunatly, python's mmap module doesn't support the offset parameter, so we just have to do the rest of the file the old fashioned way.
		return m.digest(),s

import sha
def getfilesha1(filename, callback):
	return _getfilechecksum(filename, sha.new, callback)
			
try:
	if os.environ.get('CFV_NOFCHKSUM'): raise ImportError
	import fchksum
	try:
		if fchksum.version()<5:raise ImportError
	except:
		stderr.write("old fchksum version installed, using std python modules. please update.\n") #can't use perror yet since config hasn't been done..
		raise ImportError
	def getfilemd5(filename, callback):
		if filename=='':
			f = sys.stdin
		else:
			f = open(filename, 'rb')
		if strutil.is_unicode(filename):
			sname = filename.encode(osutil.fsencoding, 'replace')
		else:
			sname = filename
		c,s=fchksum.fmd5(sname, callback, 0.03, fileno=f.fileno())
		return c,s
	def getfilecrc(filename, callback):
		if filename=='':
			f = sys.stdin
		else:
			f = open(filename, 'rb')
		if strutil.is_unicode(filename):
			sname = filename.encode(osutil.fsencoding, 'replace')
		else:
			sname = filename
		c,s=fchksum.fcrc32d(sname, callback, 0.03, fileno=f.fileno())
		return c,s
except ImportError:
	import md5
	import struct
	try:
		from zlib import crc32 as _crc32
	except ImportError:
		from binascii import crc32 as _crc32
	class CRC32:
		digest_size = 4
		def __init__(self, s=''):
			self.value = _crc32(s)
		def update(self, s):
			self.value = _crc32(s, self.value)
		def digest(self):
			return struct.pack('>I',self.value)

	def getfilemd5(filename, callback):
		return _getfilechecksum(filename, md5.new, callback)
			
	def getfilecrc(filename, callback):
		return _getfilechecksum(filename, CRC32, callback)