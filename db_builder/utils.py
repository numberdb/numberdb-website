

import yaml
import os


def load_yaml(path_filename):
	y = None
	with open(path_filename,'r') as f:
		y = yaml.load(f,Loader=yaml.BaseLoader)
	#print("y after loading file:",y)
	return y

def load_yaml_recursively(path_filename):
	'''
	Loads a yaml-file with BaseLoader.
	Replaces strings of the form 'INPUT{<other-filename>}' recursively
	by the content of the yaml file <other-filename>.
	'''
	
	path, filename = os.path.split(path_filename)
		
	def load_recursively(y):
		if isinstance(y,str):
			s = y.strip(" \n")
			if s.startswith("INPUT{") and s.endswith("}"):
				s = s[6:-1]
				filename_s = os.path.join(path,s)
				return load_yaml_recursively(filename_s)
			else:
				return s
		elif isinstance(y,list):
			#TODO: Don't construct new list, just update the old one.
			return [load_recursively(s) for s in y]
		elif isinstance(y,dict):
			#TODO: Don't construct new dict, just update the old one.
			return {k: load_recursively(v) for k,v in y.items() 
						if k not in ["IGNORE",'TODO']}
	
	y = load_yaml(path_filename)
	y = load_recursively(y)
	return y




def normalize_collection_data(data):
	'''
	Brings the collection data into a more "canonical form".	
	'''
	
	header_singulars = []
	#header_singulars.append(("Definition","definition"))
	header_singulars.append(("Formulas","formula"))
	header_singulars.append(("Comments","comment"))
	header_singulars.append(("Programs","program"))
	#header_singulars.append(("Numbers","number"))
	header_singulars.append(("References","reference"))
	header_singulars.append(("Links","link"))

	for header, singular in header_singulars:
		if header in data:
			data_header = data[header]
			if isinstance(data_header,str):
				if data_header.strip(" \n") == "":
					data[header] = {}
				else:
					data[header] = {'%s_1' % (singular,): data_header}
			elif isinstance(data_header,list):
				data[header] = {'%s_%s' % (singular,i): dhi for i, dhi in enumerate(data_header)}
			elif isinstance(data_header,dict):
				pass
			else:
				raise ValueError("YAML file contains unexpected data types at " + header)
	return data

