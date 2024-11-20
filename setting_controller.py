
import json

#=============================================================================#

class SettingController():

	def __init__(self):

		self.default_setting = {
		    "paramater": {
		        "prompt": "{context}\n\n---\n\n根據以上資料用繁體中文回答問題: {question}\n",
		        "query_num": 5,
		        "database": "database/default"
		    },
		    "llm_model": {
		        "selected": "gemma2:2b",
		        "options": [
		            "gemma2:2b"
		        ]
		    },
		    "embedding_model": {
		        "selected": "all-minilm",
		        "options": [
		            "all-minilm",
		            "shaw/dmeta-embedding-zh:latest"
		        ]
		    },
		    "text_splitter": {
		        "chunk_size": 150,
		        "chunk_overlap": 50
		    },
		    "server": {
		        "base_url": "http://localhost:11434"
		    }
		}

		self.load_setting()

#-----------------------------------------------------------------------------#

	def load_setting(self):
		with open('setting.json', 'r', encoding='utf-8') as setting_file:
		    self.setting = json.load(setting_file)

#-----------------------------------------------------------------------------#

	def generate_setting(self, new_setting):
		with open('setting.json', 'w', encoding='utf-8') as setting_file:
			setting_file.write(json.dumps(new_setting, indent=4, ensure_ascii=False))

#-----------------------------------------------------------------------------#

	def generate_default_setting(self):
		with open('setting.json', 'w', encoding='utf-8') as setting_file:
			setting_file.write(json.dumps(self.default_setting, indent=4, ensure_ascii=False))

#-----------------------------------------------------------------------------#

	def change_llm_model(self, model_name):

		if len(model_name) > 0:

			self.setting['llm_model']['selected'] = model_name

			self.generate_setting(self.setting)

#-----------------------------------------------------------------------------#

	def change_embedding_model(self, model_name):

		if len(model_name) > 0:

			self.setting['embedding_model']['selected'] = model_name

			self.generate_setting(self.setting)

#-----------------------------------------------------------------------------#

	def change_prompt(self, prompt):

		self.setting['paramater']['prompt'] = prompt

		self.generate_setting(self.setting)

#-----------------------------------------------------------------------------#

	def change_query_num(self, query_num):

		self.setting['paramater']['query_num'] = query_num

		self.generate_setting(self.setting)

#-----------------------------------------------------------------------------#

	def change_database(self, database):

		self.setting['paramater']['database'] = 'database/'+database

		self.generate_setting(self.setting)

#-----------------------------------------------------------------------------#

	def change_text_splitter(self, chunk_size, chunk_overlap):

		self.setting['text_splitter']['chunk_size'] = int(chunk_size)

		self.setting['text_splitter']['chunk_overlap'] = int(chunk_overlap)

		self.generate_setting(self.setting)

#-----------------------------------------------------------------------------#

	def change_base_url(self, base_url):

		self.setting['server']['base_url'] = base_url

		self.generate_setting(self.setting)

#-----------------------------------------------------------------------------#

	def add_llm_model(self, model_name):

		if len(model_name) > 0:

			self.setting['llm_model']['options'].append(model_name)

			self.generate_setting(self.setting)

#-----------------------------------------------------------------------------#

	def add_embedding_model(self, model_name):

		if len(model_name) > 0:

			self.setting['embedding_model']['options'].append(model_name)

			self.generate_setting(self.setting)

#-----------------------------------------------------------------------------#

	def remove_llm_model(self, model_name):

		if len(model_name) > 0:

			self.setting['llm_model']['options'].remove(model_name)

			if self.setting['llm_model']['selected'] == model_name:
				self.setting['llm_model']['selected'] = self.setting['llm_model']['options'][0]

			self.generate_setting(self.setting)

#-----------------------------------------------------------------------------#

	def remove_embedding_model(self, model_name):

		if len(model_name) > 0:

			self.setting['embedding_model']['options'].remove(model_name)

			if self.setting['embedding_model']['selected'] == model_name:
				self.setting['embedding_model']['selected'] = self.setting['embedding_model']['options'][0]

			self.generate_setting(self.setting)
