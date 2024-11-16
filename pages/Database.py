
from database_controller import DatabaseController
from setting_controller import SettingController
import streamlit as st
import subprocess
import tempfile
import sys

#=============================================================================#

SettingController = SettingController()
database_path     = SettingController.setting['paramater']['database']

DatabaseController = DatabaseController()

#=============================================================================#

st.set_page_config(layout="wide")

event_config = {
    "source": st.column_config.TextColumn(
        "資料", 
        help="資料名稱", 
        max_chars=100, 
        width="small"
    ),
    "size": st.column_config.TextColumn(
        "大小", 
        help="資料大小", 
        max_chars=100, 
        width="small"
    ),
    "chunk_size": st.column_config.TextColumn(
        "切割長度", 
        help="文章切割長度", 
        max_chars=100, 
        width="small"
    ),
    "chunk_overlap": st.column_config.TextColumn(
        "重疊長度", 
        help="區塊重疊長度", 
        max_chars=100, 
        width="small"
    ),
    "start_date": st.column_config.TextColumn(
        "開始時間", 
        help="資料開始時間", 
        max_chars=100, 
        width="small"
    ),
    "end_date": st.column_config.TextColumn(
        "結束時間", 
        help="資料結束時間", 
        max_chars=100, 
        width="small"
    ),
    "version": st.column_config.TextColumn(
        "版本", 
        help="資料版本", 
        max_chars=100, 
        width="small"
    ),
    "latest": st.column_config.TextColumn(
        "最新資料", 
        help="資料內容是否為最新", 
        max_chars=100, 
        width="small"
    ),
}

selected_config = {
    "source": st.column_config.TextColumn(
        "資料", 
        help="資料名稱", 
        max_chars=100, 
        width="small"
    ),
    "documents": st.column_config.TextColumn(
        "內容", 
        help="資料內容", 
        max_chars=100, 
        width="small"
    ),
    "start_date": st.column_config.TextColumn(
        "開始時間", 
        help="資料開始時間", 
        max_chars=100, 
        width="small"
    ),
    "end_date": st.column_config.TextColumn(
        "結束時間", 
        help="資料結束時間", 
        max_chars=100, 
        width="small"
    ),
    "version": st.column_config.TextColumn(
        "版本", 
        help="資料版本", 
        max_chars=100, 
        width="small"
    ),
    "latest": st.column_config.TextColumn(
        "是否為最新資料", 
        help="資料內容是否為最新", 
        max_chars=100, 
        width="small"
    ),
}

#=============================================================================#

st.title("資料庫")

#-----------------------------------------------------------------------------#

st.write("正在使用的資料庫：" + database_path.split('/')[-1])

#-----------------------------------------------------------------------------#

database_status = st.empty()

files = st.file_uploader(
    "請選擇要上傳的PDF", 
    type="pdf", 
    accept_multiple_files=True, 
    label_visibility="visible",
    )

#-----------------------------------------------------------------------------#

col1, col2 = st.columns([9,1])

if col2.button("更新"):

    with database_status.status('資料處理中...', expanded=True) as update_status:

        for file in files:

            DatabaseController.save_PDF(file)

            st.write(f"{file.name}上傳完成。")

        st.write("PDF解析中...")

        #subprocess.run([f"{sys.executable}", "wait.py"])
        subprocess.run([f"{sys.executable}", "convert_controller.py"])

        for file in files:
            DatabaseController.add_database(file)

        update_status.update(label="資料處理完成!", state="complete", expanded=False)

df = DatabaseController.database_to_dataframes()

df_event = df.loc[df.groupby(['source', 'start_date'])['size'].idxmax(), ['source', 'size', 'chunk_size', 'chunk_overlap', 'start_date', 'end_date', 'version', 'latest']]

df_event = df_event.sort_values(by='start_date', ascending=False)

event = col1.dataframe(
    df_event,
    column_config=event_config,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="multi-row",
    )

select_id = event.selection.rows

df_selected = df_event.iloc[select_id][['source', 'start_date']]

df_result = df.merge(df_selected, on=['source', 'start_date'])

#-----------------------------------------------------------------------------#

st.divider()

st.header("資料預覽")

st.dataframe(
    df_result[['source', 'documents', 'start_date', 'end_date', 'version', 'latest']],
    column_config=selected_config,
    use_container_width=True, 
    hide_index=True
    )

if col2.button('刪除'):

    with database_status.status('資料刪除中...', expanded=True) as remove_status:

        delete_source = df_result[['source', 'version']].values.tolist()
        delete_source = list(map(list, set(map(tuple, delete_source))))
        DatabaseController.rollback_database(delete_source)
          
        delete_ids = df_result['ids'].values.tolist()
        DatabaseController.clear_database(delete_ids)

        remove_status.update(label="資料刪除完成!", state="complete", expanded=False)

    st.rerun()

