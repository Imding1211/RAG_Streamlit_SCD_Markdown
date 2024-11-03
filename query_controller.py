
from langchain_core.prompts import ChatPromptTemplate
from database_controller import DatabaseController
from setting_controller import SettingController
from typing import Dict, Generator
from ollama import Client
import ollama

#=============================================================================#

class QueryController():

    def __init__(self):

        self.SettingController = SettingController()
        self.llm_model         = self.SettingController.setting['llm_model']['selected']
        self.query_num         = self.SettingController.setting['paramater']['query_num']
        self.prompt_templt     = self.SettingController.setting['paramater']['prompt']
        self.client            = Client(host=self.SettingController.setting['server']['base_url'])

        self.DatabaseController = DatabaseController()
        self.database           = self.DatabaseController.database

#-----------------------------------------------------------------------------#

    def generate_results(self, query_text):
        
        query_results = self.database.similarity_search_with_score(query_text, k=self.query_num, filter={"latest": True})

        sources = []
        for doc, _score in query_results:

            source_name = doc.metadata['source'].split('.')[0] + '_v' + str(doc.metadata['version']) + '.' + doc.metadata['source'].split('.')[-1]

            sources.append(source_name)

        query_sources = list(set(sources))

        return query_results, query_sources

#-----------------------------------------------------------------------------#

    def generate_prompt(self, query_text, query_results):
        
        context_text    = "\n\n---\n\n".join([doc.page_content for doc, _score in query_results])
        prompt_template = ChatPromptTemplate.from_template(self.prompt_templt)
        prompt          = prompt_template.format(context=context_text, question=query_text)

        return prompt

#-----------------------------------------------------------------------------#

    def ollama_generator(self, messages: Dict) -> Generator:
        
        stream = self.client.chat(model=self.llm_model, messages=messages, stream=True)
        
        for chunk in stream:
            yield chunk['message']['content']



