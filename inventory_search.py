import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import openpyxl

def login(base_url, email, password):
    login_url = base_url + "/login"
    login_data = {
        "userEmail": email,
        "password": password
    }
    session = requests.Session()
    
    try:
        response = session.post(login_url, data=login_data)
        if response.status_code == 200:
            return session
        else:
            print("Login failed")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Login error: {e}")
        return None

def search_inventory(search_term, session):
    if not session:
        return None
        
    base_url = "http://108.211.177.149:3000"
    search_url = base_url + "/searchInventory"
    
    params = {
        "searchTerm": search_term
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        response = session.get(search_url, params=params, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取最终库存数量
            final_stock = None
            
            # 先找到包含 "Qt." 的行
            qt_rows = soup.find_all('td', string=lambda x: x and 'Qt.' in x)
            if qt_rows:
                for qt_cell in qt_rows:
                    qt_row = qt_cell.find_parent('tr')
                    if qt_row:
                        # 获取下一行
                        next_row = qt_row.find_next_sibling('tr')
                        if next_row:
                            # 获取第三列的值
                            cells = next_row.find_all('td')
                            if len(cells) >= 3:
                                final_stock = cells[2].text.strip()
                                break
            
            # 如果上面的方法没找到，尝试原来的方法
            if not final_stock:
                rows = soup.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 8:
                        if search_term in row.text:
                            final_stock = cells[7].text.strip()
                            break
            
            # 获取所有位置信息
            locations = set()
            location_details = {}  # 存储位置和对应的数量信息
            
            # 处理所有位置信息
            all_cells = soup.find_all('td')
            for cell in all_cells:
                text = cell.text.strip()
                # 通用的位置识别条件
                if (text and 
                    '(' in text and
                    'Move Inventory to:' not in text and
                    'Order' not in text and
                    'Processed' not in text and
                    not text.isdigit() and
                    'cm' not in text.lower() and 
                    'inch' not in text.lower() and
                    not text.upper().startswith('MTIPS')):
                    
                    # 解析位置和数量
                    location_parts = text.split('(')
                    base_location = location_parts[0].strip()
                    quantity = location_parts[1].rstrip(')') if len(location_parts) > 1 else ''
                    
                    if base_location:
                        normalized_location = base_location.upper().strip()
                        base_name = normalized_location.split('-')[0] if '-' in normalized_location else normalized_location
                        
                        # 保存位置和数量信息
                        if base_name not in location_details or (
                            '-' in normalized_location and 
                            len(normalized_location) > len(location_details[base_name]['location'])
                        ):
                            location_details[base_name] = {
                                'location': normalized_location,
                                'quantity': quantity
                            }
            
            # 收集最终的位置列表（包含数量信息）
            location_quantities = {}  # 用于存储每个位置的总数量
            
            for cell in all_cells:
                text = cell.text.strip()
                for base_name, details in location_details.items():
                    if text.upper().startswith(details['location']):
                        location_parts = text.split('(')
                        base_location = location_parts[0].strip()
                        
                        # 提取数量并转换为整数
                        quantity_str = location_parts[1].rstrip(')') if len(location_parts) > 1 else '0'
                        try:
                            quantity = int(quantity_str) if quantity_str.isdigit() else 0
                        except ValueError:
                            quantity = 0
                        
                        # 累加相同位置的数量
                        if base_location in location_quantities:
                            location_quantities[base_location] += quantity
                        else:
                            location_quantities[base_location] = quantity
                        break
            
            # 将合并后的位置和数量转换为最终列表
            final_locations = []
            for location, total_quantity in location_quantities.items():
                # 只有当数量大于0时才添加数量信息
                if total_quantity > 0:
                    final_locations.append(f"{location}({total_quantity})")
                else:
                    final_locations.append(f"{location}")
            
            return {
                'final_stock': final_stock,
                'locations': sorted(list(set(final_locations)), key=str.upper)  # 去重并按大写字母排序
            }
                
    except requests.exceptions.RequestException as e:
        print(f"Search request error: {e}")
        return None

def get_inventory_info(sku_list):
    """
    获取多个SKU的库存信息
    
    Args:
        sku_list: SKU列表
        
    Returns:
        包含每个SKU信息的列表
    """
    base_url = "http://108.211.177.149:3000"
    email = "andyxiongzheng@gmail.com"
    password = "123456"
    
    # 登录获取session
    session = login(base_url, email, password)
    if not session:
        return []
    
    results = []
    for sku in sku_list:
        inventory_info = search_inventory(sku, session)
        if inventory_info:
            locations = []
            exclude_values = {'cm', 'inch', '', ' '}
            for location in inventory_info['locations']:
                if (location not in exclude_values and
                    'cm' not in location and
                    'inch' not in location and
                    'outbound' not in location.lower() and  # 排除outbound
                    location != sku):
                    locations.append(location)
            
            # 如果没有位置信息，显示none
            location_text = '\n'.join(locations) if locations else 'none'
            
            results.append({
                'id': sku,
                'final_amount': inventory_info['final_stock'],
                'location_list': location_text
            })
    
    return results

def export_to_excel(results, filename=None):
    """
    将结果导出到Excel文件，位置信息在单元格内垂直排列，每个SKU之间有空行
    """
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'inventory_report_{timestamp}.xlsx'
    
    # 创建一个新的结果列表，每个SKU后面添加空行
    expanded_results = []
    for result in results:
        # 添加实际数据行
        expanded_results.append({
            'id': result['id'],
            'final_amount': result['final_amount'],
            'location_list': result['location_list']
        })
        # 添加三个空行
        for _ in range(3):
            expanded_results.append({
                'id': '',
                'final_amount': '',
                'location_list': ''
            })
    
    # 创建DataFrame
    df = pd.DataFrame(expanded_results)
    
    # 重命名列
    df = df.rename(columns={
        'id': 'id',
        'final_amount': 'final amount',
        'location_list': 'location list'
    })
    
    # 创建Excel写入器，使用openpyxl引擎
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
        
        # 获取工作表
        worksheet = writer.sheets['Sheet1']
        
        # 调整行高和列宽
        for idx, row in enumerate(worksheet.iter_rows(min_row=2)):  # 从第2行开始（跳过标题）
            # 调整包含位置列表的单元格
            location_cell = row[2]  # 第3列是位置列表
            if location_cell.value:
                # 计算需要的行高（基于换行符数量）
                num_lines = location_cell.value.count('\n') + 1
                worksheet.row_dimensions[idx + 2].height = 15 * num_lines  # 每行15个单位高度
        
        # 调整列宽
        for column in worksheet.columns:
            max_length = 0
            column = list(column)
            for cell in column:
                if cell.value:
                    # 对于位置列表，获取最长的单行长度
                    lines = str(cell.value).split('\n')
                    max_length = max(max_length, max(len(line) for line in lines))
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
            
            # 设置文本换行和对齐方式
            for cell in column:
                cell.alignment = openpyxl.styles.Alignment(wrap_text=True, vertical='top')
    
    print(f"\nReport has been exported to {filename}")

def main():
    sku_list = [
        "CW0026-NGS-1",
        "3C-05-BK",
        "HK0002QXJ",
        "D125452HDZN",
        "X003RT4T5J",
        "X003RT4T3V",
        "D125459J27O",
        "D125452TVNA",
        "D12545D3RDM",
        "Z6X-H7"
    ]


        
    results = get_inventory_info(sku_list)
    
    # 打印结果
    for result in results:
        output = f"""id: {result['id']}
final amount: {result['final_amount']}
location list: {result['location_list']}"""
        print("\n" + output)
    
    # 导出到Excel
    export_to_excel(results)

if __name__ == "__main__":
    main() 