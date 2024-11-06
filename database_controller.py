
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters import MarkdownTextSplitter
from setting_controller import SettingController
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
import pandas as pd
import tempfile
import datetime
import humanize
import PyPDF2
import shutil
import uuid

#=============================================================================#

class DatabaseController():

    def __init__(self):

        self.SettingController = SettingController()
        self.chunk_size        = self.SettingController.setting['text_splitter']['chunk_size']
        self.chunk_overlap     = self.SettingController.setting['text_splitter']['chunk_overlap']
        database_path          = self.SettingController.setting['paramater']['database']
        embedding_model        = self.SettingController.setting['embedding_model']['selected']
        base_url               = self.SettingController.setting['server']['base_url']

        self.database  = Chroma(
            persist_directory  = database_path, 
            embedding_function = OllamaEmbeddings(base_url=base_url, model=embedding_model)
            )

        self.time_zone = datetime.timezone(datetime.timedelta(hours=8))
        self.time_now  = datetime.datetime.now(tz=self.time_zone)
        self.time_end  = datetime.datetime(9999, 12, 31, 0, 0, 0, tzinfo=self.time_zone)

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size         = self.chunk_size,
            chunk_overlap      = self.chunk_overlap,
            length_function    = len,
            is_separator_regex = False,
            )

        self.markdown_splitter = MarkdownTextSplitter(
            chunk_size         = self.chunk_size,
            chunk_overlap      = self.chunk_overlap,
            )

#-----------------------------------------------------------------------------#

    def calculate_existing_ids(self):

        existing_items = self.database.get(include=[])
        existing_ids   = set(existing_items["ids"])

        return existing_ids
            
#-----------------------------------------------------------------------------#

    def get_version_list(self, source):

        version_data = self.database.get(where={"source": source})["metadatas"]

        version_list = sorted(set(item['version'] for item in version_data), reverse=True)

        if not len(version_list):
            version_list = [0]

        return version_list

#-----------------------------------------------------------------------------#

    def database_to_dataframes(self):

        data = self.database.get()

        df = pd.DataFrame({
            'ids'           : data['ids'],
            'source'        : [meta['source'] for meta in data['metadatas']],
            'size'          : [humanize.naturalsize(meta['size'], binary=True) for meta in data['metadatas']],
            'chunk_size'    : [meta['chunk_size'] for meta in data['metadatas']],
            'chunk_overlap' : [meta['chunk_overlap'] for meta in data['metadatas']],
            'start_date'    : [meta['start_date'] for meta in data['metadatas']],
            'end_date'      : [meta['end_date'] for meta in data['metadatas']],
            'version'       : [meta['version'] for meta in data['metadatas']],
            'latest'        : [meta['latest'] for meta in data['metadatas']],
            'documents'     : data['documents']
        })

        return df

#-----------------------------------------------------------------------------#

    def add_chroma(self, pdf, markdown, start_date, end_date, current_version):

        metadata = {
        "source"        : pdf.stream.name, 
        "size"          : pdf.stream.size,
        "chunk_size"    : self.chunk_size,
        "chunk_overlap" : self.chunk_overlap,
        "start_date"    : start_date,
        "end_date"      : end_date,
        "version"       : current_version + 1,
        "latest"        : True
        }

        documents = self.markdown_splitter.create_documents([markdown], [metadata])

        #for md_document in md_documents:

            #documents = self.text_splitter.create_documents([md_document.page_content], [metadata])

        ids = [str(uuid.uuid4()) for _ in range(len(documents))]

        if len(documents):
            self.database.add_documents(documents, ids=ids)

#-----------------------------------------------------------------------------#

    def update_chroma(self, source_name, date, latest, current_version):

        old_documents = self.database.get(where={"source": source_name})

        new_documents = []
        new_ids       = []

        for ids, old_metadata, old_document in zip(old_documents["ids"], old_documents['metadatas'], old_documents['documents']):

            if old_metadata['version'] == current_version:

                updated_metedata = {
                "source"        : old_metadata['source'], 
                "size"          : old_metadata['size'],
                "chunk_size"    : old_metadata['chunk_size'],
                "chunk_overlap" : old_metadata['chunk_overlap'],
                "start_date"    : old_metadata['start_date'],
                "end_date"      : date,
                "version"       : old_metadata['version'],
                "latest"        : latest
                }

                new_documents.append(Document(page_content=old_document, metadata=updated_metedata))
                new_ids.append(ids)

        self.database.update_documents(ids=new_ids, documents=new_documents)

#-----------------------------------------------------------------------------#

    def clear_database(self, delete_ids):
        if delete_ids:
            self.database.delete(ids=delete_ids)

#-----------------------------------------------------------------------------#

    def add_database(self, file, markdown):

        start_date = self.time_now.strftime('%Y/%m/%d %H:%M:%S')
        end_date   = self.time_end.strftime('%Y/%m/%d %H:%M:%S')

        pdf = PyPDF2.PdfReader(file)

        current_version = self.get_version_list(pdf.stream.name)[0]

        if current_version > 0:
            self.update_chroma(pdf.stream.name, start_date, False, current_version)

        self.add_chroma(pdf, markdown, start_date, end_date, current_version)

#-----------------------------------------------------------------------------#

    def rollback_database(self, rollback_list):

        end_date = self.time_end.strftime('%Y/%m/%d %H:%M:%S')

        for rollback_source, rollback_version in rollback_list:

            version_list = self.get_version_list(rollback_source)

            if rollback_version == version_list[0] and len(version_list) > 1:

                self.update_chroma(rollback_source, end_date, True, version_list[1])

#-----------------------------------------------------------------------------#

    def save_PDF(self, file):

        save_path = "save_PDF/"

        current_version = self.get_version_list(PyPDF2.PdfReader(file).stream.name)[0]

        save_pdf_name = file.name.split('.')[0] + '_v' + str(current_version) + '.' + file.name.split('.')[-1]

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(file.getvalue())
            temp_pdf.seek(0)
            temp_pdf_name = temp_pdf.name

        shutil.move(temp_pdf_name, save_path+save_pdf_name)
