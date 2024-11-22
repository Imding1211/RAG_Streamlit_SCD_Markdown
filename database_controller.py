
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters import MarkdownTextSplitter
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core import ChatPromptTemplate
from llama_index.llms.ollama import Ollama

from setting_controller import SettingController

import pandas as pd
import tempfile
import datetime
import humanize
import PyPDF2
import shutil
import uuid
import json
import re

#=============================================================================#

class DatabaseController():

    def __init__(self):

        self.SettingController = SettingController()
        self.chunk_size        = self.SettingController.setting['text_splitter']['chunk_size']
        self.chunk_overlap     = self.SettingController.setting['text_splitter']['chunk_overlap']
        database_path          = self.SettingController.setting['paramater']['database']
        llm_model              = self.SettingController.setting['llm_model']['selected']
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
            is_separator_regex = False
            )

        self.llm = Ollama(
            model='llama3.2:latest', 
            request_timeout=120.0, 
            base_url=base_url, 
            json_mode=True
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

    def add_chroma(self, pdf, start_date, end_date, current_version):

        print(pdf.stream.name)

        markdown = self.load_markdown(pdf)

        PDF_info = self.markdown_to_section(markdown, pdf.stream.name.split('.')[0])

        PDF_info = self.create_propositions(PDF_info)

        self.save_json(PDF_info)
        
        #PDF_info = self.load_json()
        
        for info in PDF_info["sections"]:
            
            if isinstance(info["content"]["text"]["propositions"], list):

                info["content"]["text"]["propositions"] = [proposition for proposition in info["content"]["text"]["propositions"] if proposition != ""]

                documents = []
                for proposition in info["content"]["text"]["propositions"]:

                    print(proposition)

                    metadata = {
                    "raw_text"      : info["content"]["text"]["raw_text"],
                    "source"        : pdf.stream.name, 
                    "size"          : pdf.stream.size,
                    "chunk_size"    : self.chunk_size,
                    "chunk_overlap" : self.chunk_overlap,
                    "start_date"    : start_date,
                    "end_date"      : end_date,
                    "version"       : current_version + 1,
                    "latest"        : True
                    }

                    document = Document(page_content=str(proposition), metadata=metadata)
                    documents.append(document)

            else:
                documents = self.text_splitter.create_documents([str(info["content"]["text"]["propositions"])], [metadata])
                
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]

            if len(documents):
                self.database.add_documents(documents, ids=ids)
            
            if len(info["content"]["table"]):

                for table in info["content"]["table"]:

                    if isinstance(table["propositions"], list):

                        table["propositions"] = [proposition for proposition in table["propositions"] if proposition != ""]

                        documents = []
                        for proposition in table["propositions"]:

                            print(proposition)

                            metadata = {
                            "raw_text"      : table["raw_text"],
                            "source"        : pdf.stream.name, 
                            "size"          : pdf.stream.size,
                            "chunk_size"    : self.chunk_size,
                            "chunk_overlap" : self.chunk_overlap,
                            "start_date"    : start_date,
                            "end_date"      : end_date,
                            "version"       : current_version + 1,
                            "latest"        : True
                            }

                            document = Document(page_content=str(proposition), metadata=metadata)
                            documents.append(document)

                    else:
                        documents = self.text_splitter.create_documents([str(table["propositions"])], [metadata])

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

    def add_database(self, file):

        start_date = self.time_now.strftime('%Y/%m/%d %H:%M:%S')
        end_date   = self.time_end.strftime('%Y/%m/%d %H:%M:%S')

        pdf = PyPDF2.PdfReader(file)

        current_version = self.get_version_list(pdf.stream.name)[0]

        if current_version > 0:
            self.update_chroma(pdf.stream.name, start_date, False, current_version)

        self.add_chroma(pdf, start_date, end_date, current_version)

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

        current_version = self.get_version_list(PyPDF2.PdfReader(file).stream.name)[0]+1

        save_pdf_name = file.name.split('.')[0] + '_v' + str(current_version) + '.pdf'

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(file.getvalue())
            temp_pdf.seek(0)
            temp_pdf_name = temp_pdf.name

        shutil.move(temp_pdf_name, save_path+save_pdf_name)

#-----------------------------------------------------------------------------#

    def save_json(self, PDF_info):

        path = "output_json/"

        #current_version = self.get_version_list(PyPDF2.PdfReader(file).stream.name)[0]+1

        #save_json_name = file.name.split('.')[0] + '_v' + str(current_version) + '.json'

        json_name = PDF_info["PDF_name"] + '.json'

        with open(path+json_name, 'w', encoding='utf-8') as file:
            file.write(json.dumps(PDF_info, indent=4, ensure_ascii=False))

