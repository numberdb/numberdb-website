
from sage.all import walltime

class MyTimer:
	'''
	A simple class that keeps track of several running times.
	Call startTimer("X") and later endTimer("X"), then this class saves
	how long the process "X" took.
	'''

	def __init__(self, get_time=walltime):
		self.get_time = get_time
		self.timers = {};
		self.startTimer("CPU time at start");
	
	def startTimer(self,timerName):
		self.timers[timerName] = self.get_time();

	def endTimer(self,timerName,verbose = True):
		self.timers[timerName] = self.get_time(self.timers[timerName]);
		if verbose:
			print("Time taken for "+timerName+":",self.timers[timerName]);
		return self.timers[timerName];

	def totalTime(self):
		return self.get_time(self.timers["CPU time at start"]);

	def toString(self,linePrefix = ""):
		result = "";
		for timerName, t in self.timers.items():
			if timerName != "CPU time at start":
				result += linePrefix+timerName+": "+str(t)+"\n";
		result += linePrefix+"Total time: "+str(self.totalTime());
		return result;
		
	def __str__(self):
		return self.toString()
		
	def __repr__(self):
		return self.__str__()
		
	def run(self,function,*args,**kwargs):
		timer_name = 'Function %s' % (function.__name__,)
		timer_name += '(%s)' % (', '.join('%s=%s' % (key,kwargs[key]) for key in kwargs),) 
		self.startTimer(timer_name)
		function(*args,**kwargs)
		self.endTimer(timer_name)
