#! /usr/bin/env python

import commands,re,os;

class stats:
	ok=0
	failed=0

def logr(text):
	logfile.write(text);
def log(text):
	logr(text+"\n");

def test_log_results(cmd,s,o,r):
	"""
	cmd=command being tested (info only)
	s=return status
	o=output
	r=result (false=ok, anything else=fail (anything other than 1 will be printed))
	"""
	global stats
	log("*** testing "+cmd);
	log(o);
	if r:
		stats.failed=stats.failed+1
		print "failed test:",cmd
		result="FAILED";
		if type(r)!=type(1) or r!=1:
			result=result+" (%s)"%r
	else:
		stats.ok=stats.ok+1
		result="OK";
	log("%s (%s)"%(result,s));
	log("");
def test_generic(cmd,test):
	s,o=commands.getstatusoutput(cmd)
	r=test(s,o)
	test_log_results(cmd,s,o,r)
class cst_err(Exception): pass
def cfv_stdin_test(cmd,file):
	s1=s2=None
	o1=o2=''
	r=0
	try:
		s1,o1=commands.getstatusoutput(cmd+' '+file)
		if s1: raise cst_err, 2
		s2,o2=commands.getstatusoutput('cat '+file+' | '+cmd+' -')
		if s2: raise cst_err, 3
		x=re.search('^(.*)'+re.escape(file)+'(.*)$[\r\n]{0,2}^(\d+) files, (\d+) OK.  [\d.]+ seconds, [\d.]+K(/s)?$',o1,re.M)
		if not x: raise cst_err, 4
		x2=re.search('^'+re.escape(x.group(1)+x.group(2))+'$[\r\n]{0,2}^(\d+) files, (\d+) OK.  [\d.]+ seconds, [\d.]+K(/s)?$',o2,re.M)
		if not x2: raise cst_err, 5
	except cst_err, er:
		r=er
	test_log_results('stdin/out of '+cmd+' with file '+file,(s1,s2),o1+'\n'+o2,r)

def rx_test(pat,str):
	if re.search(pat,str): return 0
	return 1
def status_test(s,o):
	if s==0:
		return 0
	return 1

#set everything to default in case user has different in config file
cfvcmd="../cfv -VRMUI"

def cfv_test(s,o):
	x=re.search(r'^(\d+) files, (\d+) OK.  [\d.]+ seconds, [\d.]+K(/s)?$',o)
	if s==0 and x and x.group(1) == x.group(2) and int(x.group(1))>0:
		return 0
	return 1

def cfv_unv_test(s,o,unv=1):
	x=re.search(r'^(\d+) files, (\d+) OK, (\d)+ unverified.  [\d.]+ seconds, [\d.]+K(/s)?$',o,re.M)
	if s!=0 and x and x.group(1) == x.group(2) and int(x.group(1))>0:
		if unv and int(x.group(3))!=unv:
			return 1
		return 0
	return 1

def cfv_bad_test(s,o,bad=-1):
	x=re.search(r'^(\d+) files, (\d+) OK, (\d)+ bad(crc|size).  [\d.]+ seconds, [\d.]+K(/s)?$',o,re.M)
	if s!=0 and x and int(x.group(1))>0 and int(x.group(3))>0:
		if bad>0 and int(x.group(3))!=unv:
			return 1
		return 0
	return 1

def cfv_version_test(s,o):
	x=re.search(r'cfv v([\d.]+) -',o)
	x2=re.search(r'cfv ([\d.]+) ',open("../README").readline())
	x3=re.search(r' v([\d.]+):',open("../Changelog").readline())
	if x: log('cfv: '+x.group(1))
	if x2: log('README: '+x2.group(1))
	if x3: log('Changelog: '+x3.group(1))
	if os.path.isdir('../debian'):
		x4=re.search(r'cfv \(([\d.]+)-\d+\) ',open("../debian/changelog").readline())
		if x4: log('deb changelog: '+x4.group(1))
		if not x or not x4 or x4.group(1)!=x.group(1):
			return 1
	if x and x2 and x3 and x.group(1)==x2.group(1) and x.group(1)==x3.group(1):
		return 0
	return 1

def T_test(f):
	test_generic(cfvcmd+" -T -f test"+f,cfv_test)
	test_generic(cfvcmd+" -i -T -f test"+f,cfv_test) #all tests should work with -i
	test_generic(cfvcmd+" -m -T -f test"+f,cfv_test) #all tests should work with -m

def gzC_test(f,extra=None,verify=None,t=None,d=None):
	cmd=cfvcmd
	if not t:
		t=f
	f2='test.C.'+f+'.tmp.gz'
	f='test.C.'+f+'.gz'
	if extra:
		cmd=cmd+" "+extra
	test_generic("%s -q -C -t %s -zz -f - %s > %s "%(cmd,t,d,f2),status_test)
	test_generic("%s -C -f %s %s"%(cmd,f,d),cfv_test)
	test_generic("zdiff %s %s "%(f,f2),status_test)
	test_generic("%s -T -f %s"%(cmd,f),cfv_test)
	test_generic("cat %s|%s -zz -T -f -"%(f,cmd),cfv_test)
	if verify:
		verify(f)
	os.unlink(f)
	os.unlink(f2)
