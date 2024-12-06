def split_text_by_headers(text, headers):
    # 結果字典，用於存儲每個標題對應的內容
    result = {}
    
    # 遍歷標題列表
    for header in headers:
        # 找出每個標題在原文中的開始和結束位置
        start_index = text.find(f"## {header}")
        
        # 如果找不到標題，跳過
        if start_index == -1:
            continue
        
        # 找下一個標題的位置，作為當前段落的結束
        next_header_index = text.find("##", start_index + len(header) + 3)
        
        # 如果沒有找到下一個標題，則截取到文本結尾
        if next_header_index == -1:
            segment = text[start_index:].strip()
        else:
            segment = text[start_index:next_header_index].strip()
        
        # 分離標題和內容
        header_line = segment.split('\n')[0]
        content = '\n'.join(segment.split('\n')[1:]).strip()
        
        # 儲存段落
        result[header] = {
            'header': header_line.replace('## ', '').strip(),
            'content': content
        }
    
    return result

# 您的原始文本
text = '''## Window Jump Machine
- Credential
- Account: administrator - Password: Mitac@123 Hua    TCY 黃向偉
## Mariadb
- Credential
- Account: root - Password: Mitac@123
## Ms Sql
- Credential
- Account: mitacmssql - Password: mitac@12345
# 01_Software Installation And Setting
# Install The Following Softwares On Local Machine
#### Mitac
- Enable all the controller service
- DM/health_dimensions
- Enable all the controller service
- DM/user_info_dms
- Enable all the controller service
- DM/health_dms
- Enable all the controller service
- DM/health_dms/dm_health_record
- Enable all the controller service
- Device_dev/DW
- Enable all the controller service
- DM/library_dms
- Enable all the controller service
- DM/library_dms/dms_book
- Enable all the controller service
- DM/library_dms/dms_transaction
- Enable all the controller service
- Device_dev
- Enable all the controller service
- Device_dev/STG
- Enable all the controller service'''

# 標題列表
header = ["Window Jump Machine", "Mariadb", "Ms Sql", "Mitac"]

# 調用函數
result = split_text_by_headers(text, header)

# 打印結果
for key, value in result.items():
    print(f"Header: {value['header']}")
    print(f"Content:\n{value['content']}\n")