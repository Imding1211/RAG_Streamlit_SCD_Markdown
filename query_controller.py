
from langchain_core.prompts import ChatPromptTemplate
from database_controller import DatabaseController
from setting_controller import SettingController
from langchain_ollama import OllamaLLM
from typing import Dict, Generator

#=============================================================================#

class QueryController():

    def __init__(self):

        self.SettingController = SettingController()
        self.llm_model         = self.SettingController.setting['llm_model']['selected']
        self.query_num         = self.SettingController.setting['paramater']['query_num']
        self.prompt_templt     = self.SettingController.setting['paramater']['prompt']
        self.base_url          = self.SettingController.setting['server']['base_url']

        self.DatabaseController = DatabaseController()
        self.database           = self.DatabaseController.database

#-----------------------------------------------------------------------------#

    def generate_results(self, query_text):
        
        retriever     = self.database.as_retriever(search_kwargs={"k": self.query_num})
        query_results = retriever.invoke(query_text, filter={"latest": True})

        sources = []
        for doc in query_results:

            source_name = doc.metadata['source'].split('.')[0] + '_v' + str(doc.metadata['version']) + '.' + doc.metadata['source'].split('.')[-1]

            sources.append(source_name)

        query_sources = list(set(sources))

        return query_results, query_sources

#-----------------------------------------------------------------------------#

    def generate_prompt(self, query_text, query_results):
        
        context_text    = "\n\n---\n\n".join(list(set([doc.metadata['raw_text'] for doc in query_results])))
        #context_text    = "\n\n---\n\n".join(list(set([doc.page_content for doc in query_results])))
        prompt_template = ChatPromptTemplate.from_template(self.prompt_templt)
        prompt          = prompt_template.format(context=context_text, question=query_text)

        print(prompt)

        return prompt

#-----------------------------------------------------------------------------#

    def generate_response(self, messages: Dict) -> Generator:
        
        llm = OllamaLLM(model=self.llm_model, base_url=self.base_url)
        
        for chunk in llm.stream(messages):
            yield chunk