def C_test(f,extra=None,verify=None,t=None,d='data?'):
	gzC_test(f,extra=extra,t=t,d=d)
	cmd=cfvcmd
	if not t:
		t=f
	cfv_stdin_test(cmd+" -t"+f+" -C -f-","data4")
	f='test.C.'+f
	if extra:
		cmd=cmd+" "+extra
	test_generic("%s -C -f %s %s"%(cmd,f,d),cfv_test)
	test_generic("%s -T -f %s"%(cmd,f),cfv_test)
	test_generic("cat %s|%s -T -f -"%(f,cmd),cfv_test)
	test_generic("gzip -c %s|%s -zz -t%s -T -f -"%(f,cmd,t),cfv_test)
	if verify:
		verify(f)
	os.unlink(f)

def ren_test(f,extra=None,verify=None,t=None):
	join=os.path.join
	dir='n.test'
	dir2=join('n.test','d2')
	cmd=cfvcmd+' --renameformat="%(name)s-%(count)i%(ext)s" -r -p '+dir
	if extra:
		cmd=cmd+" "+extra
	try:
		os.mkdir(dir)
		os.mkdir(dir2)
		fls=[join(dir,'test.ext.end'),
			join(dir,'test2.foo'),
			join(dir,'test3'),
			join(dir2,'test4.foo')]
		flsf=[join(dir,'test.ext-%i.end'),
			join(dir,'test2-%i.foo'),
			join(dir,'test3-%i'),
			join(dir2,'test4-%i.foo')]
		flsf_1=[join(dir,'test.ext.end-%i'),
			join(dir,'test2.foo-%i'),
			join(dir2,'test4.foo-%i')]
		flsf_2=[join(dir,'test3-%i')]
		def flsw(t,fls=fls):
			for fl in fls:
				open(fl,'wb').write(t)
		def flscmp(t,n,fls=flsf):
			for fl in fls:
				fn= n!=None and fl%n or fl
				o=open(fn,'rb').read()
				r=o!=t
				test_log_results('cmp %s for %s'%(fn,t),r,o,r)
		flsw('hello')
		test_generic("%s -C -t %s"%(cmd,f),cfv_test)
		flsw('1')
		test_generic("%s -Tn"%(cmd),cfv_bad_test)
		flsw('11')
		test_generic("%s -Tn"%(cmd),cfv_bad_test)
		flsw('123')
		test_generic("%s -Tn"%(cmd),cfv_bad_test)
		flsw('63')
		test_generic(cmd+' --renameformat="%(fullname)s" -Tn',cfv_bad_test) #test for formats without count too
		flsw('hello')
		test_generic("%s -Tn"%(cmd),cfv_test)
		flscmp('1',0)
		flscmp('11',1)
		flscmp('123',2)
		flscmp('63',1,fls=flsf_1)
		flscmp('63',3,fls=flsf_2)
		flscmp('hello',None,fls=fls)
	finally:
		import glob
		for d in glob.glob(join(dir2,'*')):
			os.unlink(d)
		os.rmdir(dir2)
		for d in glob.glob(join(dir,'*')):
			os.unlink(d)
		os.rmdir(dir)
	
logfile=open("test.log","w")

ren_test('md5')
ren_test('md5',extra='-rr')
ren_test('sfv')
ren_test('csv')
ren_test('csv2')
ren_test('csv4')

T_test(".md5")
T_test(".md5.gz")
T_test(".csv")
T_test(".sfv")
T_test(".csv2")
T_test("crlf.md5")
T_test("crlf.csv")
T_test("crlf.sfv")
test_generic(cfvcmd+" -i -T -f testcase.csv",cfv_test)
test_generic(cfvcmd+r" --fixpaths \\/ -T -f testfix.csv",cfv_test)
test_generic(cfvcmd+r" --fixpaths \\/ -T -f testfix.csv4",cfv_test)
test_generic(cfvcmd+r" -i --fixpaths \\/ -T -f testfix.csv4",cfv_test)

C_test("md5",verify=lambda f: test_generic("md5sum -c "+f,status_test))
C_test("csv")
C_test("sfv")
C_test("csv2","-t csv2")
C_test("csv4","-t csv4")
#test_generic("../cfv -V -T -f test.md5",cfv_test)
#test_generic("../cfv -V -tcsv -T -f test.md5",cfv_test)

test_generic(cfvcmd+" -u -f test.md5 data* test.py",cfv_unv_test)
test_generic(cfvcmd+" -u -f test.md5 data* test.py test.md5",cfv_unv_test)
test_generic(cfvcmd+r" -i --fixpaths \\/ -Trru",lambda s,o: cfv_unv_test(s,o,None))
test_generic(cfvcmd+" -h",cfv_version_test)

donestr="tests finished:  ok: %i  failed: %i"%(stats.ok,stats.failed)
log("\n"+donestr)
print donestr
