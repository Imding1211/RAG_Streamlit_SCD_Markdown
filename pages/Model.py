
from database_controller import DatabaseController
from setting_controller import SettingController
from ollama import Client
import streamlit as st
import pandas as pd
import humanize
import ollama

#=============================================================================#

SettingController        = SettingController()
selected_llm             = SettingController.setting['llm_model']['selected']
llm_models               = SettingController.setting['llm_model']['options']
selected_llm_index       = llm_models.index(selected_llm)
selected_embedding       = SettingController.setting['embedding_model']['selected']
embedding_models         = SettingController.setting['embedding_model']['options']
selected_embedding_index = embedding_models.index(selected_embedding)
client                   = Client(host=SettingController.setting['server']['base_url'])

DatabaseController       = DatabaseController()
embedding_model_disabled = True if len(DatabaseController.calculate_existing_ids()) != 0 else False

#=============================================================================#

def change_llm_model():
	SettingController.change_llm_model(st.session_state.llm_model)

#-----------------------------------------------------------------------------#

def change_embedding_model():
	SettingController.change_embedding_model(st.session_state.embedding_model)

#-----------------------------------------------------------------------------#

@st.dialog("新增語言模型")
def add_llm_model():
    llm_model = st.text_input("輸入模型名稱")
    if st.button("新增"):
        SettingController.add_llm_model(llm_model)
        st.rerun()

#-----------------------------------------------------------------------------#

@st.dialog("新增嵌入模型")
def add_embedding_model():
    llm_model = st.text_input("輸入模型名稱")
    if st.button("新增"):
        SettingController.add_embedding_model(llm_model)
        st.rerun()

#-----------------------------------------------------------------------------#

@st.dialog("移除語言模型")
def remove_llm_model():
    llm_model = st.selectbox("選擇模型", llm_models)
    if st.button("移除"):
        SettingController.remove_llm_model(llm_model)
        st.rerun()

#-----------------------------------------------------------------------------#

@st.dialog("移除嵌入模型")
def remove_embedding_model():
    llm_model = st.selectbox("選擇模型", embedding_models)
    if st.button("移除"):
        SettingController.remove_embedding_model(llm_model)
        st.rerun()

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

if "selected_LLM_model" not in st.session_state:
    st.session_state.selected_LLM_model = ""

if "selected_embedding_model" not in st.session_state:
    st.session_state.selected_embedding_model = ""

#=============================================================================#

st.title("模型")

#-----------------------------------------------------------------------------#

st.selectbox("請選擇語言模型", 
	llm_models, 
	on_change=change_llm_model, 
	key='llm_model', 
	index=selected_llm_index
	)

st.selectbox("請選擇嵌入模型", 
	embedding_models, 
	on_change=change_embedding_model, 
	key='embedding_model', 
	index=selected_embedding_index,
	disabled=embedding_model_disabled
	)

embedding_warning = st.empty()

if embedding_model_disabled:
	embedding_warning.warning('資料庫有資料時無法更換嵌入模型。', icon="⚠️")

#-----------------------------------------------------------------------------#

st.divider()

st.header("Ollama 列表")

col1, col2 = st.columns([8.5, 1.5])

df_info = ollama_to_dataframe(client)

col1.dataframe(
	df_info,
	column_config=info_config,
    use_container_width=True,
    hide_index=True
    )

if col2.button("新增語言模型"):
	add_llm_model()

if col2.button("移除語言模型"):
	remove_llm_model()

if col2.button("新增嵌入模型"):
	add_embedding_model()

if col2.button("移除嵌入模型"):
	remove_embedding_model()



