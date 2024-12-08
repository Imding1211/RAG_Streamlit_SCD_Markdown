import pandas as pd

# 原始表格資料
data = """
| 假別      |      | 給假天數   | 給假原因                | 證明文件     | 其他說明                    |
|-----------|------|------------|-------------------------|--------------|-----------------------------|
| 特休假    | 3 日 |            | 滿 6 個月未滿 1 年      |              | 1.期間薪資照給。            |
|           | 7 日 |            | 滿 1 年未滿 2 年        |              | 2.最少請假單位為 0.5 小時。 |
|           | 10   | 日         | 滿 2 年未滿 3 年        |              | 3.特休假由員工自行排定。但  |
|           | 14   | 日         | 滿 3 年未滿 5 年        |              | 部門主管基於作業執行之急    |
|           | 15   | 日         | 滿 5 年未滿 10 年       |              | 迫需求或員工因個人因素,雙  |
|           |      | 16~30 日   | 滿 10 年以上,每滿 1 年 |              | 方得協商調整。              |
| 產假(含例 | 56   | 日         | 正常分娩前後。          | 醫院開立之生 | 1.正常分娩或妊娠滿三個月    |
| 假、休息  |      |            |                         | 產證明書或出 | 以上流產,如任職滿六個月者  |
|           | 28   | 日         | 妊娠三個月以上流產者。  |              |                             |
| 日、休假  |      |            |                         | 生證明書或戶 | 給全薪,未滿六個月者給半    |
| 日)       | 7 日 |            | 妊娠二個月以上未滿三    | 籍謄本。     | 薪;但若妊娠未滿三個月流    |
|           |      |            | 個月流產者。            |              | 產,則期間不給薪。          |
"""

# 分割點
split_point = "| 產假(含例"

# 分割資料
table1_raw, table2_raw = data.split(split_point)
table2_raw = split_point + table2_raw  # 恢復第二部分標題

# 解析表格為 DataFrame
def parse_table(raw_data):
    rows = [row.strip("|").split("|") for row in raw_data.strip().split("\n") if row.strip()]
    header = rows[0]
    data_rows = rows[1:]
    return pd.DataFrame(data_rows, columns=[col.strip() for col in header])

# 建立兩個 DataFrame
table1 = parse_table(table1_raw)
table2 = parse_table(table2_raw)

# 輸出結果
print("Table 1:")
print(table1)
print("\nTable 2:")
print(table2)