
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters import MarkdownTextSplitter
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core import ChatPromptTemplate
from llama_index.llms.ollama import Ollama

from setting_controller import SettingController

from ollama import Client
from pathlib import Path

import pandas as pd
import chromadb
import tempfile
import datetime
import humanize
import PyPDF2
import shutil
import base64
import uuid
import json
import re
import os

#=============================================================================#

class DatabaseController():

    def __init__(self):

        chromadb.api.client.SharedSystemClient.clear_system_cache()

        self.SettingController = SettingController()
        self.chunk_size        = self.SettingController.setting['text_splitter']['chunk_size']
        self.chunk_overlap     = self.SettingController.setting['text_splitter']['chunk_overlap']
        self.base_url          = self.SettingController.setting['server']['base_url']

        self.database_name      = self.SettingController.setting['database']['selected']
        self.database_path      = self.SettingController.setting['database'][self.database_name]['path']
        self.database_embedding = self.SettingController.setting['database'][self.database_name]['embedding_model']

        self.database = Chroma(
            persist_directory  = self.database_path, 
            embedding_function = OllamaEmbeddings(base_url=self.base_url, model=self.database_embedding)
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

        self.propositions_llm = Ollama(
            model='llama3.2:3b', 
            request_timeout=600.0, 
            base_url=self.base_url, 
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
            'title'         : [meta['title'] for meta in data['metadatas']],
            'raw_text'      : [meta['raw_text'] for meta in data['metadatas']],
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

        PDF_name = pdf.stream.name.split('.')[0]

        print(PDF_name)

        markdown = self.load_markdown(PDF_name, current_version)

        PDF_info = self.markdown_to_section(PDF_name, markdown, current_version)

        PDF_info = self.create_propositions(PDF_name, PDF_info, current_version)

        #PDF_info = self.load_json(PDF_name, current_version)
        
        for info in PDF_info["sections"]:

            metadata = {
                "title"         : info["title"],
                "raw_text"      : info["raw_text"],
                "image_text"    : info["image_text"],
                "source"        : pdf.stream.name, 
                "size"          : pdf.stream.size,
                "chunk_size"    : "",
                "chunk_overlap" : "",
                "start_date"    : start_date,
                "end_date"      : end_date,
                "version"       : current_version + 1,
                "latest"        : True
            }

            documents = self.section_to_documents(info, metadata)

            ids = [str(uuid.uuid4()) for _ in range(len(documents))]

            if len(documents):
                self.database.add_documents(documents, ids=ids)

        print("Done!!")

#-----------------------------------------------------------------------------#

    def update_chroma(self, source_name, date, latest, current_version):

        old_documents = self.database.get(where={"source": source_name})

        new_documents = []
        new_ids       = []

        for ids, old_metadata, old_document in zip(old_documents["ids"], old_documents['metadatas'], old_documents['documents']):

            if old_metadata['version'] == current_version:

                updated_metedata = {
                    "title"         : old_metadata["title"],
                    "raw_text"      : old_metadata["raw_text"],
                    "image_text"    : old_metadata["image_text"],
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

    def add_database(self, files):

        start_date = self.time_now.strftime('%Y/%m/%d %H:%M:%S')
        end_date   = self.time_end.strftime('%Y/%m/%d %H:%M:%S')

        for file in files:

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

    def markdown_to_section(self, PDF_name, markdown, current_version):

        meta = self.load_meta(PDF_name, current_version)

        headers = ["#"*hd["level"] + " " + hd["title"] for hd in meta["computed_toc"] if hd["level"] <= 2]

        PDF_info = {
            "PDF_name" : PDF_name,
            "sections" :[]
        }

        section_id = 1

        table_list = [table[0] for table in re.findall(r'(\|.*\|\n(\|.*\|\n)+)', markdown)]

        for index, table in enumerate(table_list):

            section_info = {
                "ID"           : section_id,
                "type"         : "Table",
                "title"        : f"Table:{index+1}",
                "raw_text"     : table,
                "propositions" : [],
                "image_text"   : "",
                "image"        : []
            }

            markdown = markdown.replace(table, '')

            PDF_info["sections"].append(section_info)
            section_id += 1

        pattern      = '|'.join(re.escape(header) for header in headers)
        content_list = re.split(f'(?i)({pattern})', markdown)

        for index in range(1, len(content_list), 2):

            title    = content_list[index].split(' ', maxsplit=1)[-1].strip()
            raw_text = content_list[index + 1].strip() if index + 1 < len(content_list) else ""

            section_info = {
                "ID"           : section_id,
                "type"         : "Text",
                "title"        : title,
                "raw_text"     : raw_text,
                "propositions" : [f"Title:{title}"],
                "image_text"   : raw_text,
                "image"        : []
            }

            image_list = [image for image in re.findall(r'(!\[(?P<image_title>[^\]]+)\]\((?P<image_path>[^\)"\s]+)\s*([^\)]*)\))', raw_text)]

            if len(image_list):

                for image in image_list:

                    image_md   = image[0]
                    image_name = image[1]
                    image_path = f'storage/{self.database_name}/output_MD/{PDF_name}_v{current_version+1}/{image_name}'
                    
                    image_info = {
                        "name" : "",
                        "path" : ""
                    }

                    image_info["name"] = image_name
                    image_info["path"] = image_path

                    section_info["image"].append(image_info)

                    img_bytes = Path(image_path).read_bytes()
                    encoded   = base64.b64encode(img_bytes).decode()
                    img_html  = f'<img src="data:image/png;base64,{encoded}" alt="{image_name}" style="max-width: 100%;">'

                    section_info["raw_text"]   = section_info["raw_text"].replace(image_md, "")
                    section_info["image_text"] = section_info["image_text"].replace(image_md, img_html)

            else:
                section_info["image_text"] = ""

            PDF_info["sections"].append(section_info)
            section_id += 1

        self.save_json(PDF_name, PDF_info, current_version)

        return PDF_info

#-----------------------------------------------------------------------------#

    def create_propositions(self, PDF_name, PDF_info, current_version):

        #decompose_prompt = self.load_decompose_prompt("decompose_prompt.json")

        text_decompose_prompt  = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content="""
                    將「內容」分解為清晰且簡單的命題，確保這些命題在脫離上下文的情況下也能被理解。

                    1. 將複合句分割成簡單句，儘可能保留輸入中的原始措辭。

                    2. 如果命名實體附帶描述性資訊，將這些資訊拆分為獨立的命題。

                    3. 通過添加必要的修飾詞，使命題去脈絡化。例如，將代名詞（例如 "它"、"他"、"她"、"他們"、"這個"、"那個"）替換為它們所指代的完整實體名稱。

                    4. 以 JSON 格式輸出結果，格式如下：: {"propositions": ["句子1", "句子2", "句子3"]}"""),
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
                        '這是一個小小的改變，卻能帶來顯著且持久的益處']"""),
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

        for info in PDF_info["sections"]:

            if info["type"] == "Table":
                messages = table_decompose_template.format_messages(table=info["raw_text"])

            elif info["type"] == "Text":
                messages = text_decompose_template.format_messages(title=info["title"], content=info["raw_text"])
            
            response = self.propositions_llm.chat(messages)

            try:
                text_response_json = json.loads(response.message.content)

                for index, proposition in enumerate(text_response_json["propositions"], 1):
                    proposition = re.sub(r"\s+", "", proposition)
                    if len(proposition) and proposition not in ['晨間運動的好處', '開始一天時進行運動，能對你的身體與心理健康產生深遠的影響。', '參與晨間運動可以提升你的精力、改善心情，並提高一天的專注力。', '身體活動會刺激內啡肽的釋放，減輕壓力並促進幸福感。', '此外，早晨運動有助於建立規律的生活習慣，使保持持續性變得更容易。', '它還能通過調節身體的自然時鐘來改善睡眠品質。', '無論是快走、瑜伽課還是健身房運動，甚至只需20到30分鐘，也能帶來顯著的效果。', '養成晨間運動的習慣，將讓你體驗到更有成效且更健康的生活方式。', '這是一個小小的改變，卻能帶來顯著且持久的益處']:
                        info["propositions"].append(proposition)
                        print(proposition)

                print("Formatted output successful.")

            except:
                info["propositions"] = response.message.content

                print(response.message.content)

                print("Formatted output failed.")

        self.save_json(PDF_name, PDF_info, current_version)

        return PDF_info

#-----------------------------------------------------------------------------#

    def section_to_documents(self, info, metadata):

        if isinstance(info["propositions"], list):

            info["propositions"] = [proposition for proposition in info["propositions"] if proposition.strip()]

            documents = []
            for proposition in info["propositions"]:
                document = Document(page_content=str(proposition), metadata=metadata)
                documents.append(document)

        else:

            metadata["chunk_size"]    = self.chunk_size
            metadata["chunk_overlap"] = self.chunk_overlap

            documents = self.text_splitter.create_documents([str(info["propositions"])], [metadata])

        return documents

#-----------------------------------------------------------------------------#

    def save_PDF(self, files):

        for file in files:

            save_path = f"storage/{self.database_name}/save_PDF/"
            temp_path = f"temp_PDF/"

            current_version = self.get_version_list(PyPDF2.PdfReader(file).stream.name)[0]+1

            save_pdf_name = file.name.split('.')[0] + '_v' + str(current_version) + '.pdf'

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                temp_pdf.write(file.getvalue())
                temp_pdf.seek(0)
                temp_pdf_name = temp_pdf.name

            shutil.move(temp_pdf_name, save_path+save_pdf_name)
            shutil.copy(save_path+save_pdf_name, temp_path)

#-----------------------------------------------------------------------------#

    def remove_temp_PDF(self, folder_path):
        
        if not os.path.exists(folder_path):
            print(f"資料夾 {folder_path} 不存在。")
            return
        
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) and filename.lower().endswith('.pdf'):
                    os.remove(file_path)
                    print(f"已刪除檔案: {file_path}")
            except Exception as e:
                print(f"無法刪除檔案 {file_path}，錯誤: {e}")

#-----------------------------------------------------------------------------#

    def save_json(self, PDF_name, PDF_info, current_version):

        path = f"storage/{self.database_name}/output_json/"

        save_json_name = PDF_name + '_v' + str(current_version+1) + '.json'

        with open(path+save_json_name, 'w', encoding='utf-8') as file:
            file.write(json.dumps(PDF_info, indent=4, ensure_ascii=False))

#-----------------------------------------------------------------------------#

    def load_json(self, json_name, current_version):

        path = f"storage/{self.database_name}/output_json/"

        load_json_name = json_name + '_v' + str(current_version+1) + '.json'

        with open(path+load_json_name, 'r', encoding='utf-8') as file:
            PDF_info = json.load(file)

        return PDF_info

#-----------------------------------------------------------------------------#

    def load_meta(self, PDF_name, current_version):

        path = f"storage/{self.database_name}/output_MD/"

        meta_folder = PDF_name + '_v' + str(current_version+1) + '/'

        meta_name = PDF_name + '_v' + str(current_version+1) + '_meta.json'
        
        with open(path+meta_folder+meta_name, 'r', encoding="utf-8") as file:
            meta = json.load(file)
        
        return meta

#-----------------------------------------------------------------------------#

    def load_markdown(self, PDF_name, current_version):

        path = f"storage/{self.database_name}/output_MD/"

        markdown_folder = PDF_name + '_v' + str(current_version+1) + '/'

        markdown_name = PDF_name + '_v' + str(current_version+1) + '.md'
        
        with open(path+markdown_folder+markdown_name, 'r', encoding="utf-8") as file:
            markdown = file.read()
        
        return markdown

#-----------------------------------------------------------------------------#

    def load_decompose_prompt(self, file_name):

        with open(file_name, 'r', encoding='utf-8') as file:
            decompose_prompt = json.load(file)

        return decompose_prompt