#-----------------------------------------------------------------------------#

    def load_json(self):

        path = "output_json/"

        #current_version = self.get_version_list(PyPDF2.PdfReader(file).stream.name)[0]+1

        #save_json_name = file.name.split('.')[0] + '_v' + str(current_version) + '.json'

        json_name = '員工請假管理程序(GEP-CW-2-07)V4.json'

        with open(path+json_name, 'r', encoding='utf-8') as file:
            PDF_info = json.load(file)

        return PDF_info

#-----------------------------------------------------------------------------#

    def load_markdown(self, pdf):

        path = "output_MD/"

        current_version = self.get_version_list(pdf.stream.name)[0]+1

        markdown_folder = pdf.stream.name.split('.')[0] + '_v' + str(current_version) + '/'

        markdown_name = pdf.stream.name.split('.')[0] + '_v' + str(current_version) + '.md'
        
        with open(path+markdown_folder+markdown_name, 'r', encoding="utf-8") as file:
            markdown = file.read()
        
        return markdown

#-----------------------------------------------------------------------------#

    def markdown_to_section(self, markdown, PDF_name):

        PDF_info = {
            "PDF_name" : PDF_name,
            "sections" :[]
        }

        section_list = re.split(r"(?=\n#{1,2} )", markdown)

        for section in section_list:

            section_info = {
                "title" : "",
                "content" : {
                    "text" : {
                        "raw_text" : "",
                        "propositions" : []
                    },
                    "table" : []
                },
                "image" : "",
            }

            match = re.match(r"(#{1,2} .+)\n([\s\S]*)", section.strip())
            if match:
                title   = match.group(1).strip()
                content = match.group(2).strip()

                table_list = [table[0] for table in re.findall(r'(\|.*\|\n(\|.*\|\n)+)', content)]

                for table in table_list:

                    table_info = {
                        "raw_text" : table,
                        "propositions" : []
                    }

                    section_info["content"]["table"].append(table_info)

                    content = content.replace(table, '')

                image_list = [image[0] for image in re.findall(r'(!\[(?P<image_title>[^\]]+)\]\((?P<image_path>[^\)"\s]+)\s*([^\)]*)\))', content)]

                section_info["image"] = image_list
                
                for image in image_list:
                    content = content.replace(image, '')

                section_info["title"] = title
                section_info["content"]["text"]["raw_text"] = content

                PDF_info["sections"].append(section_info)

        return PDF_info

