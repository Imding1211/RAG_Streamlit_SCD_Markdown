
from database_controller import DatabaseController
from setting_controller import SettingController

from ollama import Client

import streamlit as st
import pandas as pd
import humanize

#=============================================================================#

SettingController = SettingController()
client            = Client(host=SettingController.setting['server']['base_url'])

DatabaseController       = DatabaseController()
embedding_model_disabled = True if len(DatabaseController.calculate_existing_ids()) != 0 else False

#=============================================================================#

def change_llm_model():
    SettingController.change_llm_model(st.session_state.llm_model)

#-----------------------------------------------------------------------------#

def change_embedding_model():
    SettingController.change_embedding_model(st.session_state.embedding_model)

#-----------------------------------------------------------------------------#

def ollama_to_dataframe(client):

    json_info = client.list()

    df_info = pd.DataFrame({
        'name'              : [info['name'] for info in json_info['models']],
        'model'             : [info['model'] for info in json_info['models']],
        'date'              : [info['modified_at'].split("T")[0]+" "+info['modified_at'].split("T")[1].split(".")[0] for info in json_info['models']],
        'size'              : [humanize.naturalsize(info['size'], binary=True) for info in json_info['models']],
        'format'            : [info['details']['format'] for info in json_info['models']],
        'family'            : [info['details']['family'] for info in json_info['models']],
        'parameter_size'    : [info['details']['parameter_size'] for info in json_info['models']],
        'quantization_level': [info['details']['quantization_level'] for info in json_info['models']]
        })

    return df_info

#=============================================================================#

df_info              = ollama_to_dataframe(client)
list_llm_model       = df_info[df_info["family"] != "bert"]["name"].tolist()
list_embedding_model = df_info[df_info["family"] == "bert"]["name"].tolist()
selected_llm         = SettingController.setting['llm_model']['selected']
selected_embedding   = SettingController.setting['embedding_model']['selected']

#=============================================================================#

st.set_page_config(layout="wide")

info_config = {
    "name": st.column_config.TextColumn(
        "建立名稱", 
        help="建立模型時的名稱", 
        max_chars=100, 
        width="small"
    ),
    "model": st.column_config.TextColumn(
        "模型名稱", 
        help="模型名稱", 
        max_chars=100, 
        width="small"
    ),
    "date": st.column_config.TextColumn(
        "建立日期", 
        help="模型建立日期", 
        max_chars=100, 
        width="small"
    ),
    "size": st.column_config.TextColumn(
        "模型大小", 
        help="模型大小", 
        max_chars=100, 
        width="small"
    ),
    "format": st.column_config.TextColumn(
        "模型格式", 
        help="模型格式", 
        max_chars=100, 
        width="small"
    ),
    "family": st.column_config.TextColumn(
        "模型家族", 
        help="模型家族", 
        max_chars=100, 
        width="small"
    ),
    "parameter_size": st.column_config.TextColumn(
        "模型參數量", 
        help="模型參數量", 
        max_chars=100, 
        width="small"
    ),
    "quantization_level": st.column_config.TextColumn(
        "量化等級", 
        help="量化等級", 
        max_chars=100, 
        width="small"
    ),
}

#=============================================================================#

st.title("模型")

#-----------------------------------------------------------------------------#

llm_warning       = st.empty()
embedding_warning = st.empty()

if selected_llm in list_llm_model:
    index_llm = list_llm_model.index(selected_llm)
else:
    llm_warning.error(f'{selected_llm}語言模型不存在，請重新選擇。', icon="🚨")
    index_llm = None

if selected_embedding in list_embedding_model:
    index_embedding = list_embedding_model.index(selected_embedding)
else:
    embedding_warning.error(f'{selected_embedding}嵌入模型不存在，請重新選擇。', icon="🚨")
    index_embedding = None

st.selectbox("請選擇語言模型", 
    list_llm_model, 
    on_change=change_llm_model, 
    key='llm_model', 
    index=index_llm,
    placeholder='語言模型不存在，請重新選擇。'
    )

st.selectbox("請選擇嵌入模型", 
    list_embedding_model, 
    on_change=change_embedding_model, 
    key='embedding_model', 
    index=index_embedding,
    disabled=embedding_model_disabled,
    placeholder='嵌入模型不存在，請重新選擇。'
    )

embedding_warning = st.empty()

if embedding_model_disabled:
    embedding_warning.warning('資料庫有資料時無法更換嵌入模型。', icon="⚠️")

#-----------------------------------------------------------------------------#

st.divider()

st.header("Ollama 模型列表")

st.subheader("語言模型列表")

st.dataframe(
    df_info[df_info["family"] != "bert"],
    column_config=info_config,
    use_container_width=True,
    hide_index=True
    )

st.subheader("嵌入模型列表")

st.dataframe(
    df_info[df_info["family"] == "bert"],
    column_config=info_config,
    use_container_width=True,
    hide_index=True
    )