#-----------------------------------------------------------------------------#

    def create_propositions(self, PDF_info):

        text_decompose_prompt  = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content="""
                將「內容」分解為清晰且簡單的命題，確保這些命題在脫離上下文的情況下也能被理解。

                1. 將複合句分割成簡單句，儘可能保留輸入中的原始措辭。

                2. 如果命名實體附帶描述性資訊，將這些資訊拆分為獨立的命題。

                3. 通過添加必要的修飾詞，使命題去脈絡化。例如，將代名詞（例如 "它"、"他"、"她"、"他們"、"這個"、"那個"）替換為它們所指代的完整實體名稱。

                4. 以 JSON 格式輸出結果，格式如下：: {"propositions": ["句子1", "句子2", "句子3"]}""" ),
            ChatMessage(
                role=MessageRole.USER,
                content="""
                請使用繁體中文分解以下內容:

                Title: 晨間運動的好處 

                Content: 開始一天時進行運動，對身體與心理健康會產生深遠的影響。

                晨間運動能提升精力、改善心情，並提高一天的專注力。

                身體活動會刺激內啡肽的釋放，減輕壓力並帶來幸福感。

                此外，早晨運動有助於建立規律的生活習慣，使保持持續性變得更容易。

                還能通過調節身體的自然時鐘來改善睡眠品質。

                無論是快走、瑜伽課，還是健身房運動，甚至只需要20到30分鐘，也能帶來顯著的效果。

                養成晨間運動的習慣，將體驗到更有成效且更健康的生活方式。

                這是一個小小的改變，卻能帶來顯著且持久的益處。"""),
            ChatMessage(
                role=MessageRole.ASSISTANT ,
                content="""
                propositions=[
                    '晨間運動的好處',
                    '開始一天時進行運動，能對你的身體與心理健康產生深遠的影響。',
                    '參與晨間運動可以提升你的精力、改善心情，並提高一天的專注力。',
                    '身體活動會刺激內啡肽的釋放，減輕壓力並促進幸福感。',
                    '此外，早晨運動有助於建立規律的生活習慣，使保持持續性變得更容易。',
                    '它還能通過調節身體的自然時鐘來改善睡眠品質。',
                    '無論是快走、瑜伽課還是健身房運動，甚至只需20到30分鐘，也能帶來顯著的效果。',
                    '養成晨間運動的習慣，將讓你體驗到更有成效且更健康的生活方式。',
                    '這是一個小小的改變，卻能帶來顯著且持久的益處。']"""),
            ChatMessage(
                role=MessageRole.USER,
                content="""
                請使用繁體中文分解以下內容:Title:{title} Content:{content}"""),
            ]

        table_decompose_prompt = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content="""
                分析表格並基於表格內容撰寫摘要。

                1. 提供清晰且簡潔的描述，描述每一行中的關鍵資訊，避免冗長或不必要的細節。

                2. 摘要需突出主要數據點與重要特徵，針對數值型數據，強調極值（例如最大值或最小值）、趨勢或明顯的異常。

                3. 若為分類型數據，則重點說明具代表性或高頻的類別。

                4. 若某些列的內容相似度極高，可合併處理並概括為一條命題。

                5. 可在摘要的末尾加入簡短的總結，概述整體表格的核心意義或結論，例如「此表格展示了...的主要趨勢」。

                6. 以 JSON 格式輸出結果，格式如下：: {"propositions": ["句子1", "句子2", "句子3"]}""" ),
            ChatMessage(
                role=MessageRole.USER,
                content="""
                請使用繁體中文分析以下表格並基於表格內容撰寫摘要:

                Table:| CPU                          | Pentium 4 1.8 GHz         |
                      |------------------------------|---------------------------|
                      | OS                           | Redhat 7.3 (Linux 2.4.18) |
                      | Main-memory size             | 1 GB RDRAM                |
                      | Trace Cache                  | 12 K micro-ops            |
                      | ITLB                         | 128 entries               |
                      | L1 data cache size           | 16 KB                     |
                      | L1 data cacheline size       | 64 bytes                  |
                      | L2 cache size                | 256 KB                    |
                      | L2 cacheline size            | 128 bytes                 |
                      | Trace Cache miss latency     | > 27 cycles               |
                      | L1 data miss latency         | 18 cycles                 |
                      | L2 miss latency              | 276 cycles                |
                      | Branch misprediction latency | > 20 cycles               |
                      | Hardware prefetch            | Yes                       |
                      | C Compiler                   | GNU's gcc 3.2             |"""),
            ChatMessage(
                role=MessageRole.ASSISTANT ,
                content="""
                propositions=[
                    '此表格提供了一個計算系統的規格，詳細列出 CPU、記憶體、快取及效能特性：',
                    'CPU：使用 Pentium 4 1.8 GHz 處理器。',
                    '操作系統：運行於 Redhat 7.3，採用 Linux 核心版本 2.4.18。',
                    '記憶體：配備 1 GB 的 RDRAM。',
                    '指令追蹤快取（Trace Cache）：容量為 12K 微操作（micro-ops）。',
                    '指令 TLB：包含 128 個條目。',
                    'L1 資料快取：大小為 16 KB，快取線大小為 64 字節。',
                    'L2 快取：大小為 256 KB，快取線大小為 128 字節。',
                    '指令追蹤快取未命中：延遲超過 27 個週期。',
                    'L1 資料快取未命中：延遲為 18 個週期。',
                    'L2 快取未命中：延遲為 276 個週期。',
                    '分支預測錯誤：懲罰超過 20 個週期。',
                    '硬體預取（Hardware Prefetch）：已啟用。',
                    '編譯器：使用 GNU 的 gcc 版本 3.2。']"""),
            ChatMessage(
                role=MessageRole.USER,
                content="""
                請使用繁體中文分析以下表格並基於表格內容撰寫摘要:Table:{table}"""),
            ]

        text_decompose_template  = ChatPromptTemplate(message_templates=text_decompose_prompt)

        table_decompose_template = ChatPromptTemplate(message_templates=table_decompose_prompt)

        for info in PDF_info['sections']:
            
            text_messages = text_decompose_template.format_messages(title=info['title'], content=info['content']['text']['raw_text'])
            
            text_response = self.llm.chat(text_messages)

            try:
                text_response_json = json.loads(text_response.message.content)
                for index, proposition in enumerate(text_response_json["propositions"], 1):
                    info['content']['text']['propositions'].append(proposition)

            except:
                info['content']['text']['propositions'] = text_response.message.content
            
            if len(info['content']['table']):
                for table_info in info['content']['table']:
                
                    table_messages = table_decompose_template.format_messages(table=table_info['raw_text'])

                    table_response = self.llm.chat(table_messages)

                    try:
                        table_response_json = json.loads(table_response.message.content)
                        for index, proposition in enumerate(table_response_json["propositions"], 1):
                            table_info['propositions'].append(proposition)

                    except:
                        table_info['propositions'] = table_response.message.content

        return PDF_info
